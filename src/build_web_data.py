from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from floodcause.local_analysis import (
    _add_multiple_testing,
    _fit_local_trends,
    _load_hydrobasins,
)


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
MAP_MINIMUM_CATCHMENTS = 5
LARGER_SAMPLE_CATCHMENTS = 20
MINIMUM_OBSERVATIONS = 300


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


def _expit(value: float | np.ndarray) -> float | np.ndarray:
    clipped = np.clip(value, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _catchment_metric(row: pd.Series, centered_decades: np.ndarray) -> dict[str, Any]:
    sen = _native(row.get("sen_slope_per_decade"), 5)
    if len(centered_decades) != int(row["n_years"]):
        raise ValueError(
            f"Trend-year mismatch for GCIN {int(row['GCIN'])} {row['outcome']}: "
            f"table={int(row['n_years'])}, annual={len(centered_decades)}"
        )
    log_odds_per_decade = float(row["log_odds_per_decade"])
    target_positive = float(row["n_positive"])
    lower, upper = -40.0, 40.0
    for _ in range(80):
        intercept = (lower + upper) / 2.0
        fitted_positive = float(
            np.asarray(_expit(intercept + log_odds_per_decade * centered_decades)).sum()
        )
        if fitted_positive < target_positive:
            lower = intercept
        else:
            upper = intercept
    intercept = (lower + upper) / 2.0
    probability_2000 = float(_expit(intercept))
    probability_2010 = float(_expit(intercept + log_odds_per_decade))
    probability_change = (probability_2010 - probability_2000) * 100.0
    return {
        "slope": round(float(probability_change), 3),
        "senSlope": round(sen * 100.0, 3) if sen is not None else None,
        "logOdds": _native(row.get("log_odds_per_decade"), 4),
        "probability2000": round(probability_2000 * 100.0, 2),
        "probability2010": round(probability_2010 * 100.0, 2),
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
    annual = pd.read_parquet(
        PROJECT_ROOT / "data" / "derived" / "annual_maximum_events.parquet",
        columns=["GCIN", "peak_year", *PRIMARY_OUTCOMES],
    )

    primary = robustness.loc[
        (robustness["sample"] == "annual_maximum")
        & (robustness["level"] == 5)
        & robustness["outcome"].isin(PRIMARY_OUTCOMES)
    ].copy()
    mapped_trends = _fit_local_trends(
        annual,
        membership,
        "annual_maximum",
        [5],
        list(PRIMARY_OUTCOMES),
        MAP_MINIMUM_CATCHMENTS,
        MINIMUM_OBSERVATIONS,
    )
    mapped_trends = _add_multiple_testing(mapped_trends, list(PRIMARY_OUTCOMES), 0.05)
    labels = pd.read_csv(TABLES / "hydrobasin_sample_summary.csv")
    labels = labels.loc[labels["level"] == 5].copy()
    mapped_trends = mapped_trends.merge(
        labels,
        on=["level", "HYBAS_ID"],
        how="left",
        validate="many_to_one",
    )
    primary_lookup = {
        (int(row["HYBAS_ID"]), str(row["outcome"])): row
        for _, row in primary.iterrows()
    }

    eligible_ids = sorted(mapped_trends["HYBAS_ID"].astype("int64").unique())
    basins = _load_hydrobasins(HYDROBASINS, 5)
    basins = basins.loc[basins["HYBAS_ID"].isin(eligible_ids)].to_crs("EPSG:4326")
    basins["geometry"] = basins.geometry.simplify(0.035, preserve_topology=True)

    basin_metrics: dict[int, dict[str, Any]] = {}
    basin_meta: dict[int, pd.Series] = {}
    for _, row in mapped_trends.iterrows():
        basin_id = int(row["HYBAS_ID"])
        outcome = str(row["outcome"])
        metric = _metric(row)
        metric["mapQ"] = metric["q"]
        metric["mapFdrSignificant"] = bool(row["primary_fdr_significant"])
        metric["largerSample"] = bool(int(row["catchments"]) >= LARGER_SAMPLE_CATCHMENTS)
        primary_row = primary_lookup.get((basin_id, outcome))
        if primary_row is not None:
            primary_metric = _metric(primary_row)
            metric["analysisQ"] = primary_metric["q"]
            for key in [
                "potSlope",
                "pairedChange",
                "sameDirectionPot",
                "sameDirectionPaired",
                "scaleStable",
                "definitionStable",
                "jackknifeStable",
                "highConfidence",
            ]:
                metric[key] = primary_metric[key]
        else:
            metric["analysisQ"] = None
            metric["highConfidence"] = False
        metric["evidenceTier"] = (
            "high-confidence"
            if metric["highConfidence"]
            else "larger-sample-20plus"
            if metric["largerSample"]
            else "limited-sample-5to19"
        )
        basin_metrics.setdefault(basin_id, {})[outcome] = metric
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
    trend_years: dict[tuple[int, str], np.ndarray] = {}
    for outcome in PRIMARY_OUTCOMES:
        valid = annual[["GCIN", "peak_year", outcome]].dropna()
        for gcin, frame in valid.groupby("GCIN", sort=False):
            trend_years[(int(gcin), outcome)] = (
                frame["peak_year"].to_numpy(dtype=float) - 2000.0
            ) / 10.0
    trend_lookup: dict[int, dict[str, Any]] = {}
    for _, row in selected_trends.iterrows():
        gcin = int(row["GCIN"])
        outcome = str(row["outcome"])
        trend_lookup.setdefault(gcin, {})[outcome] = _catchment_metric(
            row, trend_years[(gcin, outcome)]
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

    limited_sample_ids = {
        basin_id
        for basin_id, metrics in basin_metrics.items()
        if any(not metric["largerSample"] for metric in metrics.values())
    }
    us_ids = set(
        membership.loc[membership["country"].eq("US"), "hybas_id_l5"]
        .dropna()
        .astype("int64")
    )
    payload = {
        "meta": {
            "title": "Local evolution of rainfall-driven flood causes",
            "period": "1982–2019",
            "annualMaximumEvents": 100788,
            "primaryCatchments": 2839,
            "eligibleHydrobasins": len(basin_records),
            "limitedSampleHydrobasins": len(limited_sample_ids),
            "largerSampleHydrobasins": len(basin_records) - len(limited_sample_ids),
            "unitedStatesHydrobasins": len(set(eligible_ids) & us_ids),
            "highConfidenceSignals": int(
                primary["high_confidence_local_signal"].fillna(False).astype(bool).sum()
            ),
            "analysisMinimumCatchments": MAP_MINIMUM_CATCHMENTS,
            "largerSampleCatchments": LARGER_SAMPLE_CATCHMENTS,
            "minimumObservations": MINIMUM_OBSERVATIONS,
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
                "HydroBASINS colors are catchment fixed-effect trends. The formal analysis "
                "requires at least 5 catchments and 300 observations. Regions with 5-19 "
                "catchments are marked as limited-sample estimates, while regions with at least "
                "20 catchments have stronger cluster support. Full robustness gates are evaluated "
                "for all included regions. "
                "Catchment colors are "
                "fitted logistic probability changes from 2000 to 2010; FDR support is reported "
                "separately. Sen slopes are retained only as audit fields because binary "
                "annual series make them degenerate at zero."
            ),
            "mapScales": {
                "hydrobasinMaxAbs": 7,
                "catchmentMaxAbs": 20,
            },
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
