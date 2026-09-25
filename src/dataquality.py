"""A fixed quality report for a downloaded chain.

The same checks run on every ticker so results are comparable. The report
separates the contracts the analysis uses (out of the money) from all listed
ones, because failures concentrate in deep in-the-money contracts that are
never used.
"""
from __future__ import annotations

import numpy as np

# Grades for the share of clean contracts among those used.
GRADES = [(0.85, "good"), (0.65, "fair"), (0.40, "poor")]


def _grade(frac):
    for cut, name in GRADES:
        if frac >= cut:
            return name
    return "unusable"


def used_side(df, spot_col="spot"):
    """The contracts the analysis reads: calls above spot, puts below.

    Out-of-the-money prices are all time value and invert to a meaningful
    volatility; in-the-money prices are mostly intrinsic.
    """
    otm = np.where(df["type"].eq("C"),
                   df["strike"] > df[spot_col],
                   df["strike"] < df[spot_col])
    return df[otm]


def report(df, symbol=None, spot_col="spot"):
    """Quality of one chain, as a dict ready to print or to store."""
    n = len(df)
    if not n:
        return {"symbol": symbol, "n": 0, "verdict": "empty"}

    used = used_side(df, spot_col)
    soft = [c for c in df.columns if c.startswith("soft_") and c != "soft_ok"]

    def rate(frame, col):
        return float(frame[col].mean()) if len(frame) and col in frame else np.nan

    bands = []
    for lo, hi, label in [(0.00, 0.80, "far wing"), (0.80, 0.92, "wing"),
                          (0.92, 1.08, "near money"), (1.08, 1.30, "wing"),
                          (1.30, 9.99, "far wing")]:
        b = used[(used["moneyness"] >= lo) & (used["moneyness"] < hi)]
        if len(b) < 3:
            continue
        bands.append({"lo": lo, "hi": hi, "label": label, "n": len(b),
                      "clean": rate(b, "soft_ok"),
                      "median_spread": float(b["spread_pct"].median()),
                      "median_oi": float(b["open_interest"].median()),
                      "median_mid": float(b["mid"].median())})

    out = {
        "symbol": symbol,
        "n": n,
        "n_used": len(used),
        "state": (str(df["market_state"].iloc[0])
                  if "market_state" in df else "UNKNOWN"),
        "clean_all": rate(df, "soft_ok"),
        "clean_used": rate(used, "soft_ok"),
        "warnings_all": {c[5:]: 1.0 - rate(df, c) for c in soft},
        "warnings_used": {c[5:]: 1.0 - rate(used, c) for c in soft},
        "bands": bands,
    }
    out["verdict"] = _grade(out["clean_used"])
    return out


def format_report(rep):
    """The report as text, written to be read rather than parsed."""
    if not rep or rep.get("n", 0) == 0:
        return f"{rep.get('symbol')}: no contracts"
    L = []
    L.append(f"{rep['symbol']}  ·  {rep['n']} contracts, "
             f"{rep['n_used']} out-of-the-money and therefore used")
    L.append(f"  market state at capture : {rep['state']}"
             + ("   (quotes outside trading hours are placeholders)"
                if rep["state"] != "REGULAR" else ""))
    L.append(f"  clean, all contracts    : {rep['clean_all']*100:5.1f}%")
    L.append(f"  clean, the ones used    : {rep['clean_used']*100:5.1f}%"
             f"   -> {rep['verdict']}")
    L.append("")
    L.append("  failure rates          all    used")
    for k in sorted(rep["warnings_all"]):
        a, u = rep["warnings_all"][k], rep["warnings_used"][k]
        flag = "  <-- worse where it counts" if u > a + 0.05 else ""
        L.append(f"    {k:<20}{a*100:5.1f}%  {u*100:5.1f}%{flag}")
    L.append("")
    L.append("  by moneyness (used contracts only)")
    L.append("    band            n   clean  spread   OI   med mid")
    for b in rep["bands"]:
        ivb = ("   n/a" if not np.isfinite(b.get("median_mid", np.nan))
               else f"{b['median_mid']:6.2f}")
        L.append(f"    {b['lo']:.2f}-{b['hi']:.2f} {b['n']:6d} "
                 f"{b['clean']*100:6.0f}% {b['median_spread']*100:6.0f}% "
                 f"{int(b['median_oi']):6d}  {ivb}")
    return "\n".join(L)
