from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from .analysis import SAMPLE_FILES, _fixed_effect_trend
from .io import benjamini_hochberg


def load_hydrobasins(directory: Path, level: int) -> gpd.GeoDataFrame:
    layers: list[gpd.GeoDataFrame] = []
    for path in sorted(directory.glob(f"hybas_*_lev{level:02d}_v1c.zip")):
        layer = gpd.read_file(f"zip://{path.as_posix()}")
        layers.append(
            layer[["HYBAS_ID", "PFAF_ID", "SUB_AREA", "UP_AREA", "geometry"]]
        )
    if not layers:
        raise FileNotFoundError(f"No HydroBASINS level {level} files in {directory}")
    result = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), crs=layers[0].crs)
    result["HYBAS_ID"] = result["HYBAS_ID"].astype("int64")
    return result


def assign_hydrobasins(
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
        basins = load_hydrobasins(directory, level).to_crs(points.crs)
        geometries[level] = basins
        joined = gpd.sjoin(
            points[["GCIN", "geometry"]], basins, how="left", predicate="within"
        )
        joined = joined.sort_values(
            ["GCIN", "SUB_AREA"], na_position="last"
        ).drop_duplicates("GCIN", keep="first")
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


def _fit_local_trends(
    samples: dict[str, pd.DataFrame],
    membership: pd.DataFrame,
    levels: list[int],
    metrics: list[str],
    minimum_catchments: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    id_columns = [f"hybas_id_l{level}" for level in levels]
    for sample_name, sample in samples.items():
        joined = sample.merge(
            membership[["GCIN", *id_columns]],
            on="GCIN",
            how="left",
            validate="many_to_one",
        )
        for level in levels:
            id_column = f"hybas_id_l{level}"
            for basin_id, basin in joined.dropna(subset=[id_column]).groupby(id_column):
                if basin["GCIN"].nunique() < minimum_catchments:
                    continue
                for metric in metrics:
                    estimate = _fixed_effect_trend(basin, metric)
                    if estimate is None:
                        continue
                    if estimate["catchments"] < minimum_catchments:
                        continue
                    rows.append(
                        {
                            "sample": sample_name,
                            "level": level,
                            "HYBAS_ID": int(basin_id),
                            "metric": metric,
                            **estimate,
                        }
                    )
    return pd.DataFrame(rows)


def _add_multiple_testing(
    trends: pd.DataFrame,
    primary_sample: str,
    primary_level: int,
    primary_metrics: list[str],
    alpha: float,
) -> pd.DataFrame:
    result = trends.copy()
    result["metric_q"] = result.groupby(
        ["sample", "level", "metric"], group_keys=False
    )["p_value"].transform(benjamini_hochberg)
    result["primary_family_q"] = np.nan
    primary = (
        result["sample"].eq(primary_sample)
        & result["level"].eq(primary_level)
        & result["metric"].isin(primary_metrics)
    )
    result.loc[primary, "primary_family_q"] = benjamini_hochberg(
        result.loc[primary, "p_value"]
    ).to_numpy()
    result["metric_fdr_supported"] = result["metric_q"] < alpha
    result["primary_family_fdr_supported"] = result["primary_family_q"] < alpha
    return result


def _robustness_table(
    trends: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    settings = config["local_analysis"]
    primary_level = int(settings["primary_level"])
    primary_sample = str(config["event_samples"]["primary"])
    base = trends[
        trends["sample"].eq(primary_sample) & trends["level"].eq(primary_level)
    ].copy()

    sensitivity_names = list(config["event_samples"]["sensitivity_samples"])
    for sample_name in sensitivity_names:
        sample_values = trends[
            trends["sample"].eq(sample_name) & trends["level"].eq(primary_level)
        ][["HYBAS_ID", "metric", "slope_per_decade", "p_value"]].rename(
            columns={
                "slope_per_decade": f"{sample_name}_slope",
                "p_value": f"{sample_name}_p",
            }
        )
        base = base.merge(sample_values, on=["HYBAS_ID", "metric"], how="left")

    sensitivity_slope_columns = [f"{name}_slope" for name in sensitivity_names]
    sensitivity_signs = np.sign(base[sensitivity_slope_columns])
    primary_sign = np.sign(base["slope_per_decade"])
    base["sample_direction_stable"] = (
        base[sensitivity_slope_columns].notna().all(axis=1)
        & sensitivity_signs.eq(primary_sign, axis=0).all(axis=1)
    )

    wet_metrics = [f"ssi_{window}d" for window in config["classification"]["ssi_windows_days"]]
    wet_pivot = base[base["metric"].isin(wet_metrics)].pivot(
        index="HYBAS_ID", columns="metric", values="slope_per_decade"
    )
    wet_pivot = wet_pivot.reindex(columns=wet_metrics)
    wet_stable = wet_pivot.notna().all(axis=1) & np.sign(wet_pivot).nunique(axis=1).eq(1)
    base = base.merge(
        wet_stable.rename("wetness_window_stable"),
        left_on="HYBAS_ID",
        right_index=True,
        how="left",
    )
    base.loc[~base["metric"].isin(wet_metrics), "wetness_window_stable"] = True

    return base


def _jackknife_signs(
    primary: pd.DataFrame,
    membership: pd.DataFrame,
    evidence: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    level = int(config["local_analysis"]["primary_level"])
    id_column = f"hybas_id_l{level}"
    joined = primary.merge(
        membership[["GCIN", id_column]], on="GCIN", how="left", validate="many_to_one"
    )
    candidates = evidence[
        evidence["primary_family_fdr_supported"].fillna(False)
    ][["HYBAS_ID", "metric", "slope_per_decade"]]
    rows: list[dict[str, Any]] = []
    for candidate in candidates.itertuples(index=False):
        basin = joined[joined[id_column].eq(candidate.HYBAS_ID)]
        estimates: list[float] = []
        for gcin in basin["GCIN"].unique():
            estimate = _fixed_effect_trend(
                basin[basin["GCIN"].ne(gcin)], candidate.metric, minimum_clusters=2
            )
            if estimate is not None:
                estimates.append(float(estimate["slope_per_decade"]))
        values = np.asarray(estimates, dtype=float)
        rows.append(
            {
                "HYBAS_ID": int(candidate.HYBAS_ID),
                "metric": candidate.metric,
                "jackknife_replicates": int(len(values)),
                "jackknife_slope_min": float(values.min()) if len(values) else np.nan,
                "jackknife_slope_max": float(values.max()) if len(values) else np.nan,
                "jackknife_sign_stable": bool(
                    len(values)
                    and np.all(np.sign(values) == np.sign(candidate.slope_per_decade))
                ),
            }
        )
    return pd.DataFrame(rows)


def _add_evidence_grade(
    evidence: pd.DataFrame, jackknife: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    result = evidence.merge(jackknife, on=["HYBAS_ID", "metric"], how="left")
    primary_metrics = set(config["local_analysis"]["primary_metrics"])
    result["strong_evidence"] = (
        result["metric"].isin(primary_metrics)
        & result["primary_family_fdr_supported"].fillna(False)
        & result["sample_direction_stable"].fillna(False)
        & result["wetness_window_stable"].fillna(False)
        & result["jackknife_sign_stable"].fillna(False)
    )
    result["evidence_grade"] = np.select(
        [
            result["strong_evidence"],
            result["primary_family_fdr_supported"].fillna(False),
        ],
        ["strong", "fdr-supported"],
        default="estimate",
    )
    return result


def _basin_trajectories(
    primary: pd.DataFrame,
    membership: pd.DataFrame,
    trends: pd.DataFrame,
    metrics: list[str],
    level: int,
) -> pd.DataFrame:
    id_column = f"hybas_id_l{level}"
    joined = primary.merge(
        membership[["GCIN", id_column]], on="GCIN", how="left", validate="many_to_one"
    )
    estimates = trends[
        trends["sample"].eq("pot_q95") & trends["level"].eq(level)
    ].set_index(["HYBAS_ID", "metric"])
    rows: list[dict[str, Any]] = []
    for basin_id, basin in joined.dropna(subset=[id_column]).groupby(id_column):
        for metric in metrics:
            data = basin[["GCIN", "peak_year", metric]].dropna()
            if data.empty or (int(basin_id), metric) not in estimates.index:
                continue
            catchment_year = data.groupby(["GCIN", "peak_year"], as_index=False).agg(
                value=(metric, "mean"), events=(metric, "size")
            )
            catchment_mean = catchment_year.groupby("GCIN")["value"].transform("mean")
            reference = float(catchment_year.groupby("GCIN")["value"].mean().mean())
            catchment_year["adjusted"] = catchment_year["value"] - catchment_mean + reference
            year_center = float(catchment_year["peak_year"].mean())
            slope = float(estimates.loc[(int(basin_id), metric), "slope_per_decade"])
            raw_slope = slope / 100.0 if metric == "intensity_fraction" else slope
            annual = catchment_year.groupby("peak_year").agg(
                adjusted_mean=("adjusted", "mean"),
                catchments=("GCIN", "nunique"),
                events=("events", "sum"),
            )
            for year, values in annual.iterrows():
                rows.append(
                    {
                        "HYBAS_ID": int(basin_id),
                        "metric": metric,
                        "year": int(year),
                        "adjusted_mean": float(values["adjusted_mean"]),
                        "fitted_mean": float(
                            reference + raw_slope * (float(year) - year_center) / 10.0
                        ),
                        "catchments": int(values["catchments"]),
                        "events": int(values["events"]),
                    }
                )
    return pd.DataFrame(rows)


def _mechanism_summary(evidence: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    primary_metrics = evidence[evidence["metric"].isin(config["local_analysis"]["primary_metrics"])]
    rows: list[dict[str, Any]] = []
    for basin_id, basin in primary_metrics.groupby("HYBAS_ID"):
        concentration = basin[basin["metric"].eq("intensity_fraction")]
        wet = basin[basin["metric"].str.startswith("ssi_")]
        rainfall_direction = "unavailable"
        rainfall_evidence = "estimate"
        if not concentration.empty:
            value = float(concentration.iloc[0]["slope_per_decade"])
            rainfall_direction = "toward_intensity" if value > 0 else "toward_volume"
            rainfall_evidence = str(concentration.iloc[0]["evidence_grade"])
        wetness_direction = "mixed_or_uncertain"
        wetness_evidence = "estimate"
        if len(wet) == 4 and wet["wetness_window_stable"].all():
            wetness_direction = "toward_wetter" if wet["slope_per_decade"].mean() > 0 else "toward_drier"
            wetness_evidence = "strong" if wet["strong_evidence"].any() else str(
                wet.sort_values("primary_family_q").iloc[0]["evidence_grade"]
            )
        rows.append(
            {
                "HYBAS_ID": int(basin_id),
                "rainfall_direction": rainfall_direction,
                "rainfall_evidence": rainfall_evidence,
                "wetness_direction": wetness_direction,
                "wetness_evidence": wetness_evidence,
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
    derived = config["paths"]["derived_data"]
    samples = {
        name: pd.read_parquet(derived / filename)
        for name, filename in SAMPLE_FILES.items()
    }
    primary = samples[str(config["event_samples"]["primary"])]
    catchments = primary[
        ["GCIN", "country", "longitude", "latitude"]
    ].drop_duplicates("GCIN")
    membership, _ = assign_hydrobasins(
        catchments, config["paths"]["hydrobasins"], levels
    )
    labels = pd.concat(
        [_basin_labels(membership, level) for level in levels], ignore_index=True
    )
    metrics = list(
        dict.fromkeys(
            [
                *settings["displayed_metrics"],
                *settings["driver_metrics"],
                *settings["primary_metrics"],
            ]
        )
    )
    trends = _fit_local_trends(
        samples,
        membership,
        levels,
        metrics,
        int(settings["minimum_catchments"]),
    )
    trends = _add_multiple_testing(
        trends,
        str(config["event_samples"]["primary"]),
        primary_level,
        list(settings["primary_metrics"]),
        float(config["trends"]["alpha"]),
    )
    trends = trends.merge(
        labels, on=["level", "HYBAS_ID"], how="left", validate="many_to_one"
    )
    evidence = _robustness_table(trends, config)
    jackknife = _jackknife_signs(primary, membership, evidence, config)
    evidence = _add_evidence_grade(evidence, jackknife, config)
    trajectories = _basin_trajectories(
        primary,
        membership,
        trends,
        list(settings["displayed_metrics"]),
        primary_level,
    )
    mechanism = _mechanism_summary(evidence, config)

    tables = config["paths"]["tables"]
    membership.to_csv(tables / "hydrobasin_catchment_membership.csv", index=False)
    labels.to_csv(tables / "hydrobasin_sample_summary.csv", index=False)
    trends.to_csv(tables / "hydrobasin_mechanism_trends.csv", index=False)
    evidence.to_csv(tables / "hydrobasin_evidence.csv", index=False)
    trajectories.to_csv(tables / "hydrobasin_trajectories.csv", index=False)
    mechanism.to_csv(tables / "hydrobasin_mechanism_summary.csv", index=False)

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

    primary_l5 = evidence[evidence["level"].eq(primary_level)]
    summary = {
        "status": "complete",
        "hydrobasins_version": "1.c",
        "primary_sample": str(config["event_samples"]["primary"]),
        "primary_level": primary_level,
        "minimum_catchments": int(settings["minimum_catchments"]),
        "matched_catchments": int(membership[f"hybas_id_l{primary_level}"].notna().sum()),
        "eligible_primary_basins": int(primary_l5["HYBAS_ID"].nunique()),
        "primary_family_tests": int(
            primary_l5["metric"].isin(settings["primary_metrics"]).sum()
        ),
        "primary_family_fdr_signals": int(
            primary_l5["primary_family_fdr_supported"].sum()
        ),
        "strong_evidence_signals": int(primary_l5["strong_evidence"].sum()),
        "strong_evidence_basins": int(
            primary_l5.loc[primary_l5["strong_evidence"], "HYBAS_ID"].nunique()
        ),
        "elapsed_seconds": time.time() - started,
    }
    output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
