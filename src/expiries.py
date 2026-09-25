"""Expiry selection: monthlies (third Friday) and, optionally, weeklies."""
from __future__ import annotations

import pandas as pd


def is_monthly(ts) -> bool:
    """Third Friday, or the Thursday standing in for a holiday Friday."""
    ts = pd.Timestamp(ts)
    if not 15 <= ts.day <= 21:
        return False
    return ts.dayofweek in (3, 4)  # Thu (holiday shift) or Fri


def all_monthlies(expiries, max_days=180, min_days=1, today=None,
                  weeklies=False):
    """Every expiry within the horizon, monthlies only or all of them.

    Thin weekly contracts are filtered by the per-contract quality checks
    rather than excluded by expiry.
    """
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    out = []
    for e in expiries:
        d = (pd.Timestamp(e) - today).days
        if min_days <= d <= max_days and (weeklies or is_monthly(e)):
            out.append((e, d))
    return sorted(out, key=lambda x: x[1])


def select(expiries, targets=(30, 60, 120), today=None, monthly_only=True):
    """Map each target horizon to the nearest available expiry.

    Returns [(target_days, 'YYYY-MM-DD', actual_days), ...] without duplicates;
    two targets can map to the same expiry.
    """
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    cand = [(e, (pd.Timestamp(e) - today).days) for e in expiries]
    cand = [(e, d) for e, d in cand if d > 0]
    if monthly_only:
        monthlies = [(e, d) for e, d in cand if is_monthly(e)]
        if monthlies:
            cand = monthlies
    if not cand:
        return []

    out, seen = [], set()
    for tgt in targets:
        e, d = min(cand, key=lambda x: abs(x[1] - tgt))
        if e not in seen:
            seen.add(e)
            out.append((tgt, e, d))
    return out
