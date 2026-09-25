"""Which contracts' implied volatilities can be trusted."""
from __future__ import annotations

import numpy as np


def usable_ivs(frame, spread_mult=3.0, spread_cap=0.60, min_keep=6):
    """Implied volatilities from the contracts whose quotes can carry one.

    Two tests: the spread must be within a multiple of the chain's median
    spread (capped), and the volatility must be plausible relative to the
    contracts nearest the money, which rejects tight but stale quotes far in
    the wings.

    Returns (ivs, n_total, n_kept).
    """
    n_total = len(frame)
    if not n_total:
        return np.array([]), 0, 0
    d = frame[np.isfinite(frame.get("iv", np.nan))].copy()
    if not len(d):
        return np.array([]), n_total, 0

    # Reference volatility from the contracts nearest the money; the band is
    # wider upwards because skew is steep.
    if "moneyness" in d:
        near = d.iloc[(d["moneyness"] - 1.0).abs().to_numpy().argsort()[:8]]
        ref = float(np.median(near["iv"]))
    else:
        ref = float(np.median(d["iv"]))
    d = d[(d["iv"] > ref * 0.5) & (d["iv"] < ref * 2.0)]
    if not len(d):
        return np.array([]), n_total, 0

    if "spread_pct" in d and np.isfinite(d["spread_pct"]).any():
        b = d[np.isfinite(d["spread_pct"])].copy()
        thresh = min(spread_cap, spread_mult * float(np.median(b["spread_pct"])))
        keep = b[b["spread_pct"] <= thresh].sort_values("spread_pct")
        if len(keep) < min_keep:
            keep = b.sort_values("spread_pct").head(min_keep)
    else:
        keep = d
    return keep["iv"].to_numpy(float), n_total, len(keep)
