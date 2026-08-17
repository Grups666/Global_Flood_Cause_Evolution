from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .io import assign_continent
from .statistics import fit_binary_trends, fit_continuous_trends


def _wetness_class(values: pd.Series, thresholds: list[float]) -> pd.Categorical:
    low, high = thresholds
    return pd.cut(
        values,
        bins=[-np.inf, low, high, np.inf],
        labels=["Dry", "Moderate", "Wet"],
        right=True,
    )


def _add_classifications(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    classification = config["classification"]
    primary_threshold = float(classification["intensity_fraction_threshold"])
    sensitivity_threshold = float(classification["intensity_fraction_sensitivity_threshold"])
    cv_threshold = float(classification["intensity_cv_threshold"])
    result["intensity_050"] = (result["intensity_fraction"] > primary_threshold).astype(int)
    result["intensity_joint_050_cv1"] = (
        (result["intensity_fraction"] > primary_threshold)
        & (result["precipitation_cv"] > cv_threshold)
    ).astype(int)
    result["intensity_075"] = (result["intensity_fraction"] > sensitivity_threshold).astype(int)
    for window in classification["ssi_windows_days"]:
        result[f"wetness_{window}d"] = _wetness_class(
            result[f"ssi_{window}d"], classification["ssi_thresholds"]
        )
        result[f"wet_{window}d"] = (result[f"wetness_{window}d"] == "Wet").astype("Int64")
        result[f"dry_{window}d"] = (result[f"wetness_{window}d"] == "Dry").astype("Int64")
    primary_window = int(classification["primary_ssi_window_days"])
    result["rainfall_organization"] = np.where(
        result["intensity_050"].eq(1), "Intensity", "Volume"
    )
    result["cause_primary"] = (
        result["rainfall_organization"].astype(str)
        + "-"
        + result[f"wetness_{primary_window}d"].astype(str)
    )
    result.loc[result[f"ssi_{primary_window}d"].isna(), "cause_primary"] = np.nan
    for cause in (
        "Intensity-Dry", "Intensity-Moderate", "Intensity-Wet",
        "Volume-Dry", "Volume-Moderate", "Volume-Wet",
    ):
        result[f"cause_{cause.lower().replace('-', '_')}"] = (
            result["cause_primary"] == cause
        ).astype(int)
    return result


def _select_annual_maximum(features: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid = features.dropna(subset=["q_peak_mm_day", "peak_year", "intensity_fraction"]).copy()
    study = config["study"]
    valid = valid[
        valid["peak_year"].between(int(study["start_year"]), int(study["end_year"]))
    ]
    index = valid.groupby(["GCIN", "peak_year"])["q_peak_mm_day"].idxmax()
    annual = valid.loc[index].copy().sort_values(["GCIN", "peak_year"])
    coverage = annual.groupby("GCIN").agg(
        n_years=("peak_year", "nunique"),
        first_year=("peak_year", "min"),
        last_year=("peak_year", "max"),
    )
    coverage["record_span_years"] = coverage["last_year"] - coverage["first_year"] + 1
    coverage["coverage_fraction"] = coverage["n_years"] / coverage["record_span_years"]
    coverage["eligible_for_trends"] = (
        (coverage["n_years"] >= int(study["minimum_annual_observations"]))
        & (coverage["record_span_years"] >= int(study["minimum_record_span_years"]))
        & (coverage["coverage_fraction"] >= float(study["minimum_record_coverage"]))
    )
    eligible_ids = set(coverage.index[coverage["eligible_for_trends"]])
    annual = annual[annual["GCIN"].isin(eligible_ids)].copy()
    return annual, coverage.reset_index()


def _select_pot(features: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    valid = features.dropna(subset=["q_peak_mm_day", "peak_year", "intensity_fraction"]).copy()
    quantile = float(config["event_samples"]["pot_quantile"])
    threshold = valid.groupby("GCIN")["q_peak_mm_day"].transform(lambda values: values.quantile(quantile))
    pot = valid[valid["q_peak_mm_day"] >= threshold].copy()
    counts = pot.groupby("GCIN").size()
    eligible = set(counts.index[counts >= int(config["event_samples"]["minimum_pot_events"])])
    return pot[pot["GCIN"].isin(eligible)].copy()


def _regional_annual_composition(sample: pd.DataFrame) -> pd.DataFrame:
    categories = [
        "Intensity-Dry", "Intensity-Moderate", "Intensity-Wet",
        "Volume-Dry", "Volume-Moderate", "Volume-Wet",
    ]
    grouped = sample.groupby(["continent", "peak_year"], observed=True)
    rows = []
    for (continent, year), frame in grouped:
        denominator = len(frame)
        for category in categories:
            count = int((frame["cause_primary"] == category).sum())
            rows.append({
                "continent": continent,
                "year": int(year),
                "cause": category,
                "count": count,
                "total": denominator,
                "proportion": count / denominator if denominator else np.nan,
            })
    result = pd.DataFrame(rows)
    result["rolling_5yr_proportion"] = result.groupby(
        ["continent", "cause"], observed=True
    )["proportion"].transform(lambda values: values.rolling(5, center=True, min_periods=3).mean())
    return result


def _period_comparison_pooled(sample: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    early_start, early_end = config["trends"]["early_period"]
    late_start, late_end = config["trends"]["late_period"]
    outcomes = [
        "intensity_050", "intensity_joint_050_cv1", "intensity_075",
        *[f"wet_{window}d" for window in config["classification"]["ssi_windows_days"]],
    ]
    rows = []
    for sample_name, frame in [("annual_maximum", sample)]:
        for region, region_frame in [("Global", frame), *list(frame.groupby("continent"))]:
            for outcome in outcomes:
                early = region_frame.loc[region_frame["peak_year"].between(early_start, early_end), outcome].dropna().astype(float)
                late = region_frame.loc[region_frame["peak_year"].between(late_start, late_end), outcome].dropna().astype(float)
                rows.append({
                    "sample": sample_name,
                    "region": region,
                    "outcome": outcome,
                    "early_start": early_start,
                    "early_end": early_end,
                    "late_start": late_start,
                    "late_end": late_end,
                    "early_n": len(early),
                    "late_n": len(late),
                    "early_proportion": early.mean() if len(early) else np.nan,
                    "late_proportion": late.mean() if len(late) else np.nan,
                    "late_minus_early_percentage_points": (late.mean() - early.mean()) * 100 if len(early) and len(late) else np.nan,
                })
    return pd.DataFrame(rows)


def _period_comparison_paired(
    sample: pd.DataFrame, config: dict[str, Any], sample_name: str
) -> pd.DataFrame:
    """Compare equal early/late windows within catchments before regional aggregation."""
    early_start, early_end = config["trends"]["early_period"]
    late_start, late_end = config["trends"]["late_period"]
    outcomes = [
        "intensity_050", "intensity_joint_050_cv1", "intensity_075",
        *[f"wet_{window}d" for window in config["classification"]["ssi_windows_days"]],
    ]
    catchment_rows = []
    for (gcin, continent), frame in sample.groupby(["GCIN", "continent"], observed=True):
        for outcome in outcomes:
            early = frame.loc[frame["peak_year"].between(early_start, early_end), outcome].dropna().astype(float)
            late = frame.loc[frame["peak_year"].between(late_start, late_end), outcome].dropna().astype(float)
            if len(early) < 5 or len(late) < 5:
                continue
            catchment_rows.append({
                "sample": sample_name,
                "GCIN": int(gcin),
                "continent": continent,
                "outcome": outcome,
                "early_n": len(early),
                "late_n": len(late),
                "early_proportion": early.mean(),
                "late_proportion": late.mean(),
                "difference_percentage_points": (late.mean() - early.mean()) * 100.0,
            })
    catchments = pd.DataFrame(catchment_rows)
    rows = []
    for outcome in outcomes:
        outcome_frame = catchments[catchments["outcome"] == outcome]
        for region, region_frame in [("Global", outcome_frame), *list(outcome_frame.groupby("continent"))]:
            differences = region_frame["difference_percentage_points"].dropna()
            if differences.empty:
                continue
            standard_error = differences.std(ddof=1) / np.sqrt(len(differences)) if len(differences) > 1 else np.nan
            t_critical = stats.t.ppf(0.975, len(differences) - 1) if len(differences) > 1 else np.nan
            try:
                wilcoxon_p = float(stats.wilcoxon(differences, zero_method="zsplit").pvalue)
            except ValueError:
                wilcoxon_p = np.nan
            rows.append({
                "sample": sample_name,
                "region": region,
                "outcome": outcome,
                "catchments": len(differences),
                "mean_difference_percentage_points": differences.mean(),
                "mean_ci_low": differences.mean() - t_critical * standard_error,
                "mean_ci_high": differences.mean() + t_critical * standard_error,
                "median_difference_percentage_points": differences.median(),
                "wilcoxon_p": wilcoxon_p,
                "catchments_increasing": int((differences > 0).sum()),
                "catchments_decreasing": int((differences < 0).sum()),
                "catchments_unchanged": int((differences == 0).sum()),
            })
    return pd.DataFrame(rows)


def _fixed_effect_panel_trends(
    sample: pd.DataFrame, config: dict[str, Any], sample_name: str
) -> pd.DataFrame:
    """Estimate within-catchment temporal slopes with catchment-clustered uncertainty."""
    outcomes = [
        "intensity_050", "intensity_joint_050_cv1", "intensity_075",
        *[f"wet_{window}d" for window in config["classification"]["ssi_windows_days"]],
        "intensity_fraction",
        *[f"ssi_{window}d" for window in config["classification"]["ssi_windows_days"]],
    ]
    rows = []
    for outcome in outcomes:
        outcome_frame = sample[["GCIN", "continent", "peak_year", outcome]].dropna()
        for region, frame in [("Global", outcome_frame), *list(outcome_frame.groupby("continent"))]:
            if frame["GCIN"].nunique() < 5:
                continue
            data = frame.copy()
            data["x"] = (data["peak_year"].astype(float) - 2000.0) / 10.0
            data["y"] = data[outcome].astype(float)
            data["x_within"] = data["x"] - data.groupby("GCIN")["x"].transform("mean")
            data["y_within"] = data["y"] - data.groupby("GCIN")["y"].transform("mean")
            denominator = float(np.square(data["x_within"]).sum())
            if denominator <= 0:
                continue
            beta = float((data["x_within"] * data["y_within"]).sum() / denominator)
            data["residual"] = data["y_within"] - beta * data["x_within"]
            scores = data.assign(score=data["x_within"] * data["residual"]).groupby("GCIN")["score"].sum()
            clusters = len(scores)
            observations = len(data)
            degrees_residual = observations - clusters - 1
            correction = (
                clusters / (clusters - 1) * (observations - 1) / degrees_residual
                if clusters > 1 and degrees_residual > 0 else 1.0
            )
            variance = correction * float(np.square(scores).sum()) / (denominator ** 2)
            standard_error = float(np.sqrt(max(variance, 0.0)))
            t_value = beta / standard_error if standard_error > 0 else np.nan
            p_value = float(2 * stats.t.sf(abs(t_value), clusters - 1)) if np.isfinite(t_value) else np.nan
            scale = 100.0 if outcome.startswith(("intensity_0", "intensity_joint", "wet_")) else 1.0
            rows.append({
                "sample": sample_name,
                "region": region,
                "outcome": outcome,
                "observations": observations,
                "catchments": clusters,
                "slope_per_decade": beta * scale,
                "slope_unit": "percentage points per decade" if scale == 100.0 else "index units per decade",
                "ci_low": (beta - 1.96 * standard_error) * scale,
                "ci_high": (beta + 1.96 * standard_error) * scale,
                "cluster_robust_p": p_value,
            })
    return pd.DataFrame(rows)


def run_analysis(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    output_summary = config["paths"]["logs"] / "analysis_summary.json"
    if output_summary.exists() and not force:
        return json.loads(output_summary.read_text(encoding="utf-8"))

    started = time.time()
    features = pd.read_parquet(config["paths"]["derived_data"] / "event_features.parquet")
    features["continent"] = assign_continent(features["country"])
    features = _add_classifications(features, config)
    annual, coverage = _select_annual_maximum(features, config)
    pot = _select_pot(features, config)
    pot = _add_classifications(pot, config)

    tables = config["paths"]["tables"]
    derived = config["paths"]["derived_data"]
    annual.to_parquet(derived / "annual_maximum_events.parquet", index=False, compression="zstd")
    pot.to_parquet(derived / "pot_q95_events.parquet", index=False, compression="zstd")
    coverage.to_csv(tables / "annual_sample_coverage.csv", index=False)

    binary_outcomes = [
        "intensity_050",
        *[f"wet_{window}d" for window in config["classification"]["ssi_windows_days"]],
        *[f"dry_{window}d" for window in config["classification"]["ssi_windows_days"]],
        "cause_intensity_dry", "cause_intensity_moderate", "cause_intensity_wet",
        "cause_volume_dry", "cause_volume_moderate", "cause_volume_wet",
    ]
    binary_trends = fit_binary_trends(
        annual,
        binary_outcomes,
        int(config["trends"]["minimum_occurrences"]),
        int(config["trends"]["minimum_nonoccurrences"]),
        float(config["trends"]["alpha"]),
    )
    continuous_variables = [
        "intensity_fraction",
        *[f"ssi_{window}d" for window in config["classification"]["ssi_windows_days"]],
    ]
    continuous_trends = fit_continuous_trends(
        annual, continuous_variables, float(config["trends"]["alpha"])
    )
    metadata = features[["GCIN", "country", "continent", "longitude", "latitude", "snow_fraction"]].drop_duplicates("GCIN")
    binary_trends = binary_trends.merge(metadata, on="GCIN", how="left", validate="many_to_one")
    continuous_trends = continuous_trends.merge(metadata, on="GCIN", how="left", validate="many_to_one")
    binary_trends.to_csv(tables / "catchment_binary_trends.csv", index=False)
    continuous_trends.to_csv(tables / "catchment_continuous_trends.csv", index=False)

    composition = _regional_annual_composition(annual)
    composition.to_csv(tables / "regional_annual_composition.csv", index=False)
    pooled_comparison = _period_comparison_pooled(annual, config)

    # Add POT composition as a sample-definition sensitivity check.
    pot_period = _period_comparison_pooled(pot, config)
    pot_period["sample"] = "pot_q95"
    pooled_comparison = pd.concat([pooled_comparison, pot_period], ignore_index=True)
    pooled_comparison.to_csv(tables / "period_comparison_pooled.csv", index=False)

    paired_comparison = pd.concat([
        _period_comparison_paired(annual, config, "annual_maximum"),
        _period_comparison_paired(pot, config, "pot_q95"),
    ], ignore_index=True)
    paired_comparison.to_csv(tables / "period_comparison_paired.csv", index=False)

    panel_trends = pd.concat([
        _fixed_effect_panel_trends(annual, config, "annual_maximum"),
        _fixed_effect_panel_trends(pot, config, "pot_q95"),
    ], ignore_index=True)
    panel_trends.to_csv(tables / "panel_fixed_effect_trends.csv", index=False)

    cause_counts = annual.groupby(["continent", "cause_primary"], observed=True).size().rename("events").reset_index()
    cause_counts["region_total"] = cause_counts.groupby("continent")["events"].transform("sum")
    cause_counts["proportion"] = cause_counts["events"] / cause_counts["region_total"]
    cause_counts.to_csv(tables / "cause_composition_by_region.csv", index=False)

    sample_diagnostics = pd.DataFrame([
        {
            "stage": "source event catalogue",
            "events": len(features),
            "catchments": features["GCIN"].nunique(),
        },
        {
            "stage": "valid reconstructed event features",
            "events": int(features[["q_peak_mm_day", "intensity_fraction", "ssi_1d"]].notna().all(axis=1).sum()),
            "catchments": int(features.loc[features[["q_peak_mm_day", "intensity_fraction", "ssi_1d"]].notna().all(axis=1), "GCIN"].nunique()),
        },
        {"stage": "annual maxima before record screen", "events": int(coverage["n_years"].sum()), "catchments": len(coverage)},
        {"stage": "primary annual-max sample", "events": len(annual), "catchments": annual["GCIN"].nunique()},
        {"stage": "POT/Q95 sensitivity sample", "events": len(pot), "catchments": pot["GCIN"].nunique()},
    ])
    sample_diagnostics.to_csv(tables / "sample_diagnostics.csv", index=False)

    summary = {
        "status": "complete",
        "annual_events": len(annual),
        "annual_catchments": int(annual["GCIN"].nunique()),
        "annual_year_min": int(annual["peak_year"].min()),
        "annual_year_max": int(annual["peak_year"].max()),
        "pot_events": len(pot),
        "pot_catchments": int(pot["GCIN"].nunique()),
        "binary_trend_rows": len(binary_trends),
        "continuous_trend_rows": len(continuous_trends),
        "elapsed_seconds": time.time() - started,
    }
    output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
