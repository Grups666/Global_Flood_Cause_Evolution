"""Event-level fits for one-axis filters, retaining the selected-Q95 denominator.

These are overlapping filter views, not five additional event types. Continuous
trends are refitted after pooling matching events, never averaged from class
slopes. The original six joint classes and all-event fits remain unchanged.
"""
from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd

from .analysis import (
    MARGINAL_GROUPS, SAMPLE_FILES, _assign_mechanism, _attach_sensitivity,
    _direction_only_trends, _finalize_evidence, _group_mask, _mechanism_trends,
    _record_eligibility, _study_events,
)


def run_filter_groups(config: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    derived, tables = config["paths"]["derived_data"], config["paths"]["tables"]
    samples = {name: pd.read_parquet(derived / filename) for name, filename in SAMPLE_FILES.items()}
    primary = samples["pot_q95"]
    # Frequency includes zero selected events in observed catalogue years;
    # years absent from that catalogue must never be manufactured as zeros.
    events = _study_events(pd.read_parquet(derived / "event_features.parquet"), config)
    _, eligible_ids = _record_eligibility(events, config)
    record_years = events[events.GCIN.isin(eligible_ids)][["GCIN", "peak_year"]].drop_duplicates()
    del events
    print("Fitting five one-axis event groups...", flush=True)
    result = _mechanism_trends(primary, record_years, config, groups=MARGINAL_GROUPS)
    alternatives = {}
    for name in config["event_samples"]["sensitivity_samples"]:
        print(f"Checking event sample: {name}", flush=True)
        alternatives[name] = _direction_only_trends(
            samples[name], record_years, config, include_overall=False, groups=MARGINAL_GROUPS,
        )
    cutoffs = {}
    forcing_groups = [group for group in MARGINAL_GROUPS if not group.endswith("-All")]
    for cutoff in config["classification"]["rainfall_intensity_share_sensitivity"]:
        print(f"Checking rainfall cutoff: {cutoff}", flush=True)
        alternate = _assign_mechanism(primary, float(cutoff), float(config["classification"]["rainfall_temporal_cv_threshold"]))
        cutoffs[f"cutoff_{str(cutoff).replace('.', '_')}"] = _direction_only_trends(
            alternate, record_years, config, include_overall=False, groups=forcing_groups,
        )
    result = _attach_sensitivity(result, alternatives, cutoffs)
    result["classification_check_applies"] = result.mechanism.isin(forcing_groups)
    # A wetness-only filter does not depend on rainfall-type cutoffs.
    result.loc[~result.classification_check_applies, "classification_direction_stable"] = True
    print("Checking leave-one-year-out stability...", flush=True)
    result = _finalize_evidence(primary, result, record_years, config, require_classification_check=True)
    metadata = primary[["GCIN", "country", "continent", "longitude", "latitude"]].drop_duplicates("GCIN")
    result = result.merge(metadata, on="GCIN", how="left", validate="many_to_one")
    result.to_csv(tables / "catchment_filter_group_trends.csv", index=False)
    counts = []
    for group in MARGINAL_GROUPS:
        matching = primary[_group_mask(primary, group)].groupby("GCIN").size()
        for gcin, total in primary.groupby("GCIN").size().items():
            count = int(matching.get(gcin, 0))
            counts.append({"GCIN": int(gcin), "group": group, "events": count,
                           "other_events": int(total) - count, "all_q95_events": int(total)})
    pd.DataFrame(counts).to_csv(tables / "catchment_filter_group_counts.csv", index=False)
    summary = {
        "status": "complete", "sample": "pot_q95", "events": len(primary),
        "groups": {group: {
            "events": int(_group_mask(primary, group).sum()),
            "estimates": int(result.mechanism.eq(group).sum()),
            "supported": int((result.mechanism.eq(group) & result.supported_shift).sum()),
        } for group in MARGINAL_GROUPS},
        "elapsed_seconds": round(time.time() - started, 1),
    }
    (config["paths"]["logs"] / "filter_groups_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
