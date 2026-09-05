"""Independently reconcile one-axis filter results with their source events."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from floodcause.analysis import MAGNITUDE_VARIABLES, MARGINAL_GROUPS, _group_mask
from floodcause.statistics import binomial_probability_trend, poisson_rate_trend
from validate_outputs import study_events, expected_eligibility

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs/tables"


def main() -> None:
    sample = pd.read_parquet(ROOT / "data/derived/primary_extreme_events.parquet")
    table = pd.read_csv(TABLES / "catchment_filter_group_trends.csv", low_memory=False)
    counts = pd.read_csv(TABLES / "catchment_filter_group_counts.csv")
    payload = json.loads((ROOT / "public/modules/flood-cause-evolution/data/flood-cause-explorer.json").read_text(encoding="utf-8"))
    web = {item["id"]: item for item in payload["catchments"]}
    assert not table.duplicated(["GCIN", "mechanism", "outcome"]).any()
    assert set(table.mechanism) == set(MARGINAL_GROUPS)
    assert counts.groupby("group").size().eq(sample.GCIN.nunique()).all()
    checked_slopes, checked_metrics = 0, 0
    all_counts = sample.groupby("GCIN").size()
    for group in MARGINAL_GROUPS:
        wetness, forcing = group.split("-")
        # Independent rainfall membership remains known even without SSI.
        intensity = sample.intensity_fraction.gt(.5) & sample.precipitation_cv.gt(1)
        expected = (sample.antecedent_state.eq(wetness) if wetness != "All" else pd.Series(True, index=sample.index))
        expected &= (intensity.eq(forcing == "Intensity") if forcing != "All" else pd.Series(True, index=sample.index))
        known = sample if wetness == "All" else sample[sample.ssi_1d.notna()]
        known_counts = known.groupby("GCIN").size().reindex(all_counts.index, fill_value=0)
        assert expected.equals(_group_mask(sample, group))
        selected = sample[expected]
        observed = selected.groupby("GCIN").size().reindex(all_counts.index, fill_value=0)
        audit = counts[counts.group.eq(group)].set_index("GCIN").reindex(all_counts.index)
        np.testing.assert_array_equal(audit.events, observed)
        np.testing.assert_array_equal(audit.other_events, known_counts - observed)
        np.testing.assert_array_equal(audit.known_group_events, known_counts)
        np.testing.assert_array_equal(audit.unknown_group_events, all_counts - known_counts)
        np.testing.assert_array_equal(audit.all_q95_events, all_counts)
        part = table[table.mechanism.eq(group)]
        assert part.classification_check_applies.eq(forcing != "All").all()
        if forcing == "All":
            assert part.classification_direction_stable.all()
        for outcome, (variable, _) in MAGNITUDE_VARIABLES.items():
            valid = selected.dropna(subset=[variable])
            annual = valid.groupby(["GCIN", "peak_year"])[variable].mean()
            groups = {int(gcin): values.droplevel(0) for gcin, values in annual.groupby(level=0)}
            event_counts = valid.groupby("GCIN").size()
            estimates = part[part.outcome.eq(outcome)].set_index("GCIN")
            eligible = {gcin for gcin, values in groups.items() if len(values) >= 5 and values.index.max() - values.index.min() + 1 >= 15}
            assert set(estimates.index) == eligible, (group, outcome, "eligibility")
            for gcin, row in estimates.iterrows():
                values = groups[gcin]
                x, y = values.index.to_numpy(float), values.to_numpy(float)
                i, j = np.triu_indices(len(x), 1)
                slope = 10 * np.median((y[j] - y[i]) / (x[j] - x[i]))
                if outcome == "rainfall_concentration":
                    slope *= 100
                np.testing.assert_allclose(row.display_slope_per_decade, slope, rtol=1e-9, atol=1e-10)
                assert row.n_observations == event_counts[gcin]
                assert row.n_years == len(values)
                checked_slopes += 1
        shares = part[part.outcome.eq("mechanism_share")].set_index("GCIN")
        for gcin, row in shares.iterrows():
            assert row.n_mechanism_events == observed[gcin]
            assert row.n_other_events == known_counts[gcin] - observed[gcin]
            assert row.n_observations == known_counts[gcin]
            np.testing.assert_allclose(row.mean_level, 100 * observed[gcin] / known_counts[gcin])
        for row in part.itertuples(index=False):
            metric = web[row.GCIN]["processes"][group][row.outcome]
            assert metric["slope"] == round(row.display_slope_per_decade, 6)
            assert metric["events"] == row.n_observations
            expected_gate = row.p_value < 0.05 and row.sample_direction_stable and row.classification_direction_stable and row.leave_one_year_stable
            assert metric["supported"] == bool(expected_gate) == bool(row.supported_shift)
            checked_metrics += 1
    # Refit one share and one frequency model per marginal group, ensuring
    # the denominator/calendar has not become only the matching-event years.
    features = pd.read_parquet(ROOT / "data/derived/event_features.parquet")
    events = study_events(features)
    coverage = expected_eligibility(events)
    eligible = set(coverage.loc[coverage.eligible, "GCIN"])
    record = events[events.GCIN.isin(eligible)][["GCIN", "peak_year"]].drop_duplicates()
    model_checks = 0
    for group in MARGINAL_GROUPS:
        for outcome in ["mechanism_share", "mechanism_frequency"]:
            row = table[table.mechanism.eq(group) & table.outcome.eq(outcome)].iloc[0]
            catchment = sample[sample.GCIN.eq(row.GCIN)]
            selected = catchment[_group_mask(catchment, group)]
            yes = selected.groupby("peak_year").size()
            if outcome == "mechanism_share":
                known = catchment if group.startswith("All-") else catchment[catchment.ssi_1d.notna()]
                totals = known.groupby("peak_year").size()
                fit = binomial_probability_trend(totals.index.to_numpy(float), yes.reindex(totals.index, fill_value=0).to_numpy(float), totals.to_numpy(float))
            else:
                years = record.loc[record.GCIN.eq(row.GCIN), "peak_year"].sort_values().to_numpy(float)
                if not group.startswith("All-"):
                    unknown_years = catchment.loc[catchment.ssi_1d.isna(), "peak_year"]
                    years = years[~np.isin(years, unknown_years)]
                values = yes.reindex(years, fill_value=0).to_numpy(float)
                fit = poisson_rate_trend(years, values)
                assert row.n_years == len(years)
                np.testing.assert_allclose(row.mean_level, values.mean())
            np.testing.assert_allclose(row.display_slope_per_decade, fit["display_slope_per_decade"], atol=1e-10)
            np.testing.assert_allclose(row.p_value, fit["p_value"], atol=1e-10)
            model_checks += 1
    print(json.dumps({"status": "passed", "groups": len(MARGINAL_GROUPS),
                      "event_count_rows": len(counts), "continuous_slopes": checked_slopes,
                      "web_metrics": checked_metrics, "count_model_refits": model_checks}))


if __name__ == "__main__":
    main()
