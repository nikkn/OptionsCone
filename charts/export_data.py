"""Export price history and the touch-probability surface per ticker.

Rows are real strike prices and columns real expiry dates on the candles'
calendar scale.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from barrier import prob_touch_down, prob_touch_up
from american import prob_below_at_expiry
from varswap import variance_one_expiry
from dataquality import report as dq_report
from realized import realized
from earnings import earnings, past_earnings
from montecarlo import (_log_bars, basis_run, hit_rates_at, TRADING_DAYS)
from optionev import usable_ivs

SYMBOLS = sys.argv[1:] or ["AAPL"]
# The archive is the source, so tickers captured at different times can be
# exported together.
from archive import (load as archive_load, index as archive_index,  # noqa: E402
                     pick as archive_pick, state_of)

# Use the newest pull taken while the market was open; pulls from outside
# trading hours have no usable quotes.
_frames = []
for _s in SYMBOLS:
    _df = archive_load(_s, prefer_state="REGULAR")
    if _df is None:
        print(f"{_s}: nothing archived, skipped")
        continue
    _rows = archive_index(_s)
    _st = str(_df["market_state"].iloc[0]) if "market_state" in _df else "?"
    _stamp = str(_df["asof"].iloc[0])[:16] if "asof" in _df else _rows[-1]["stamp"]
    _note = "" if _st == "REGULAR" else f"  !! no open-market pull held ({_st})"
    print(f"{_s}: pull {_stamp}  {_st}  {len(_df)} contracts{_note}")
    _frames.append(_df)
if not _frames:
    raise SystemExit("archive holds none of the requested symbols")
ch = pd.concat(_frames, ignore_index=True)

# Strike ladder. Each wing reaches as far as the listed strikes keep a touch
# probability above P_FLOOR, so the cone widens with maturity, within fixed
# moneyness caps.
P_FLOOR = 0.10  # stop a wing where a touch becomes this unlikely
MONEY_LO_CAP = 0.55  # put wing never reaches further than this
MONEY_HI_CAP = 2.00  # call wing never reaches further than this
# Upper bound on the probability grid's rows. High enough that a normal chain
# passes whole; strikes missing from the ladder are not exported.
MAX_ROWS = 400



# Checks that decide whether a contract's own volatility can be used: the ones
# about the price (spread, penny bid, parity, forward consistency). Thin open
# interest does not make a quote unreadable.
_IV_CHECKS = ["soft_tight_spread", "soft_not_penny_bid",
              "soft_parity_ok", "soft_fwd_consistent"]


def iv_usable(frame):
    """Rows whose quote can be inverted, ignoring how thinly they trade."""
    if not len(frame):
        return frame
    m = np.ones(len(frame), dtype=bool)
    for c in _IV_CHECKS:
        if c in frame.columns:
            m &= frame[c].to_numpy(dtype=bool)
    return frame[m]


def call_ceiling(g, spot, T):
    """Highest call strike whose touch probability still clears P_FLOOR.

    Mirrors put_floor, so the reach follows volatility rather than a constant.
    """
    ca = g[g["type"] == "C"]
    if not len(ca):
        return spot * 1.22
    pool = ca[ca["soft_ok"]] if len(ca[ca["soft_ok"]]) else ca
    ks = sorted(float(k) for k in ca["strike"].unique() if k > spot)
    highest = spot
    for k in ks:
        row = pool.iloc[(pool["strike"] - k).abs().argsort()[:1]]
        iv = float(row["iv"].iloc[0])
        if float(prob_touch_up(spot, k, T, iv)) < P_FLOOR:
            break
        highest = k
    return min(highest, spot * MONEY_HI_CAP)


def put_floor(g, spot, T):
    """Lowest put strike whose touch probability still clears P_FLOOR, using
    each listed strike's own implied volatility.
    """
    pu = g[g["type"] == "P"]
    if not len(pu):
        return spot * 0.75
    pool = pu[pu["soft_ok"]] if len(pu[pu["soft_ok"]]) else pu
    ks = sorted(float(k) for k in pu["strike"].unique() if k < spot)
    lowest = spot
    for k in reversed(ks):                      # walk down from the money
        row = pool.iloc[(pool["strike"] - k).abs().argsort()[:1]]
        iv = float(row["iv"].iloc[0])
        if float(prob_touch_down(spot, k, T, iv)) < P_FLOOR:
            break
        lowest = k
    return max(lowest, spot * MONEY_LO_CAP)


def ladder(strikes, spot, lo, hi):
    ks = sorted({float(k) for k in strikes if lo <= k <= hi})
    if not ks:
        return []
    if len(ks) <= MAX_ROWS:
        return ks
    atm = min(ks, key=lambda k: abs(k - spot))
    stride = int(np.ceil(len(ks) / MAX_ROWS))
    i = ks.index(atm)
    out = {atm}
    for d in range(1, len(ks)):
        for j in (i - d * stride, i + d * stride):
            if 0 <= j < len(ks):
                out.add(ks[j])
        if len(out) >= MAX_ROWS:
            break
    return sorted(out)


out = {}
for sym in SYMBOLS:
    s = ch[ch["symbol"] == sym]
    if s.empty:
        print(f"{sym}: not in chain, skipped")
        continue
    spot = float(s["spot"].iloc[0])

    h = yf.Ticker(sym).history(period="11y", auto_adjust=False)
    h.index = pd.to_datetime(h.index).tz_localize(None)
    d = h
    # The chart shows the full ten years. Weekly bars are resampled here.
    hist = h.tail(2520)
    ohlc = [{"t": d.strftime("%Y-%m-%d"), "o": round(r.Open, 2),
             "h": round(r.High, 2), "l": round(r.Low, 2),
             "c": round(r.Close, 2)} for d, r in hist.iterrows()]
    wk = hist.resample("W-FRI").agg({"Open": "first", "High": "max",
                                     "Low": "min", "Close": "last"}).dropna()
    ohlcw = [{"t": d.strftime("%Y-%m-%d"), "o": round(r.Open, 2),
              "h": round(r.High, 2), "l": round(r.Low, 2),
              "c": round(r.Close, 2)} for d, r in wk.iterrows()]

    # Bootstrap models: five and ten years of history, drift kept. Each is one
    # run to the longest expiry, read off at every shorter one, so the
    # probabilities cannot fall with maturity.
    #
    # 10,000 paths: the counting noise (about 0.4 points near 27%) is far below
    # the uncertainty from which years happen to be sampled.
    N_PATHS, BLOCK = 10000, 20
    # With daily highs and lows a touch is observed on the simulated intraday
    # range rather than inferred between closes.
    rets = {"5": _log_bars(h.tail(1260)), "10": _log_bars(h.tail(2520))}

    max_dte = int(s["dte"].max())
    max_nd = max(2, int(round(max_dte * TRADING_DAYS / 365.0)))
    BASIS = {}
    for win, rr in rets.items():
        # Only the drift-kept runs are shown, so only those are computed.
        for dtag, dm in (("drift", False),):
            try:
                _ret, _hi, _lo = rr
                BASIS[f"{win}_{dtag}"] = basis_run(
                    spot, _ret, max_nd, N_PATHS, BLOCK, seed=7, demean=dm,
                    bars=(_hi, _lo))
            except Exception:
                BASIS[f"{win}_{dtag}"] = None

    tk = yf.Ticker(sym)
    # The bound comes from the longest expiry, which reaches furthest; every
    # column uses the same ladder so rows line up.
    last = s[s["expiry"] == sorted(s["expiry"].unique())[-1]]
    lo_k = put_floor(last, spot, float(last["T"].iloc[0]))
    hi_k = call_ceiling(last, spot, float(last["T"].iloc[0]))
    rows = ladder(s["strike"], spot, lo_k, hi_k)
    expiries = []
    _all_exp = sorted(s["expiry"].unique())
    for _ei, exp in enumerate(_all_exp, 1):
        # One line per expiry, forwarded to the app's status bar.
        print(f"{sym}: expiry {_ei}/{len(_all_exp)}  {exp}", flush=True)
        g = s[s["expiry"] == exp]
        T = float(g["T"].iloc[0])
        clean = g[g["soft_ok"]]
        atm_src = clean if len(clean) else g
        near = atm_src.iloc[(atm_src["moneyness"] - 1).abs().argsort()[:3]]
        atm_iv = float(near["iv"].mean())

        # Model-free variance needs the whole surface including the far wings,
        # so a live chain is preferred; outside trading hours it falls back to
        # the stored snapshot.
        mf = None
        try:
            raw = tk.option_chain(str(exp))
            mf = variance_one_expiry(raw.calls[["strike", "bid", "ask"]],
                                     raw.puts[["strike", "bid", "ask"]],
                                     T, float(s["r"].iloc[0]), spot=spot)
        except Exception:
            pass
        if mf is None:
            try:
                mf = variance_one_expiry(
                    g[g["type"] == "C"][["strike", "bid", "ask"]],
                    g[g["type"] == "P"][["strike", "bid", "ask"]],
                    T, float(s["r"].iloc[0]), spot=spot)
            except Exception:
                pass

        nd = max(2, int(round(g["dte"].iloc[0] * TRADING_DAYS / 365.0)))

        qc = {}
        for side_is_call in (True, False):
            side_f = g[g["type"] == ("C" if side_is_call else "P")]
            _, n_tot, n_ok = usable_ivs(side_f)
            qc["C" if side_is_call else "P"] = [n_tot, n_ok]

        cells = []
        for K in rows:
            up = K > spot
            # Calls above spot, puts below.
            side = g[g["type"] == ("C" if up else "P")]
            # Skip ladder rows this expiry does not list.
            _listed = side[np.isclose(side["strike"], K)]
            # Unlisted strikes still get a probability, so the field stays
            # continuous between expiries that list different ranges.
            # `synthetic` marks such cells: no contract, quote, dot or tooltip.
            # Their volatility is the nearest listed strike's.
            _synth = not len(_listed)
            _ok = iv_usable(side)
            pool = _ok if len(_ok) else side
            if len(pool):
                row = pool.iloc[(pool["strike"] - K).abs().argsort()[:1]]
                iv = float(row["iv"].iloc[0])
                exact = bool(abs(float(row["strike"].iloc[0]) - K) < 1e-9)
                warn = int(row["n_warnings"].iloc[0])
            else:
                iv, exact, warn = atm_iv, False, 9
            f = prob_touch_up if up else prob_touch_down
            # Risk-neutral log drift, the same as in N(d2) below: r -
            # sigma^2/2.
            mu_rn = float(s["r"].iloc[0]) - 0.5 * iv * iv
            # Terminal probability N(d2). Not delta: delta is N(d1), and the
            # two differ more as volatility times root-time grows.
            below = prob_below_at_expiry(spot, K, T,
                                         float(s["r"].iloc[0]), iv)
            # Touch and terminal from the same paths; the final close is
            # observed exactly, so the terminal rate needs no bridge
            # correction.
            mc, mce = {}, {}
            for tag, paths in BASIS.items():
                if paths is None:
                    mc[tag] = mce[tag] = None
                    continue
                hr = hit_rates_at(paths, spot, K, nd, up)
                mc[tag] = round(hr["touch_continuous"], 4)
                mce[tag] = round(hr["terminal"], 4)
            mkt = None
            if len(pool):
                mrow = pool.iloc[(pool["strike"] - K).abs().argsort()[:1]]
                if abs(float(mrow["strike"].iloc[0]) - K) < 1e-9:
                    mkt = float(mrow["mid"].iloc[0])


            # Per-contract fields for the IV, open-interest and spread maps.
            # Taken from the contract at exactly this strike, including
            # contracts whose quote failed the checks: open interest is not a
            # quote.
            _row = None
            if len(side):
                _cand = side.iloc[(side["strike"] - K).abs().argsort()[:1]]
                if abs(float(_cand["strike"].iloc[0]) - K) < 1e-9:
                    _row = _cand
            _oi = float(_row["open_interest"].iloc[0]) if _row is not None else None
            _sp = float(_row["spread_pct"].iloc[0]) if _row is not None else None
            # Spread in dollars as well as per cent; bid and ask for the
            # tooltip.
            _bd = float(_row["bid"].iloc[0]) if _row is not None else None
            _ak = float(_row["ask"].iloc[0]) if _row is not None else None
            _sa = (None if _bd is None or _ak is None
                   or not (np.isfinite(_bd) and np.isfinite(_ak))
                   else round(_ak - _bd, 4))
            _vol = float(_row["volume"].iloc[0]) if _row is not None else None
            # The contract's own delta and gamma from the American tree, for
            # comparing with a broker. Calls above spot, puts below.
            _dl = (float(_row["delta"].iloc[0])
                   if _row is not None and "delta" in _row else None)
            _gm = (float(_row["gamma"].iloc[0])
                   if _row is not None and "gamma" in _row else None)
            if _synth:
                cells.append({"k": round(K, 2), "synthetic": True,
                              # The volatility used for this cell's
                              # probability. The IV map needs it to bridge
                              # between expiries; open interest and spread are
                              # left out because no contract exists here.
                              "iv": round(float(iv), 4),
                              "p": round(float(f(spot, K, T, iv, mu_rn)), 4),
                              "pexp": round(float(1.0 - below if up else below), 4),
                              "pct": round((K / spot - 1) * 100, 1),
                              "up": bool(up),
                              "mc5d": mc.get("5_drift"),
                              "mc10d": mc.get("10_drift"),
                              "mc5dexp": mce.get("5_drift"),
                              "mc10dexp": mce.get("10_drift")})
                continue
            cells.append({"k": round(K, 2), "mid": mkt,
                          "oi": (None if _oi is None else round(_oi)),
                          "delta": (None if _dl is None or not np.isfinite(_dl)
                                    else round(_dl, 4)),
                          "gamma": (None if _gm is None or not np.isfinite(_gm)
                                    else round(_gm, 6)),
                          "vol": (None if _vol is None or not np.isfinite(_vol)
                                  else round(_vol)),
                          "bid": (None if _bd is None or not np.isfinite(_bd)
                                  else round(_bd, 2)),
                          "ask": (None if _ak is None or not np.isfinite(_ak)
                                  else round(_ak, 2)),
                          "sprusd": _sa,
                          "spr": (None if _sp is None or not np.isfinite(_sp)
                                  else round(float(_sp), 4)),
                          "mc5d": mc.get("5_drift"),
                          "mc10d": mc.get("10_drift"),
                          "mc5dexp": mce.get("5_drift"),
                          "mc10dexp": mce.get("10_drift"),
                          "pct": round((K / spot - 1) * 100, 1),
                          "iv": round(iv, 4),
                          "p": round(float(f(spot, K, T, iv, mu_rn)), 4),
                          "pexp": round(float(1.0 - below if up else below), 4),
                          "up": up, "exact": exact, "warn": warn})
        expiries.append({"expiry": str(exp), "dte": int(g["dte"].iloc[0]),
                         "qc_c": qc.get("C"), "qc_p": qc.get("P"),
                         "atm_iv": round(atm_iv, 4), "n": int(len(g)),
                         "mf_iv": round(mf["sigma"], 4) if mf else None,
                         "mf_n": mf["n_strikes"] if mf else 0,
                         "mf_lo": round(mf["k_min"], 1) if mf else None,
                         "mf_hi": round(mf["k_max"], 1) if mf else None,
                         "mf_f": round(mf["F"], 2) if mf else None,
                         "clean_pct": round(float(g["soft_ok"].mean() * 100), 1),
                         "cells": cells})

    # Trailing realized volatility on the calendar-day convention of the option
    # maturities.
    end = pd.Timestamp(max(h.index))
    HL = 42.0                      # six-week half-life
    rv = {"ewma": realized(h, end, 365, "ewma", HL),
          "30": realized(h, end, 30, "cc"),
          "90": realized(h, end, 90, "cc")}
    rv30 = rv["ewma"]
    for e in expiries:
        iv = e.get("mf_iv") or e["atm_iv"]
        e["ivrv"] = (round(iv / rv30["sigma"], 3)
                     if rv30["sigma"] and np.isfinite(rv30["sigma"]) else None)
    got = [(e["dte"], e["ivrv"]) for e in expiries if e["ivrv"]]
    slope = (float(np.polyfit([g[0] for g in got], [g[1] for g in got], 1)[0] * 100)
             if len(got) >= 2 else None)

    # No usable strikes: skip the symbol rather than export an empty surface.
    if not rows or not expiries:
        print(f"{sym}: no usable strikes survived the quality gate "
              f"({len(s)} contracts, state {s['market_state'].iloc[0]}) "
              f"(skipped)")
        continue

    last_exp = pd.Timestamp(expiries[-1]["expiry"]) if expiries else end
    ern = [{"d": e["date"].strftime("%Y-%m-%d"),
            "confirmed": e["confirmed"], "when": e["when"]}
           for e in earnings(tk, last_exp, end)]
    ern += [{"d": x.strftime("%Y-%m-%d"), "confirmed": True, "when": None,
             "past": True}
            for x in past_earnings(tk, pd.Timestamp(ohlc[0]["t"]), end)]

    out[sym] = {"spot": spot, "ohlc": ohlc, "ohlcw": ohlcw, "earnings": ern,
                "rv": {k: {kk: (round(vv, 4) if isinstance(vv, float)
                               and np.isfinite(vv) else vv)
                           for kk, vv in val.items()} for k, val in rv.items()},
                "ivrv_slope": round(slope, 4) if slope is not None else None,
                "rv_method": "ewma-cc", "rv_half_life": HL, "rows": [round(k, 2) for k in rows],
                "expiries": expiries, "state": str(s["market_state"].iloc[0]),
                "asof": str(s["asof"].iloc[0]), "r": float(s["r"].iloc[0]),
                "clean_pct": round(float(s["soft_ok"].mean() * 100), 1),
                "n": int(len(s)),
                "n_clean": int(s["soft_ok"].sum()),
                "dq": dq_report(s, sym)}
    print(f"{sym}: spot {spot:.2f}  bars {len(ohlc)}  rows {len(rows)}  "
          f"expiries {len(expiries)}  strikes {rows[0]:.0f}-{rows[-1]:.0f}  "
          f"({rows[0]/spot:.2f}-{rows[-1]/spot:.2f})  put floor from "
          f"P>={P_FLOOR:.0%}")

# Provenance: the pull the chart rests on, the newest pull held (which differs
# when later pulls were taken outside trading hours), and how many are held.
for _s in out:
    _idx = archive_index(_s)
    _used = archive_pick(_s, prefer_state="REGULAR")
    if _idx and _used:
        out[_s]["archive"] = {"stamp": _used["stamp"],
                              "captured": _used["captured"],
                              "n_pulls": len(_idx),
                              "latest": _idx[-1]["captured"],
                              "latest_state": state_of(_idx[-1])}

# One file per ticker; the combined file for the all-in-one page is rebuilt
# from all of them.
from tickerfiles import (write_ticker, write_index, write_combined,  # noqa: E402
                         migrate_from_combined)
# Exports made before per-ticker files existed live only in the combined file;
# split it first so no ticker is lost.
migrate_from_combined()
for _s, _obj in out.items():
    write_ticker(_s, _obj)
write_index()
_all = write_combined()
print(f"-> {len(out)} exported, {len(_all)} held")
