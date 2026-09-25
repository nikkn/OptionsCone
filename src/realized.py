"""Realized volatility estimators and the implied-to-realized ratio.

The default is exponentially weighted close-to-close volatility over a year.
Close-to-close includes overnight gaps, which is the move an option pays out
on; range-based estimators (Parkinson, Garman-Klass, Rogers-Satchell) see only
the trading session. A six-week half-life gives an effective sample of about 83
days while the latest six weeks carry half the weight.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252.0


def _window(h, end, calendar_days):
    """Bars inside a calendar window, as option maturity is counted."""
    end = pd.Timestamp(end)
    return h[(h.index > end - pd.Timedelta(days=calendar_days)) & (h.index <= end)]


def ewma_close_to_close(w, half_life_days=42.0):
    """Exponentially weighted close-to-close volatility.

    The half-life is given in calendar days and converted to trading days.
    """
    lr = np.log(w["Close"] / w["Close"].shift(1)).dropna()
    n = len(lr)
    if n < 5:
        return np.nan
    hl = half_life_days * TRADING_DAYS / 365.0
    lam = 0.5 ** (1.0 / hl)
    age = np.arange(n - 1, -1, -1)          # 0 = most recent bar
    wt = lam ** age
    wt /= wt.sum()
    # Weighted about zero rather than the mean: an option prices the size of
    # moves, not their dispersion around a drift.
    var = float((wt * lr.values ** 2).sum())
    return float(np.sqrt(var * TRADING_DAYS))


def effective_n(n, half_life_days=42.0):
    """Kish effective sample size of the weighting, for reporting."""
    hl = half_life_days * TRADING_DAYS / 365.0
    lam = 0.5 ** (1.0 / hl)
    wt = lam ** np.arange(n)
    wt = wt / wt.sum()
    return float(1.0 / (wt ** 2).sum())


def close_to_close(w):
    lr = np.log(w["Close"] / w["Close"].shift(1)).dropna()
    if len(lr) < 2:
        return np.nan
    return float(lr.std(ddof=1) * np.sqrt(TRADING_DAYS))


def parkinson(w):
    hl = np.log(w["High"] / w["Low"])
    if len(hl) < 2:
        return np.nan
    return float(np.sqrt((hl ** 2).mean() / (4 * np.log(2)) * TRADING_DAYS))


def garman_klass(w):
    hl = np.log(w["High"] / w["Low"])
    co = np.log(w["Close"] / w["Open"])
    if len(hl) < 2:
        return np.nan
    v = (0.5 * hl ** 2 - (2 * np.log(2) - 1) * co ** 2).mean()
    return float(np.sqrt(max(v, 0) * TRADING_DAYS))


def rogers_satchell(w):
    ho = np.log(w["High"] / w["Open"])
    lo = np.log(w["Low"] / w["Open"])
    co = np.log(w["Close"] / w["Open"])
    if len(ho) < 2:
        return np.nan
    v = (ho * (ho - co) + lo * (lo - co)).mean()
    return float(np.sqrt(max(v, 0) * TRADING_DAYS))


def yang_zhang(w):
    """Overnight + opening + Rogers-Satchell, drift-independent."""
    n = len(w)
    if n < 3:
        return np.nan
    o = np.log(w["Open"] / w["Close"].shift(1)).dropna()
    c = np.log(w["Close"] / w["Open"])
    c = c.loc[o.index]
    n = len(o)
    if n < 3:
        return np.nan
    vo = o.var(ddof=1)                     # overnight jump
    vc = c.var(ddof=1)                     # open-to-close
    ho = np.log(w["High"] / w["Open"]); lo = np.log(w["Low"] / w["Open"])
    co = np.log(w["Close"] / w["Open"])
    rs = (ho * (ho - co) + lo * (lo - co)).loc[o.index].mean()
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    v = vo + k * vc + (1 - k) * rs
    return float(np.sqrt(max(v, 0) * TRADING_DAYS))


ESTIMATORS = {"ewma": ewma_close_to_close, "cc": close_to_close,
              "parkinson": parkinson, "gk": garman_klass,
              "rs": rogers_satchell, "yz": yang_zhang}


def realized(history, end, calendar_days, how="ewma", half_life_days=42.0):
    w = _window(history, end, calendar_days)
    if len(w) < 3:
        return {"sigma": np.nan, "bars": len(w)}
    out = {k: (f(w, half_life_days) if k == "ewma" else f(w))
           for k, f in ESTIMATORS.items()}
    return {"sigma": out.get(how, np.nan), "bars": len(w),
            "eff_n": round(effective_n(max(len(w) - 1, 1), half_life_days), 1),
            "half_life": half_life_days, **out}
