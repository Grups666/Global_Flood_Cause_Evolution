"""Audit pooled daily SSI terciles for the actual primary-Q95 catchment cohort.

Read-only on source data and existing analysis. Writes a calibration receipt,
catchment/year missingness, and event-date alignment under outputs only. It does
not mutate source files. The analysis applies its thresholds to the day before
rainfall onset; source-catalogue start-day values are retained only for audit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from floodcause.config import load_config
from floodcause.io import source_paths


ROOT = Path(__file__).resolve().parents[1]


def calibrate(events: pd.DataFrame | None = None, config: dict | None = None) -> dict:
    config = config or load_config(ROOT / "config/analysis.yaml")
    settings = config["classification"]
    if settings["event_ssi_variable"] != "ssi_1d" or settings["event_ssi_day_offset"] != -1:
        raise ValueError("This protocol requires daily SSI on the day before rainfall starts")
    if not np.allclose(settings["wetness_quantiles"], [1 / 3, 2 / 3], rtol=0, atol=1e-15):
        raise ValueError("Primary wetness classification requires pooled daily terciles")
    primary_path = config["paths"]["derived_data"] / "primary_extreme_events.parquet"
    columns = ["GCIN", "event_key", "start_precip_date", "source_ssi"]
    events = pd.read_parquet(primary_path, columns=columns) if events is None else events[columns].copy()
    groups = {int(gcin): frame for gcin, frame in events.groupby("GCIN", sort=True)}
    ids = sorted(groups)
    start = pd.Timestamp(config["study"]["start_year"], 1, 1)
    end = pd.Timestamp(config["study"]["end_year"], 12, 31)
    expected_days = (end - start).days + 1
    arrays, catchments, annual_rows, alignment = [], [], [], []
    for position, gcin in enumerate(ids, 1):
        path = source_paths(config)["daily"] / f"{gcin}.csv"
        daily = pd.read_csv(path, usecols=["date", "soil_saturation_index"])
        dates = pd.to_datetime(daily.date, errors="coerce")
        invalid_dates = int(dates.isna().sum())
        daily["date"] = dates
        daily = daily[daily.date.between(start, end)].copy()
        if daily.date.duplicated().any():
            raise ValueError(f"Duplicate daily dates in GCIN {gcin}; resolve before pooling")
        values = pd.to_numeric(daily.soil_saturation_index, errors="coerce")
        missing = ~np.isfinite(values)
        invalid = ~missing & ~values.between(0, 1)
        valid = ~missing & ~invalid
        daily["valid_ssi"] = values.where(valid)
        arrays.append(values[valid].to_numpy(float))
        catchments.append({
            "GCIN": gcin, "first_date": daily.date.min(), "last_date": daily.date.max(),
            "expected_days": expected_days, "present_days": len(daily),
            "absent_days": expected_days - len(daily), "missing_ssi_days": int(missing.sum()),
            "out_of_range_ssi_days": int(invalid.sum()), "valid_ssi_days": int(valid.sum()),
            "invalid_date_rows": invalid_dates,
        })
        for year in range(start.year, end.year + 1):
            part = daily[daily.date.dt.year.eq(year)]
            days = 366 if pd.Timestamp(year, 1, 1).is_leap_year else 365
            annual_rows.append({"GCIN": gcin, "year": year, "expected_days": days,
                                "present_days": len(part), "valid_ssi_days": int(part.valid_ssi.notna().sum()),
                                "missing_or_invalid_or_absent_days": days - int(part.valid_ssi.notna().sum())})
        lookup = daily.set_index("date").valid_ssi
        part = groups[gcin].copy()
        part["ssi_on_start_day"] = part.start_precip_date.map(lookup)
        part["ssi_on_previous_day"] = (part.start_precip_date - pd.Timedelta(days=1)).map(lookup)
        part["matches_start_day"] = np.isclose(part.source_ssi, part.ssi_on_start_day, rtol=0, atol=1e-10)
        part["matches_previous_day"] = np.isclose(part.source_ssi, part.ssi_on_previous_day, rtol=0, atol=1e-10)
        alignment.append(part)
        if position % 500 == 0:
            print(f"Read {position}/{len(ids)} catchments", flush=True)
    pooled = np.concatenate(arrays)
    probabilities = [0.25, 1 / 3, 0.4, 0.6, 2 / 3, 0.75]
    thresholds = np.quantile(pooled, probabilities, method="linear")
    daily_audit = pd.DataFrame(catchments)
    align = pd.concat(alignment, ignore_index=True)
    low, high = float(thresholds[1]), float(thresholds[4])
    def label(values: pd.Series) -> pd.Series:
        return pd.Series(np.select([values.le(low), values.le(high), values.gt(high)],
                                   ["Dry", "Moderate", "Wet"], default="Missing"), index=values.index)
    align["class_start_day"] = label(align.ssi_on_start_day)
    align["class_previous_day"] = label(align.ssi_on_previous_day)
    align["class_differs_by_day"] = align.class_start_day.ne(align.class_previous_day)
    tables, logs = config["paths"]["tables"], config["paths"]["logs"]
    daily_audit.to_csv(tables / "wetness_daily_calibration_catchments.csv", index=False)
    pd.DataFrame(annual_rows).to_csv(tables / "wetness_daily_calibration_years.csv", index=False)
    align.to_csv(tables / "wetness_event_time_alignment.csv", index=False)
    receipt = {
        "status": "complete",
        "event_ssi_day_offset": -1,
        "event_ssi_variable": "ssi_1d",
        "cohort": "Unique catchments in this project's primary Q95 event sample",
        "cohort_catchments": len(ids), "primary_events": len(events),
        "cohort_id_sha256": hashlib.sha256(",".join(map(str, ids)).encode()).hexdigest(),
        "primary_event_keys_sha256": hashlib.sha256("\n".join(sorted(events.event_key)).encode()).hexdigest(),
        "daily_source": str(source_paths(config)["daily"]),
        "start_date": str(start.date()), "end_date": str(end.date()),
        "weighting": "One equal weight per valid unique catchment-day; all days, not only event days",
        "quantile_method": "numpy linear interpolation; h=(N-1)*q, zero-based sorted ranks",
        "valid_ssi_days": len(pooled),
        "present_days": int(daily_audit.present_days.sum()),
        "absent_days": int(daily_audit.absent_days.sum()),
        "missing_ssi_days": int(daily_audit.missing_ssi_days.sum()),
        "out_of_range_ssi_days": int(daily_audit.out_of_range_ssi_days.sum()),
        "terciles": {"lower": low, "upper": high},
        "sensitivity_quantiles": {str(q): float(t) for q, t in zip(probabilities, thresholds)},
        "daily_class_counts": {"Dry": int((pooled <= low).sum()),
                               "Moderate": int(((pooled > low) & (pooled <= high)).sum()),
                               "Wet": int((pooled > high).sum())},
        "event_time_alignment": {
            "matches_start_day": int(align.matches_start_day.sum()),
            "matches_previous_day": int(align.matches_previous_day.sum()),
            "previous_day_missing": int(align.ssi_on_previous_day.isna().sum()),
            "classification_differs_between_days": int(align.class_differs_by_day.sum()),
        },
    }
    (logs / "wetness_daily_calibration.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=2))
