"""Project future discrete dividends from yfinance history."""
from __future__ import annotations

import pandas as pd


def infer_schedule(ticker, horizon_end: pd.Timestamp, today: pd.Timestamp | None = None):
    """Return [(ex_date, amount), ...] out to horizon_end.

    The payment frequency is inferred from the dividend history and stepped
    forward from the last ex-date. The most recent amount is carried forward,
    since dividends change in steps rather than drift.
    """
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    horizon_end = pd.Timestamp(horizon_end)

    try:
        hist = ticker.dividends
    except Exception:
        return []
    if hist is None or len(hist) == 0:
        return []

    hist = hist.copy()
    hist.index = pd.to_datetime(hist.index).tz_localize(None)
    hist = hist[hist.index > today - pd.DateOffset(years=3)]
    if len(hist) == 0:
        return []

    amount = float(hist.iloc[-1])
    if amount <= 0:
        return []

    # Median spacing of recent payments gives the cadence (about 91 days for
    # quarterly).
    if len(hist) >= 3:
        step_days = float(pd.Series(hist.index).diff().dt.days.dropna().median())
    else:
        step_days = 91.0
    step_days = min(max(step_days, 25.0), 400.0)
    step = pd.Timedelta(days=round(step_days))

    # Prefer Yahoo's declared next ex-date when it is still ahead of us.
    cursor = None
    try:
        cal = ticker.calendar or {}
        declared = cal.get("Ex-Dividend Date")
        if declared is not None:
            declared = pd.Timestamp(declared)
            if declared > today:
                cursor = declared
    except Exception:
        pass
    if cursor is None:
        cursor = hist.index[-1] + step
        while cursor <= today:
            cursor += step

    out = []
    while cursor <= horizon_end:
        out.append((cursor, amount))
        cursor += step
    return out
