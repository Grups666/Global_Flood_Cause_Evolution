# Validation report

**Status:** PASS
**Checks:** 20 / 20 passed
**Execution date:** 2026-09-01

| Check | Status | Evidence |
|---|---:|---|
| `event_key_unique` | PASS | source feature rows=1,407,121 |
| `record_eligibility_exact` | PASS | eligible=2,839 |
| `primary_pot_q95_exact` | PASS | expected=59,048; saved=59,048; catchments=2,624 |
| `primary_event_and_span_floor` | PASS | minimum events=10; minimum span=20 |
| `event_independence_diagnostics` | PASS | Q95 overlaps=0; Q95 pairs<10d=2,194; declustered pairs<10d=0 |
| `complete_regional_fdr` | PASS | tests=1,475; L5=295; FDR-supported=106; max error=3.77e-15 |
| `regional_statistical_gates` | PASS | signals=94; L5=43 |
| `area_support_threshold_sensitivity` | PASS | thresholds=[10, 20, 30, 40, 50]; passing L5=[156, 85, 50, 34, 19]; strong signals=[84, 42, 28, 19, 10] |
| `continuous_time_trajectories` | PASS | rows=35,833; years=1982–2019 |
| `catchment_trend_eligibility` | PASS | catchments=2,435; tests=12,163 |
| `catchment_fdr_and_stability` | PASS | metric q max error=6.18e-14; family q error=1.33e-15; stable candidates=378; FDR signals=0 |
| `figure_assets` | PASS | 6 report PNGs synchronized; 6 publication SVGs generated |
| `self_contained_html_report` | PASS | bytes=5,219,309; embedded PNGs=6 |
| `published_research_materials` | PASS | self-contained report and 6 overview figures synchronized to public/ |
| `interactive_web_explorer` | PASS | basins=295; catchments=2435; strong signals=94; bytes=11,900,481 |
| `current_only_narrative` | PASS | obsolete phrases=[] |
| `daily_reconstruction_spot_check` | PASS | 20 events; failures=[] |
| `markdown_local_links` | PASS | none missing |
| `utf8_documents` | PASS | replacement-character files=[] |
| `hydrobasins_reference_integrity` | PASS | archives=8; failures=[] |

The validator independently reconstructs the primary POT/Q95 sample, recomputes the declared FDR family and evidence gates, checks display eligibility, verifies all report assets and the self-contained HTML, and validates the interactive JSON schema.
