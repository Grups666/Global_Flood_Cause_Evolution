from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from floodcause.local_analysis import _load_hydrobasins


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
PRIMARY_OUTCOMES = ("intensity_050", "wet_1d")


def _native(value: Any, digits: int | None = None) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return round(number, digits) if digits is not None else number
    return str(value)


def _coordinates(value: Any) -> Any:
    if isinstance(value, (tuple, list)):
        if value and isinstance(value[0], (int, float, np.integer, np.floating)):
            return [round(float(value[0]), 4), round(float(value[1]), 4)]
        return [_coordinates(item) for item in value]
    return value


def _metric(row: pd.Series) -> dict[str, Any]:
    return {
        "slope": _native(row.get("slope_per_decade"), 3),
        "ci": [_native(row.get("ci_low"), 3), _native(row.get("ci_high"), 3)],
        "p": _native(row.get("cluster_robust_p"), 5),
        "q": _native(row.get("primary_q"), 5),
        "observations": _native(row.get("observations")),
        "catchments": _native(row.get("catchments")),
        "meanLevel": _native(row.get("mean_level"), 2),
        "potSlope": _native(row.get("pot_slope_per_decade"), 3),
        "pairedChange": _native(row.get("paired_period_change"), 3),
        "sameDirectionPot": _native(row.get("same_direction_pot")),
        "sameDirectionPaired": _native(row.get("same_direction_paired")),
        "scaleStable": _native(row.get("scale_stable")),
        "definitionStable": _native(row.get("definition_direction_stable")),
        "jackknifeStable": _native(row.get("jackknife_sign_stable")),
        "highConfidence": _native(row.get("high_confidence_local_signal")),
    }


def _catchment_metric(row: pd.Series) -> dict[str, Any]:
    sen = _native(row.get("sen_slope_per_decade"), 5)
    return {
        "slope": round(sen * 100.0, 3) if sen is not None else None,
        "oddsRatio": _native(row.get("odds_ratio_per_decade"), 3),
        "oddsRatioCi": [
            _native(row.get("odds_ratio_ci_low"), 3),
            _native(row.get("odds_ratio_ci_high"), 3),
        ],
        "p": _native(row.get("logistic_p"), 5),
        "q": _native(row.get("logistic_q"), 5),
        "years": _native(row.get("n_years")),
        "positiveYears": _native(row.get("n_positive")),
        "fdrSignificant": _native(row.get("fdr_significant")),
    }


def build_web_data(destination: Path = DESTINATION) -> dict[str, Any]:
    robustness = pd.read_csv(TABLES / "local_hydrobasin_robustness.csv")
    membership = pd.read_csv(TABLES / "hydrobasin_catchment_membership.csv")
    catchment_trends = pd.read_csv(TABLES / "catchment_binary_trends.csv")

    primary = robustness.loc[
        (robustness["sample"] == "annual_maximum")
        & (robustness["level"] == 5)
        & robustness["outcome"].isin(PRIMARY_OUTCOMES)
    ].copy()
    eligible_ids = sorted(primary["HYBAS_ID"].astype("int64").unique())
    basins = _load_hydrobasins(HYDROBASINS, 5)
    basins = basins.loc[basins["HYBAS_ID"].isin(eligible_ids)].to_crs("EPSG:4326")
    basins["geometry"] = basins.geometry.simplify(0.035, preserve_topology=True)

    basin_metrics: dict[int, dict[str, Any]] = {}
    basin_meta: dict[int, pd.Series] = {}
    for _, row in primary.iterrows():
        basin_id = int(row["HYBAS_ID"])
        basin_metrics.setdefault(basin_id, {})[str(row["outcome"])] = _metric(row)
        basin_meta[basin_id] = row

    basin_records: list[dict[str, Any]] = []
    for _, row in basins.sort_values("HYBAS_ID").iterrows():
        basin_id = int(row["HYBAS_ID"])
        meta = basin_meta[basin_id]
        geometry = row.geometry.__geo_interface__
        basin_records.append(
            {
                "id": str(basin_id),
                "code": str(meta["basin_code"]),
                "countries": str(meta["dominant_countries"]),
                "center": [
                    _native(meta["centroid_longitude"], 3),
                    _native(meta["centroid_latitude"], 3),
                ],
                "assignedCatchments": _native(meta["assigned_catchments"]),
                "subAreaKm2": _native(row["SUB_AREA"], 1),
                "upAreaKm2": _native(row["UP_AREA"], 1),
                "geometry": {
                    "type": geometry["type"],
                    "coordinates": _coordinates(geometry["coordinates"]),
                },
                "metrics": basin_metrics[basin_id],
            }
        )

    selected_trends = catchment_trends.loc[
        catchment_trends["outcome"].isin(PRIMARY_OUTCOMES)
    ].copy()
    trend_lookup: dict[int, dict[str, Any]] = {}
    for _, row in selected_trends.iterrows():
        trend_lookup.setdefault(int(row["GCIN"]), {})[str(row["outcome"])] = (
            _catchment_metric(row)
        )

    catchment_records: list[dict[str, Any]] = []
    for _, row in membership.sort_values("GCIN").iterrows():
        gcin = int(row["GCIN"])
        basin_id = _native(row.get("hybas_id_l5"))
        catchment_records.append(
            {
                "id": str(gcin),
                "country": str(row["country"]),
                "lon": _native(row["longitude"], 4),
                "lat": _native(row["latitude"], 4),
                "hydrobasinId": str(basin_id) if basin_id is not None else None,
                "subAreaKm2": _native(row.get("sub_area_km2_l5"), 1),
                "metrics": trend_lookup.get(gcin, {}),
            }
        )

    payload = {
        "meta": {
            "title": "Local evolution of rainfall-driven flood causes",
            "period": "1982–2019",
            "annualMaximumEvents": 100788,
            "primaryCatchments": 2839,
            "eligibleHydrobasins": len(basin_records),
            "highConfidenceSignals": int(
                primary["high_confidence_local_signal"].fillna(False).astype(bool).sum()
            ),
            "outcomes": {
                "intensity_050": {
                    "short": "Intensity-dominated",
                    "label": "Intensity-dominated annual maxima",
                    "definition": "Event Pmax/Pvolume > 0.50",
                },
                "wet_1d": {
                    "short": "Wet antecedent",
                    "label": "Wet one-day antecedent conditions",
                    "definition": "One-day antecedent wetness above its threshold",
                },
            },
            "units": "percentage points per decade",
            "sources": [
                "Event_Typology annual maximum events",
                "HydroBASINS v1.c level 5",
            ],
            "interpretation": (
                "HydroBASINS colors are catchment fixed-effect trends. Catchment colors are "
                "descriptive Sen slopes; FDR support is reported separately."
            ),
        },
        "basins": basin_records,
        "catchments": catchment_records,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )
    return {
        "status": "complete",
        "destination": str(destination),
        "bytes": destination.stat().st_size,
        "basins": len(basin_records),
        "catchments": len(catchment_records),
    }


if __name__ == "__main__":
    print(json.dumps(build_web_data(), indent=2, ensure_ascii=False))
