from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from floodcause.local_analysis import load_hydrobasins


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


OUTCOMES = {
    "intensity_fraction": {
        "group": "Rainfall organization",
        "short": "Rainfall concentration",
        "label": "Share of event rainfall concentrated in the wettest day",
        "definition": "Maximum daily event rainfall divided by total event rainfall. A positive trend moves toward short, concentrated rainfall; a negative trend moves toward long, volume-dominated rainfall.",
        "unit": "percentage points of event rainfall per decade",
        "limit": 3.0,
        "low": "toward long / volume-dominated rainfall",
        "high": "toward short / concentrated rainfall",
        "digits": 2,
    },
    "intensity_050": {
        "group": "Rainfall organization",
        "short": "Intensity-type share",
        "label": "Share of extreme events classified as intensity-dominated",
        "definition": "Selected extreme events for which more than half of event rainfall fell in the wettest day. This thresholded view is interpretive; rainfall concentration is the primary continuous metric.",
        "unit": "percentage points per decade",
        "limit": 8.0,
        "low": "fewer intensity-dominated events",
        "high": "more intensity-dominated events",
        "digits": 2,
    },
    "ssi_1d": {
        "group": "Antecedent wetness",
        "short": "SSI · 1 day",
        "label": "One-day antecedent Soil Saturation Index",
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
        "label": "Three-day antecedent Soil Saturation Index",
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
        "label": "Seven-day antecedent Soil Saturation Index",
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
        "label": "Thirty-day antecedent Soil Saturation Index",
        "definition": "Mean SSI over the thirty complete days before event rainfall begins.",
        "unit": "SSI units per decade",
        "limit": 0.015,
        "low": "toward drier antecedent conditions",
        "high": "toward wetter antecedent conditions",
        "digits": 3,
    },
}


DRIVERS = {
    "log_p_max": "Maximum daily rainfall",
    "log_p_volume": "Total event rainfall",
    "log_precip_duration": "Precipitation duration",
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


def _metric_payload(row: pd.Series, trajectory: pd.DataFrame) -> dict[str, Any]:
    metric = str(row.metric)
    digits = int(OUTCOMES[metric]["digits"])
    series = trajectory[trajectory["metric"].eq(metric)].sort_values("year")
    trajectory_scale = 100.0 if metric in {"intensity_fraction", "intensity_050"} else 1.0
    q_value = row.primary_family_q if pd.notna(row.primary_family_q) else row.metric_q
    payload = {
        "slope": _native(row.slope_per_decade, digits + 1),
        "ci": [_native(row.ci_low, digits + 1), _native(row.ci_high, digits + 1)],
        "p": _native(row.p_value, 6),
        "q": _native(q_value, 6),
        "mean": _native(row.mean_level, digits + 1),
        "unit": row.slope_unit,
        "catchments": int(row.catchments),
        "observations": int(row.observations),
        "grade": str(row.evidence_grade),
        "strong": bool(row.strong_evidence),
        "limited": bool(row.limited_sample),
        "sampleStable": bool(row.sample_direction_stable),
        "windowStable": bool(row.wetness_window_stable),
        "jackknifeStable": bool(row.jackknife_sign_stable) if pd.notna(row.jackknife_sign_stable) else False,
        "fdrSupported": bool(row.primary_family_fdr_supported) if pd.notna(row.primary_family_fdr_supported) else bool(row.metric_fdr_supported),
        "sensitivities": {
            "Annual maximum": _native(row.get("annual_maximum_slope"), digits + 1),
            "POT/Q90": _native(row.get("pot_q90_slope"), digits + 1),
            "POT/Q95 · 10-day gap": _native(row.get("pot_q95_gap10_slope"), digits + 1),
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
    mean_scale = 100.0 if metric in {"intensity_fraction", "intensity_050"} else 1.0
    return {
        "slope": _native(row.display_slope_per_decade, digits + 1),
        "ci": [
            _native(row.display_ci_low_per_decade, digits + 1),
            _native(row.display_ci_high_per_decade, digits + 1),
        ],
        "q": _native(row.mk_q, 6),
        "tau": _native(row.mk_tau, 4),
        "mean": _native(row.mean_level * mean_scale, digits + 1),
        "unit": str(row.display_unit),
        "observations": int(row.n_observations),
        "years": int(row.n_years),
        "firstYear": int(row.first_year),
        "lastYear": int(row.last_year),
        "span": int(row.year_span),
        "fdrSupported": bool(row.fdr_significant),
    }


def build_web_data(destination: Path = DESTINATION) -> dict[str, Any]:
    evidence = pd.read_csv(TABLES / "hydrobasin_evidence.csv")
    evidence = evidence[evidence["level"].eq(5)].copy()
    trajectories = pd.read_csv(TABLES / "hydrobasin_trajectories.csv")
    summaries = pd.read_csv(TABLES / "hydrobasin_mechanism_summary.csv").set_index("HYBAS_ID")
    catchment_trends = pd.read_csv(TABLES / "catchment_mechanism_trends.csv")
    membership = pd.read_csv(TABLES / "hydrobasin_catchment_membership.csv")
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
        timeline = trajectories[trajectories["HYBAS_ID"].eq(basin_id)]
        metrics = {}
        for metric, metric_rows in rows[rows["metric"].isin(OUTCOMES)].groupby("metric"):
            metrics[metric] = _metric_payload(metric_rows.iloc[0], timeline)
        drivers = {}
        for metric, driver_rows in rows[rows["metric"].isin(DRIVERS)].groupby("metric"):
            driver = driver_rows.iloc[0]
            drivers[metric] = {
                "label": DRIVERS[metric],
                "slope": _native(driver.slope_per_decade, 2),
                "ci": [_native(driver.ci_low, 2), _native(driver.ci_high, 2)],
                "unit": driver.slope_unit,
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

    membership = membership.set_index("GCIN")
    catchments = []
    for gcin, rows in catchment_trends[
        catchment_trends["variable"].isin(OUTCOMES)
    ].groupby("GCIN"):
        first = rows.iloc[0]
        member = membership.loc[gcin] if gcin in membership.index else None
        metrics = {
            str(row.variable): _catchment_metric(row)
            for row in rows.itertuples(index=False)
        }
        if not metrics:
            continue
        catchments.append(
            {
                "id": str(int(gcin)),
                "country": str(first.country),
                "continent": str(first.continent),
                "lon": round(float(first.longitude), 4),
                "lat": round(float(first.latitude), 4),
                "hydrobasinId": str(int(member.hybas_id_l5)) if member is not None and pd.notna(member.hybas_id_l5) else None,
                "subAreaKm2": _native(member.sub_area_km2_l5, 0) if member is not None else None,
                "metrics": metrics,
            }
        )

    strong = evidence[evidence["strong_evidence"] & evidence["metric"].isin(OUTCOMES)]
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
            "eligibleHydrobasins": len(basins),
            "strongEvidenceSignals": int(strong.shape[0]),
            "strongEvidenceBasins": int(strong["HYBAS_ID"].nunique()),
            "minimumCatchments": 5,
            "strongMinimumCatchments": 20,
            "minimumObservations": 100,
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
