# Global Flood Cause Evolution

This repository contains a reproducible global analysis of whether the
hydrometeorological conditions associated with large rainfall-driven floods
changed during 1982–2019.

The completed analysis uses 1,407,121 rain-event records reconstructed
from daily precipitation, streamflow, and Soil Saturation Index data. The
primary trend sample contains 100,788 annual maximum events from 2,839
low-snow catchments. A 95th-percentile peaks-over-threshold sample is retained as
a sensitivity branch.

## Main result

Global averages are weak because localized HydroBASINS units change in opposite
directions. Seventeen level-5 basin signals remain after primary-family FDR,
POT/Q95, paired-period, definition-stability, and leave-one-catchment-out checks;
their magnitudes reach roughly 2–11 percentage points per decade. The formal
level-5 family contains 72 units with at least 5 catchments and 300 observations;
44 units with fewer than 20 catchments are explicitly marked as limited-sample
estimates. Almost no
individual-catchment trends survive false-discovery-rate correction, so the
supported evidence scale is a group of neighboring catchments rather than an
isolated gauge.

Read the full technical report:
[reports/global_flood_cause_evolution.md](reports/global_flood_cause_evolution.md).
For remote reading, use the self-contained browser version:
[reports/global_flood_cause_evolution.html](reports/global_flood_cause_evolution.html).

The Tereon-based interactive explorer is published through GitHub Pages at
[grups666.github.io/Global_Flood_Cause_Evolution](https://grups666.github.io/Global_Flood_Cause_Evolution/).
It provides separately toggleable HydroBASINS level-5 polygons and individual
catchment points, with metric switching and click-through evidence details.

## Repository map

- `config/analysis.yaml`: frozen analysis parameters and paths.
- `data/`: compact project-owned reference and derived assets; source data remain read-only in `Event_Typology`.
- `docs/background/`: literature synthesis and scientific framing.
- `docs/methods/`: canonical protocol and data dictionary.
- `docs/decisions/`: dated records of consequential method decisions.
- `docs/quality/`: data and analysis validation records.
- `docs/meeting_notes/`: dated source notes from project meetings.
- `docs/archive/`: superseded design documents organized by date.
- `src/floodcause/`: reusable pipeline modules.
- `outputs/tables/`: auditable analysis tables.
- `outputs/figures/`: publication-ready PNG and SVG figures.
- `outputs/logs/`: machine-readable execution receipts.
- `reports/`: reader-facing research report.
- `public/`: Tereon module, compact web dataset, and GitHub Pages entry point.

## Reproduce

The Python environment used for this run is located outside the repository at:

```text
D:/Program Files/python-envs/Global_Flood_Cause_Evolution
```

From the project root:

```powershell
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage audit
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage features
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage analysis
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage local
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage figures
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage html
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/run_pipeline.py --stage web
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' src/validate_outputs.py
```

The source project `D:/MyPaper/papers/Event_Typology` is treated as read-only.
