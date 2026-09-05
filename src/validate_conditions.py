"""Independent annual-observation and UI-data reconciliation for conditions."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    tables = ROOT / "outputs" / "tables"
    sample = pd.read_parquet(ROOT / "data" / "derived" / "primary_extreme_events.parquet")
    trends = pd.read_csv(tables / "catchment_conditions_trends.csv")
    annual = pd.read_csv(tables / "catchment_conditions_annual.csv")
    audit = pd.read_csv(tables / "catchment_conditions_eligibility.csv")
    payload = json.loads((ROOT / "public" / "modules" / "flood-cause-evolution" / "data" / "flood-cause-explorer.json").read_text(encoding="utf-8"))
    web = {row["id"]: row for row in payload["catchments"]}
    checks = []
    for outcome, variable, factor, bound in [
        ("rainfall_concentration", "intensity_fraction", 100., 100.),
        ("antecedent_wetness", "source_ssi", 1., 1.),
    ]:
        valid = sample.dropna(subset=[variable])
        expected = valid.groupby(["GCIN", "peak_year"])[variable].agg(["mean", "size"]).reset_index()
        expected["mean"] *= factor
        saved = annual[annual.outcome.eq(outcome)].sort_values(["GCIN", "peak_year"]).reset_index(drop=True)
        assert np.array_equal(expected[["GCIN", "peak_year"]], saved[["GCIN", "peak_year"]])
        assert np.allclose(expected["mean"], saved.value, atol=1e-12)
        assert np.array_equal(expected["size"], saved.events)
        assert expected["mean"].between(0, bound).all()
        audit_part = audit[audit.outcome.eq(outcome)]
        assert (audit_part.valid_events + audit_part.missing_events).equals(audit_part.selected_events)
        assert audit_part.selected_events.sum() == len(sample)
        expected_ids = set(audit_part.loc[(audit_part.valid_years >= 10) & (audit_part.span >= 20), "GCIN"])
        fitted = trends[trends.outcome.eq(outcome)]
        assert expected_ids == set(fitted.GCIN)
        grouped = {int(key): frame for key, frame in expected.groupby("GCIN")}
        for row in fitted.itertuples(index=False):
            points = grouped[int(row.GCIN)]
            model = stats.theilslopes(points["mean"], points.peak_year)
            metric = web[int(row.GCIN)]["conditions"][outcome]
            assert np.isclose(row.display_slope_per_decade, model.slope * 10, atol=1e-10)
            assert np.isclose(metric["slope"], model.slope * 10, atol=0.00000051)
            assert np.allclose(np.array(metric["annual"]), points[["peak_year", "mean", "size"]], atol=0.00000051)
            assert np.isclose(metric["from"], model.intercept + model.slope * row.first_year, atol=0.00000051)
            assert np.isclose(metric["to"], model.intercept + model.slope * row.last_year, atol=0.00000051)
            assert metric["supported"] == bool(row.p_value < .05 and row.sample_direction_stable and row.leave_one_year_stable)
            assert metric["classificationStable"]  # not an applicable gate in this population
        checks.append({"metric": outcome, "annual_points": len(expected), "trends": len(fitted), "supported": int(fitted.supported_shift.sum()), "excluded_catchments": len(audit_part) - len(fitted)})
    assert len(trends) == sum(len(item["conditions"]) for item in web.values())
    receipt = {"status": "passed", "checks": checks}
    (ROOT / "outputs" / "logs" / "conditions_validation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
