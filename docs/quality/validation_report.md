# Validation report

**Status:** PASS
**Checks:** 19 / 19 passed
**Execution date:** 2026-09-01

| Check | Status | Evidence |
|---|---:|---|
| `event_key_unique` | PASS | source feature rows=1,407,121 |
| `record_eligibility_exact` | PASS | eligible=2,839 |
| `primary_pot_q95_exact` | PASS | expected=59,048; saved=59,048; catchments=2,624 |
| `primary_event_and_span_floor` | PASS | minimum events=10; minimum span=20 |
| `event_independence_diagnostics` | PASS | Q95 overlaps=0; Q95 pairs<10d=2,194; declustered pairs<10d=0 |
| `complete_primary_fdr` | PASS | tests=140; FDR-supported=80; max error=3e-16 |
| `single_regional_sample_threshold` | PASS | minimum catchments=20; regions=28 |
| `strong_evidence_gates` | PASS | signals=62; basins=21 |
| `continuous_time_trajectories` | PASS | rows=5,164; years=1982–2019 |
| `catchment_trend_eligibility` | PASS | catchments=2,624; FDR-supported=1 |
| `figure_assets` | PASS | 6 report PNGs synchronized; 6 publication SVGs generated |
| `self_contained_html_report` | PASS | bytes=3,890,921; embedded PNGs=6 |
| `published_research_materials` | PASS | self-contained report and 6 overview figures synchronized to public/ |
| `interactive_web_explorer` | PASS | basins=28; catchments=2624; strong signals=62; bytes=3,835,094 |
| `current_only_narrative` | PASS | obsolete phrases=[] |
| `daily_reconstruction_spot_check` | PASS | 20 events; failures=[] |
| `markdown_local_links` | PASS | none missing |
| `utf8_documents` | PASS | replacement-character files=[] |
| `hydrobasins_reference_integrity` | PASS | archives=8; failures=[] |

The validator independently reconstructs the primary POT/Q95 sample, recomputes the declared FDR family and evidence gates, checks display eligibility, verifies all report assets and the self-contained HTML, and validates the interactive JSON schema.
