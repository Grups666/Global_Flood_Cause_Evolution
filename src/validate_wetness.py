"""Independent timing, label, missingness and unchanged-outcome regression checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from floodcause.analysis import _assign_wetness, _group_observed, _usable_rate_years

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "1112b2e787fd071e9a99a7e6df56217647941696"


def main():
    tables, logs = ROOT / "outputs/tables", ROOT / "outputs/logs"
    calibration = json.loads((logs / "wetness_daily_calibration.json").read_text(encoding="utf-8"))
    sample = pd.read_parquet(ROOT / "data/derived/primary_extreme_events.parquet")
    alignment = pd.read_csv(tables / "wetness_event_time_alignment.csv").set_index("event_key")
    aligned = sample.set_index("event_key").join(alignment[["ssi_on_previous_day"]], validate="one_to_one")
    np.testing.assert_allclose(aligned.ssi_1d, aligned.ssi_on_previous_day, rtol=0, atol=1e-14, equal_nan=True)
    assert calibration["event_ssi_day_offset"] == -1
    ids = sorted(sample.GCIN.unique())
    assert hashlib.sha256(",".join(map(str, ids)).encode()).hexdigest() == calibration["cohort_id_sha256"]
    assert hashlib.sha256("\n".join(sorted(sample.event_key)).encode()).hexdigest() == calibration["primary_event_keys_sha256"]
    catchment_audit = pd.read_csv(tables / "wetness_daily_calibration_catchments.csv")
    assert set(catchment_audit.GCIN) == set(ids)
    assert catchment_audit.valid_ssi_days.sum() == calibration["valid_ssi_days"]
    assert sum(calibration["daily_class_counts"].values()) == calibration["valid_ssi_days"]
    assert max(calibration["daily_class_counts"].values()) - min(calibration["daily_class_counts"].values()) <= 10
    low, high = calibration["terciles"]["lower"], calibration["terciles"]["upper"]
    expected = np.select([sample.ssi_1d.le(low), sample.ssi_1d.le(high), sample.ssi_1d.gt(high)],
        ["Dry", "Moderate", "Wet"], default="Unknown")
    np.testing.assert_array_equal(sample.antecedent_state, expected)
    fixture = pd.DataFrame({"ssi_1d": [0., low, (low+high)/2, high, 1., np.nan, -1., 2.]})
    assert _assign_wetness(fixture, low, high).antecedent_state.tolist() == ["Dry", "Dry", "Moderate", "Moderate", "Wet", "Unknown", "Unknown", "Unknown"]
    missing = sample[sample.ssi_1d.isna()]
    assert len(missing) == 7 and missing.start_precip_date.eq(pd.Timestamp("1982-01-01")).all()
    assert sample.mechanism.eq("Unclassified").sum() == len(missing)
    for group in ["Wet-All", "Dry-Intensity", "All-Intensity"]:
        known = _group_observed(sample, group)
        assert known.sum() == len(sample) - (0 if group.startswith("All-") else 7)
        years = sample[["GCIN", "peak_year"]].drop_duplicates()
        retained = _usable_rate_years(sample, years, group)
        assert len(years) - len(retained) == (0 if group.startswith("All-") else 7)
    # Selection and non-wetness whole-sample inference must not move.
    relative = "public/modules/flood-cause-evolution/data/flood-cause-explorer.json"
    old = json.loads(subprocess.check_output(["git", "show", f"{BASELINE_COMMIT}:{relative}"], cwd=ROOT))
    new = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    old_by_id = {item["id"]: item for item in old["catchments"]}
    assert old["meta"]["primaryEvents"] == new["meta"]["primaryEvents"] == len(sample)
    checked = 0
    for item in new["catchments"]:
        prior = old_by_id[item["id"]]
        for outcome, metric in item["overall"].items():
            reference = prior["overall"][outcome]
            assert all(metric[key] == value for key, value in reference.items()), (item["id"], outcome)
            checked += 1
        concentration = item["conditions"].get("rainfall_concentration")
        if concentration:
            assert all(concentration[key] == value for key, value in prior["conditions"]["rainfall_concentration"].items())
            checked += 1
        assert item["missingPreviousDaySSI"] == int((missing.GCIN == item["id"]).sum())
    calibration_public = {key: value for key, value in calibration.items() if key != "daily_source"}
    calibration_public["source"] = "Event_Typology: Global Data/daily_data/observations (read-only)"
    calibration_public["sensitivity"] = json.loads((logs / "wetness_sensitivity_summary.json").read_text(encoding="utf-8"))
    calibration_public["validation"] = {"status": "passed", "aligned_primary_events": len(aligned),
        "unchanged_flood_and_concentration_trends": checked, "baseline_commit": BASELINE_COMMIT}
    (ROOT / "docs/quality/wetness_calibration.json").write_text(json.dumps(calibration_public, indent=2), encoding="utf-8")
    print(json.dumps(calibration_public["validation"]))


if __name__ == "__main__":
    main()
