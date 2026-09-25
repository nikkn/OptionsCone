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
    if T <= 0 or sigma <= 0 or S <= 0:
        intrinsic = (S - K) if is_call else (K - S)
        return max(intrinsic, 0.0)

    divs = divs or []
    # Risky part of the spot: remove the PV of dividends paid before expiry.
    S_risky = S - _pv_dividends(divs, T, r)
    if S_risky <= 0:
        return max((S - K) if is_call else (K - S), 0.0)

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

    for i in range(steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        S_i = ladder[steps + np.arange(i, -i - 1, -2)]
        if pv_at is not None:
            S_i = S_i + pv_at[i]
        exercise = (S_i - K) if is_call else (K - S_i)
        np.maximum(values, exercise, out=values)

    return float(values[0])


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


def greeks(S, K, T, r, sigma, is_call=False, divs=None, steps=200, h_rel=0.01):
    """Delta and gamma by central difference on the spot."""
    h = max(S * h_rel, 1e-4)
    up = crr_price(S + h, K, T, r, sigma, is_call, divs, steps)
    mid = crr_price(S, K, T, r, sigma, is_call, divs, steps)
    dn = crr_price(S - h, K, T, r, sigma, is_call, divs, steps)
    return {
        "delta": (up - dn) / (2 * h),
        "gamma": (up - 2 * mid + dn) / (h * h),
        "price": mid,
    }


def bs_d2(S, K, T, r, sigma, q=0.0):
    return (np.log(S / K) + (r - q - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))


def prob_below_at_expiry(S, K, T, r, sigma, q=0.0):
    """Risk-neutral P(S_T < K), the terminal probability N(-d2)."""
    return float(norm.cdf(-bs_d2(S, K, T, r, sigma, q)))
