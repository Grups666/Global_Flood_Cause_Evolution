"""Wetness cut-point and pre-rainfall window diagnostics (not eligibility gates)."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .analysis import (
    MECHANISMS, _assign_wetness, _assign_mechanism, _direction_only_trends,
    _magnitude_trends, _record_eligibility, _study_events,
)


def run_wetness_sensitivity(config):
    derived, tables, logs = (config["paths"][key] for key in ("derived_data", "tables", "logs"))
    calibration = json.loads((logs / "wetness_daily_calibration.json").read_text(encoding="utf-8"))
    primary = pd.read_parquet(derived / "primary_extreme_events.parquet")
    catalogue = _study_events(pd.read_parquet(derived / "event_features.parquet"), config)
    _, ids = _record_eligibility(catalogue, config)
    years = catalogue[catalogue.GCIN.isin(ids)][["GCIN", "peak_year"]].drop_duplicates()
    del catalogue
    groups = MECHANISMS + ["Dry-All", "Moderate-All", "Wet-All"]
    baseline = pd.concat([
        pd.read_csv(tables / "catchment_mechanism_trends.csv", low_memory=False),
        pd.read_csv(tables / "catchment_filter_group_trends.csv", low_memory=False),
    ], ignore_index=True)
    baseline = baseline[baseline.mechanism.isin(groups)]
    keys = ["GCIN", "mechanism", "outcome"]
    reference = baseline[keys + ["display_slope_per_decade", "supported_shift"]].rename(
        columns={"display_slope_per_decade": "primary_slope"})
    threshold_frames, threshold_summary = [], []
    for low_q, high_q in config["classification"]["wetness_quantile_sensitivity"]:
        quantiles = calibration["sensitivity_quantiles"]
        lower, upper = quantiles[str(low_q)], quantiles[str(high_q)]
        sample = _assign_wetness(primary, lower, upper)
        sample = _assign_mechanism(sample,
            config["classification"]["rainfall_intensity_share_threshold"],
            config["classification"]["rainfall_temporal_cv_threshold"])
        print(f"Wetness cut-point diagnostic: {low_q}/{high_q}", flush=True)
        alternate = _direction_only_trends(sample, years, config, include_overall=False, groups=groups)
        compared = reference.merge(alternate[keys + ["display_slope_per_decade"]], on=keys, how="left", validate="one_to_one")
        compared["estimable"] = compared.display_slope_per_decade.notna()
        compared["same_direction"] = compared.estimable & (np.sign(compared.primary_slope) == np.sign(compared.display_slope_per_decade))
        compared["lower_quantile"], compared["upper_quantile"] = low_q, high_q
        compared["lower_ssi"], compared["upper_ssi"] = lower, upper
        threshold_frames.append(compared)
        supported = compared[compared.supported_shift]
        threshold_summary.append({
            "quantiles": [low_q, high_q], "ssi_cutoffs": [lower, upper],
            "primary_supported": len(supported),
            "estimable": int(supported.estimable.sum()),
            "same_direction": int(supported.same_direction.sum()),
        })
    pd.concat(threshold_frames, ignore_index=True).to_csv(tables / "wetness_threshold_sensitivity.csv", index=False)
    conditions = pd.read_csv(tables / "catchment_conditions_trends.csv")
    reference = conditions.loc[conditions.outcome.eq("antecedent_wetness"), ["GCIN", "display_slope_per_decade", "supported_shift"]].rename(columns={"display_slope_per_decade": "primary_slope"})
    window_frames, window_summary = [], []
    for window in config["classification"]["ssi_windows_days"]:
        sample = primary.assign(ssi_1d=primary[f"ssi_{window}d"])
        result = _magnitude_trends(sample, config["trends"]["minimum_overall_years"],
            config["trends"]["minimum_overall_span_years"], outcomes=["antecedent_wetness"])
        compared = reference.merge(result[["GCIN", "display_slope_per_decade", "n_years", "p_value"]], on="GCIN", how="left", validate="one_to_one")
        compared["window_days"] = window
        compared["same_direction"] = np.sign(compared.primary_slope) == np.sign(compared.display_slope_per_decade)
        window_frames.append(compared)
        supported = compared[compared.supported_shift]
        window_summary.append({"days": window, "estimated": len(result),
            "primary_supported": len(supported), "estimable": int(supported.display_slope_per_decade.notna().sum()),
            "same_direction": int(supported.same_direction.sum())})
    pd.concat(window_frames, ignore_index=True).to_csv(tables / "wetness_window_sensitivity.csv", index=False)
    summary = {"status": "complete", "role": "Diagnostics; not additional support gates",
        "thresholds": threshold_summary, "windows": window_summary}
    (logs / "wetness_sensitivity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
