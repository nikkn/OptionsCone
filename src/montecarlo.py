"""Barrier hit rates from a block bootstrap of the stock's own history.

The bootstrap resamples contiguous runs of real returns, so fat tails,
skew and volatility clustering carry over into the simulated paths.
Bootstrapped paths describe the historical distribution; option-implied figures
are risk-neutral. The difference between them is the risk premium, not an error
in either.
"""
from __future__ import annotations

import numpy as np

TRADING_DAYS = 252.0


def _log_bars(history):
    """Per-day log return plus the day's reach.

    A barrier is touched intraday, so each day keeps its high and low as
    offsets from its own close. A resampled block then reproduces real daily
    ranges, including overnight gaps.

    Returns (ret, hi, lo): the log return and the log distances from the close
    up to the high and down to the low.
    """
    h = history.dropna(subset=["Open", "High", "Low", "Close"])
    c = h["Close"].to_numpy(float)
    ret = np.log(c[1:] / c[:-1])
    hi = np.log(h["High"].to_numpy(float)[1:] / c[1:])
    lo = np.log(h["Low"].to_numpy(float)[1:] / c[1:])
    return ret, np.maximum(hi, 0.0), np.minimum(lo, 0.0)


def simulate_block_bootstrap(S0, returns, n_days, n_paths=10000, block=20,
                             seed=None, demean=True, drift=0.0, bars=None):
    """Resample contiguous blocks of realised returns.

    Blocks are drawn with replacement from every possible starting point and
    joined until the horizon is filled. The block length sets how much memory
    survives; 20 trading days keeps about a month of volatility clustering.

    `demean` removes the realised drift; `drift` (annual, log terms) imposes
    one instead.
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, float)
    if demean:
        r = r - r.mean()
    if drift:
        r = r + drift / TRADING_DAYS
    n = len(r)
    if n < block + 1:
        raise ValueError("not enough history for this block length")

    # Whole blocks only: the horizon is rounded up to a block boundary.
    n_blocks = int(np.ceil(n_days / block))
    starts = rng.integers(0, n - block, size=(n_paths, n_blocks))
    idx = starts[:, :, None] + np.arange(block)[None, None, :]
    steps = r[idx].reshape(n_paths, n_blocks * block)
    closes = S0 * np.exp(np.cumsum(steps, axis=1))
    if bars is None:
        return closes
    # The same draws index each day's high and low.
    hi, lo = bars
    return (closes,
            closes * np.exp(hi[idx].reshape(closes.shape)),
            closes * np.exp(lo[idx].reshape(closes.shape)))


_LOGCACHE = {}


def _log_of(paths, S0):
    """log(paths) and the step variance, cached per path array."""
    key = id(paths)
    hit = _LOGCACHE.get(key)
    if hit is not None and hit[0] is paths:
        return hit[1], hit[2]
    lp = np.log(paths)
    steps = np.diff(lp, axis=1, prepend=np.log(S0))
    var = float(np.var(steps))
    if len(_LOGCACHE) > 8:
        _LOGCACHE.clear()
    _LOGCACHE[key] = (paths, lp, var)
    return lp, var


def hit_rates(paths, S0, barrier, up=False, rng=None, extreme=None):
    """Touch and terminal rates for one barrier.

    `extreme` is each simulated day's high or low from a bootstrap with bars;
    with it, a touch is observed on the intraday range. Without it the closes
    are used and a Brownian-bridge correction estimates crossings between
    closes.
    """
    n_paths, n_days = paths.shape
    if up:
        terminal = paths[:, -1] >= barrier
        touched = ((extreme if extreme is not None else paths)
                   >= barrier).any(axis=1)
    else:
        terminal = paths[:, -1] <= barrier
        touched = ((extreme if extreme is not None else paths)
                   <= barrier).any(axis=1)

    rate = float(touched.mean())
    if extreme is None:
        # No bars: Brownian-bridge correction between closes.
        lp, var = _log_of(paths, S0)
        lb = np.log(barrier)
        live = ~touched
        if live.any() and var > 0:
            q = lp[live]
            a, b = q[:, :-1], q[:, 1:]
            gap = ((lb - a) * (lb - b)) if up else ((a - lb) * (b - lb))
            np.maximum(gap, 0.0, out=gap)
            near = gap < 10.0 * var
            p_none = np.ones(q.shape[0])
            if near.any():
                pc = np.zeros_like(gap)
                pc[near] = np.exp(-2.0 * gap[near] / var)
                p_none = np.prod(1.0 - pc, axis=1)
            rate += float((1.0 - p_none).sum()) / n_paths

    return {"touch_daily": float(touched.mean()),
            "touch_continuous": rate,
            "terminal": float(terminal.mean()),
            "n_paths": n_paths}


def basis_run(S0, returns, max_days, n_paths=50000, block=20, seed=7,
              demean=True, drift=0.0, bars=None):
    """One simulation to the longest horizon, read off at every shorter one.

    Shorter horizons are prefixes of the same paths, so touch probabilities can
    never fall with maturity.
    """
    return simulate_block_bootstrap(S0, returns, max_days, n_paths, block,
                                    seed=seed, demean=demean, drift=drift,
                                    bars=bars)


def hit_rates_at(run, S0, barrier, n_days, up=False):
    """Hit rates using only the first n_days columns of a basis run.

    `run` is either the closes alone or the (close, high, low) triple the
    bootstrap returns when it was given bars.
    """
    if isinstance(run, tuple):
        # With highs and lows available, a touch is 'the lowest low reached the
        # barrier' (or the highest high). Each path's extreme and final close
        # are sorted once per horizon, and every barrier is a binary search
        # into those lists: the same counts as testing each path, much faster.
        mins, maxs, ends = _sorted_extremes(run, n_days)
        n = len(ends)
        b = float(barrier)
        if up:
            touched = n - np.searchsorted(maxs, b, side="left")
            term = n - np.searchsorted(ends, b, side="left")
        else:
            touched = np.searchsorted(mins, b, side="right")
            term = np.searchsorted(ends, b, side="right")
        rate = float(touched) / n
        return {"touch_daily": rate, "touch_continuous": rate,
                "terminal": float(term) / n, "n_paths": n}
    return hit_rates(run[:, :n_days], S0, barrier, up)


_EXTCACHE = {}


def _sorted_extremes(run, n_days):
    """Sorted per-path lowest low, highest high and final close, cached.

    Keyed on the path array's identity with a weak reference, so an entry
    cannot be confused with a later array at the same address.
    """
    import weakref
    closes, hi, lo = run
    key = (id(closes), int(n_days))
    hit = _EXTCACHE.get(key)
    if hit is not None and hit[0]() is closes:
        return hit[1]
    for k in [k for k, v in _EXTCACHE.items() if v[0]() is None]:
        del _EXTCACHE[k]
    val = (np.sort(lo[:, :n_days].min(axis=1)),
           np.sort(hi[:, :n_days].max(axis=1)),
           np.sort(closes[:, n_days - 1]))
    _EXTCACHE[key] = (weakref.ref(closes), val)
    return val
