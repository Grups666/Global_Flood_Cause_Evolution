# Execution manifest

**Execution date:** 2026-09-04

**Study period:** 1982–2019

**Primary selection:** catchment-specific full-record Q95 of event direct stormflow volume

## Data flow

| Stage | Output |
|---|---:|
| Reconstructed hydrological events | 1,407,121 |
| Catchments processed | 4,150 |
| Catchments passing the long-record gate | 2,839 |
| Primary Q95 events | 58,991 |
| Catchments retained in the primary Q95 sample | 2,637 |
| Q90 sensitivity events | 119,334 |
| Q97.5 sensitivity events | 24,291 |
| Annual-maximum sensitivity events | 100,788 |

## Current inference

- Three catchment-level outcomes describe all selected floods: direct stormflow volume, maximum daily streamflow and annual Q95-event frequency.
- Six event mechanisms cross dry/moderate/wet antecedent state with intensity/volume rainfall organization.
- Each mechanism is analysed for annual frequency, share of selected floods, rainfall concentration, antecedent SSI, direct stormflow volume and daily peak.
- Continuous physical variables use Theil–Sen slopes and tie-corrected Mann–Kendall tests.
- Annual counts use Poisson trends with sandwich standard errors and reader-facing absolute rate changes.
- Process shares use bias-reduced binomial trends and reader-facing percentage-point changes.
- Five events is the single process-specific minimum.
- Supported results require p<0.05, alternative-sample direction agreement, classification-threshold agreement where applicable and leave-one-year-out direction stability.

## Deliverables

- Six PNG/SVG figure families with stable descriptive names.
- Chinese and English Markdown technical reports.
- One self-contained Chinese HTML reading edition with left navigation and click-to-enlarge figures.
- One point-only interactive JSON dataset and Tereon module.
- Independent machine-readable and Markdown validation receipts.

Exact result counts and checks are regenerated into `outputs/logs/analysis_summary.json` and `outputs/logs/validation_summary.json` on every complete run.
