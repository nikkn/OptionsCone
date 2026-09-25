"""Model-free implied volatility per expiry, by the VIX construction.

The Cboe variance-swap replication applied to one expiry at a time, reported at
its own maturity without interpolation to 30 days. The forward comes from the
strike where call and put mids are closest, only out-of-the-money quotes
contribute, each wing stops after two consecutive zero bids, and each strike is
weighted by dK/K^2. No pricing model is inverted, which is why the result can
differ from an at-the-money implied volatility.
"""
from __future__ import annotations

import numpy as np


def _mid(df):
    d = df.copy()
    d["mid"] = (d["bid"] + d["ask"]) / 2.0
    return d


def _walk(strikes_sorted, quotes, start_idx, direction, max_zero=2):
    """Collect strikes outward from start_idx, stopping after two zero bids
    (the VIX rule).
    """
    out, zeros = [], 0
    i = start_idx + direction
    while 0 <= i < len(strikes_sorted):
        k = strikes_sorted[i]
        q = quotes.get(k)
        if q is None or q["bid"] <= 0:
            zeros += 1
            if zeros >= max_zero:
                break
        else:
            zeros = 0
            out.append(k)
        i += direction
    return out


def variance_one_expiry(calls, puts, T, r, max_zero=2, spot=None):
    """Return the model-free implied variance for a single expiry.

    calls/puts: frames with strike, bid, ask.
    Returns a dict with sigma, the forward, K0 and the contributing strikes,
    or None when the chain is too thin to replicate the variance.
    """
    if T <= 0 or calls is None or puts is None or len(calls) == 0 or len(puts) == 0:
        return None

    c, p = _mid(calls), _mid(puts)

    # No-arbitrage bounds: a call is worth at most the stock, a put at most its
    # strike. Stale wing quotes beyond them would dominate the dK/K^2 sum.
    ref = float(spot) if spot else None
    cq = {float(t.strike): {"mid": float(t.mid), "bid": float(t.bid)}
          for t in c.itertuples()
          if t.ask > 0 and (ref is None or t.mid <= ref * 1.05)}
    pq = {float(t.strike): {"mid": float(t.mid), "bid": float(t.bid)}
          for t in p.itertuples()
          if t.ask > 0 and t.mid <= t.strike * 1.05}

    # Forward from put-call parity at the strike where call and put agree most
    # closely: F = K + e^{rT}(C - P).
    both = sorted(set(cq) & set(pq))
    both = [k for k in both if cq[k]["bid"] > 0 and pq[k]["bid"] > 0]
    if len(both) < 3:
        return None
    # Search only near the money: far out both sides are worth almost nothing
    # and agree trivially.
    anchor = spot if spot else float(np.median(both))
    near = [k for k in both if 0.6 * anchor <= k <= 1.6 * anchor]
    if len(near) >= 3:
        both = near
    k_star = min(both, key=lambda k: abs(cq[k]["mid"] - pq[k]["mid"]))
    F = k_star + np.exp(r * T) * (cq[k_star]["mid"] - pq[k_star]["mid"])

    all_k = sorted(set(cq) | set(pq))
    below = [k for k in all_k if k <= F]
    if not below:
        return None
    K0 = max(below)
    i0 = all_k.index(K0)

    # Out-of-the-money only: puts below K0, calls above, both averaged at K0.
    put_ks = _walk(all_k, pq, i0, -1, max_zero)
    call_ks = _walk(all_k, cq, i0, +1, max_zero)

    contrib = {}
    for k in put_ks:
        contrib[k] = pq[k]["mid"]
    for k in call_ks:
        contrib[k] = cq[k]["mid"]
    at_k0 = [q[K0]["mid"] for q in (cq, pq) if K0 in q and q[K0]["bid"] > 0]
    if at_k0:
        contrib[K0] = float(np.mean(at_k0))
    if len(contrib) < 3:
        return None

    ks = sorted(contrib)
    # dK is the central difference between neighbouring strikes, halved at the
    # ends.
    dk = {}
    for i, k in enumerate(ks):
        if i == 0:
            dk[k] = ks[1] - ks[0]
        elif i == len(ks) - 1:
            dk[k] = ks[-1] - ks[-2]
        else:
            dk[k] = (ks[i + 1] - ks[i - 1]) / 2.0

    disc = np.exp(r * T)
    total = sum(dk[k] / (k * k) * disc * contrib[k] for k in ks)
    var = (2.0 / T) * total - (1.0 / T) * ((F / K0 - 1.0) ** 2)
    if not np.isfinite(var) or var <= 0:
        return None

    return {"sigma": float(np.sqrt(var)), "variance": float(var),
            "F": float(F), "K0": float(K0), "n_strikes": len(ks),
            "k_min": float(ks[0]), "k_max": float(ks[-1]),
            "n_puts": len(put_ks), "n_calls": len(call_ks)}
