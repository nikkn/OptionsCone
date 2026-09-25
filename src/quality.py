"""Quote quality checks, split into hard filters and soft warnings.

Hard checks reject impossible data (a crossed market, a price below intrinsic
value); such rows never reach the model. Soft checks flag doubtful quotes (a
wide spread, a parity or forward inconsistency) and are reported, not filtered.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Thresholds

HARD = {
    "min_price": 0.01,      # below this the tick grid dominates the price
    "max_iv": 3.00,  # 300%, beyond any plausible equity volatility
    "min_iv": 0.01,
}

SOFT = {
    "min_bid": 0.01,          # a bid at or below this is a tick-grid artefact
    "max_spread_pct": 0.25,   # the quote width, as a fraction of the mid
    "min_open_interest": 50,  # a floor, relaxed per chain (see below)
    "max_fwd_dev_pct": 0.02,  # |implied fwd / median fwd - 1|
    "max_parity_err_mult": 1.0,   # parity error in units of the half-spread
}


# Hard checks

def hard_checks(df, spot_col="spot"):
    """Flag rows that are impossible rather than merely poor.

    Returns the frame with boolean `hard_*` columns and a combined `hard_ok`.
    """
    d = df.copy()
    S = d[spot_col]

    d["hard_two_sided"] = (d["bid"] > 0) & (d["ask"] > 0)
    d["hard_not_crossed"] = d["ask"] >= d["bid"]
    d["hard_priceable"] = d["mid"] >= HARD["min_price"]

    # Intrinsic value is a floor: an American option can be exercised at once.
    intrinsic = np.where(d["type"].eq("C"), S - d["strike"], d["strike"] - S)
    intrinsic = np.maximum(intrinsic, 0.0)
    d["hard_above_intrinsic"] = d["ask"] >= intrinsic - 1e-9

    # A call cannot be worth more than the stock; a put more than its strike.
    cap = np.where(d["type"].eq("C"), S, d["strike"])
    d["hard_below_cap"] = d["mid"] <= cap + 1e-9

    if "iv" in d:
        d["hard_iv_sane"] = d["iv"].between(HARD["min_iv"], HARD["max_iv"])
    else:
        d["hard_iv_sane"] = True

    cols = [c for c in d.columns if c.startswith("hard_")]
    d["hard_ok"] = d[cols].all(axis=1)
    return d


# Soft checks

def implied_forward(df, r):
    """Per-strike forward from put-call parity: F = (C - P) + K*exp(-rT).

    A consistent chain implies one forward per expiry, so its spread across
    strikes measures coherence without needing a spot price or dividends.
    """
    out = []
    for (sym, exp), g in df.groupby(["symbol", "expiry"], sort=False):
        c = g[g["type"] == "C"][["strike", "mid", "bid", "ask"]]
        p = g[g["type"] == "P"][["strike", "mid", "bid", "ask"]]
        m = c.merge(p, on="strike", suffixes=("_c", "_p"))
        if m.empty:
            continue
        T = float(g["T"].iloc[0])
        m["fwd"] = (m["mid_c"] - m["mid_p"]) + m["strike"] * np.exp(-r * T)
        m["half_spread"] = ((m["ask_c"] - m["bid_c"])
                            + (m["ask_p"] - m["bid_p"])) / 2.0
        m["symbol"], m["expiry"] = sym, exp
        out.append(m)
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


def soft_checks(df, r, spot_col="spot"):
    """Attach reliability warnings. Never drops a row."""
    d = df.copy()

    # A one-tick bid is not a price; the mid is an artefact of the tick grid.
    d["soft_not_penny_bid"] = d["bid"] > SOFT["min_bid"]
    # Spread as a fraction of the mid. A locked quote (bid equal to ask) is not
    # a real two-sided market and also fails.
    d["soft_tight_spread"] = ((d["spread_pct"] <= SOFT["max_spread_pct"])
                              & (d["spread"] > 0))
    # Open interest is judged relative to the chain, with an absolute floor
    # only as a backstop; a fixed floor would reject whole chains of tightly
    # quoted but small-size instruments.
    _oi = d["open_interest"]
    _rel = max(5.0, float(_oi.median()) * 0.10) if len(_oi) else 5.0
    d["soft_liquid"] = _oi >= min(SOFT["min_open_interest"], _rel)

    # Forward consistency per expiry, against the median forward, so a few bad
    # strikes cannot move the reference.
    fwd = implied_forward(d, r)
    d["soft_fwd_consistent"] = True
    d["fwd_dev"] = np.nan
    d["parity_err"] = np.nan
    if not fwd.empty:
        for (sym, exp), g in fwd.groupby(["symbol", "expiry"], sort=False):
            ref = g["fwd"].median()
            if not np.isfinite(ref) or ref <= 0:
                continue
            dev = (g["fwd"] / ref - 1.0).abs()
            bad = set(g.loc[dev > SOFT["max_fwd_dev_pct"], "strike"])
            key = (d["symbol"].eq(sym) & d["expiry"].eq(exp))
            d.loc[key & d["strike"].isin(bad), "soft_fwd_consistent"] = False
            dev_map = dict(zip(g["strike"], dev))
            d.loc[key, "fwd_dev"] = d.loc[key, "strike"].map(dev_map)

            # Parity error relative to the pair's half-spread.
            #
            # The error is attributed to the in-the-money leg only. That leg is
            # usually stale and thinly traded, and it is never used; charging
            # the error to both legs would condemn a liquid out-of-the-money
            # contract.
            perr = (g["fwd"] - ref).abs()
            tol = g["half_spread"] * SOFT["max_parity_err_mult"]
            pe = dict(zip(g["strike"], perr / tol.replace(0, np.nan)))
            spot_ref = float(d.loc[key, "spot"].iloc[0])
            itm = key & (((d["type"] == "P") & (d["strike"] > spot_ref))
                         | ((d["type"] == "C") & (d["strike"] < spot_ref)))
            d.loc[itm, "parity_err"] = d.loc[itm, "strike"].map(pe)

    d["soft_parity_ok"] = ~(d["parity_err"] > 1.0)  # NaN-safe: unpaired passes

    cols = [c for c in d.columns if c.startswith("soft_")]
    d["soft_ok"] = d[cols].all(axis=1)
    # n_warnings counts quote problems only. Thin open interest is recorded
    # separately in `thin`; it does not make a quote unreadable.
    _quote = [c for c in cols if c not in ("soft_ok", "soft_liquid")]
    d["n_warnings"] = (~d[_quote]).sum(axis=1)
    d["thin"] = ~d["soft_liquid"] if "soft_liquid" in d else False
    return d


def apply_checks(df, r, spot_col="spot"):
    """Run both layers. Hard failures are dropped; soft ones are annotated."""
    d = hard_checks(df, spot_col)
    n_hard = int((~d["hard_ok"]).sum())
    d = d[d["hard_ok"]].copy()
    d = soft_checks(d, r, spot_col)
    return d, n_hard


def report(df, n_hard_dropped=0):
    """Human-readable reliability summary for an analysis header."""
    lines = [f"rows dropped by hard checks : {n_hard_dropped}",
             f"rows retained               : {len(df)}"]
    if len(df) == 0:
        return "\n".join(lines)
    soft_cols = [c for c in df.columns if c.startswith("soft_") and c != "soft_ok"]
    for c in sorted(soft_cols):
        n = int((~df[c]).sum())
        lines.append(f"  warning {c[5:]:18s}: {n:4d} rows ({n / len(df):5.1%})")
    clean = int(df["soft_ok"].sum())
    lines.append(f"rows with no warnings       : {clean} ({clean / len(df):.1%})")
    return "\n".join(lines)
