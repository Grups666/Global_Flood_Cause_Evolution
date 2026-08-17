from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io import load_canonical_metadata, load_events, source_paths


DAY = np.timedelta64(1, "D")


def _date64(value: pd.Timestamp) -> np.datetime64:
    return np.datetime64(value.to_datetime64(), "D")


def _slice_positions(
    dates: np.ndarray, start: np.datetime64, end: np.datetime64
) -> tuple[int, int, bool]:
    left = int(np.searchsorted(dates, start, side="left"))
    right = int(np.searchsorted(dates, end, side="right"))
    valid = (
        left < len(dates)
        and right > left
        and dates[left] == start
        and dates[right - 1] == end
        and right - left == int((end - start) / DAY) + 1
    )
    return left, right, valid


def _safe_cv(values: np.ndarray) -> float:
    if values.size == 0 or not np.isfinite(values).all():
        return np.nan
    mean = float(values.mean())
    return float(values.std(ddof=0) / mean) if mean > 0 else np.nan


def _extract_for_catchment(
    gcin: int,
    events: pd.DataFrame,
    daily_file: Path,
    windows: list[int],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    daily = pd.read_csv(
        daily_file,
        usecols=["date", "water_input_mm", "streamflow_mm", "soil_saturation_index"],
    )
    daily["date"] = pd.to_datetime(daily["date"], format="mixed", errors="coerce")
    daily = daily.dropna(subset=["date"]).sort_values("date").drop_duplicates("date", keep="first")
    dates = daily["date"].to_numpy(dtype="datetime64[D]")
    precipitation = pd.to_numeric(daily["water_input_mm"], errors="coerce").to_numpy(float)
    streamflow = pd.to_numeric(daily["streamflow_mm"], errors="coerce").to_numpy(float)
    ssi = pd.to_numeric(daily["soil_saturation_index"], errors="coerce").to_numpy(float)

    rows: list[dict[str, Any]] = []
    invalid_windows = 0
    for event in events.itertuples(index=False):
        p_start = _date64(event.start_precip_date)
        p_end = _date64(event.end_precip_date)
        q_start = _date64(event.start_stormflow_date)
        q_end = _date64(event.end_stormflow_date)
        p_left, p_right, p_complete = _slice_positions(dates, p_start, p_end)
        q_left, q_right, q_complete = _slice_positions(dates, q_start, q_end)

        p_values = precipitation[p_left:p_right] if p_complete else np.array([], dtype=float)
        q_values = streamflow[q_left:q_right] if q_complete else np.array([], dtype=float)
        p_valid = p_complete and p_values.size > 0 and np.isfinite(p_values).all()
        q_valid = q_complete and q_values.size > 0 and np.isfinite(q_values).all()

        if q_valid:
            peak_offset = int(np.nanargmax(q_values))
            q_peak = float(q_values[peak_offset])
            q_peak_date = dates[q_left + peak_offset]
            peak_year = int(str(q_peak_date)[:4])
        else:
            q_peak = np.nan
            q_peak_date = np.datetime64("NaT")
            peak_year = np.nan

        p_sum = float(p_values.sum()) if p_valid else np.nan
        p_max = float(p_values.max()) if p_valid else np.nan
        intensity_fraction = p_max / p_sum if p_valid and p_sum > 0 else np.nan
        p_cv = _safe_cv(p_values)

        row: dict[str, Any] = {
            "event_key": event.event_key,
            "event_id": event._0,
            "GCIN": gcin,
            "season": event.season,
            "start_precip_date": event.start_precip_date,
            "end_precip_date": event.end_precip_date,
            "start_stormflow_date": event.start_stormflow_date,
            "end_stormflow_date": event.end_stormflow_date,
            "q_peak_date": q_peak_date,
            "peak_year": peak_year,
            "q_peak_mm_day": q_peak,
            "q_event_total_mm": event.streamflow_mm,
            "q_direct_volume_mm": event.volume_stormflow_mm,
            "p_volume_table_mm": event.volume_precip_mm,
            "p_volume_daily_mm": p_sum,
            "p_max_daily_mm": p_max,
            "intensity_fraction": intensity_fraction,
            "precipitation_cv": p_cv,
            "runoff_ratio": event.runoff_ratio,
            "source_ssi": event.soil_saturation_index,
            "event_type_source": event.event_type,
            "snowmelt_contribution_ratio": event.snowmelt_contribution_ratio,
            "precip_window_complete": p_valid,
            "streamflow_window_complete": q_valid,
            "p_volume_absolute_error_mm": abs(p_sum - event.volume_precip_mm) if p_valid else np.nan,
        }

        start_position = int(np.searchsorted(dates, p_start, side="left"))
        for window in windows:
            left = start_position - window
            right = start_position
            complete = (
                left >= 0
                and right <= len(dates)
                and dates[start_position] == p_start
                and dates[left] == p_start - window * DAY
                and dates[right - 1] == p_start - DAY
            )
            values = ssi[left:right] if complete else np.array([], dtype=float)
            valid = complete and len(values) == window and np.isfinite(values).all()
            row[f"ssi_{window}d"] = float(values.mean()) if valid else np.nan
            row[f"ssi_{window}d_complete"] = valid
            if not valid:
                invalid_windows += 1
        rows.append(row)

    result = pd.DataFrame(rows)
    expected_days = int((dates[-1] - dates[0]) / DAY) + 1 if len(dates) else 0
    audit = {
        "GCIN": gcin,
        "daily_rows": len(daily),
        "daily_start": str(dates[0]) if len(dates) else None,
        "daily_end": str(dates[-1]) if len(dates) else None,
        "daily_missing_calendar_days": expected_days - len(dates),
        "water_input_missing": int(np.isnan(precipitation).sum()),
        "streamflow_missing": int(np.isnan(streamflow).sum()),
        "ssi_missing": int(np.isnan(ssi).sum()),
        "candidate_events": len(events),
        "valid_precip_windows": int(result["precip_window_complete"].sum()) if len(result) else 0,
        "valid_streamflow_windows": int(result["streamflow_window_complete"].sum()) if len(result) else 0,
        "invalid_ssi_windows_total": invalid_windows,
    }
    return result, audit


def build_event_features(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    """Reconstruct daily peak flow, rainfall organization, and antecedent SSI."""
    output = config["paths"]["derived_data"] / "event_features.parquet"
    audit_output = config["paths"]["tables"] / "daily_event_feature_audit.csv"
    if output.exists() and audit_output.exists() and not force:
        return {"status": "reused", "event_features": str(output)}

    paths = source_paths(config)
    metadata = load_canonical_metadata(config)
    events = load_events(config)
    study = config["study"]
    windows = [int(value) for value in config["classification"]["ssi_windows_days"]]

    eligible = metadata[
        metadata["has_daily_file"]
        & (metadata["snow_fraction"] < float(study["snow_fraction_max_exclusive"]))
    ].copy()
    if study.get("require_both_season_catalogues", True):
        eligible = eligible[eligible["in_metadata_growing"]]
    eligible_ids = set(eligible["GCIN"].astype(int))

    events = events[
        events["GCIN"].isin(eligible_ids)
        & events["event_type"].astype(str).str.startswith("Rain-")
    ].copy()
    events = events.dropna(
        subset=["start_precip_date", "end_precip_date", "start_stormflow_date", "end_stormflow_date"]
    )

    feature_frames = []
    audit_rows = []
    started = time.time()
    grouped = events.groupby("GCIN", sort=True)
    for index, (gcin_value, catchment_events) in enumerate(grouped, start=1):
        gcin = int(gcin_value)
        frame, audit = _extract_for_catchment(
            gcin,
            catchment_events,
            paths["daily"] / f"{gcin}.csv",
            windows,
        )
        feature_frames.append(frame)
        audit_rows.append(audit)
        if index % 250 == 0:
            print(f"features: {index}/{len(grouped)} catchments, {time.time() - started:.1f}s")

    features = pd.concat(feature_frames, ignore_index=True)
    metadata_columns = ["GCIN", "country", "longitude", "latitude", "snow_fraction"]
    features = features.merge(eligible[metadata_columns], on="GCIN", how="left", validate="many_to_one")
    features.to_parquet(output, index=False, compression="zstd")
    pd.DataFrame(audit_rows).to_csv(audit_output, index=False)

    summary = {
        "status": "built",
        "eligible_catchments": len(eligible_ids),
        "catchments_with_events": int(features["GCIN"].nunique()),
        "event_rows": len(features),
        "valid_q_peak": int(features["q_peak_mm_day"].notna().sum()),
        "valid_intensity_fraction": int(features["intensity_fraction"].notna().sum()),
        "elapsed_seconds": time.time() - started,
        "event_features": str(output),
    }
    (config["paths"]["logs"] / "feature_build.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary
