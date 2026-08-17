from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from .io import load_canonical_metadata, source_paths


def _inventory_row(name: str, path: Path, rows: int | None = None) -> dict[str, Any]:
    return {
        "asset": name,
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else np.nan,
        "rows": rows,
    }


def run_source_audit(config: dict[str, Any]) -> dict[str, Any]:
    """Profile source assets and record cross-file inconsistencies."""
    paths = source_paths(config)
    tables = config["paths"]["tables"]
    logs = config["paths"]["logs"]

    metadata_d = pd.read_csv(paths["metadata_dormant"])
    metadata_g = pd.read_csv(paths["metadata_growing"])
    event_usecols = [
        "Event ID", "GCIN", "start_precip_date", "end_precip_date",
        "start_stormflow_date", "end_stormflow_date", "volume_precip_mm",
        "volume_stormflow_mm", "runoff_ratio", "soil_saturation_index",
        "streamflow_mm", "snowmelt_contribution_ratio", "event_type",
    ]
    events_d = pd.read_csv(paths["events_dormant"], usecols=event_usecols)
    events_g = pd.read_csv(paths["events_growing"], usecols=event_usecols)
    daily_files = list(paths["daily"].glob("*.csv"))
    daily_ids = {int(path.stem) for path in daily_files if path.stem.isdigit()}

    boundaries = gpd.read_file(paths["boundaries"], columns=["GCIN", "geometry"])
    boundary_valid = boundaries.dropna(subset=["GCIN"]).copy()
    boundary_valid["GCIN"] = boundary_valid["GCIN"].astype(int)
    boundary_counts = boundary_valid.groupby("GCIN").size()

    inventory = pd.DataFrame([
        _inventory_row("metadata_dormant", paths["metadata_dormant"], len(metadata_d)),
        _inventory_row("metadata_growing", paths["metadata_growing"], len(metadata_g)),
        _inventory_row("events_dormant", paths["events_dormant"], len(events_d)),
        _inventory_row("events_growing", paths["events_growing"], len(events_g)),
        _inventory_row("catchment_boundaries", paths["boundaries"], len(boundaries)),
        {
            "asset": "daily_observations",
            "path": str(paths["daily"]),
            "exists": paths["daily"].exists(),
            "bytes": sum(path.stat().st_size for path in daily_files),
            "rows": np.nan,
            "files": len(daily_files),
        },
    ])
    inventory.to_csv(tables / "source_inventory.csv", index=False)

    missingness_rows = []
    for name, frame in (
        ("metadata_dormant", metadata_d),
        ("metadata_growing", metadata_g),
        ("events_dormant", events_d),
        ("events_growing", events_g),
    ):
        for column in frame.columns:
            missingness_rows.append({
                "asset": name,
                "column": column,
                "rows": len(frame),
                "missing_count": int(frame[column].isna().sum()),
                "missing_fraction": float(frame[column].isna().mean()),
                "distinct_nonmissing": int(frame[column].nunique(dropna=True)),
            })
    pd.DataFrame(missingness_rows).to_csv(tables / "source_missingness.csv", index=False)

    all_events = pd.concat(
        [events_d.assign(season="dormant"), events_g.assign(season="growing")],
        ignore_index=True,
    )
    for column in ("start_precip_date", "end_precip_date", "start_stormflow_date", "end_stormflow_date"):
        all_events[column] = pd.to_datetime(all_events[column], format="mixed", errors="coerce")

    metadata_union = set(metadata_d["GCIN"]) | set(metadata_g["GCIN"])
    event_ids = set(all_events["GCIN"].dropna().astype(int))
    issues = [
        {
            "severity": "high",
            "check": "event_catchments_without_daily_file",
            "count": len(event_ids - daily_ids),
            "examples": ",".join(map(str, sorted(event_ids - daily_ids)[:20])),
            "analysis_action": "exclude because event features cannot be independently reconstructed",
        },
        {
            "severity": "medium",
            "check": "metadata_catchments_without_daily_file",
            "count": len(metadata_union - daily_ids),
            "examples": ",".join(map(str, sorted(metadata_union - daily_ids)[:20])),
            "analysis_action": "exclude from the canonical catchment universe",
        },
        {
            "severity": "medium",
            "check": "boundary_rows_with_missing_gcin",
            "count": int(boundaries["GCIN"].isna().sum()),
            "examples": "",
            "analysis_action": "exclude from GCIN-linked maps",
        },
        {
            "severity": "low",
            "check": "boundary_rows_with_duplicate_nonmissing_gcin",
            "count": int((boundary_counts > 1).sum()),
            "examples": ",".join(map(str, boundary_counts[boundary_counts > 1].index[:20])),
            "analysis_action": "dissolve geometries by GCIN if non-zero",
        },
        {
            "severity": "low",
            "check": "cross_season_duplicate_event_windows",
            "count": int(all_events.duplicated(["GCIN", "start_precip_date", "start_stormflow_date"]).sum()),
            "examples": "",
            "analysis_action": "none if zero; otherwise retain one record and investigate",
        },
        {
            "severity": "medium",
            "check": "invalid_or_missing_event_dates",
            "count": int(all_events[["start_precip_date", "end_precip_date", "start_stormflow_date", "end_stormflow_date"]].isna().any(axis=1).sum()),
            "examples": "",
            "analysis_action": "exclude affected events and report by catchment-year",
        },
    ]
    issues_frame = pd.DataFrame(issues)
    issues_frame.to_csv(tables / "source_quality_issues.csv", index=False)

    canonical = load_canonical_metadata(config)
    canonical.to_parquet(config["paths"]["derived_data"] / "catchment_metadata.parquet", index=False)

    summary = {
        "metadata_dormant_rows": len(metadata_d),
        "metadata_growing_rows": len(metadata_g),
        "metadata_union_catchments": len(metadata_union),
        "daily_files": len(daily_files),
        "daily_total_bytes": int(sum(path.stat().st_size for path in daily_files)),
        "event_rows_dormant": len(events_d),
        "event_rows_growing": len(events_g),
        "event_catchments": len(event_ids),
        "event_date_min": str(all_events["start_precip_date"].min().date()),
        "event_date_max": str(all_events["end_stormflow_date"].max().date()),
        "rain_event_fraction": float(all_events["event_type"].astype(str).str.startswith("Rain-").mean()),
        "boundary_rows": len(boundaries),
        "boundary_unique_gcin": int(boundary_valid["GCIN"].nunique()),
        "boundary_missing_gcin": int(boundaries["GCIN"].isna().sum()),
        "boundary_duplicate_gcin": int((boundary_counts > 1).sum()),
        "issues": issues,
    }
    (logs / "source_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary
