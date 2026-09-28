"""American option pricing on a Cox-Ross-Rubinstein tree with discrete
dividends, plus implied volatility and Greeks.

Dividends use the escrowed-dividend method: the present value of dividends paid
before expiry is removed from the spot, the tree is built on the remainder, and
the outstanding dividends are added back at each node. The tree stays
recombining while still producing the ex-dividend drop that drives early
exercise.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

DAYS = 365.0


def _pv_dividends(divs, T, r, t=0.0):
    """Present value at time t of dividends with ex-times in (t, T]."""
    if not divs:
        return 0.0
    return sum(a * np.exp(-r * (s - t)) for s, a in divs if t < s <= T)


def crr_price(S, K, T, r, sigma, is_call=False, divs=None, steps=200):
    """American option price on a Cox-Ross-Rubinstein tree.

    divs: [(t_years, amount), ...], ex-times measured from now.
    """
    return _crr(S, K, T, r, sigma, is_call, divs, steps)["price"]


def _crr(S, K, T, r, sigma, is_call, divs, steps):
    """Price, and the node values after the first two steps for the Greeks."""
    intrinsic = max((S - K) if is_call else (K - S), 0.0)
    if T <= 0 or sigma <= 0 or S <= 0:
        return {"price": intrinsic, "nodes": None}

    divs = divs or []
    # Risky part of the spot: remove the PV of dividends paid before expiry.
    S_risky = S - _pv_dividends(divs, T, r)
    if S_risky <= 0:
        return {"price": intrinsic, "nodes": None}
    steps = max(int(steps), 2)

    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    disc = np.exp(-r * dt)
    p = (np.exp(r * dt) - d) / (u - d)
    if not (0.0 < p < 1.0):  # sigma too small for the step size
        p = np.clip(p, 1e-12, 1 - 1e-12)

    # All nodes lie on one geometric ladder: node (i, j) is S*u^(i-2j).
    # Precomputing it avoids a power per node.
    ladder = S_risky * u ** np.arange(-steps, steps + 1)

    # Outstanding dividend PV per step, precomputed.
    pv_at = np.array([_pv_dividends(divs, T, r, i * dt)
                      for i in range(steps + 1)]) if divs else None

    ST = ladder[steps + np.arange(steps, -steps - 1, -2)]
    values = np.maximum(ST - K, 0.0) if is_call else np.maximum(K - ST, 0.0)

    nodes = {}
    for i in range(steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        S_i = ladder[steps + np.arange(i, -i - 1, -2)]
        if pv_at is not None:
            S_i = S_i + pv_at[i]
        exercise = (S_i - K) if is_call else (K - S_i)
        np.maximum(values, exercise, out=values)
        if i <= 2:
            nodes[i] = (S_i.copy(), values.copy())

    return {"price": float(values[0]), "nodes": nodes}


def implied_vol(price, S, K, T, r, is_call=False, divs=None, steps=200,
                lo=1e-3, hi=5.0, tol=1e-6, maxiter=60):
    """Implied volatility by inverting crr_price. None if no root is bracketed.
    """
    if price is None or not np.isfinite(price) or price <= 0 or T <= 0:
        return None

    # A price at or below intrinsic has no time value, so no volatility solves
    # it.
    fwd_spot = S - _pv_dividends(divs or [], T, r)
    intrinsic = max((fwd_spot - K) if is_call else (K - fwd_spot), 0.0)
    if price <= intrinsic + 1e-8:
        return None

    f = lambda s: crr_price(S, K, T, r, s, is_call, divs, steps) - price
    f_lo, f_hi = f(lo), f(hi)
    if f_lo * f_hi > 0:
        return None

    # Brent converges in a few tree evaluations where bisection needs about
    # thirty.
    try:
        return float(brentq(f, lo, hi, xtol=tol, rtol=1e-8, maxiter=maxiter))
    except Exception:
        pass

    for _ in range(maxiter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return float(mid)
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return float(0.5 * (lo + hi))


def greeks(S, K, T, r, sigma, is_call=False, divs=None, steps=200):
    """Delta and gamma read from the tree's own nodes (Hull).

    Delta is the slope between the two nodes after one step, gamma the change
    in slope across the three nodes after two. Bumping the spot and pricing
    three trees would make gamma a second difference of a price that moves in
    small steps as the strike falls between different nodes, which is mostly
    noise. The node values come from the same tree as the price, so one tree
    gives all three.
    """
    res = _crr(S, K, T, r, sigma, is_call, divs, steps)
    nodes = res["nodes"]
    if not nodes:
        return {"delta": np.nan, "gamma": np.nan, "price": res["price"]}
    (s1, v1), (s2, v2) = nodes[1], nodes[2]
    delta = (v1[0] - v1[1]) / (s1[0] - s1[1])
    slope_up = (v2[0] - v2[1]) / (s2[0] - s2[1])
    slope_dn = (v2[1] - v2[2]) / (s2[1] - s2[2])
    gamma = (slope_up - slope_dn) / (0.5 * (s2[0] - s2[2]))
    return {"delta": float(delta), "gamma": float(gamma), "price": res["price"]}


def bs_d2(S, K, T, r, sigma, q=0.0):
    return (np.log(S / K) + (r - q - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def prob_below_at_expiry(S, K, T, r, sigma, q=0.0):
    """Risk-neutral P(S_T < K), the terminal probability N(-d2)."""
    return float(norm.cdf(-bs_d2(S, K, T, r, sigma, q)))
