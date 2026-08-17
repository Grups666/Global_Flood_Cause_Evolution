from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .io import benjamini_hochberg


def logistic_trend(year: np.ndarray, outcome: np.ndarray) -> dict[str, float]:
    """Fit a one-predictor logistic trend using stable IRLS."""
    x = (np.asarray(year, dtype=float) - np.mean(year)) / 10.0
    y = np.asarray(outcome, dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    beta = np.array([math.log((y.mean() + 0.01) / (1.01 - y.mean())), 0.0])
    converged = False
    for _ in range(100):
        eta = np.clip(design @ beta, -30, 30)
        probability = 1.0 / (1.0 + np.exp(-eta))
        weights = np.clip(probability * (1.0 - probability), 1e-8, None)
        working = eta + (y - probability) / weights
        information = design.T @ (weights[:, None] * design)
        information.flat[:: information.shape[0] + 1] += 1e-9
        updated = np.linalg.solve(information, design.T @ (weights * working))
        if np.max(np.abs(updated - beta)) < 1e-9:
            beta = updated
            converged = True
            break
        beta = updated

    eta = np.clip(design @ beta, -30, 30)
    probability = 1.0 / (1.0 + np.exp(-eta))
    weights = np.clip(probability * (1.0 - probability), 1e-8, None)
    information = design.T @ (weights[:, None] * design)
    covariance = np.linalg.inv(information)
    standard_error = float(np.sqrt(covariance[1, 1]))
    z_value = float(beta[1] / standard_error) if standard_error > 0 else np.nan
    p_value = float(2.0 * stats.norm.sf(abs(z_value))) if np.isfinite(z_value) else np.nan
    return {
        "log_odds_per_decade": float(beta[1]),
        "odds_ratio_per_decade": float(np.exp(beta[1])),
        "odds_ratio_ci_low": float(np.exp(beta[1] - 1.96 * standard_error)),
        "odds_ratio_ci_high": float(np.exp(beta[1] + 1.96 * standard_error)),
        "logistic_p": p_value,
        "logistic_converged": converged,
    }


def mann_kendall_tie_corrected(values: np.ndarray) -> dict[str, float]:
    """Tie-corrected asymptotic Mann-Kendall test for a time-ordered series."""
    y = np.asarray(values, dtype=float)
    n = len(y)
    s_value = 0
    for index in range(n - 1):
        s_value += int(np.sign(y[index + 1 :] - y[index]).sum())
    _, counts = np.unique(y, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    variance = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0
    if variance <= 0:
        z_value = 0.0
    elif s_value > 0:
        z_value = (s_value - 1) / np.sqrt(variance)
    elif s_value < 0:
        z_value = (s_value + 1) / np.sqrt(variance)
    else:
        z_value = 0.0
    p_value = float(2.0 * stats.norm.sf(abs(z_value)))
    tau = float(s_value / (0.5 * n * (n - 1))) if n > 1 else np.nan
    return {"mk_s": float(s_value), "mk_tau": tau, "mk_z": float(z_value), "mk_p": p_value}


def theil_sen_per_decade(year: np.ndarray, values: np.ndarray) -> dict[str, float]:
    slope, intercept, low, high = stats.theilslopes(values, year, alpha=0.95)
    mk = mann_kendall_tie_corrected(values)
    return {
        "sen_slope_per_decade": float(slope * 10.0),
        "sen_ci_low_per_decade": float(low * 10.0),
        "sen_ci_high_per_decade": float(high * 10.0),
        **mk,
    }


def fit_binary_trends(
    sample: pd.DataFrame,
    outcomes: list[str],
    min_positive: int,
    min_negative: int,
    alpha: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for outcome in outcomes:
        for gcin, frame in sample.groupby("GCIN", sort=False):
            subset = frame[["peak_year", outcome]].dropna().sort_values("peak_year")
            if subset.empty:
                continue
            y = subset[outcome].astype(int).to_numpy()
            positive = int(y.sum())
            negative = int(len(y) - positive)
            if positive < min_positive or negative < min_negative:
                continue
            year = subset["peak_year"].to_numpy(float)
            rows.append({
                "GCIN": int(gcin),
                "outcome": outcome,
                "n_years": len(y),
                "n_positive": positive,
                "n_negative": negative,
                **logistic_trend(year, y),
                **theil_sen_per_decade(year, y),
            })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["logistic_q"] = result.groupby("outcome", group_keys=False)["logistic_p"].apply(benjamini_hochberg)
    result["mk_q"] = result.groupby("outcome", group_keys=False)["mk_p"].apply(benjamini_hochberg)
    result["direction"] = np.select(
        [result["log_odds_per_decade"] > 0, result["log_odds_per_decade"] < 0],
        ["increase", "decrease"],
        default="stable",
    )
    result["fdr_significant"] = result["logistic_q"] < alpha
    return result


def fit_continuous_trends(sample: pd.DataFrame, variables: list[str], alpha: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variable in variables:
        for gcin, frame in sample.groupby("GCIN", sort=False):
            subset = frame[["peak_year", variable]].dropna().sort_values("peak_year")
            if len(subset) < 10:
                continue
            year_span = int(subset["peak_year"].max() - subset["peak_year"].min() + 1)
            if year_span < 20:
                continue
            estimate = theil_sen_per_decade(
                subset["peak_year"].to_numpy(float), subset[variable].to_numpy(float)
            )
            rows.append({
                "GCIN": int(gcin),
                "variable": variable,
                "n_observations": len(subset),
                "n_years": int(subset["peak_year"].nunique()),
                "first_year": int(subset["peak_year"].min()),
                "last_year": int(subset["peak_year"].max()),
                "year_span": year_span,
                "mean_level": float(subset[variable].mean()),
                **estimate,
            })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["mk_q"] = result.groupby("variable", group_keys=False)["mk_p"].apply(benjamini_hochberg)
    result["direction"] = np.select(
        [result["sen_slope_per_decade"] > 0, result["sen_slope_per_decade"] < 0],
        ["increase", "decrease"],
        default="stable",
    )
    result["fdr_significant"] = result["mk_q"] < alpha
    result["display_slope_per_decade"] = result["sen_slope_per_decade"]
    result["display_ci_low_per_decade"] = result["sen_ci_low_per_decade"]
    result["display_ci_high_per_decade"] = result["sen_ci_high_per_decade"]
    result["display_unit"] = "units per decade"
    percentage_points = result["variable"].isin(
        ["intensity_fraction", "intensity_050", "intensity_075"]
    )
    result.loc[percentage_points, "display_slope_per_decade"] *= 100.0
    result.loc[percentage_points, "display_ci_low_per_decade"] *= 100.0
    result.loc[percentage_points, "display_ci_high_per_decade"] *= 100.0
    result.loc[percentage_points, "display_unit"] = "percentage points per decade"
    log_metrics = result["variable"].str.startswith("log_")
    result.loc[log_metrics, "display_slope_per_decade"] = (
        100.0 * np.expm1(result.loc[log_metrics, "sen_slope_per_decade"])
    )
    result.loc[log_metrics, "display_ci_low_per_decade"] = (
        100.0 * np.expm1(result.loc[log_metrics, "sen_ci_low_per_decade"])
    )
    result.loc[log_metrics, "display_ci_high_per_decade"] = (
        100.0 * np.expm1(result.loc[log_metrics, "sen_ci_high_per_decade"])
    )
    result.loc[log_metrics, "display_unit"] = "approximate percent per decade"
    return result
