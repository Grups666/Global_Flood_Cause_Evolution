from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

from .io import benjamini_hochberg


def _load_hydrobasins(directory: Path, level: int) -> gpd.GeoDataFrame:
    layers: list[gpd.GeoDataFrame] = []
    pattern = f"hybas_*_lev{level:02d}_v1c.zip"
    for path in sorted(directory.glob(pattern)):
        layer = gpd.read_file(f"zip://{path.as_posix()}")
        layers.append(
            layer[["HYBAS_ID", "PFAF_ID", "SUB_AREA", "UP_AREA", "geometry"]]
        )
    if not layers:
        raise FileNotFoundError(f"No HydroBASINS files found for level {level}: {directory}")
    result = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), crs=layers[0].crs)
    result["HYBAS_ID"] = result["HYBAS_ID"].astype("int64")
    return result


def _assign_hydrobasins(
    catchments: pd.DataFrame, directory: Path, levels: list[int]
) -> tuple[pd.DataFrame, dict[int, gpd.GeoDataFrame]]:
    points = gpd.GeoDataFrame(
        catchments.copy(),
        geometry=gpd.points_from_xy(catchments["longitude"], catchments["latitude"]),
        crs="EPSG:4326",
    )
    membership = catchments[["GCIN", "country", "longitude", "latitude"]].copy()
    geometries: dict[int, gpd.GeoDataFrame] = {}
    for level in levels:
        basins = _load_hydrobasins(directory, level).to_crs(points.crs)
        geometries[level] = basins
        joined = gpd.sjoin(
            points[["GCIN", "geometry"]], basins, how="left", predicate="within"
        )
        # Boundary points can match more than one polygon. The smallest polygon is
        # the deterministic hydrologically local assignment.
        joined = joined.sort_values(["GCIN", "SUB_AREA"], na_position="last").drop_duplicates(
            "GCIN", keep="first"
        )
        membership = membership.merge(
            joined[["GCIN", "HYBAS_ID", "PFAF_ID", "SUB_AREA", "UP_AREA"]].rename(
                columns={
                    "HYBAS_ID": f"hybas_id_l{level}",
                    "PFAF_ID": f"pfaf_id_l{level}",
                    "SUB_AREA": f"sub_area_km2_l{level}",
                    "UP_AREA": f"up_area_km2_l{level}",
                }
            ),
            on="GCIN",
            how="left",
            validate="one_to_one",
        )
        membership[f"hybas_id_l{level}"] = membership[f"hybas_id_l{level}"].astype(
            "Int64"
        )
    return membership, geometries


def _basin_labels(membership: pd.DataFrame, level: int) -> pd.DataFrame:
    id_column = f"hybas_id_l{level}"
    rows: list[dict[str, Any]] = []
    for basin_id, frame in membership.dropna(subset=[id_column]).groupby(id_column):
        country_counts = frame["country"].value_counts()
        countries = "/".join(country_counts.index[:2].astype(str))
        longitude = float(frame["longitude"].median())
        latitude = float(frame["latitude"].median())
        rows.append(
            {
                "level": level,
                "HYBAS_ID": int(basin_id),
                "basin_code": f"HB{level}-{str(int(basin_id))[-6:]}",
                "basin_label": f"{countries} · {latitude:.1f}°, {longitude:.1f}°",
                "dominant_countries": countries,
                "centroid_longitude": longitude,
                "centroid_latitude": latitude,
                "assigned_catchments": int(frame["GCIN"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def _fixed_effect_slope(frame: pd.DataFrame, outcome: str) -> dict[str, Any] | None:
    data = frame[["GCIN", "peak_year", outcome]].dropna().copy()
    clusters = int(data["GCIN"].nunique())
    if clusters < 2:
        return None
    data["x"] = (data["peak_year"].astype(float) - 2000.0) / 10.0
    data["y"] = data[outcome].astype(float)
    data["x_within"] = data["x"] - data.groupby("GCIN")["x"].transform("mean")
    data["y_within"] = data["y"] - data.groupby("GCIN")["y"].transform("mean")
    denominator = float(np.square(data["x_within"]).sum())
    if denominator <= 0:
        return None
    beta = float((data["x_within"] * data["y_within"]).sum() / denominator)
    data["residual"] = data["y_within"] - beta * data["x_within"]
    scores = data.assign(score=data["x_within"] * data["residual"]).groupby("GCIN")[
        "score"
    ].sum()
    observations = len(data)
    degrees_residual = observations - clusters - 1
    correction = (
        clusters / (clusters - 1) * (observations - 1) / degrees_residual
        if clusters > 1 and degrees_residual > 0
        else 1.0
    )
    variance = correction * float(np.square(scores).sum()) / denominator**2
    standard_error = float(np.sqrt(max(variance, 0.0)))
    t_value = beta / standard_error if standard_error > 0 else np.nan
    p_value = (
        float(2 * stats.t.sf(abs(t_value), clusters - 1))
        if np.isfinite(t_value)
        else np.nan
    )
    t_critical = float(stats.t.ppf(0.975, clusters - 1))
    scale = 100.0 if outcome.startswith(("intensity_", "wet_", "cause_")) else 1.0
    return {
        "observations": observations,
        "catchments": clusters,
        "mean_level": float(data["y"].mean() * scale),
        "slope_per_decade": beta * scale,
        "slope_unit": (
            "percentage points per decade" if scale == 100.0 else "index units per decade"
        ),
        "ci_low": (beta - t_critical * standard_error) * scale,
        "ci_high": (beta + t_critical * standard_error) * scale,
        "cluster_robust_p": p_value,
    }


def _fit_local_trends(
    sample: pd.DataFrame,
    membership: pd.DataFrame,
    sample_name: str,
    levels: list[int],
    outcomes: list[str],
    minimum_catchments: int,
    minimum_observations: int,
) -> pd.DataFrame:
    sample = sample.merge(
        membership[["GCIN", *[f"hybas_id_l{level}" for level in levels]]],
        on="GCIN",
        how="left",
        validate="many_to_one",
    )
    rows: list[dict[str, Any]] = []
    for level in levels:
        id_column = f"hybas_id_l{level}"
        for basin_id, basin_frame in sample.dropna(subset=[id_column]).groupby(id_column):
            if basin_frame["GCIN"].nunique() < minimum_catchments:
                continue
            for outcome in outcomes:
                estimate = _fixed_effect_slope(basin_frame, outcome)
                if estimate is None:
                    continue
                if (
                    estimate["catchments"] < minimum_catchments
                    or estimate["observations"] < minimum_observations
                ):
                    continue
                rows.append(
                    {
                        "sample": sample_name,
                        "level": level,
                        "HYBAS_ID": int(basin_id),
                        "outcome": outcome,
                        **estimate,
                    }
                )
    return pd.DataFrame(rows)


def _add_multiple_testing(
    trends: pd.DataFrame, primary_outcomes: list[str], alpha: float
) -> pd.DataFrame:
    result = trends.copy()
    result["outcome_q"] = result.groupby(
        ["sample", "level", "outcome"], group_keys=False
    )["cluster_robust_p"].apply(benjamini_hochberg)
    result["all_outcomes_q"] = result.groupby(
        ["sample", "level"], group_keys=False
    )["cluster_robust_p"].apply(benjamini_hochberg)
    result["primary_q"] = np.nan
    primary = result["outcome"].isin(primary_outcomes)
    result.loc[primary, "primary_q"] = result.loc[primary].groupby(
        ["sample", "level"], group_keys=False
    )["cluster_robust_p"].apply(benjamini_hochberg)
    result["outcome_fdr_significant"] = result["outcome_q"] < alpha
    result["all_outcomes_fdr_significant"] = result["all_outcomes_q"] < alpha
    result["primary_fdr_significant"] = result["primary_q"] < alpha
    return result


def _paired_period_changes(
    sample: pd.DataFrame,
    membership: pd.DataFrame,
    level: int,
    outcomes: list[str],
    early_period: list[int],
    late_period: list[int],
    minimum_catchments: int,
    minimum_period_observations: int,
    primary_outcomes: list[str],
    alpha: float,
) -> pd.DataFrame:
    id_column = f"hybas_id_l{level}"
    frame = sample.merge(
        membership[["GCIN", id_column]], on="GCIN", how="left", validate="many_to_one"
    )
    early_start, early_end = early_period
    late_start, late_end = late_period
    catchment_rows: list[dict[str, Any]] = []
    for (basin_id, gcin), catchment in frame.dropna(subset=[id_column]).groupby(
        [id_column, "GCIN"]
    ):
        for outcome in outcomes:
            early = catchment.loc[
                catchment["peak_year"].between(early_start, early_end), outcome
            ].dropna()
            late = catchment.loc[
                catchment["peak_year"].between(late_start, late_end), outcome
            ].dropna()
            if (
                len(early) < minimum_period_observations
                or len(late) < minimum_period_observations
            ):
                continue
            catchment_rows.append(
                {
                    "HYBAS_ID": int(basin_id),
                    "GCIN": int(gcin),
                    "outcome": outcome,
                    "early_n": len(early),
                    "late_n": len(late),
                    "early_mean": float(early.mean() * 100.0),
                    "late_mean": float(late.mean() * 100.0),
                    "difference_percentage_points": float((late.mean() - early.mean()) * 100.0),
                }
            )
    catchment_changes = pd.DataFrame(catchment_rows)
    rows: list[dict[str, Any]] = []
    for (basin_id, outcome), group in catchment_changes.groupby(["HYBAS_ID", "outcome"]):
        differences = group["difference_percentage_points"].to_numpy(float)
        if len(differences) < minimum_catchments:
            continue
        standard_error = float(np.std(differences, ddof=1) / np.sqrt(len(differences)))
        t_critical = float(stats.t.ppf(0.975, len(differences) - 1))
        t_test = stats.ttest_1samp(differences, popmean=0.0)
        try:
            wilcoxon_p = float(stats.wilcoxon(differences, zero_method="zsplit").pvalue)
        except ValueError:
            wilcoxon_p = np.nan
        rows.append(
            {
                "level": level,
                "HYBAS_ID": int(basin_id),
                "outcome": outcome,
                "catchments": len(differences),
                "early_start": early_start,
                "early_end": early_end,
                "late_start": late_start,
                "late_end": late_end,
                "early_mean_percentage_points": float(group["early_mean"].mean()),
                "late_mean_percentage_points": float(group["late_mean"].mean()),
                "mean_difference_percentage_points": float(np.mean(differences)),
                "ci_low": float(np.mean(differences) - t_critical * standard_error),
                "ci_high": float(np.mean(differences) + t_critical * standard_error),
                "paired_t_p": float(t_test.pvalue),
                "wilcoxon_p": wilcoxon_p,
            }
        )
    result = pd.DataFrame(rows)
    result["outcome_q"] = result.groupby("outcome", group_keys=False)["paired_t_p"].apply(
        benjamini_hochberg
    )
    result["all_outcomes_q"] = benjamini_hochberg(result["paired_t_p"])
    result["primary_q"] = np.nan
    primary = result["outcome"].isin(primary_outcomes)
    result.loc[primary, "primary_q"] = benjamini_hochberg(
        result.loc[primary, "paired_t_p"]
    )
    result["outcome_fdr_significant"] = result["outcome_q"] < alpha
    result["all_outcomes_fdr_significant"] = result["all_outcomes_q"] < alpha
    result["primary_fdr_significant"] = result["primary_q"] < alpha
    return result


def _parent_lookup(membership: pd.DataFrame, child_level: int, parent_level: int) -> pd.DataFrame:
    child = f"hybas_id_l{child_level}"
    parent = f"hybas_id_l{parent_level}"
    frame = membership.dropna(subset=[child, parent])[[child, parent, "GCIN"]]
    counts = frame.groupby([child, parent])["GCIN"].nunique().rename("overlap").reset_index()
    return (
        counts.sort_values([child, "overlap"], ascending=[True, False])
        .drop_duplicates(child)
        .rename(columns={child: "HYBAS_ID", parent: f"parent_l{parent_level}_id"})
    )


def _build_robustness(
    trends: pd.DataFrame,
    membership: pd.DataFrame,
    paired: pd.DataFrame,
    primary_level: int,
    comparison_levels: list[int],
) -> pd.DataFrame:
    base = trends[
        (trends["sample"] == "annual_maximum") & (trends["level"] == primary_level)
    ].copy()
    for level in comparison_levels:
        lookup = _parent_lookup(membership, primary_level, level)
        parent = trends[
            (trends["sample"] == "annual_maximum") & (trends["level"] == level)
        ][["HYBAS_ID", "outcome", "slope_per_decade", "cluster_robust_p"]].rename(
            columns={
                "HYBAS_ID": f"parent_l{level}_id",
                "slope_per_decade": f"slope_l{level}",
                "cluster_robust_p": f"p_l{level}",
            }
        )
        base = base.merge(lookup.drop(columns="overlap"), on="HYBAS_ID", how="left")
        base = base.merge(parent, on=[f"parent_l{level}_id", "outcome"], how="left")
        base[f"same_direction_l{level}"] = (
            np.sign(base["slope_per_decade"]) == np.sign(base[f"slope_l{level}"])
        ) & base[f"slope_l{level}"].notna()

    pot = trends[(trends["sample"] == "pot_q95") & (trends["level"] == primary_level)][
        ["HYBAS_ID", "outcome", "slope_per_decade", "cluster_robust_p", "outcome_q"]
    ].rename(
        columns={
            "slope_per_decade": "pot_slope_per_decade",
            "cluster_robust_p": "pot_p",
            "outcome_q": "pot_outcome_q",
        }
    )
    base = base.merge(pot, on=["HYBAS_ID", "outcome"], how="left")
    base["same_direction_pot"] = (
        np.sign(base["slope_per_decade"]) == np.sign(base["pot_slope_per_decade"])
    ) & base["pot_slope_per_decade"].notna()
    paired_columns = paired[
        [
            "HYBAS_ID",
            "outcome",
            "mean_difference_percentage_points",
            "paired_t_p",
            "outcome_q",
            "primary_q",
        ]
    ].rename(
        columns={
            "mean_difference_percentage_points": "paired_period_change",
            "paired_t_p": "paired_period_p",
            "outcome_q": "paired_period_outcome_q",
            "primary_q": "paired_period_primary_q",
        }
    )
    base = base.merge(paired_columns, on=["HYBAS_ID", "outcome"], how="left")
    base["same_direction_paired"] = (
        np.sign(base["slope_per_decade"]) == np.sign(base["paired_period_change"])
    ) & base["paired_period_change"].notna()
    direction_columns = [f"same_direction_l{level}" for level in comparison_levels]
    base["scale_stable"] = base[direction_columns].all(axis=1)
    base["sample_stable"] = base["same_direction_pot"]
    base["robust_direction"] = (
        base["scale_stable"] & base["sample_stable"] & base["same_direction_paired"]
    )
    base["locally_replicated_signal"] = (
        base["primary_fdr_significant"]
        & (base["paired_period_primary_q"] < 0.05)
        & base["sample_stable"]
        & base["same_direction_paired"]
    )
    base["multiscale_replicated_signal"] = (
        base["locally_replicated_signal"] & base["scale_stable"]
    )
    sensitivity = trends[
        (trends["sample"] == "annual_maximum") & (trends["level"] == primary_level)
    ].pivot(index="HYBAS_ID", columns="outcome", values="slope_per_decade")
    for outcome in (
        "intensity_050",
        "intensity_joint_050_cv1",
        "intensity_075",
        "wet_1d",
        "wet_3d",
        "wet_7d",
        "wet_30d",
    ):
        if outcome in sensitivity:
            base = base.merge(
                sensitivity[[outcome]].rename(columns={outcome: f"sensitivity_{outcome}_slope"}),
                left_on="HYBAS_ID",
                right_index=True,
                how="left",
            )
    intensity_signs = np.column_stack(
        [
            np.sign(base[f"sensitivity_{outcome}_slope"])
            for outcome in ("intensity_050", "intensity_joint_050_cv1", "intensity_075")
        ]
    )
    wetness_signs = np.column_stack(
        [
            np.sign(base[f"sensitivity_{outcome}_slope"])
            for outcome in ("wet_1d", "wet_3d", "wet_7d")
        ]
    )
    base["definition_direction_stable"] = np.where(
        base["outcome"] == "intensity_050",
        np.all(intensity_signs == intensity_signs[:, [0]], axis=1),
        np.where(
            base["outcome"] == "wet_1d",
            np.all(wetness_signs == wetness_signs[:, [0]], axis=1),
            np.nan,
        ),
    )
    return base


def _jackknife_sign_stability(
    annual: pd.DataFrame,
    membership: pd.DataFrame,
    robustness: pd.DataFrame,
    primary_level: int,
) -> pd.DataFrame:
    id_column = f"hybas_id_l{primary_level}"
    sample = annual.merge(
        membership[["GCIN", id_column]], on="GCIN", how="left", validate="many_to_one"
    )
    signals = robustness[robustness["locally_replicated_signal"]][
        ["HYBAS_ID", "outcome", "slope_per_decade"]
    ]
    rows: list[dict[str, Any]] = []
    for signal in signals.itertuples():
        basin = sample[sample[id_column] == signal.HYBAS_ID]
        estimates: list[float] = []
        for gcin in basin["GCIN"].unique():
            estimate = _fixed_effect_slope(basin[basin["GCIN"] != gcin], signal.outcome)
            if estimate is not None:
                estimates.append(float(estimate["slope_per_decade"]))
        values = np.asarray(estimates, dtype=float)
        rows.append(
            {
                "HYBAS_ID": int(signal.HYBAS_ID),
                "outcome": signal.outcome,
                "jackknife_replicates": len(values),
                "jackknife_slope_min": float(np.min(values)),
                "jackknife_slope_max": float(np.max(values)),
                "jackknife_slope_median": float(np.median(values)),
                "jackknife_sign_stable": bool(
                    np.all(np.sign(values) == np.sign(signal.slope_per_decade))
                ),
            }
        )
    return pd.DataFrame(rows)


def run_local_analysis(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    output_summary = config["paths"]["logs"] / "local_analysis_summary.json"
    if output_summary.exists() and not force:
        return json.loads(output_summary.read_text(encoding="utf-8"))

    started = time.time()
    settings = config["local_analysis"]
    levels = [int(value) for value in settings["hydrobasins_levels"]]
    primary_level = int(settings["primary_level"])
    comparison_levels = [level for level in levels if level < primary_level]
    outcomes = list(settings["outcomes"])
    primary_outcomes = list(settings["primary_outcomes"])
    annual = pd.read_parquet(config["paths"]["derived_data"] / "annual_maximum_events.parquet")
    pot = pd.read_parquet(config["paths"]["derived_data"] / "pot_q95_events.parquet")
    catchments = annual[["GCIN", "country", "longitude", "latitude"]].drop_duplicates("GCIN")
    membership, _ = _assign_hydrobasins(
        catchments, config["paths"]["hydrobasins"], levels
    )

    labels = pd.concat([_basin_labels(membership, level) for level in levels], ignore_index=True)
    trends = pd.concat(
        [
            _fit_local_trends(
                annual,
                membership,
                "annual_maximum",
                levels,
                outcomes,
                int(settings["minimum_catchments"]),
                int(settings["minimum_observations"]),
            ),
            _fit_local_trends(
                pot,
                membership,
                "pot_q95",
                levels,
                outcomes,
                int(settings["minimum_catchments"]),
                int(settings["minimum_observations"]),
            ),
        ],
        ignore_index=True,
    )
    trends = _add_multiple_testing(trends, primary_outcomes, float(config["trends"]["alpha"]))
    trends = trends.merge(labels, on=["level", "HYBAS_ID"], how="left", validate="many_to_one")
    trends["approx_full_period_change"] = trends["slope_per_decade"] * (
        int(config["study"]["end_year"]) - int(config["study"]["start_year"])
    ) / 10.0

    paired = _paired_period_changes(
        annual,
        membership,
        primary_level,
        outcomes,
        list(config["trends"]["early_period"]),
        list(config["trends"]["late_period"]),
        int(settings["minimum_catchments"]),
        10,
        primary_outcomes,
        float(config["trends"]["alpha"]),
    )
    paired = paired.merge(
        labels[labels["level"] == primary_level],
        on=["level", "HYBAS_ID"],
        how="left",
        validate="many_to_one",
    )

    robustness = _build_robustness(
        trends, membership, paired, primary_level, comparison_levels
    )
    jackknife = _jackknife_sign_stability(annual, membership, robustness, primary_level)
    robustness = robustness.merge(jackknife, on=["HYBAS_ID", "outcome"], how="left")
    robustness["high_confidence_local_signal"] = (
        robustness["locally_replicated_signal"]
        & robustness["definition_direction_stable"].fillna(False)
        & robustness["jackknife_sign_stable"].fillna(False)
    )

    tables = config["paths"]["tables"]
    membership.to_csv(tables / "hydrobasin_catchment_membership.csv", index=False)
    labels.to_csv(tables / "hydrobasin_sample_summary.csv", index=False)
    trends.to_csv(tables / "local_hydrobasin_trends.csv", index=False)
    paired.to_csv(tables / "local_hydrobasin_period_comparison.csv", index=False)
    robustness.to_csv(tables / "local_hydrobasin_robustness.csv", index=False)
    checksum_rows = []
    for path in sorted(config["paths"]["hydrobasins"].glob("hybas_*_v1c.zip")):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        checksum_rows.append(
            {"file": path.name, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}
        )
    pd.DataFrame(checksum_rows).to_csv(
        config["paths"]["logs"] / "hydrobasins_reference_sha256.csv", index=False
    )

    primary = trends[
        (trends["sample"] == "annual_maximum") & (trends["level"] == primary_level)
    ]
    summary = {
        "status": "complete",
        "hydrobasins_version": "1.c",
        "levels": levels,
        "primary_level": primary_level,
        "minimum_catchments": int(settings["minimum_catchments"]),
        "matched_catchments": int(membership[f"hybas_id_l{primary_level}"].notna().sum()),
        "eligible_primary_basins": int(primary["HYBAS_ID"].nunique()),
        "primary_tests": int(primary["outcome"].isin(primary_outcomes).sum()),
        "primary_fdr_signals": int(primary["primary_fdr_significant"].sum()),
        "all_outcome_fdr_signals": int(primary["all_outcomes_fdr_significant"].sum()),
        "locally_replicated_primary_signals": int(
            robustness["locally_replicated_signal"].sum()
        ),
        "multiscale_replicated_primary_signals": int(
            robustness["multiscale_replicated_signal"].sum()
        ),
        "high_confidence_local_signals": int(
            robustness["high_confidence_local_signal"].sum()
        ),
        "elapsed_seconds": time.time() - started,
    }
    output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
