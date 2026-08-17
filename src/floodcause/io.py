from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EVENT_COLUMNS = [
    "Event ID",
    "GCIN",
    "start_precip_date",
    "end_precip_date",
    "duration_precip",
    "start_stormflow_date",
    "end_stormflow_date",
    "duration_stormflow",
    "volume_precip_mm",
    "volume_stormflow_mm",
    "runoff_ratio",
    "soil_saturation_index",
    "streamflow_mm",
    "event_magnitude_response_index",
    "snowpack_mm",
    "snowmelt_contribution_ratio",
    "event_type",
]


def source_paths(config: dict[str, Any]) -> dict[str, Path]:
    root = config["paths"]["source_global_data"]
    return {
        "root": root,
        "events_dormant": root / "events_dormant.csv",
        "events_growing": root / "events_growing.csv",
        "metadata_dormant": root / "metadata_dormant.csv",
        "metadata_growing": root / "metadata_growing.csv",
        "daily": root / "daily_data" / "observations",
        "boundaries": root / "Gauged_Catchments_Boundaries.gpkg",
    }


def load_canonical_metadata(config: dict[str, Any]) -> pd.DataFrame:
    """Build one audited catchment row, preferring the complete dormant catalogue."""
    paths = source_paths(config)
    dormant = pd.read_csv(paths["metadata_dormant"])
    growing = pd.read_csv(paths["metadata_growing"])
    dormant["in_metadata_dormant"] = True
    growing_ids = set(growing["GCIN"].astype(int))
    daily_ids = {
        int(path.stem)
        for path in paths["daily"].glob("*.csv")
        if path.stem.isdigit()
    }

    metadata = dormant.drop_duplicates("GCIN", keep="first").copy()
    metadata["GCIN"] = metadata["GCIN"].astype(int)
    metadata["in_metadata_growing"] = metadata["GCIN"].isin(growing_ids)
    metadata["has_daily_file"] = metadata["GCIN"].isin(daily_ids)
    metadata["daily_file"] = metadata["GCIN"].map(
        lambda value: str(paths["daily"] / f"{int(value)}.csv")
    )
    return metadata


def load_events(config: dict[str, Any]) -> pd.DataFrame:
    paths = source_paths(config)
    frames = []
    for season in ("dormant", "growing"):
        frame = pd.read_csv(paths[f"events_{season}"], usecols=EVENT_COLUMNS)
        frame["season"] = season
        frames.append(frame)
    events = pd.concat(frames, ignore_index=True)
    events["GCIN"] = pd.to_numeric(events["GCIN"], errors="coerce").astype("Int64")
    for column in (
        "start_precip_date",
        "end_precip_date",
        "start_stormflow_date",
        "end_stormflow_date",
    ):
        events[column] = pd.to_datetime(events[column], format="mixed", errors="coerce")
    numeric = [
        "volume_precip_mm",
        "volume_stormflow_mm",
        "runoff_ratio",
        "soil_saturation_index",
        "streamflow_mm",
        "snowpack_mm",
        "snowmelt_contribution_ratio",
    ]
    for column in numeric:
        events[column] = pd.to_numeric(events[column], errors="coerce")
    events["event_key"] = (
        events["season"].str[0].str.upper()
        + "-"
        + events["Event ID"].astype(str)
    )
    return events


def assign_continent(country: pd.Series) -> pd.Series:
    """Map ISO alpha-2 country codes to six reader-facing continental regions."""
    region_codes = {
        "Africa": {
            "BW", "CI", "DZ", "ET", "GH", "GN", "LS", "MA", "MU", "MW",
            "MZ", "NG", "SZ", "TZ", "ZA", "ZM", "ZW",
        },
        "Asia": {"CN", "GE", "ID", "IL", "LA", "LK", "MM", "MY", "TH", "TR", "VN"},
        "Europe": {"AT", "CH", "CY", "DE", "DK", "FR", "GB", "HU", "IE", "IT", "RU", "SE", "SI"},
        "North America": {"CA", "CR", "JM", "MX", "NI", "PA", "PR", "TT", "US"},
        "South America": {"AR", "BR", "CL", "CO", "EC", "GF", "GY", "UY", "VE"},
        "Oceania": {"AU", "NZ"},
    }
    lookup = {code: region for region, codes in region_codes.items() for code in codes}
    return country.map(lookup).fillna("Unassigned")


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    """Benjamini-Hochberg adjusted p-values, preserving missing entries."""
    result = pd.Series(np.nan, index=p_values.index, dtype=float)
    valid = p_values.dropna().astype(float)
    if valid.empty:
        return result
    ordered = valid.sort_values()
    m = len(ordered)
    ranks = np.arange(1, m + 1, dtype=float)
    adjusted = ordered.to_numpy() * m / ranks
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    result.loc[ordered.index] = adjusted
    return result
