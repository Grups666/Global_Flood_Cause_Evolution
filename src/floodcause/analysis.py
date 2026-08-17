from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .io import assign_continent
from .statistics import fit_continuous_trends


SAMPLE_FILES = {
    "pot_q95": "primary_extreme_events.parquet",
    "annual_maximum": "sensitivity_annual_maximum_events.parquet",
    "pot_q90": "sensitivity_pot_q90_events.parquet",
    "pot_q95_gap10": "sensitivity_pot_q95_gap10_events.parquet",
    "pot_q975": "sensitivity_pot_q975_events.parquet",
}


def _wetness_class(values: pd.Series, thresholds: list[float]) -> pd.Categorical:
    low, high = thresholds
    return pd.cut(
        values,
        bins=[-np.inf, low, high, np.inf],
        labels=["Dry", "Moderate", "Wet"],
        right=True,
    )


def add_mechanism_metrics(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Add continuous mechanism drivers and secondary interpretation labels."""
    result = frame.copy()
    classification = config["classification"]
    threshold = float(classification["intensity_fraction_threshold"])
    threshold_high = float(classification["intensity_fraction_sensitivity_threshold"])
    cv_threshold = float(classification["intensity_cv_threshold"])

    result["precip_duration_days"] = (
        result["end_precip_date"] - result["start_precip_date"]
    ).dt.days + 1
    result["log_p_max"] = np.log(result["p_max_daily_mm"].clip(lower=1e-6))
    result["log_p_volume"] = np.log(result["p_volume_daily_mm"].clip(lower=1e-6))
    result["log_precip_duration"] = np.log(result["precip_duration_days"].clip(lower=1))
    result["intensity_050"] = (result["intensity_fraction"] > threshold).astype("Int64")
    result["intensity_075"] = (result["intensity_fraction"] > threshold_high).astype("Int64")
    result["intensity_joint_050_cv1"] = (
        (result["intensity_fraction"] > threshold)
        & (result["precipitation_cv"] > cv_threshold)
    ).astype("Int64")
    result["rainfall_organization"] = np.where(
        result["intensity_050"].eq(1), "Intensity-dominated", "Volume-dominated"
    )

    for window in classification["ssi_windows_days"]:
        wetness = _wetness_class(
            result[f"ssi_{window}d"], classification["ssi_thresholds"]
        )
        result[f"wetness_{window}d"] = wetness
        result[f"wet_{window}d"] = (wetness == "Wet").astype("Int64")
    return result


def _study_events(features: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    study = config["study"]
    required = [
        "q_peak_mm_day",
        "peak_year",
        "intensity_fraction",
        "p_max_daily_mm",
        "p_volume_daily_mm",
    ]
    valid = features.dropna(subset=required).copy()
    return valid[
        valid["peak_year"].between(int(study["start_year"]), int(study["end_year"]))
    ].copy()


def _record_eligibility(
    events: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, set[int]]:
    index = events.groupby(["GCIN", "peak_year"])["q_peak_mm_day"].idxmax()
    annual = events.loc[index].copy().sort_values(["GCIN", "peak_year"])
    coverage = annual.groupby("GCIN").agg(
        n_event_years=("peak_year", "nunique"),
        first_year=("peak_year", "min"),
        last_year=("peak_year", "max"),
    )
    coverage["record_span_years"] = coverage["last_year"] - coverage["first_year"] + 1
    coverage["coverage_fraction"] = (
        coverage["n_event_years"] / coverage["record_span_years"]
    )
    study = config["study"]
    coverage["eligible"] = (
        (coverage["n_event_years"] >= int(study["minimum_annual_observations"]))
        & (coverage["record_span_years"] >= int(study["minimum_record_span_years"]))
        & (coverage["coverage_fraction"] >= float(study["minimum_record_coverage"]))
    )
    eligible = set(coverage.index[coverage["eligible"]].astype(int))
    return coverage.reset_index(), eligible


def _screen_selected_events(
    selected: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    settings = config["event_samples"]
    summary = selected.groupby("GCIN").agg(
        selected_events=("event_key", "size"),
        selected_first_year=("peak_year", "min"),
        selected_last_year=("peak_year", "max"),
    )
    summary["selected_span_years"] = (
        summary["selected_last_year"] - summary["selected_first_year"] + 1
    )
    keep = summary.index[
        (summary["selected_events"] >= int(settings["minimum_events"]))
        & (
            summary["selected_span_years"]
            >= int(settings["minimum_selected_span_years"])
        )
    ]
    return selected[selected["GCIN"].isin(set(keep))].copy()


def _decluster_peak_dates(frame: pd.DataFrame, gap_days: int) -> pd.DataFrame:
    """Keep the largest peak from runs separated by less than ``gap_days``."""
    rows: list[pd.DataFrame] = []
    for _, catchment in frame.groupby("GCIN", sort=False):
        ordered = catchment.sort_values("q_peak_date").copy()
        gaps = ordered["q_peak_date"].diff().dt.days
        ordered["cluster"] = gaps.ge(gap_days).fillna(True).cumsum()
        chosen = ordered.loc[
            ordered.groupby("cluster")["q_peak_mm_day"].idxmax()
        ].drop(columns="cluster")
        rows.append(chosen)
    if not rows:
        return frame.iloc[0:0].copy()
    return pd.concat(rows, ignore_index=True)


def _select_pot(
    events: pd.DataFrame,
    eligible_ids: set[int],
    quantile: float,
    config: dict[str, Any],
    decluster_gap_days: int | None = None,
) -> pd.DataFrame:
    eligible = events[events["GCIN"].isin(eligible_ids)].copy()
    thresholds = eligible.groupby("GCIN")["q_peak_mm_day"].transform(
        lambda values: values.quantile(quantile)
    )
    selected = eligible[eligible["q_peak_mm_day"] >= thresholds].copy()
    if decluster_gap_days is not None:
        selected = _decluster_peak_dates(selected, decluster_gap_days)
    return _screen_selected_events(selected, config).sort_values(
        ["GCIN", "q_peak_date"]
    )


def _select_annual_maximum(
    events: pd.DataFrame, eligible_ids: set[int]
) -> pd.DataFrame:
    eligible = events[events["GCIN"].isin(eligible_ids)]
    index = eligible.groupby(["GCIN", "peak_year"])["q_peak_mm_day"].idxmax()
    return eligible.loc[index].copy().sort_values(["GCIN", "peak_year"])


def _metric_scale(metric: str) -> tuple[float, str]:
    if metric in {"intensity_fraction", "intensity_050", "intensity_075"}:
        return 100.0, "percentage points per decade"
    if metric.startswith("ssi_"):
        return 1.0, "SSI units per decade"
    if metric.startswith("log_"):
        return 1.0, "log units per decade"
    return 1.0, "units per decade"


def _fixed_effect_trend(frame: pd.DataFrame, metric: str) -> dict[str, Any] | None:
    data = frame[["GCIN", "peak_year", metric]].dropna().copy()
    clusters = int(data["GCIN"].nunique())
    observations = len(data)
    if clusters < 5 or observations <= clusters + 1:
        return None
    data["x"] = (data["peak_year"].astype(float) - 2000.0) / 10.0
    data["y"] = data[metric].astype(float)
    data["x_within"] = data["x"] - data.groupby("GCIN")["x"].transform("mean")
    data["y_within"] = data["y"] - data.groupby("GCIN")["y"].transform("mean")
    denominator = float(np.square(data["x_within"]).sum())
    if denominator <= 0:
        return None
    beta = float((data["x_within"] * data["y_within"]).sum() / denominator)
    residual = data["y_within"] - beta * data["x_within"]
    scores = (data["x_within"] * residual).groupby(data["GCIN"]).sum()
    degrees_residual = observations - clusters - 1
    correction = clusters / (clusters - 1) * (observations - 1) / degrees_residual
    variance = correction * float(np.square(scores).sum()) / denominator**2
    standard_error = float(np.sqrt(max(variance, 0.0)))
    t_value = beta / standard_error if standard_error > 0 else np.nan
    p_value = (
        float(2.0 * stats.t.sf(abs(t_value), clusters - 1))
        if np.isfinite(t_value)
        else np.nan
    )
    t_critical = float(stats.t.ppf(0.975, clusters - 1))
    scale, unit = _metric_scale(metric)
    slope = beta * scale
    low = (beta - t_critical * standard_error) * scale
    high = (beta + t_critical * standard_error) * scale
    if metric.startswith("log_"):
        slope = 100.0 * np.expm1(beta)
        low = 100.0 * np.expm1(beta - t_critical * standard_error)
        high = 100.0 * np.expm1(beta + t_critical * standard_error)
        unit = "approximate percent per decade"
    return {
        "observations": observations,
        "catchments": clusters,
        "mean_level": float(data["y"].mean() * scale),
        "slope_per_decade": float(slope),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": p_value,
        "slope_unit": unit,
    }


def _global_regional_trends(
    samples: dict[str, pd.DataFrame], metrics: list[str]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for sample_name, sample in samples.items():
        for metric in metrics:
            metric_frame = sample.dropna(subset=[metric])
            regions = [("Global", metric_frame), *list(metric_frame.groupby("continent"))]
            for region, region_frame in regions:
                estimate = _fixed_effect_trend(region_frame, metric)
                if estimate is not None:
                    rows.append(
                        {
                            "sample": sample_name,
                            "region": region,
                            "metric": metric,
                            **estimate,
                        }
                    )
    return pd.DataFrame(rows)


def _annual_adjusted_trajectories(
    sample: pd.DataFrame, metrics: list[str]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        available = sample[["GCIN", "continent", "peak_year", metric]].dropna()
        for region, frame in [("Global", available), *list(available.groupby("continent"))]:
            catchment_year = (
                frame.groupby(["GCIN", "peak_year"], as_index=False)
                .agg(value=(metric, "mean"), events=(metric, "size"))
            )
            catchment_means = catchment_year.groupby("GCIN")["value"].transform("mean")
            reference = float(
                catchment_year.groupby("GCIN")["value"].mean().mean()
            )
            catchment_year["adjusted"] = catchment_year["value"] - catchment_means + reference
            annual = catchment_year.groupby("peak_year").agg(
                adjusted_mean=("adjusted", "mean"),
                catchments=("GCIN", "nunique"),
                events=("events", "sum"),
            )
            for year, values in annual.iterrows():
                rows.append(
                    {
                        "sample": "pot_q95",
                        "region": region,
                        "metric": metric,
                        "year": int(year),
                        "adjusted_mean": float(values["adjusted_mean"]),
                        "catchments": int(values["catchments"]),
                        "events": int(values["events"]),
                    }
                )
    return pd.DataFrame(rows)


def _independence_diagnostics(sample: pd.DataFrame) -> dict[str, Any]:
    ordered = sample.sort_values(["GCIN", "q_peak_date"])
    previous_peak = ordered.groupby("GCIN")["q_peak_date"].shift()
    gaps = (ordered["q_peak_date"] - previous_peak).dt.days.dropna()
    previous_end = ordered.groupby("GCIN")["end_stormflow_date"].shift()
    overlaps = (ordered["start_stormflow_date"] <= previous_end).fillna(False)
    return {
        "adjacent_pairs": int(len(gaps)),
        "minimum_peak_gap_days": int(gaps.min()) if len(gaps) else None,
        "pairs_under_5_days": int((gaps < 5).sum()),
        "pairs_under_10_days": int((gaps < 10).sum()),
        "stormflow_window_overlaps": int(overlaps.sum()),
    }


def _write_samples(
    samples: dict[str, pd.DataFrame], derived: Path
) -> None:
    for name, sample in samples.items():
        sample.to_parquet(
            derived / SAMPLE_FILES[name], index=False, compression="zstd"
        )


def run_analysis(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    output_summary = config["paths"]["logs"] / "analysis_summary.json"
    if output_summary.exists() and not force:
        return json.loads(output_summary.read_text(encoding="utf-8"))

    started = time.time()
    features = pd.read_parquet(config["paths"]["derived_data"] / "event_features.parquet")
    features["continent"] = assign_continent(features["country"])
    events = add_mechanism_metrics(_study_events(features, config), config)
    coverage, eligible_ids = _record_eligibility(events, config)
    settings = config["event_samples"]
    gap = int(settings["declustering_gap_days"])

    samples = {
        "pot_q95": _select_pot(events, eligible_ids, 0.95, config),
        "annual_maximum": _select_annual_maximum(events, eligible_ids),
        "pot_q90": _select_pot(events, eligible_ids, 0.90, config),
        "pot_q95_gap10": _select_pot(events, eligible_ids, 0.95, config, gap),
        "pot_q975": _select_pot(events, eligible_ids, 0.975, config),
    }
    _write_samples(samples, config["paths"]["derived_data"])

    tables = config["paths"]["tables"]
    coverage.to_csv(tables / "record_eligibility.csv", index=False)
    metrics = [
        *config["trends"]["continuous_primary_metrics"],
        *config["trends"]["interpretive_metrics"],
        *config["trends"]["physical_driver_metrics"],
    ]
    panel = _global_regional_trends(samples, metrics)
    panel.to_csv(tables / "global_regional_trends.csv", index=False)
    trajectories = _annual_adjusted_trajectories(
        samples["pot_q95"],
        [
            *config["trends"]["continuous_primary_metrics"],
            *config["trends"]["interpretive_metrics"],
        ],
    )
    trajectories.to_csv(tables / "global_regional_trajectories.csv", index=False)

    catchment_metrics = [
        *config["local_analysis"]["displayed_metrics"],
        *config["local_analysis"]["driver_metrics"],
    ]
    catchment_trends = fit_continuous_trends(
        samples["pot_q95"], catchment_metrics, float(config["trends"]["alpha"])
    )
    metadata = events[
        ["GCIN", "country", "continent", "longitude", "latitude", "snow_fraction"]
    ].drop_duplicates("GCIN")
    catchment_trends = catchment_trends.merge(
        metadata, on="GCIN", how="left", validate="many_to_one"
    )
    catchment_trends.to_csv(tables / "catchment_mechanism_trends.csv", index=False)

    diagnostics_rows = []
    for name, sample in samples.items():
        independence = _independence_diagnostics(sample)
        diagnostics_rows.append(
            {
                "sample": name,
                "events": len(sample),
                "catchments": int(sample["GCIN"].nunique()),
                "first_year": int(sample["peak_year"].min()),
                "last_year": int(sample["peak_year"].max()),
                **independence,
            }
        )
    diagnostics = pd.DataFrame(diagnostics_rows)
    diagnostics.to_csv(tables / "extreme_sample_diagnostics.csv", index=False)

    summary = {
        "status": "complete",
        "primary_sample": "pot_q95",
        "eligible_record_catchments": len(eligible_ids),
        "sample_counts": {
            name: {
                "events": len(sample),
                "catchments": int(sample["GCIN"].nunique()),
            }
            for name, sample in samples.items()
        },
        "primary_independence": _independence_diagnostics(samples["pot_q95"]),
        "catchment_trend_rows": len(catchment_trends),
        "elapsed_seconds": time.time() - started,
    }
    output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
