from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .io import assign_continent
from .statistics import fit_continuous_trends, theil_sen_per_decade


SAMPLE_FILES = {
    "pot_q95": "primary_extreme_events.parquet",
    "annual_maximum": "sensitivity_annual_maximum_events.parquet",
    "pot_q90": "sensitivity_pot_q90_events.parquet",
    "pot_q975": "sensitivity_pot_q975_events.parquet",
}


def add_mechanism_metrics(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Add only continuous, physically interpretable mechanism variables."""
    result = frame.copy()
    result["precip_duration_days"] = (
        result["end_precip_date"] - result["start_precip_date"]
    ).dt.days + 1
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


def _select_pot(
    events: pd.DataFrame,
    eligible_ids: set[int],
    quantile: float,
    config: dict[str, Any],
) -> pd.DataFrame:
    eligible = events[events["GCIN"].isin(eligible_ids)].copy()
    thresholds = eligible.groupby("GCIN")["q_peak_mm_day"].transform(
        lambda values: values.quantile(quantile)
    )
    selected = eligible[eligible["q_peak_mm_day"] >= thresholds].copy()
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
    if metric == "intensity_fraction":
        return 100.0, "percentage points per decade"
    if metric.startswith("ssi_"):
        return 1.0, "SSI units per decade"
    if metric in {"p_max_daily_mm", "p_volume_daily_mm"}:
        return 1.0, "mm per decade"
    if metric == "precip_duration_days":
        return 1.0, "days per decade"
    return 1.0, "units per decade"


def _fixed_effect_trend(
    frame: pd.DataFrame, metric: str, minimum_clusters: int = 2
) -> dict[str, Any] | None:
    event_data = frame[["GCIN", "peak_year", metric]].dropna().copy()
    data = event_data.groupby(["GCIN", "peak_year"], as_index=False).agg(
        **{metric: (metric, "mean")},
        events=(metric, "size"),
    )
    clusters = int(data["GCIN"].nunique())
    modeled_observations = len(data)
    if clusters < minimum_clusters or modeled_observations <= clusters + 1:
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
    degrees_residual = modeled_observations - clusters - 1
    correction = (
        clusters
        / (clusters - 1)
        * (modeled_observations - 1)
        / degrees_residual
    )
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
    reference_raw = float(data.groupby("GCIN")["y"].mean().mean())
    relative = 100.0 * beta / reference_raw if reference_raw != 0 else np.nan
    relative_low = (
        100.0 * (beta - t_critical * standard_error) / reference_raw
        if reference_raw != 0 else np.nan
    )
    relative_high = (
        100.0 * (beta + t_critical * standard_error) / reference_raw
        if reference_raw != 0 else np.nan
    )
    return {
        "observations": int(len(event_data)),
        "modeled_observations": int(modeled_observations),
        "catchments": clusters,
        "mean_level": float(reference_raw * scale),
        "slope_per_decade": float(slope),
        "ci_low": float(low),
        "ci_high": float(high),
        "relative_slope_percent_per_decade": float(relative),
        "relative_ci_low_percent_per_decade": float(relative_low),
        "relative_ci_high_percent_per_decade": float(relative_high),
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


def _leave_one_year_out_stability(
    sample: pd.DataFrame, candidates: pd.DataFrame
) -> pd.DataFrame:
    """Check whether a catchment trend sign depends on one observed event year."""
    rows: list[dict[str, Any]] = []
    for candidate in candidates[["GCIN", "variable", "sen_slope_per_decade"]].itertuples(
        index=False
    ):
        annual = (
            sample.loc[sample["GCIN"].eq(candidate.GCIN), ["peak_year", candidate.variable]]
            .dropna()
            .groupby("peak_year", as_index=False)
            .agg(value=(candidate.variable, "mean"))
            .sort_values("peak_year")
        )
        slopes: list[float] = []
        if len(annual) >= 4:
            for year in annual["peak_year"]:
                reduced = annual[annual["peak_year"].ne(year)]
                estimate = theil_sen_per_decade(
                    reduced["peak_year"].to_numpy(float),
                    reduced["value"].to_numpy(float),
                )
                slopes.append(float(estimate["sen_slope_per_decade"]))
        values = np.asarray(slopes, dtype=float)
        primary_sign = np.sign(float(candidate.sen_slope_per_decade))
        rows.append(
            {
                "GCIN": int(candidate.GCIN),
                "variable": str(candidate.variable),
                "leave_one_year_out_replicates": int(len(values)),
                "leave_one_year_out_min": float(values.min()) if len(values) else np.nan,
                "leave_one_year_out_max": float(values.max()) if len(values) else np.nan,
                "leave_one_year_out_stable": bool(
                    len(values) and np.all(np.sign(values) == primary_sign)
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_catchment_evidence(
    trend_tables: dict[str, pd.DataFrame],
    primary_events: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble primary catchment estimates and their sensitivity evidence."""
    alpha = float(config["trends"]["alpha"])
    primary_sample = str(config["event_samples"]["primary"])
    primary_metrics = list(config["local_analysis"]["primary_metrics"])
    all_trends = pd.concat(
        [frame.assign(sample=name) for name, frame in trend_tables.items()],
        ignore_index=True,
    )
    primary = all_trends[all_trends["sample"].eq(primary_sample)].copy()
    sensitivity_names = list(config["event_samples"]["sensitivity_samples"])
    for sample_name in sensitivity_names:
        alternate = all_trends[all_trends["sample"].eq(sample_name)][
            ["GCIN", "variable", "sen_slope_per_decade", "display_slope_per_decade", "mk_p"]
        ].rename(
            columns={
                "sen_slope_per_decade": f"{sample_name}_raw_slope",
                "display_slope_per_decade": f"{sample_name}_slope",
                "mk_p": f"{sample_name}_p",
            }
        )
        primary = primary.merge(alternate, on=["GCIN", "variable"], how="left")

    primary_sign = np.sign(primary["sen_slope_per_decade"])
    q90 = primary["pot_q90_raw_slope"]
    q975 = primary["pot_q975_raw_slope"]
    annual_maximum = primary["annual_maximum_raw_slope"]
    primary["alternative_sample_direction_stable"] = (
        q90.notna()
        & q975.notna()
        & annual_maximum.notna()
        & np.sign(q90).eq(primary_sign)
        & np.sign(q975).eq(primary_sign)
        & np.sign(annual_maximum).eq(primary_sign)
    )

    wet_metrics = [
        f"ssi_{window}d" for window in config["classification"]["ssi_windows_days"]
    ]
    wet_pivot = primary[primary["variable"].isin(wet_metrics)].pivot(
        index="GCIN", columns="variable", values="sen_slope_per_decade"
    ).reindex(columns=wet_metrics)
    wet_stable = wet_pivot.notna().all(axis=1) & np.sign(wet_pivot).nunique(axis=1).eq(1)
    primary = primary.merge(
        wet_stable.rename("wetness_window_stable"),
        left_on="GCIN",
        right_index=True,
        how="left",
    )
    primary.loc[~primary["variable"].isin(wet_metrics), "wetness_window_stable"] = True

    candidates = primary[
        primary["variable"].isin(primary_metrics) & primary["mk_p"].lt(alpha)
    ]
    leave_one_year = _leave_one_year_out_stability(primary_events, candidates)
    primary = primary.merge(leave_one_year, on=["GCIN", "variable"], how="left")
    primary["leave_one_year_out_stable"] = primary["leave_one_year_out_stable"].fillna(
        False
    )
    primary["robust_local_trend"] = (
        primary["variable"].isin(primary_metrics)
        & primary["mk_p"].lt(alpha)
        & primary["alternative_sample_direction_stable"]
        & primary["leave_one_year_out_stable"]
        & primary["wetness_window_stable"].fillna(False)
    )
    is_wetness = primary["variable"].isin(wet_metrics)
    primary["local_check_count"] = (
        primary["mk_p"].lt(alpha).astype(int)
        + primary["alternative_sample_direction_stable"].fillna(False).astype(int)
        + primary["leave_one_year_out_stable"].fillna(False).astype(int)
        + (is_wetness & primary["wetness_window_stable"].fillna(False)).astype(int)
    )
    primary["local_check_total"] = np.where(is_wetness, 4, 3)
    primary["evidence_grade"] = np.where(
        primary["robust_local_trend"], "robust", "estimate"
    )
    return primary, all_trends


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
    samples = {
        "pot_q95": _select_pot(events, eligible_ids, 0.95, config),
        "annual_maximum": _select_annual_maximum(events, eligible_ids),
        "pot_q90": _select_pot(events, eligible_ids, 0.90, config),
        "pot_q975": _select_pot(events, eligible_ids, 0.975, config),
    }
    _write_samples(samples, config["paths"]["derived_data"])

    tables = config["paths"]["tables"]
    coverage.to_csv(tables / "record_eligibility.csv", index=False)
    metrics = [
        *config["trends"]["continuous_primary_metrics"],
            *config["trends"]["physical_driver_metrics"],
    ]
    panel = _global_regional_trends(samples, metrics)
    panel.to_csv(tables / "global_regional_trends.csv", index=False)
    trajectories = _annual_adjusted_trajectories(
        samples["pot_q95"],
        [
            *config["trends"]["continuous_primary_metrics"],
        ],
    )
    trajectories.to_csv(tables / "global_regional_trajectories.csv", index=False)

    catchment_metrics = list(
        dict.fromkeys(
            [
                *config["local_analysis"]["displayed_metrics"],
                *config["local_analysis"]["driver_metrics"],
            ]
        )
    )
    primary_metrics = list(config["local_analysis"]["primary_metrics"])
    trend_tables: dict[str, pd.DataFrame] = {}
    for sample_name, sample in samples.items():
        variables = catchment_metrics if sample_name == "pot_q95" else primary_metrics
        trend_tables[sample_name] = fit_continuous_trends(
            sample,
            variables,
            minimum_years=int(config["event_samples"]["minimum_events"]),
            minimum_span_years=int(
                config["event_samples"]["minimum_selected_span_years"]
            ),
        )
    catchment_trends, catchment_sensitivity = _build_catchment_evidence(
        trend_tables, samples["pot_q95"], config
    )
    metadata = events[
        ["GCIN", "country", "continent", "longitude", "latitude", "snow_fraction"]
    ].drop_duplicates("GCIN")
    catchment_trends = catchment_trends.merge(
        metadata, on="GCIN", how="left", validate="many_to_one"
    )
    catchment_sensitivity = catchment_sensitivity.merge(
        metadata, on="GCIN", how="left", validate="many_to_one"
    )
    catchment_trends.to_csv(tables / "catchment_mechanism_trends.csv", index=False)
    catchment_sensitivity.to_csv(
        tables / "catchment_sensitivity_trends.csv", index=False
    )

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
        "catchment_primary_tests": int(
            catchment_trends["variable"].isin(primary_metrics).sum()
        ),
        "robust_catchment_trends": int(
            catchment_trends["robust_local_trend"].sum()
        ),
        "elapsed_seconds": time.time() - started,
    }
    output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
