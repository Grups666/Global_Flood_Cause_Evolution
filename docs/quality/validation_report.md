# Validation report

**Status:** PASS
**Checks:** 20 / 20 passed
**Execution date:** 2026-09-05

| Check | Status | Evidence |
|---|---:|---|
| `event_key_unique` | PASS | feature rows=1,407,121 |
| `record_eligibility_exact` | PASS | eligible catchments=2,839 |
| `pot_q95_sample_exact` | PASS | events=58,991; catchments=2,637 |
| `annual_maximum_sample_exact` | PASS | events=100,788; catchments=2,839 |
| `pot_q90_sample_exact` | PASS | events=119,334; catchments=2,814 |
| `pot_q975_sample_exact` | PASS | events=24,291; catchments=1,877 |
| `six_process_classification_exact` | PASS | Dry-Intensity=1,037, Dry-Volume=11,325, Moderate-Intensity=1,776, Moderate-Volume=15,960, Wet-Intensity=2,920, Wet-Volume=25,973 |
| `primary_event_and_span_floor` | PASS | minimum events=10; minimum selected span=20 |
| `event_independence_diagnostics` | PASS | overlapping stormflow windows=0; adjacent peaks under 10 days=875 |
| `catchment_evidence_gates_exact` | PASS | overall supported=264; process supported=523 |
| `single_process_event_threshold` | PASS | threshold=5; no sample-size tiers |
| `finite_reported_effects` | PASS | overall estimates=7,631; process estimates=19,300 |
| `daily_reconstruction_spot_check` | PASS | 20 events; failures=[] |
| `six_current_figures` | PASS | figure_01_sample_and_process_coverage:3981x2107; figure_02_overall_flood_changes:4312x1595; figure_03_process_frequency_changes:4105x2278; figure_04_process_share_changes:4105x2278; figure_05_process_response_rankings:3943x2107; figure_06_example_process_trajectories:3914x1425 |
| `current_report_scope` | PASS | forbidden terms absent: HydroBASINS, BH-FDR, unadjusted p, 10-day declustering, previous version, old version |
| `markdown_local_links` | PASS | none missing |
| `self_contained_html` | PASS | embedded figures=6; bytes=5,861,161 |
| `catchment_point_web_schema` | PASS | catchment points=2,637; process classes=6 |
| `interactive_ui_semantics` | PASS | catchment points, pale all-estimate directions, supported z-order, pointer-anchored opaque tooltip |
| `public_report_sync` | PASS | HTML and six PNG assets match reports/ |

The validator independently reconstructs record eligibility and the event-volume Q95 sample, checks the six process labels and evidence gates, verifies report assets and the self-contained HTML, and confirms that the interactive payload contains observed catchment points only.
