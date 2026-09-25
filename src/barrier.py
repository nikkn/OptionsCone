"""Barrier-touch (first-passage) probabilities under geometric Brownian motion.

A touch triggers the first time the price reaches the level, even if it
recovers later, so it is always at least as likely as finishing beyond the
level. With zero log drift the touch probability is about twice the terminal
one (reflection principle).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def prob_touch_down(S, B, T, sigma, mu=0.0):
    """P(min_{t<=T} S_t <= B) under GBM with log drift mu.

    mu is the drift of log(S); risk-neutral: mu = r - q - sigma^2/2.
    """
    S, B = np.asarray(S, float), np.asarray(B, float)
    S, B, T = np.broadcast_arrays(S, B, np.asarray(T, float))
    sigma = np.broadcast_to(np.asarray(sigma, float), S.shape)

    s = sigma * np.sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.log(B / S)
        p = norm.cdf((x - mu * T) / s) + np.exp(
            2 * mu * x / sigma**2) * norm.cdf((x + mu * T) / s)
    # At or through the barrier: certain. Degenerate inputs: zero.
    p = np.where(B >= S, 1.0, p)
    p = np.where((T <= 0) | (sigma <= 0), np.where(B >= S, 1.0, 0.0), p)
    p = np.nan_to_num(p, nan=0.0)
    return np.clip(p, 0.0, 1.0)


def prob_touch_up(S, B, T, sigma, mu=0.0):
    """P(max_{t<=T} S_t >= B) under GBM with log drift mu.

    Mirror image of prob_touch_down.
    """
    S, B = np.asarray(S, float), np.asarray(B, float)
    S, B, T = np.broadcast_arrays(S, B, np.asarray(T, float))
    sigma = np.broadcast_to(np.asarray(sigma, float), S.shape)

    s = sigma * np.sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.log(B / S)
        p = norm.cdf((-x + mu * T) / s) + np.exp(
            2 * mu * x / sigma**2) * norm.cdf((-x - mu * T) / s)
    p = np.where(B <= S, 1.0, p)
    p = np.where((T <= 0) | (sigma <= 0), np.where(B <= S, 1.0, 0.0), p)
    return np.clip(np.nan_to_num(p, nan=0.0), 0.0, 1.0)
