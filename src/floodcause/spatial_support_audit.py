from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely import make_valid, union_all


EQUAL_AREA_CRS = "EPSG:6933"
THRESHOLDS = (0.10, 0.20, 0.30, 0.40, 0.50)
HYDROBASINS_REGIONS = {
    1: "Africa",
    2: "Europe",
    3: "Siberia",
    4: "Asia",
    5: "Oceania",
    6: "South America",
    7: "North America",
    8: "Arctic",
    9: "Greenland",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_gcin(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True)


def _repair_geometry(geometry: Any) -> Any:
    if geometry is None or geometry.is_empty:
        return geometry
    return make_valid(geometry) if not geometry.is_valid else geometry


def _load_hydrobasins(directory: Path, level: int = 5) -> gpd.GeoDataFrame:
    layers: list[gpd.GeoDataFrame] = []
    for path in sorted(directory.glob(f"hybas_*_lev{level:02d}_v1c.zip")):
        layer = gpd.read_file(
            f"zip://{path.as_posix()}",
            columns=["HYBAS_ID", "PFAF_ID", "SUB_AREA", "UP_AREA", "geometry"],
        )
        layers.append(layer)
    if not layers:
        raise FileNotFoundError(f"No HydroBASINS level-{level} archives in {directory}")
    result = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), crs=layers[0].crs)
    result["HYBAS_ID"] = result["HYBAS_ID"].astype("int64")
    return result


def _dominant_country(frame: pd.DataFrame) -> str:
    counts = frame["country"].astype(str).value_counts()
    return str(counts.index[0]) if len(counts) else ""


def _region_from_hybas_id(hybas_id: int) -> str:
    region_code = int(str(int(hybas_id))[0])
    return HYDROBASINS_REGIONS.get(region_code, f"Region {region_code}")


def _build_threshold_sensitivity(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scopes = [("Global", audit), ("United States", audit[audit["contains_us"]])]
    scopes.extend((region, frame) for region, frame in audit.groupby("hydrobasins_region"))
    for scope, frame in scopes:
        if frame.empty:
            continue
        for threshold in THRESHOLDS:
            for metric in ("coverage_fraction", "iou_fraction"):
                passed = frame[metric] >= threshold
                rows.append(
                    {
                        "scope": scope,
                        "metric": metric,
                        "threshold_pct": int(round(threshold * 100)),
                        "candidate_l5": int(len(frame)),
                        "passing_l5": int(passed.sum()),
                        "passing_share_pct": float(100 * passed.mean()),
                        "matched_catchments": int(frame["catchments"].sum()),
                        "passing_catchments": int(frame.loc[passed, "catchments"].sum()),
                        "passing_catchment_share_pct": float(
                            100
                            * frame.loc[passed, "catchments"].sum()
                            / frame["catchments"].sum()
                        ),
                        "single_dominant_l5": int(
                            (passed & (frame["largest_catchment_coverage_fraction"] >= threshold)).sum()
                        ),
                        "multi_catchment_l5": int(
                            (passed & (frame["largest_catchment_coverage_fraction"] < threshold)).sum()
                        ),
                    }
                )
    return pd.DataFrame(rows)


def run_audit(repo: Path, output_directory: Path) -> dict[str, Any]:
    config_path = repo / "config" / "analysis.yaml"
    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    source_root = Path(config["paths"]["source_global_data"])
    catchment_path = source_root / "Gauged_Catchments_Boundaries.gpkg"
    membership_path = repo / "outputs" / "tables" / "hydrobasin_catchment_membership.csv"
    hydrobasins_path = repo / config["paths"]["hydrobasins"]

    membership = pd.read_csv(membership_path, dtype={"GCIN": str})
    membership["GCIN"] = _normalise_gcin(membership["GCIN"])
    membership_duplicate_rows = int(membership.duplicated("GCIN", keep=False).sum())
    membership_missing_l5 = int(membership["hybas_id_l5"].isna().sum())
    if membership_duplicate_rows:
        raise ValueError(f"Membership has {membership_duplicate_rows} duplicate-GCIN rows")

    boundaries = gpd.read_file(catchment_path, columns=["GCIN", "geometry"])
    boundaries["GCIN"] = _normalise_gcin(boundaries["GCIN"])
    boundary_rows_full_source = int(len(boundaries))
    boundary_duplicate_rows = int(boundaries.duplicated("GCIN", keep=False).sum())
    invalid_before = int((~boundaries.geometry.is_valid).sum())
    empty_before = int((boundaries.geometry.isna() | boundaries.geometry.is_empty).sum())
    boundaries = boundaries[boundaries["GCIN"].isin(set(membership["GCIN"]))].copy()
    selected_boundary_rows = int(len(boundaries))
    selected_invalid_before = int((~boundaries.geometry.is_valid).sum())
    boundaries["geometry"] = boundaries.geometry.map(_repair_geometry)
    boundaries = boundaries[boundaries.geometry.notna() & ~boundaries.geometry.is_empty].copy()
    selected_invalid_after = int((~boundaries.geometry.is_valid).sum())
    missing_boundary_ids = sorted(set(membership["GCIN"]) - set(boundaries["GCIN"]))

    joined = boundaries.merge(
        membership[
            [
                "GCIN",
                "country",
                "longitude",
                "latitude",
                "hybas_id_l5",
                "pfaf_id_l5",
                "sub_area_km2_l5",
                "up_area_km2_l5",
            ]
        ],
        on="GCIN",
        how="inner",
        validate="one_to_one",
    )
    joined = joined.dropna(subset=["hybas_id_l5"]).copy()
    joined["hybas_id_l5"] = joined["hybas_id_l5"].astype("int64")
    joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=boundaries.crs).to_crs(
        EQUAL_AREA_CRS
    )

    hydrobasins = _load_hydrobasins(hydrobasins_path, level=5)
    candidate_ids = set(joined["hybas_id_l5"].astype("int64"))
    hydrobasins = hydrobasins[hydrobasins["HYBAS_ID"].isin(candidate_ids)].copy()
    hydrobasins["geometry"] = hydrobasins.geometry.map(_repair_geometry)
    hydrobasins = hydrobasins[
        hydrobasins.geometry.notna() & ~hydrobasins.geometry.is_empty
    ].to_crs(EQUAL_AREA_CRS)
    missing_hydrobasin_ids = sorted(candidate_ids - set(hydrobasins["HYBAS_ID"]))
    hydrobasin_lookup = {
        int(row.HYBAS_ID): row for row in hydrobasins.itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []
    for hybas_id, frame in joined.groupby("hybas_id_l5", sort=True):
        hybas_id = int(hybas_id)
        hydrobasin = hydrobasin_lookup.get(hybas_id)
        if hydrobasin is None:
            continue
        l5_geometry = hydrobasin.geometry
        l5_area = float(l5_geometry.area)
        catchment_records = [
            (str(row.GCIN), row.geometry)
            for row in frame.itertuples(index=False)
            if row.geometry is not None and not row.geometry.is_empty
        ]
        catchment_geometries = [geometry for _, geometry in catchment_records]
        catchment_union = union_all(catchment_geometries)
        intersection_geometry = _repair_geometry(l5_geometry.intersection(catchment_union))
        intersection_area = float(intersection_geometry.area)
        catchment_union_area = float(catchment_union.area)
        union_area = l5_area + catchment_union_area - intersection_area
        individual_intersection_areas = np.asarray(
            [float(l5_geometry.intersection(geometry).area) for geometry in catchment_geometries],
            dtype=float,
        )
        raw_intersection_area = float(individual_intersection_areas.sum())
        largest_intersection_area = float(individual_intersection_areas.max(initial=0.0))
        largest_position = int(individual_intersection_areas.argmax())
        largest_catchment_gcin = catchment_records[largest_position][0]
        coverage = intersection_area / l5_area if l5_area else np.nan
        iou = intersection_area / union_area if union_area else np.nan
        outside_fraction = (
            max(catchment_union_area - intersection_area, 0.0) / catchment_union_area
            if catchment_union_area
            else np.nan
        )
        largest_coverage = largest_intersection_area / l5_area if l5_area else np.nan
        dominant_observed_share = (
            largest_intersection_area / intersection_area if intersection_area else np.nan
        )
        overlap_factor = raw_intersection_area / intersection_area if intersection_area else np.nan
        countries = sorted(set(frame["country"].astype(str)))
        rows.append(
            {
                "hybas_id_l5": hybas_id,
                "pfaf_id_l5": int(hydrobasin.PFAF_ID),
                "hydrobasins_region": _region_from_hybas_id(hybas_id),
                "dominant_country": _dominant_country(frame),
                "countries": "/".join(countries),
                "contains_us": "US" in countries,
                "catchments": int(frame["GCIN"].nunique()),
                "largest_catchment_gcin": largest_catchment_gcin,
                "l5_area_km2": l5_area / 1e6,
                "hydrobasins_sub_area_km2": float(hydrobasin.SUB_AREA),
                "observed_union_inside_km2": intersection_area / 1e6,
                "catchment_union_total_km2": catchment_union_area / 1e6,
                "coverage_fraction": float(np.clip(coverage, 0.0, 1.0)),
                "coverage_pct": float(np.clip(100 * coverage, 0.0, 100.0)),
                "iou_fraction": float(np.clip(iou, 0.0, 1.0)),
                "iou_pct": float(np.clip(100 * iou, 0.0, 100.0)),
                "outside_union_fraction": float(np.clip(outside_fraction, 0.0, 1.0)),
                "outside_union_pct": float(np.clip(100 * outside_fraction, 0.0, 100.0)),
                "largest_catchment_coverage_fraction": float(
                    np.clip(largest_coverage, 0.0, 1.0)
                ),
                "largest_catchment_coverage_pct": float(
                    np.clip(100 * largest_coverage, 0.0, 100.0)
                ),
                "largest_catchment_observed_share_pct": float(
                    np.clip(100 * dominant_observed_share, 0.0, 100.0)
                ),
                "raw_sum_coverage_pct": 100 * raw_intersection_area / l5_area,
                "overlap_factor": overlap_factor,
                "single_dominant_50": bool(largest_coverage >= 0.50),
                "single_dominant_80": bool(largest_coverage >= 0.80),
            }
        )

    audit = pd.DataFrame(rows).sort_values("hybas_id_l5").reset_index(drop=True)

    event_path = repo / "data" / "derived" / "primary_extreme_events.parquet"
    primary_events = pd.read_parquet(
        event_path,
        columns=["GCIN", "peak_year", "intensity_fraction", "ssi_1d"],
    )
    primary_events["GCIN"] = _normalise_gcin(primary_events["GCIN"])
    event_membership = primary_events.merge(
        membership[["GCIN", "hybas_id_l5"]],
        on="GCIN",
        how="left",
        validate="many_to_one",
    ).dropna(subset=["hybas_id_l5"])
    event_membership["hybas_id_l5"] = event_membership["hybas_id_l5"].astype("int64")
    l5_event_summary = (
        event_membership.groupby("hybas_id_l5")
        .agg(
            primary_event_observations=("GCIN", "size"),
            primary_event_catchments=("GCIN", "nunique"),
            primary_event_years=("peak_year", "nunique"),
            primary_event_first_year=("peak_year", "min"),
            primary_event_last_year=("peak_year", "max"),
        )
        .reset_index()
    )
    catchment_event_summary = (
        primary_events.groupby("GCIN")
        .agg(
            largest_catchment_primary_events=("peak_year", "size"),
            largest_catchment_event_years=("peak_year", "nunique"),
            largest_catchment_first_event_year=("peak_year", "min"),
            largest_catchment_last_event_year=("peak_year", "max"),
        )
        .reset_index()
    )
    audit = audit.merge(
        l5_event_summary,
        on="hybas_id_l5",
        how="left",
        validate="one_to_one",
    ).merge(
        catchment_event_summary,
        left_on="largest_catchment_gcin",
        right_on="GCIN",
        how="left",
        validate="many_to_one",
    )
    audit = audit.drop(columns=["GCIN"])
    threshold_sensitivity = _build_threshold_sensitivity(audit)

    output_directory.mkdir(parents=True, exist_ok=True)
    audit_path = output_directory / "l5_spatial_support_audit.csv"
    threshold_path = output_directory / "l5_spatial_support_threshold_sensitivity.csv"
    summary_path = output_directory / "l5_spatial_support_audit_summary.json"
    audit.to_csv(audit_path, index=False)
    threshold_sensitivity.to_csv(threshold_path, index=False)

    us = audit[audit["contains_us"]]
    area_error_pct = 100 * (
        audit["l5_area_km2"] - audit["hydrobasins_sub_area_km2"]
    ).abs() / audit["hydrobasins_sub_area_km2"].replace(0, np.nan)
    summary: dict[str, Any] = {
        "inputs": {
            "membership": str(membership_path),
            "membership_sha256": _sha256(membership_path),
            "catchment_boundaries": str(catchment_path),
            "catchment_boundaries_sha256": _sha256(catchment_path),
            "hydrobasins_directory": str(hydrobasins_path),
            "equal_area_crs": EQUAL_AREA_CRS,
        },
        "data_quality": {
            "membership_rows": int(len(membership)),
            "membership_duplicate_gcin_rows": membership_duplicate_rows,
            "membership_missing_l5": membership_missing_l5,
            "boundary_rows_full_source": boundary_rows_full_source,
            "boundary_duplicate_gcin_rows": boundary_duplicate_rows,
            "boundary_invalid_full_source": invalid_before,
            "boundary_empty_full_source": empty_before,
            "selected_boundary_rows": selected_boundary_rows,
            "selected_boundary_invalid_before_repair": selected_invalid_before,
            "selected_boundary_invalid_after_repair": selected_invalid_after,
            "selected_missing_boundary_count": int(len(missing_boundary_ids)),
            "selected_missing_boundary_ids": missing_boundary_ids,
            "missing_hydrobasin_count": int(len(missing_hydrobasin_ids)),
            "missing_hydrobasin_ids": missing_hydrobasin_ids,
            "median_l5_area_difference_pct": float(area_error_pct.median()),
            "p95_l5_area_difference_pct": float(area_error_pct.quantile(0.95)),
        },
        "global": {
            "candidate_l5": int(len(audit)),
            "eligible_catchments": int(joined["GCIN"].nunique()),
            "count_coverage_correlation": float(
                audit["catchments"].corr(audit["coverage_fraction"])
            ),
            "coverage_iou_correlation": float(
                audit["coverage_fraction"].corr(audit["iou_fraction"])
            ),
            "median_coverage_pct": float(audit["coverage_pct"].median()),
            "median_iou_pct": float(audit["iou_pct"].median()),
            "median_outside_union_pct": float(audit["outside_union_pct"].median()),
            "p90_outside_union_pct": float(audit["outside_union_pct"].quantile(0.90)),
            "median_overlap_factor": float(audit["overlap_factor"].median()),
            "p90_overlap_factor": float(audit["overlap_factor"].quantile(0.90)),
            "coverage_ge_10": int((audit["coverage_fraction"] >= 0.10).sum()),
            "coverage_ge_20": int((audit["coverage_fraction"] >= 0.20).sum()),
            "coverage_ge_30": int((audit["coverage_fraction"] >= 0.30).sum()),
            "coverage_ge_40": int((audit["coverage_fraction"] >= 0.40).sum()),
            "coverage_ge_50": int((audit["coverage_fraction"] >= 0.50).sum()),
            "iou_ge_50": int((audit["iou_fraction"] >= 0.50).sum()),
            "single_dominant_50": int(audit["single_dominant_50"].sum()),
            "single_dominant_80": int(audit["single_dominant_80"].sum()),
        },
        "united_states": {
            "candidate_l5": int(len(us)),
            "eligible_catchments": int(
                joined.loc[joined["country"].astype(str).eq("US"), "GCIN"].nunique()
            ),
            "count_coverage_correlation": float(
                us["catchments"].corr(us["coverage_fraction"])
            ),
            "coverage_iou_correlation": float(
                us["coverage_fraction"].corr(us["iou_fraction"])
            ),
            "median_coverage_pct": float(us["coverage_pct"].median()),
            "median_iou_pct": float(us["iou_pct"].median()),
            "median_outside_union_pct": float(us["outside_union_pct"].median()),
            "coverage_ge_10": int((us["coverage_fraction"] >= 0.10).sum()),
            "coverage_ge_20": int((us["coverage_fraction"] >= 0.20).sum()),
            "coverage_ge_30": int((us["coverage_fraction"] >= 0.30).sum()),
            "coverage_ge_40": int((us["coverage_fraction"] >= 0.40).sum()),
            "coverage_ge_50": int((us["coverage_fraction"] >= 0.50).sum()),
            "iou_ge_50": int((us["iou_fraction"] >= 0.50).sum()),
            "single_dominant_50": int(us["single_dominant_50"].sum()),
            "single_dominant_80": int(us["single_dominant_80"].sum()),
        },
        "outputs": {
            "audit": str(audit_path),
            "threshold_sensitivity": str(threshold_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit whether HydroBASINS L5 eligibility can be based on polygon area support."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project repository root.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help="Audit output directory (default: <repo>/outputs/tables/spatial_support).",
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    output_directory = (
        args.output_directory.resolve()
        if args.output_directory is not None
        else repo / "outputs" / "tables" / "spatial_support"
    )
    summary = run_audit(repo, output_directory)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
