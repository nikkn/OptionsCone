"""Download an option chain and attach American implied volatility, Greeks and
touch probabilities.

All filtering is done by quality.hard_checks, so the reported drop counts are
complete. The moneyness window only sets the scope of the download.
"""
from __future__ import annotations

import os
import sys
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent))
from american import DAYS, greeks, implied_vol, prob_below_at_expiry
from barrier import prob_touch_down
from dividends import infer_schedule
from expiries import all_monthlies, select as select_expiries
from archive import save as archive_save
from dataquality import format_report, report as dq_report
from quality import apply_checks, hard_checks, report


def risk_free_rate(default=0.04):
    """13-week T-bill from ^IRX, quoted in percent."""
    try:
        s = yf.download("^IRX", period="1mo", progress=False,
                        auto_adjust=False)["Close"].dropna()
        if len(s):
            return float(np.ravel(s.iloc[-1])[0]) / 100.0
    except Exception:
        pass
    return default


def _spot(ticker):
    h = ticker.history(period="5d")["Close"].dropna()
    if len(h) == 0:
        raise RuntimeError("no spot price")
    return float(h.iloc[-1])


def market_state(ticker):
    """Yahoo's market state, recorded with every pull.

    Quotes taken outside regular trading hours are placeholders, so spread and
    parity statistics from such a snapshot describe a closed market.
    """
    try:
        return ticker.info.get("marketState", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def _raw_rows(tk, symbol, S, exps, divs_abs, today, moneyness, verbose,
              put_moneyness=None):
    """Every contract in the requested expiries, unfiltered except for
    moneyness.

    Puts and calls get separate windows. They only need to be wide enough; the
    probability floor in the export decides where the strike ladder ends.
    """
    rows = []
    for exp in exps:
        before = len(rows)
        exp_ts = pd.Timestamp(exp)
        dte = (exp_ts - today).days
        if dte <= 0:
            continue
        T = dte / DAYS
        divs = [(((d - today).days / DAYS), a) for d, a in divs_abs
                if today < d <= exp_ts]
        try:
            ch = tk.option_chain(exp)
        except Exception as e:
            if verbose:
                print(f"  {exp}: fetch failed ({e})")
            continue

        for side, df in (("C", ch.calls), ("P", ch.puts)):
            if df is None or len(df) == 0:
                continue
            d = df.copy()
            win = (put_moneyness or moneyness) if side == "P" else moneyness
            d = d[(d["strike"] >= S * win[0]) & (d["strike"] <= S * win[1])]
            for t in d.itertuples():
                bid, ask = float(t.bid), float(t.ask)
                mid = (bid + ask) / 2.0
                rows.append({
                    "symbol": symbol, "asof": today.date(),
                    "expiry": exp_ts.date(), "T": T, "dte": dte,
                    "type": side, "strike": float(t.strike), "spot": S,
                    "moneyness": float(t.strike) / S,
                    "bid": bid, "ask": ask, "mid": mid,
                    "spread": ask - bid,
                    "spread_pct": (ask - bid) / mid if mid > 0 else np.inf,
                    "open_interest": float(t.openInterest or 0),
                    "volume": float(t.volume) if pd.notna(t.volume) else 0.0,
                    "iv_yahoo": float(t.impliedVolatility),
                    "divs": divs,
                })
        if verbose:
            print(f"  {exp}  dte={dte:4d}  raw_rows={len(rows) - before}")
    return pd.DataFrame(rows)


_CARRY = ("symbol", "asof", "expiry", "T", "dte", "type", "strike", "spot",
          "moneyness", "bid", "ask", "mid", "spread", "spread_pct",
          "open_interest", "volume", "iv_yahoo")


def _solve_rows(rows, S, r, steps, mu):
    """Implied volatility, Greeks and probabilities for a batch of contracts.

    Module level so that worker processes can run it.
    """
    out = []
    for t in rows:
        is_call = t["type"] == "C"
        iv = implied_vol(t["mid"], S, t["strike"], t["T"], r, is_call,
                         t["divs"], steps)
        if iv is None:
            continue
        g = greeks(S, t["strike"], t["T"], r, iv, is_call, t["divs"], steps)
        out.append({
            **{k: t[k] for k in _CARRY},
            "iv": iv, "delta": g["delta"], "gamma": g["gamma"],
            "model_price": g["price"],
            "p_below_expiry": prob_below_at_expiry(S, t["strike"], t["T"], r, iv),
            "p_touch": float(prob_touch_down(S, t["strike"], t["T"], iv, mu)),
        })
    return out


# Solves run on all but one CPU core; each contract is a binomial tree solved
# by root finding (about 25 ms). The pool is created once and reused. Small
# chains stay serial because starting workers costs more than it saves.
# OPTIONSCONE_SERIAL=1 forces serial.
PARALLEL_MIN = 150
_POOL = None
# Called as PROGRESS(done, total) during the solves, for the app's progress
# bar.
PROGRESS = None


def _pool():
    global _POOL
    if _POOL is None:
        import atexit
        from concurrent.futures import ProcessPoolExecutor
        n = max(1, min((os.cpu_count() or 2) - 1, 15))
        _POOL = ProcessPoolExecutor(max_workers=n)
        atexit.register(_POOL.shutdown, wait=False, cancel_futures=True)
    return _POOL


def _solve(rows, S, r, steps, mu):
    """All contracts, in their original order, in parallel where it pays."""
    if len(rows) < PARALLEL_MIN or os.environ.get("OPTIONSCONE_SERIAL") == "1":
        out = _solve_rows(rows, S, r, steps, mu)
        if PROGRESS:
            PROGRESS(1, 1)
        return out
    try:
        pool = _pool()
        # Contiguous batches, several per worker for load balance. map() keeps
        # the order, so the result equals a serial solve.
        k = pool._max_workers * 4
        size = max(1, -(-len(rows) // k))
        batches = [rows[i:i + size] for i in range(0, len(rows), size)]
        out = []
        for i, part in enumerate(pool.map(
                partial(_solve_rows, S=S, r=r, steps=steps, mu=mu), batches), 1):
            out.extend(part)
            if PROGRESS:
                PROGRESS(i, len(batches))
        return out
    except Exception as e:
        print(f"  parallel solve unavailable ({e}); solving serially")
        return _solve_rows(rows, S, r, steps, mu)


# Contracts excluded before anything is drawn.
#
# MIN_DTE: near expiry an option is almost all intrinsic, vega is close to
# zero, and the implied volatility mostly reflects the price tick.
#
# MIN_ABS_DELTA: far out-of-the-money quotes of a few cents give the same kind
# of noise, and a single one can stretch the colour scale of the whole chain.
MIN_DTE = 10
MIN_ABS_DELTA = 0.05


def enrich(symbol, expiries=None, max_days=180, targets=None, r=None,
           weeklies=False,
           steps=160, moneyness=(0.55, 2.60), put_moneyness=(0.35, 1.30),
           today=None, monthly_only=True, mu=0.0, verbose=True,
           archive=True, min_dte=MIN_DTE, min_abs_delta=MIN_ABS_DELTA):
    """Download, hard-filter, price and annotate one symbol's chain.

    Hard checks run on the raw quotes first so nothing impossible reaches the
    solver; then implied volatility and Greeks are computed; then the
    volatility-dependent hard check and the soft warnings are applied.
    """
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    r = risk_free_rate() if r is None else r
    tk = yf.Ticker(symbol)
    S = _spot(tk)
    state = market_state(tk)

    available = list(tk.options)
    if not available:
        raise RuntimeError(f"{symbol}: no option expiries")
    if expiries:
        exps = [e for e in available if e in set(expiries)]
    elif targets:
        exps = [e for _, e, _ in
                select_expiries(available, targets, today, monthly_only)]
    else:
        # Default: every monthly expiry inside the horizon.
        exps = [e for e, _ in all_monthlies(available, max_days, today=today,
                                            weeklies=weeklies)]
    # Drop near expiries before downloading them.
    if min_dte:
        _t0 = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
        _keep = [e for e in exps
                 if (pd.Timestamp(e) - _t0.normalize()).days >= min_dte]
        if _keep:
            exps = _keep
    if not exps:
        raise RuntimeError(f"{symbol}: no expiries matched")

    divs_abs = infer_schedule(tk, pd.Timestamp(max(exps)), today=today)
    if verbose:
        print(f"{symbol}: S={S:.2f} r={r:.4f} state={state} "
              f"expiries={len(exps)} projected_divs={len(divs_abs)}")

    raw = _raw_rows(tk, symbol, S, exps, divs_abs, today, moneyness,
                    verbose, put_moneyness)
    if raw.empty:
        return raw
    n_raw = len(raw)

    # Hard layer, pass 1: quote-only checks, before anything is solved.
    h = hard_checks(raw.drop(columns=["divs"]))
    keep = h["hard_ok"].values
    n_hard_quote = int((~keep).sum())
    work = raw[keep].copy()

    rows = work[list(_CARRY) + ["divs"]].to_dict("records")
    solved = _solve(rows, S, r, steps, mu)
    n_unsolved = len(work) - len(solved)
    if not solved:
        return pd.DataFrame()

    df = pd.DataFrame(solved)
    n_thin = 0
    if min_abs_delta:
        _keep = df["delta"].abs() >= min_abs_delta
        n_thin = int((~_keep).sum())
        df = df[_keep].copy()
        if not len(df):
            return pd.DataFrame()
    # Hard layer, pass 2 (IV sanity) plus the soft warnings.
    df, n_hard_iv = apply_checks(df, r=r)
    df["market_state"] = state
    df["asof_ts"] = pd.Timestamp.now()
    df["r"] = r

    if verbose:
        print(f"  raw={n_raw}  dropped_hard_quote={n_hard_quote}  "
              f"unsolved_iv={n_unsolved}  dropped_hard_iv={n_hard_iv}  "
              f"dropped_thin_delta={n_thin}  kept={len(df)}")
        print(report(df, n_hard_quote + n_hard_iv))
        print()
        print(format_report(dq_report(df, symbol)))
        if state != "REGULAR":
            print(f"  !! market_state={state}: spreads and parity statistics "
                  f"reflect a closed market")

    df = df.sort_values(["expiry", "type", "strike"]).reset_index(drop=True)

    # Every pull is archived. Option quotes cannot be downloaded again later.
    if archive:
        try:
            row = archive_save(symbol, df, meta={"quality": dq_report(df, symbol)})
            if verbose:
                print(f"  archived -> archive/{symbol}/{row['file']}")
        except Exception as e:
            if verbose:
                print(f"  archive failed: {type(e).__name__}: {e}")
    return df


def enrich_many(symbols, **kw):
    out = []
    for s in symbols:
        try:
            d = enrich(s, **kw)
            if len(d):
                out.append(d)
        except Exception as e:
            print(f"{s}: FAILED ({e})")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


if __name__ == "__main__":
    argv = sys.argv[1:]
    wk = "--weeklies" in argv
    syms = [a for a in argv if not a.startswith("--")] or ["AAPL"]
    df = enrich_many(syms, weeklies=wk)
    from paths import sub
    out = sub("data")
    path = out / f"chain_{'_'.join(syms)}_{pd.Timestamp.today():%Y%m%d}.csv"
    df.to_csv(path, index=False)
    print(f"\n{len(df)} contracts -> {path}")
