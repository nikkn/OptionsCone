"""Earnings dates: confirmed where Yahoo has them, projected beyond.

Rows without reported EPS are future dates. Past the last confirmed date, dates
are projected from the reporting cadence and flagged as projected.
"""
from __future__ import annotations

import pandas as pd


def _clean(df):
    """Drop the timezone without shifting the clock.

    Feed times are already exchange-local (08:00 before the open, 16:00 after
    the close); converting to UTC would lose that distinction.
    """
    if df is None or len(df) == 0:
        return None
    d = df.copy()
    idx = pd.to_datetime(d.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    d.index = idx
    return d.sort_index()


def earnings(ticker, horizon_end, today=None, max_projected=6):
    """Return [{date, confirmed, when}] up to horizon_end.

    `when` is 'bmo' (before the open) or 'amc' (after the close) where the feed
    gives a time.
    """
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    horizon_end = pd.Timestamp(horizon_end)

    try:
        raw = ticker.get_earnings_dates(limit=32)
    except Exception:
        try:
            raw = ticker.earnings_dates
        except Exception:
            raw = None
    d = _clean(raw)
    if d is None:
        return []

    def when(ts):
        h = ts.hour
        if h == 0:
            return None
        return "bmo" if h < 12 else "amc"

    reported = ("Reported EPS" in d.columns)
    out, future = [], []
    for ts, row in d.iterrows():
        done = bool(reported and pd.notna(row.get("Reported EPS")))
        if ts.normalize() < today and done:
            continue
        if ts.normalize() >= today:
            future.append(ts)
        out.append({"date": ts.normalize(), "confirmed": True, "when": when(ts)})

    out = [o for o in out if today <= o["date"] <= horizon_end]

    # Cadence from the realised history, for anything past the last known date.
    hist = d.index.normalize().unique()
    hist = [h for h in hist if h < today]
    step = 91
    if len(hist) >= 3:
        gaps = pd.Series(pd.DatetimeIndex(sorted(hist))).diff().dt.days.dropna()
        gaps = gaps[(gaps > 45) & (gaps < 200)]
        if len(gaps):
            step = int(round(float(gaps.median())))

    cursor = max([o["date"] for o in out], default=None)
    if cursor is None:
        cursor = max(hist) if hist else today
    last_when = out[-1]["when"] if out else None
    n = 0
    cursor = cursor + pd.Timedelta(days=step)
    while cursor <= horizon_end and n < max_projected:
        if cursor >= today:
            out.append({"date": cursor, "confirmed": False, "when": last_when})
            n += 1
        cursor = cursor + pd.Timedelta(days=step)

    out.sort(key=lambda o: o["date"])
    return out


def past_earnings(ticker, start, end):
    """Past earnings dates inside a window, for marking the price history."""
    try:
        raw = ticker.get_earnings_dates(limit=32)
    except Exception:
        return []
    d = _clean(raw)
    if d is None:
        return []
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    done = d
    if "Reported EPS" in d.columns:
        done = d[d["Reported EPS"].notna()]
    ds = sorted({ts.normalize() for ts in done.index})
    return [x for x in ds if start <= x <= end]
