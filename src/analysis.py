"""Aggregations used by EDA, MapReduce/MongoDB cross-checks and the dashboard.

Author: Abin Shaji Thomas
Adapted from src/analysis.py of
https://github.com/rit-vik/Accident-Severity-Prediction-and-Hotspot-Analysis-of-US-Road-Accidents-BDA-Project-
(MIT, Ritvik Kar, Dhruv Abhijit Desai, Mithil S) - see NOTICE.md.
Upstream ran these as Spark SQL queries; here they are pandas group-bys.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def group_summary(df: pd.DataFrame, by, sort_by_count: bool = True) -> pd.DataFrame:
    """Accidents, mean severity and share of severe (3-4) accidents per group."""
    g = (df.assign(_severe=(df["Severity"] >= 3).astype(int))
         .groupby(by, observed=True)
         .agg(accidents=("Severity", "size"), avg_severity=("Severity", "mean"), severe_pct=("_severe", "mean"))
         .reset_index())
    g["avg_severity"] = g["avg_severity"].round(4)
    g["severe_pct"] = (100 * g["severe_pct"]).round(2)
    if sort_by_count:
        g = g.sort_values("accidents", ascending=False, ignore_index=True)
    return g


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Bias-corrected Cramer's V (Bergsma 2013)."""
    ct = pd.crosstab(x, y)
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n = ct.values.sum()
    phi2 = chi2 / n
    r, k = ct.shape
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2c / max(min(kc - 1, rc - 1), 1e-12)))


def epsilon_squared(h: float, n: int) -> float:
    """Effect size for the Kruskal-Wallis H statistic."""
    return float(h / ((n ** 2 - 1) / (n + 1)))
