from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import make_valid, union_all

from floodcause.config import load_config
from floodcause.local_analysis import load_hydrobasins


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(PROJECT_ROOT / "config" / "analysis.yaml")
TABLES = PROJECT_ROOT / "outputs" / "tables"
HYDROBASINS = PROJECT_ROOT / "data" / "reference" / "hydrobasins"
DESTINATION = (
    PROJECT_ROOT
    / "public"
    / "modules"
    / "flood-cause-evolution"
    / "data"
    / "flood-cause-explorer.json"
)
CATCHMENT_BOUNDARIES = (
    CONFIG["paths"]["source_global_data"] / "Gauged_Catchments_Boundaries.gpkg"
)


OUTCOMES = {
    "intensity_fraction": {
        "group": "Rainfall organization",
        "short": "Rainfall concentration",
        "label": "Rainfall concentration · rainiest-day rainfall divided by total event rainfall",
        "definition": "Rainfall concentration is the rainfall on the event's rainiest single day divided by total rainfall over the whole event. A positive trend means a larger one-day share; a negative trend means a smaller one-day share.",
        "unit": "percentage-point change per decade",
        "limit": 3.0,
        "low": "toward less concentrated event rainfall",
        "high": "toward more concentrated event rainfall",
        "digits": 2,
    },
    "ssi_1d": {
        "group": "Antecedent wetness",
        "short": "SSI · 1 day",
        "label": "Antecedent wetness · mean SSI over 1 day before rainfall onset",
        "definition": "Mean SSI over the complete day before event rainfall begins.",
        "unit": "SSI units per decade",
        "limit": 0.015,
        "low": "toward drier antecedent conditions",
        "high": "toward wetter antecedent conditions",
        "digits": 3,
    },
    "ssi_3d": {
        "group": "Antecedent wetness",
        "short": "SSI · 3 days",
        "label": "Antecedent wetness · mean SSI over 3 days before rainfall onset",
        "definition": "Mean SSI over the three complete days before event rainfall begins.",
        "unit": "SSI units per decade",
        "limit": 0.015,
        "low": "toward drier antecedent conditions",
        "high": "toward wetter antecedent conditions",
        "digits": 3,
    },
    "ssi_7d": {
        "group": "Antecedent wetness",
        "short": "SSI · 7 days",
        "label": "Antecedent wetness · mean SSI over 7 days before rainfall onset",
        "definition": "Mean SSI over the seven complete days before event rainfall begins.",
        "unit": "SSI units per decade",
        "limit": 0.015,
        "low": "toward drier antecedent conditions",
        "high": "toward wetter antecedent conditions",
        "digits": 3,
    },
    "ssi_30d": {
        "group": "Antecedent wetness",
        "short": "SSI · 30 days",
        "label": "Antecedent wetness · mean SSI over 30 days before rainfall onset",
        "definition": "Mean SSI over the thirty complete days before event rainfall begins.",
        "unit": "SSI units per decade",
        "limit": 0.015,
        "low": "toward drier antecedent conditions",
        "high": "toward wetter antecedent conditions",
        "digits": 3,
    },
}


DRIVERS = {
    "p_max_daily_mm": "Maximum daily rainfall",
    "p_volume_daily_mm": "Total event rainfall",
    "precip_duration_days": "Precipitation duration",
}


def _native(value: Any, digits: int | None = None) -> Any:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), digits) if digits is not None else float(value)
    return value


def _coordinates(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (float, int)):
            return [round(float(value[0]), 4), round(float(value[1]), 4)]
        return [_coordinates(item) for item in value]
    return value


def _polygonal_geometry(geometry: Any) -> Any:
    if geometry is None or geometry.is_empty:
        return geometry
    repaired = make_valid(geometry) if not geometry.is_valid else geometry
    if repaired.geom_type in {"Polygon", "MultiPolygon"}:
        return repaired
    polygons = [
        part
        for part in getattr(repaired, "geoms", [])
        if part.geom_type in {"Polygon", "MultiPolygon"}
    ]
    return union_all(polygons) if polygons else None


def _metric_payload(row: pd.Series, trajectory: pd.DataFrame) -> dict[str, Any]:
    metric = str(row.metric)
    digits = int(OUTCOMES[metric]["digits"])
    series = trajectory[trajectory["metric"].eq(metric)].sort_values("year")
    trajectory_scale = 100.0 if metric == "intensity_fraction" else 1.0
    q_value = row.primary_family_q if pd.notna(row.primary_family_q) else row.metric_q
    payload = {
        "slope": _native(row.slope_per_decade, digits + 1),
        "ci": [_native(row.ci_low, digits + 1), _native(row.ci_high, digits + 1)],
        "p": _native(row.p_value, 6),
        "q": _native(q_value, 6),
        "mean": _native(row.mean_level, digits + 1),
        "relativeSlope": _native(row.relative_slope_percent_per_decade, 2),
        "relativeCi": [
            _native(row.relative_ci_low_percent_per_decade, 2),
            _native(row.relative_ci_high_percent_per_decade, 2),
        ],
        "unit": row.slope_unit,
        "catchments": int(row.catchments),
        "observations": int(row.observations),
        "modeledObservations": int(row.modeled_observations),
        "estimatorType": str(row.estimator_type),
        "grade": str(row.evidence_grade),
        "strong": bool(row.strong_evidence),
        "sampleStable": bool(row.sample_direction_stable),
        "windowStable": bool(row.wetness_window_stable),
        "jackknifeStable": bool(row.jackknife_sign_stable) if pd.notna(row.jackknife_sign_stable) else False,
        "fdrSupported": bool(row.primary_family_fdr_supported) if pd.notna(row.primary_family_fdr_supported) else bool(row.metric_fdr_supported),
        "sensitivities": {
            "Annual maximum": _native(row.get("annual_maximum_slope"), digits + 1),
            "POT/Q90": _native(row.get("pot_q90_slope"), digits + 1),
            "POT/Q97.5": _native(row.get("pot_q975_slope"), digits + 1),
        },
        "trajectory": [
            [
                int(item.year),
                _native(item.adjusted_mean * trajectory_scale, digits + 1),
                _native(item.fitted_mean * trajectory_scale, digits + 1),
                int(item.catchments),
                int(item.events),
            ]
            for item in series.itertuples(index=False)
        ],
    }
    return payload


def _catchment_metric(row: pd.Series) -> dict[str, Any]:
    metric = str(row.variable)
    digits = int(OUTCOMES[metric]["digits"])
    mean_scale = 100.0 if metric == "intensity_fraction" else 1.0
    return {
        "slope": _native(row.display_slope_per_decade, digits + 1),
        "ci": [
            _native(row.display_ci_low_per_decade, digits + 1),
            _native(row.display_ci_high_per_decade, digits + 1),
        ],
        "p": _native(row.mk_p, 6),
        "tau": _native(row.mk_tau, 4),
        "mean": _native(row.mean_level * mean_scale, digits + 1),
        "fittedFirst": _native(row.fitted_first_level * mean_scale, digits + 1),
        "fittedLast": _native(row.fitted_last_level * mean_scale, digits + 1),
        "relativeSlope": _native(row.relative_slope_percent_per_decade, 2),
        "unit": str(row.display_unit),
        "observations": int(row.n_observations),
        "years": int(row.n_years),
        "firstYear": int(row.first_year),
        "lastYear": int(row.last_year),
        "span": int(row.year_span),
        "robust": bool(row.robust_local_trend),
        "grade": str(row.evidence_grade),
        "checkCount": int(row.local_check_count),
        "checkTotal": int(row.local_check_total),
        "alternativeSampleStable": bool(row.alternative_sample_direction_stable),
        "windowStable": bool(row.wetness_window_stable),
        "leaveOneYearStable": bool(row.leave_one_year_out_stable),
        "sensitivities": {
            "Annual maximum": _native(
                getattr(row, "annual_maximum_slope", None), digits + 1
            ),
            "POT/Q90": _native(getattr(row, "pot_q90_slope", None), digits + 1),
            "POT/Q97.5": _native(
                getattr(row, "pot_q975_slope", None), digits + 1
            ),
        },
    }


def build_web_data(destination: Path = DESTINATION) -> dict[str, Any]:
    evidence = pd.read_csv(TABLES / "hydrobasin_evidence.csv")
    evidence = evidence[evidence["level"].eq(5)].copy()
    trajectories = pd.read_csv(TABLES / "hydrobasin_trajectories.csv")
    summaries = pd.read_csv(TABLES / "hydrobasin_mechanism_summary.csv").set_index("HYBAS_ID")
    catchment_trends = pd.read_csv(TABLES / "catchment_mechanism_trends.csv")
    membership = pd.read_csv(TABLES / "hydrobasin_catchment_membership.csv")
    spatial_support = pd.read_csv(
        TABLES / "spatial_support" / "l5_spatial_support_audit.csv"
    ).set_index("hybas_id_l5")
    threshold_sensitivity = pd.read_csv(
        TABLES
        / "spatial_support"
        / "l5_spatial_support_threshold_sensitivity.csv"
    )
    diagnostics = pd.read_csv(TABLES / "extreme_sample_diagnostics.csv")
    primary_diag = diagnostics[diagnostics["sample"].eq("pot_q95")].iloc[0]

    eligible_ids = set(evidence["HYBAS_ID"].astype(int))
    geometry = load_hydrobasins(HYDROBASINS, 5).to_crs("EPSG:4326")
    geometry = geometry[geometry["HYBAS_ID"].isin(eligible_ids)].copy()
    geometry["geometry"] = geometry.geometry.simplify(0.025, preserve_topology=True)
    geometry = geometry.set_index("HYBAS_ID")

    basins = []
    for basin_id, rows in evidence.groupby("HYBAS_ID"):
        basin_id = int(basin_id)
        if basin_id not in geometry.index:
            continue
        row = rows.iloc[0]
        support = spatial_support.loc[basin_id] if basin_id in spatial_support.index else None
        timeline = trajectories[trajectories["HYBAS_ID"].eq(basin_id)]
        metrics = {}
        for metric, metric_rows in rows[rows["metric"].isin(OUTCOMES)].groupby("metric"):
            metrics[metric] = _metric_payload(metric_rows.iloc[0], timeline)
        drivers = {}
        for metric, driver_rows in rows[rows["metric"].isin(DRIVERS)].groupby("metric"):
            driver = driver_rows.iloc[0]
            drivers[metric] = {
                "label": DRIVERS[metric],
                "slope": _native(driver.relative_slope_percent_per_decade, 2),
                "ci": [
                    _native(driver.relative_ci_low_percent_per_decade, 2),
                    _native(driver.relative_ci_high_percent_per_decade, 2),
                ],
                "absoluteSlope": _native(driver.slope_per_decade, 2),
                "absoluteUnit": driver.slope_unit,
                "unit": "percent of the catchment-equal mean per decade",
            }
        summary = summaries.loc[basin_id] if basin_id in summaries.index else None
        geom = geometry.loc[basin_id].geometry
        basins.append(
            {
                "id": str(basin_id),
                "code": str(row.basin_code),
                "label": str(row.basin_label),
                "countries": str(row.dominant_countries),
                "center": [round(float(row.centroid_longitude), 4), round(float(row.centroid_latitude), 4)],
                "subAreaKm2": _native(geometry.loc[basin_id].SUB_AREA, 0),
                "coveragePct": _native(support.coverage_pct, 2) if support is not None else None,
                "observedAreaKm2": _native(support.observed_union_inside_km2, 0) if support is not None else None,
                "largestCatchmentCoveragePct": _native(
                    support.largest_catchment_coverage_pct, 2
                ) if support is not None else None,
                "largestCatchmentId": (
                    str(int(float(support.largest_catchment_gcin)))
                    if support is not None
                    and pd.notna(support.largest_catchment_gcin)
                    else None
                ),
                "assignedCatchments": int(support.catchments) if support is not None else int(row.assigned_catchments),
                "geometry": {"type": geom.geom_type, "coordinates": _coordinates(geom.__geo_interface__["coordinates"])},
                "mechanism": {
                    "rainfall": str(summary.rainfall_direction) if summary is not None else "unavailable",
                    "rainfallEvidence": str(summary.rainfall_evidence) if summary is not None else "estimate",
                    "wetness": str(summary.wetness_direction) if summary is not None else "unavailable",
                    "wetnessEvidence": str(summary.wetness_evidence) if summary is not None else "estimate",
                },
                "metrics": metrics,
                "drivers": drivers,
            }
        )

    catchment_ids = set(
        catchment_trends.loc[
            catchment_trends["variable"].isin(OUTCOMES), "GCIN"
        ].astype(int).astype(str)
    )
    boundaries = gpd.read_file(
        CATCHMENT_BOUNDARIES, columns=["GCIN", "geometry"]
    )
    boundaries["GCIN"] = (
        boundaries["GCIN"].astype(str).str.replace(r"\.0$", "", regex=True)
    )
    boundaries = boundaries[boundaries["GCIN"].isin(catchment_ids)].copy()
    boundaries["geometry"] = boundaries.geometry.map(_polygonal_geometry)
    boundaries = boundaries[
        boundaries.geometry.notna() & ~boundaries.geometry.is_empty
    ].copy()
    equal_area = boundaries.to_crs("EPSG:6933")
    boundaries["area_km2"] = equal_area.geometry.area.to_numpy() / 1e6
    boundaries = boundaries.to_crs("EPSG:4326")
    boundaries["geometry"] = boundaries.geometry.simplify(
        0.01, preserve_topology=True
    )
    boundary_lookup = boundaries.set_index("GCIN")

    membership["GCIN"] = membership["GCIN"].astype(int)
    membership = membership.set_index("GCIN")
    catchments = []
    for gcin, rows in catchment_trends[
        catchment_trends["variable"].isin(OUTCOMES)
    ].groupby("GCIN"):
        first = rows.iloc[0]
        member = membership.loc[gcin] if gcin in membership.index else None
        boundary_key = str(int(gcin))
        boundary = (
            boundary_lookup.loc[boundary_key]
            if boundary_key in boundary_lookup.index
            else None
        )
        metrics = {
            str(row.variable): _catchment_metric(row)
            for row in rows.itertuples(index=False)
        }
        if not metrics:
            continue
        catchment_geometry = boundary.geometry if boundary is not None else None
        bounds = list(catchment_geometry.bounds) if catchment_geometry is not None else None
        catchments.append(
            {
                "id": str(int(gcin)),
                "country": str(first.country),
                "continent": str(first.continent),
                "lon": round(float(first.longitude), 4),
                "lat": round(float(first.latitude), 4),
                "hydrobasinId": str(int(member.hybas_id_l5)) if member is not None and pd.notna(member.hybas_id_l5) else None,
                "subAreaKm2": _native(member.sub_area_km2_l5, 0) if member is not None else None,
                "areaKm2": _native(boundary.area_km2, 1) if boundary is not None else None,
                "bounds": [_native(value, 4) for value in bounds] if bounds else None,
                "geometry": {
                    "type": catchment_geometry.geom_type,
                    "coordinates": _coordinates(
                        catchment_geometry.__geo_interface__["coordinates"]
                    ),
                } if catchment_geometry is not None else None,
                "metrics": metrics,
            }
        )

    primary_family = evidence[evidence["metric"].isin(OUTCOMES)]
    strong = primary_family[primary_family["strong_evidence"]]
    catchment_primary = catchment_trends[
        catchment_trends["variable"].isin(OUTCOMES)
    ]
    threshold_rows = threshold_sensitivity[
        threshold_sensitivity["scope"].isin(["Global", "United States"])
        & threshold_sensitivity["metric"].eq("coverage_fraction")
    ].copy()
    ranking = []
    for item in strong.itertuples(index=False):
        limit = float(OUTCOMES[item.metric]["limit"])
        ranking.append(
            {
                "basinId": str(int(item.HYBAS_ID)),
                "code": str(item.basin_code),
                "countries": str(item.dominant_countries),
                "metric": str(item.metric),
                "slope": _native(item.slope_per_decade, int(OUTCOMES[item.metric]["digits"]) + 1),
                "score": abs(float(item.slope_per_decade)) / limit,
            }
        )
    ranking.sort(key=lambda item: item["score"], reverse=True)

    payload = {
        "meta": {
            "title": "Global Flood Cause Evolution",
            "period": "1982–2019",
            "primarySample": "Catchment-specific upper 5% of reconstructed event peaks (POT/Q95)",
            "primaryEvents": int(primary_diag.events),
            "primaryCatchments": int(primary_diag.catchments),
            "catchmentsWithTrend": len(catchments),
            "catchmentPrimaryTests": int(catchment_primary.shape[0]),
            "robustCatchmentTrends": int(
                catchment_primary["robust_local_trend"].sum()
            ),
            "estimableHydrobasins": len(basins),
            "strongEvidenceSignals": int(strong.shape[0]),
            "strongEvidenceBasins": int(strong["HYBAS_ID"].nunique()),
            "primaryFamilyTests": int(primary_family.shape[0]),
            "fdrSupportedSignals": int(primary_family["primary_family_fdr_supported"].sum()),
            "strongByMetric": {
                metric: int(count)
                for metric, count in strong.groupby("metric").size().items()
            },
            "defaultCoverageThreshold": int(
                CONFIG["local_analysis"]["default_area_coverage_threshold_percent"]
            ),
            "coverageThresholdOptions": list(
                CONFIG["local_analysis"]["area_coverage_threshold_options_percent"]
            ),
            "coverageSensitivity": [
                {
                    "scope": str(item.scope),
                    "threshold": int(item.threshold_pct),
                    "estimableL5": int(item.candidate_l5),
                    "passingL5": int(item.passing_l5),
                    "passingCatchments": int(item.passing_catchments),
                    "passingCatchmentShare": _native(
                        item.passing_catchment_share_pct, 2
                    ),
                }
                for item in threshold_rows.sort_values(
                    ["scope", "threshold_pct"]
                ).itertuples(index=False)
            ],
            "outcomes": OUTCOMES,
            "driverLabels": DRIVERS,
            "ranking": ranking,
            "independence": {
                "stormflowWindowOverlaps": int(primary_diag.stormflow_window_overlaps),
                "pairsUnder10Days": int(primary_diag.pairs_under_10_days),
            },
        },
        "basins": basins,
        "catchments": catchments,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return {
        "status": "complete",
        "destination": str(destination),
        "bytes": destination.stat().st_size,
        "basins": len(basins),
        "catchments": len(catchments),
        "strong_signals": int(strong.shape[0]),
    }


if __name__ == "__main__":
    print(json.dumps(build_web_data(), indent=2))
