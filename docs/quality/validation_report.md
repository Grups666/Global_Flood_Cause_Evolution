# Validation report

**Status:** PASS
**Checks:** 17 / 17 passed
**Execution date:** 2026-08-18

| Check | Status | Evidence |
|---|---:|---|
| `event_key_unique` | PASS | source feature rows=1,407,121 |
| `record_eligibility_exact` | PASS | eligible=2,839 |
| `primary_pot_q95_exact` | PASS | expected=59,048; saved=59,048; catchments=2,624 |
| `primary_event_and_span_floor` | PASS | minimum events=10; minimum span=20 |
| `event_independence_diagnostics` | PASS | Q95 overlaps=0; Q95 pairs<10d=2,194; declustered pairs<10d=0 |
| `complete_primary_fdr` | PASS | tests=490; FDR-supported=160; max error=1.26e-15 |
| `strong_evidence_gates` | PASS | signals=63; basins=23 |
| `continuous_time_trajectories` | PASS | rows=19,648; years=1982–2019 |
| `catchment_trend_eligibility` | PASS | catchments=2,624; FDR-supported=1 |
| `figure_assets` | PASS | 6 report PNGs synchronized; 6 publication SVGs generated |
| `self_contained_html_report` | PASS | bytes=3,993,379; embedded PNGs=6 |
| `interactive_web_explorer` | PASS | basins=98; catchments=2624; strong signals=63; bytes=5,184,149 |
| `current_only_narrative` | PASS | obsolete phrases=[] |
| `daily_reconstruction_spot_check` | PASS | 20 events; failures=[] |
| `markdown_local_links` | PASS | none missing |
| `utf8_documents` | PASS | replacement-character files=[] |
| `hydrobasins_reference_integrity` | PASS | archives=24; failures=[] |

The validator independently reconstructs the primary POT/Q95 sample, recomputes the declared FDR family and evidence gates, checks display eligibility, verifies all report assets and the self-contained HTML, and validates the interactive JSON schema.
