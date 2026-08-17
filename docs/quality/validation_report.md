# Analysis Validation Report

**Validation date:** 2026-08-17  
**Overall status:** Computational checks pass; scientific conclusions are
shareable with the documented representativeness and attribution caveats.

## Scope

The validation suite checks the saved analytical objects independently of the
report prose. It does not establish causal attribution or validate the GLASS
soil-moisture product against a second remote-sensing product.

## Results

All 21 automated checks pass:

| Area | Result | Evidence |
|---|---|---|
| Event identity | Pass | 1,407,121 unique event keys |
| Annual-max sample | Pass | Exact reproduction of 100,788 saved events; one event per catchment-year |
| POT/Q95 sample | Pass | Exact reproduction of 68,135 saved events and minimum-event screen |
| Rainfall classifications | Pass | 0.50, joint 0.50/CV, and 0.75 definitions reproduced exactly |
| Wetness classifications | Pass | 1-, 3-, 7-, and 30-day labels reproduced exactly |
| Fixed-effect slopes | Pass | Four global slopes recalculated to numerical precision below `1e-12` |
| Multiple testing | Pass | Binary-trend Benjamini–Hochberg values reproduced; maximum absolute error `3.87e-14` |
| Cause composition | Pass | Regional category shares sum to one; maximum error `2.22e-16` |
| HydroBASINS assignment | Pass | 2,835 of 2,839 primary catchments assigned; the four unmatched island gauges are explicitly retained in the audit |
| Local primary FDR | Pass | 144 planned tests, 138 finite p-values; independently reproduced with maximum error `1.28e-15` |
| Largest local slope | Pass | `HB5-712410` intensity slope independently reproduced as `+10.543555` percentage points/decade |
| Local paired-period change | Pass | Same-basin early/late comparison independently reproduced across 10 catchments |
| Local stability gates | Pass | All 17 high-confidence signals pass replication, definition-direction, and leave-one-catchment-out gates |
| Raw daily reconstruction | Pass | Deterministic sample of 24 events matched precipitation total, maximum daily precipitation, and peak flow |
| Figure assets | Pass | Nine PNG/SVG pairs valid; report-local PNG copies match their source hashes |
| Markdown links | Pass | No unresolved local report or documentation links |
| Browser report | Pass | Self-contained HTML includes the four core-report figures, navigation, and no local image dependency |
| Interactive explorer | Pass | 72 HydroBASINS polygons, 2,839 catchments, three sample-support outline states, and 17 high-confidence signals validated |
| Text encoding | Pass | All Markdown files decode as UTF-8 without replacement characters |
| HydroBASINS archives | Pass | All 24 official level 3–5 regional ZIP archives pass ZIP integrity, byte-size, and SHA-256 checks |

The machine-readable receipt is
[`outputs/logs/validation.json`](../../outputs/logs/validation.json). The suite
is implemented in [`src/validate_outputs.py`](../../src/validate_outputs.py).

## Manual figure review

All nine PNG figures were inspected after generation. Titles, legends,
confidence intervals, map keys, footnotes, whitespace, and text collisions were
checked. The focused report uses four of these figures; the other five remain
available as supporting analysis outputs. The self-contained HTML is 3,068,460
bytes and has no local image dependency. It contains the figure lightbox, zoom
cursor, and Escape-key close handler. SVG counterparts are retained for
publication editing.

## Reference-file integrity

Natural Earth archive:

```text
data/reference/ne_110m_admin_0_countries.zip
SHA-256 0f243aeac8ac6cf26f0417285b0bd33ac47f1b5bdb719fd3e0df37d03ea37110
```

The multi-gigabyte source dataset remains outside this repository and is
read-only. Its row counts, file counts, date span, and known identifier issues
are recorded in [data_audit.md](data_audit.md).

## Interpretation gate

The computational evidence supports the report's three central statements:

1. high-confidence local hydrological units contain opposing changes of roughly
   two to eleven percentage points per decade that are hidden by broad averages,
   with two signals explicitly marked as limited-sample units;
2. short-window antecedent wetness declines modestly in both extreme-event
   samples; and
3. the global rainfall-organization trend is threshold- and sample-sensitive.

The following stronger claims are not validated and must not be made:

- a globally representative land-area-weighted trend;
- a universal change from volume- to intensity-dominated floods;
- a causal interpretation of any HydroBASINS hotspot or independence between
  neighboring hydrological units;
- causal attribution to anthropogenic climate change;
- robustness to sub-daily precipitation or an independent soil-moisture
  product.

## Release decision

The current research package is ready for internal circulation and for use as
the quantitative foundation of a manuscript. Journal submission should wait
for the priority robustness work listed in the main report, especially an
independent soil-moisture product check and a finer-time-resolution rainfall
validation where data permit.
