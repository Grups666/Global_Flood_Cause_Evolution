"""Unclassified continuous conditions for the same selected Q95 flood sample.

This stage reuses the established catchment trend and evidence functions. No
wetness or rainfall-type threshold is used to subset the selected events.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .analysis import (
    MAGNITUDE_VARIABLES, SAMPLE_FILES, _attach_sensitivity,
    _finalize_evidence, _magnitude_trends,
)

CONDITION_OUTCOMES = ["rainfall_concentration", "antecedent_wetness"]


def run_conditions_analysis(config: dict[str, Any]) -> dict[str, Any]:
    derived, tables = config["paths"]["derived_data"], config["paths"]["tables"]
    samples = {name: pd.read_parquet(derived / filename) for name, filename in SAMPLE_FILES.items()}
    settings = config["trends"]
    estimates = {
        name: _magnitude_trends(
            sample, settings["minimum_overall_years"],
            settings["minimum_overall_span_years"], outcomes=CONDITION_OUTCOMES,
        )
        for name, sample in samples.items()
    }
    primary = samples["pot_q95"]
    result = _attach_sensitivity(estimates["pot_q95"], {
        name: estimates[name] for name in config["event_samples"]["sensitivity_samples"]
    })
    result = _finalize_evidence(
        primary, result, primary[["GCIN", "peak_year"]].drop_duplicates(),
        config, require_classification_check=False,
    )
    metadata = primary[["GCIN", "country", "continent", "longitude", "latitude"]].drop_duplicates("GCIN")
    result = result.merge(metadata, on="GCIN", how="left", validate="many_to_one")
    result.to_csv(tables / "catchment_conditions_trends.csv", index=False)

    annual_frames, audit_rows = [], []
    for outcome in CONDITION_OUTCOMES:
        variable = MAGNITUDE_VARIABLES[outcome][0]
        valid = primary.dropna(subset=[variable])
        annual = valid.groupby(["GCIN", "peak_year"], as_index=False).agg(
            value=(variable, "mean"), events=(variable, "size"),
        )
        annual["outcome"] = outcome
        if outcome == "rainfall_concentration":
            annual["value"] *= 100.0
        annual_frames.append(annual)
        estimated = set(result.loc[result.outcome.eq(outcome), "GCIN"])
        for gcin, frame in primary.groupby("GCIN", sort=False):
            values = frame.dropna(subset=[variable])
            years = values.peak_year.nunique()
            span = int(values.peak_year.max() - values.peak_year.min() + 1) if years else 0
            audit_rows.append({
                "GCIN": int(gcin), "outcome": outcome, "selected_events": len(frame),
                "valid_events": len(values), "missing_events": len(frame) - len(values),
                "valid_years": years, "span": span, "estimated": gcin in estimated,
                "reason": "estimated" if gcin in estimated else (
                    "insufficient_valid_years" if years < settings["minimum_overall_years"]
                    else "insufficient_year_span"
                ),
            })
    pd.concat(annual_frames, ignore_index=True).to_csv(tables / "catchment_conditions_annual.csv", index=False)
    pd.DataFrame(audit_rows).to_csv(tables / "catchment_conditions_eligibility.csv", index=False)
    summary = {
        "sample": "pot_q95", "events": len(primary), "catchments": int(primary.GCIN.nunique()),
        "population": "All selected floods, without a wetness or rainfall-class filter",
        "minimum_valid_years": settings["minimum_overall_years"],
        "minimum_span_years": settings["minimum_overall_span_years"],
        "metrics": {
            outcome: {
                "estimated": int(result.outcome.eq(outcome).sum()),
                "supported": int((result.outcome.eq(outcome) & result.supported_shift).sum()),
            } for outcome in CONDITION_OUTCOMES
        },
    }
    (config["paths"]["logs"] / "conditions_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
