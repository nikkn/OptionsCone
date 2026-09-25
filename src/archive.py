"""Archive of every downloaded option chain.

Each download is stored as a snapshot, so the history can be replayed later:
how a position aged, whether probabilities were borne out, what the surface
looked like before an earnings date. Option quotes cannot be downloaded again
after the fact.

Layout:

    archive/
      AAPL/
        2026-09-21T1618_chain.parquet     every contract, as captured
        2026-09-21T1618_meta.json         spot, rate, market state, quality
        _index.json                       one row per snapshot

Parquet when pyarrow is available, CSV otherwise.
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from paths import home as _home  # noqa: E402
ROOT = _home() / "archive"


def _dir(symbol):
    d = ROOT / symbol.upper()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stamp(ts=None):
    ts = ts or datetime.now()
    return ts.strftime("%Y-%m-%dT%H%M")


def save(symbol, chain, meta=None, ts=None):
    """Store one pull. Returns the index row that was written."""
    symbol = symbol.upper()
    d = _dir(symbol)
    stamp = _stamp(ts)

    body = d / f"{stamp}_chain.parquet"
    try:
        chain.to_parquet(body, index=False)
        fmt = "parquet"
    except Exception:
        body = d / f"{stamp}_chain.csv"
        chain.to_csv(body, index=False)
        fmt = "csv"

    row = {
        "symbol": symbol,
        "stamp": stamp,
        "captured": (ts or datetime.now()).isoformat(timespec="seconds"),
        "file": body.name,
        "format": fmt,
        "n_contracts": int(len(chain)),
        "n_clean": int(chain["soft_ok"].sum()) if "soft_ok" in chain else None,
        "spot": (float(chain["spot"].iloc[0]) if len(chain)
                 and "spot" in chain else None),
        "market_state": (str(chain["market_state"].iloc[0])
                         if len(chain) and "market_state" in chain else None),
        "expiries": (sorted(str(x) for x in chain["expiry"].unique())
                     if "expiry" in chain else []),
    }
    if meta:
        row["meta"] = meta
    (d / f"{stamp}_meta.json").write_text(
        json.dumps({**row, **(meta or {})}, indent=1, default=str),
        encoding="utf-8")

    idx = index(symbol)
    idx = [r for r in idx if r.get("stamp") != stamp] + [row]
    idx.sort(key=lambda r: r["stamp"])
    (d / "_index.json").write_text(json.dumps(idx, indent=1, default=str),
                                   encoding="utf-8")
    return row


def index(symbol):
    """Every snapshot held for one symbol, oldest first."""
    f = _dir(symbol) / "_index.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def symbols():
    """Symbols with at least one snapshot, and what is held for each."""
    if not ROOT.exists():
        return []
    out = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        idx = index(d.name)
        if not idx:
            continue
        last = idx[-1]
        out.append({"symbol": d.name, "n": len(idx),
                    "first": idx[0]["captured"], "last": last["captured"],
                    "spot": last.get("spot"),
                    "state": last.get("market_state")})
    return out


def load(symbol, stamp=None, prefer_state=None):
    """One snapshot as a DataFrame; the latest when no stamp is given.

    prefer_state selects the newest snapshot taken in that market state.
    Snapshots taken outside trading hours have no usable quotes, so the chart
    asks for the newest one taken while the market was open. Falls back to the
    latest snapshot if none matches.
    """
    if stamp is None:
        row = pick(symbol, prefer_state)
    else:
        row = next((r for r in index(symbol) if r["stamp"] == stamp), None)
    if not row:
        return None
    f = _dir(symbol) / row["file"]
    if not f.exists():
        return None
    return (pd.read_parquet(f) if row.get("format") == "parquet"
            else pd.read_csv(f))


def state_of(row):
    """Market state recorded with a snapshot's index row."""
    return str(row.get("state") or row.get("market_state"))


def pick(symbol, prefer_state=None):
    """Index row of the snapshot load() returns when no stamp is given: the
    newest one taken in prefer_state, else the newest one."""
    idx = index(symbol)
    if not idx:
        return None
    if prefer_state:
        want = [r for r in idx if state_of(r) == prefer_state]
        if want:
            return want[-1]
    return idx[-1]


def history(symbol, expiry=None, strike=None, option_type=None):
    """One contract, or one expiry, across every snapshot held."""
    rows = []
    for r in index(symbol):
        df = load(symbol, r["stamp"])
        if df is None or not len(df):
            continue
        m = df
        if expiry is not None:
            m = m[m["expiry"].astype(str) == str(expiry)]
        if strike is not None:
            m = m[m["strike"] == float(strike)]
        if option_type is not None:
            m = m[m["type"] == option_type]
        if not len(m):
            continue
        m = m.copy()
        m["captured"] = r["captured"]
        m["stamp"] = r["stamp"]
        rows.append(m)
    return pd.concat(rows, ignore_index=True) if rows else None
