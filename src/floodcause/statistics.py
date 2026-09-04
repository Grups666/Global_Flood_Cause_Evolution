from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def mann_kendall_tie_corrected(values: np.ndarray) -> dict[str, float]:
    """Tie-corrected asymptotic Mann-Kendall test for an ordered series."""
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
    return {"mk_s": float(s_value), "mk_tau": tau, "mk_z": float(z_value), "p_value": p_value}


def theil_sen_per_decade(year: np.ndarray, values: np.ndarray) -> dict[str, float]:
    """Theil-Sen magnitude trend with a Mann-Kendall trend test."""
    x = np.asarray(year, dtype=float)
    y = np.asarray(values, dtype=float)
    slope, intercept, low, high = stats.theilslopes(y, x, alpha=0.95)
    fitted_first = intercept + slope * float(x.min())
    fitted_last = intercept + slope * float(x.max())
    result = {
        "raw_slope_per_decade": float(slope * 10.0),
        "raw_ci_low_per_decade": float(low * 10.0),
        "raw_ci_high_per_decade": float(high * 10.0),
        "fitted_first": float(fitted_first),
        "fitted_last": float(fitted_last),
        **mann_kendall_tie_corrected(y),
    }
    return result


def binomial_probability_trend(
    year: np.ndarray,
    success: np.ndarray,
    total: np.ndarray,
) -> dict[str, float] | None:
    """Binomial time trend expressed as fitted probability change.

    ``success`` and ``total`` are annual event counts. The reported effect is
    the fitted start-to-end probability difference divided by elapsed decades,
    so its unit is percentage points per decade rather than an odds ratio.
    """
    x_year = np.asarray(year, dtype=float)
    yes = np.asarray(success, dtype=float)
    n = np.asarray(total, dtype=float)
    valid = np.isfinite(x_year) & np.isfinite(yes) & np.isfinite(n) & (n > 0)
    x_year, yes, n = x_year[valid], yes[valid], n[valid]
    if len(x_year) < 3 or yes.sum() <= 0 or (n - yes).sum() <= 0:
        return None
    x = (x_year - 2000.0) / 10.0
    design = np.column_stack([np.ones(len(x)), x])

    # Firth's Jeffreys-prior bias reduction keeps estimates finite when a
    # process occurs only in the early or late part of a short event record.
    # This is preferable to reporting an infinite ordinary-logistic slope.
    coefficients = np.zeros(2, dtype=float)
    converged = False
    for _ in range(100):
        eta = np.clip(design @ coefficients, -35.0, 35.0)
        probability = 1.0 / (1.0 + np.exp(-eta))
        weights = np.maximum(n * probability * (1.0 - probability), 1e-10)
        information = design.T @ (weights[:, None] * design)
        inverse = np.linalg.pinv(information)
        leverage = weights * np.einsum("ij,jk,ik->i", design, inverse, design)
        adjusted_score = design.T @ (
            yes - n * probability + leverage * (0.5 - probability)
        )
        step = inverse @ adjusted_score
        coefficients += step
        if float(np.max(np.abs(step))) < 1e-8:
            converged = True
            break
    if not converged or not np.isfinite(coefficients).all():
        return None
    eta = np.clip(design @ coefficients, -35.0, 35.0)
    probability = 1.0 / (1.0 + np.exp(-eta))
    weights = np.maximum(n * probability * (1.0 - probability), 1e-10)
    covariance = np.linalg.pinv(design.T @ (weights[:, None] * design))
    beta = float(coefficients[1])
    beta_se = float(np.sqrt(max(covariance[1, 1], 0.0)))
    first_year = float(x_year.min())
    last_year = float(x_year.max())
    elapsed_decades = (last_year - first_year) / 10.0
    if elapsed_decades <= 0:
        return None
    first_x = (first_year - 2000.0) / 10.0
    last_x = (last_year - 2000.0) / 10.0
    intercept = float(coefficients[0])
    logistic = lambda value: 1.0 / (1.0 + np.exp(-np.clip(value, -35.0, 35.0)))
    p_first = float(logistic(intercept + beta * first_x))
    p_last = float(logistic(intercept + beta * last_x))
    change = 100.0 * (p_last - p_first) / elapsed_decades
    # Transform the coefficient confidence limits into the same probability
    # scale while retaining the fitted intercept.
    beta_low = beta - 1.96 * beta_se
    beta_high = beta + 1.96 * beta_se
    low_change = 100.0 * (
        logistic(intercept + beta_low * last_x)
        - logistic(intercept + beta_low * first_x)
    ) / elapsed_decades
    high_change = 100.0 * (
        logistic(intercept + beta_high * last_x)
        - logistic(intercept + beta_high * first_x)
    ) / elapsed_decades
    ci_low, ci_high = sorted((float(low_change), float(high_change)))
    return {
        "raw_slope_per_decade": beta,
        "raw_ci_low_per_decade": beta_low,
        "raw_ci_high_per_decade": beta_high,
        "display_slope_per_decade": float(change),
        "display_ci_low_per_decade": ci_low,
        "display_ci_high_per_decade": ci_high,
        "fitted_first": 100.0 * p_first,
        "fitted_last": 100.0 * p_last,
        "p_value": float(2.0 * stats.norm.sf(abs(beta / beta_se))) if beta_se > 0 else np.nan,
        "odds_ratio_per_decade": float(np.exp(beta)),
        "firth_converged": True,
    }


def poisson_rate_trend(year: np.ndarray, count: np.ndarray) -> dict[str, float] | None:
    """Poisson annual-count trend with a sandwich standard error.

    The canonical coefficient is fitted per decade. Reader-facing effects are
    converted to absolute events/year change per decade between the fitted
    record endpoints, avoiding the zero-median slopes produced by sparse
    annual count series.
    """
    x_year = np.asarray(year, dtype=float)
    y = np.asarray(count, dtype=float)
    valid = np.isfinite(x_year) & np.isfinite(y) & (y >= 0)
    x_year, y = x_year[valid], y[valid]
    if len(x_year) < 3 or y.sum() <= 0:
        return None
    x = (x_year - 2000.0) / 10.0
    design = np.column_stack([np.ones(len(x)), x])
    coefficients = np.array([np.log(max(y.mean(), 1e-8)), 0.0], dtype=float)
    converged = False
    for _ in range(100):
        eta = np.clip(design @ coefficients, -25.0, 25.0)
        mean = np.exp(eta)
        information = design.T @ (mean[:, None] * design)
        step = np.linalg.pinv(information) @ (design.T @ (y - mean))
        coefficients += step
        if float(np.max(np.abs(step))) < 1e-10:
            converged = True
            break
    if not converged or not np.isfinite(coefficients).all():
        return None
    eta = np.clip(design @ coefficients, -25.0, 25.0)
    mean = np.exp(eta)
    information_inverse = np.linalg.pinv(design.T @ (mean[:, None] * design))
    residual = y - mean
    meat = design.T @ ((residual**2)[:, None] * design)
    covariance = information_inverse @ meat @ information_inverse
    beta = float(coefficients[1])
    beta_se = float(np.sqrt(max(covariance[1, 1], 0.0)))
    first_year = float(x_year.min())
    last_year = float(x_year.max())
    elapsed_decades = (last_year - first_year) / 10.0
    if elapsed_decades <= 0:
        return None
    intercept = float(coefficients[0])
    first_x = (first_year - 2000.0) / 10.0
    last_x = (last_year - 2000.0) / 10.0
    fitted_first = float(np.exp(np.clip(intercept + beta * first_x, -25.0, 25.0)))
    fitted_last = float(np.exp(np.clip(intercept + beta * last_x, -25.0, 25.0)))
    display_change = (fitted_last - fitted_first) / elapsed_decades

    def change_for(candidate: float) -> float:
        first = np.exp(np.clip(intercept + candidate * first_x, -25.0, 25.0))
        last = np.exp(np.clip(intercept + candidate * last_x, -25.0, 25.0))
        return float((last - first) / elapsed_decades)

    low, high = sorted((change_for(beta - 1.96 * beta_se), change_for(beta + 1.96 * beta_se)))
    return {
        "raw_slope_per_decade": beta,
        "raw_ci_low_per_decade": beta - 1.96 * beta_se,
        "raw_ci_high_per_decade": beta + 1.96 * beta_se,
        "display_slope_per_decade": float(display_change),
        "display_ci_low_per_decade": low,
        "display_ci_high_per_decade": high,
        "fitted_first": fitted_first,
        "fitted_last": fitted_last,
        "p_value": float(2.0 * stats.norm.sf(abs(beta / beta_se))) if beta_se > 0 else np.nan,
        "rate_ratio_per_decade": float(np.exp(np.clip(beta, -25.0, 25.0))),
        "poisson_converged": True,
    }


def fit_continuous_trends(
    sample: pd.DataFrame,
    variables: list[str],
    minimum_years: int,
    minimum_span_years: int,
) -> pd.DataFrame:
    """Fit annualized Theil-Sen/Mann-Kendall trends by catchment."""
    rows: list[dict[str, Any]] = []
    for variable in variables:
        for gcin, frame in sample.groupby("GCIN", sort=False):
            subset = frame[["peak_year", variable]].dropna().sort_values("peak_year")
            annual = subset.groupby("peak_year", as_index=False).agg(
                value=(variable, "mean"), events=(variable, "size")
            )
            if len(annual) < minimum_years:
                continue
            span = int(annual["peak_year"].max() - annual["peak_year"].min() + 1)
            if span < minimum_span_years:
                continue
            estimate = theil_sen_per_decade(
                annual["peak_year"].to_numpy(float), annual["value"].to_numpy(float)
            )
            rows.append({
                "GCIN": int(gcin),
                "variable": variable,
                "n_observations": int(len(subset)),
                "n_years": int(len(annual)),
                "first_year": int(annual["peak_year"].min()),
                "last_year": int(annual["peak_year"].max()),
                "year_span": span,
                "mean_level": float(annual["value"].mean()),
                **estimate,
            })
    return pd.DataFrame(rows)
