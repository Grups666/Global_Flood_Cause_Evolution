from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .io import benjamini_hochberg


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
        "sen_intercept": float(intercept),
        "sen_ci_low_per_decade": float(low * 10.0),
        "sen_ci_high_per_decade": float(high * 10.0),
        **mk,
    }


def fit_continuous_trends(
    sample: pd.DataFrame,
    variables: list[str],
    alpha: float,
    minimum_years: int = 10,
    minimum_span_years: int = 20,
) -> pd.DataFrame:
    """Estimate one non-parametric trend per catchment and continuous metric.

    Multiple selected floods can occur in one calendar year.  The event values
    are therefore averaged within catchment-year before fitting so a year with
    several reconstructed events cannot receive more trend weight solely for
    that reason.  ``n_observations`` retains the underlying event count while
    ``n_years`` records the number of annual values used by Theil-Sen and
    Mann-Kendall.
    """
    rows: list[dict[str, Any]] = []
    for variable in variables:
        for gcin, frame in sample.groupby("GCIN", sort=False):
            subset = frame[["peak_year", variable]].dropna().sort_values("peak_year")
            annual = subset.groupby("peak_year", as_index=False).agg(
                value=(variable, "mean"),
                events=(variable, "size"),
            )
            if len(annual) < minimum_years:
                continue
            year_span = int(annual["peak_year"].max() - annual["peak_year"].min() + 1)
            if year_span < minimum_span_years:
                continue
            estimate = theil_sen_per_decade(
                annual["peak_year"].to_numpy(float), annual["value"].to_numpy(float)
            )
            rows.append({
                "GCIN": int(gcin),
                "variable": variable,
                "n_observations": len(subset),
                "n_years": int(len(annual)),
                "first_year": int(annual["peak_year"].min()),
                "last_year": int(annual["peak_year"].max()),
                "year_span": year_span,
                "mean_level": float(annual["value"].mean()),
                **estimate,
            })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["metric_q"] = result.groupby("variable", group_keys=False)["mk_p"].apply(
        benjamini_hochberg
    )
    result["family_q"] = benjamini_hochberg(result["mk_p"])
    # Compatibility alias used by existing audit and presentation code.
    result["mk_q"] = result["metric_q"]
    result["direction"] = np.select(
        [result["sen_slope_per_decade"] > 0, result["sen_slope_per_decade"] < 0],
        ["increase", "decrease"],
        default="stable",
    )
    result["fdr_significant"] = result["metric_q"] < alpha
    result["family_fdr_significant"] = result["family_q"] < alpha
    result["display_slope_per_decade"] = result["sen_slope_per_decade"]
    result["display_ci_low_per_decade"] = result["sen_ci_low_per_decade"]
    result["display_ci_high_per_decade"] = result["sen_ci_high_per_decade"]
    result["display_unit"] = "units per decade"
    result["fitted_first_level"] = (
        result["sen_intercept"]
        + result["sen_slope_per_decade"] * result["first_year"] / 10.0
    )
    result["fitted_last_level"] = (
        result["sen_intercept"]
        + result["sen_slope_per_decade"] * result["last_year"] / 10.0
    )
    percentage_points = result["variable"].eq("intensity_fraction")
    result.loc[percentage_points, "display_slope_per_decade"] *= 100.0
    result.loc[percentage_points, "display_ci_low_per_decade"] *= 100.0
    result.loc[percentage_points, "display_ci_high_per_decade"] *= 100.0
    result.loc[percentage_points, "display_unit"] = "percentage points per decade"
    reference = result["mean_level"].replace(0, np.nan)
    result["relative_slope_percent_per_decade"] = (
        100.0 * result["sen_slope_per_decade"] / reference
    )
    result["relative_ci_low_percent_per_decade"] = (
        100.0 * result["sen_ci_low_per_decade"] / reference
    )
    result["relative_ci_high_percent_per_decade"] = (
        100.0 * result["sen_ci_high_per_decade"] / reference
    )
    rain = result["variable"].isin(["p_max_daily_mm", "p_volume_daily_mm"])
    duration = result["variable"].eq("precip_duration_days")
    result.loc[rain, "display_unit"] = "mm per decade"
    result.loc[duration, "display_unit"] = "days per decade"
    return result
