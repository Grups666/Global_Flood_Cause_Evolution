# Full Experiment Execution Manifest

**Execution date:** 2026-08-16  
**Execution mode:** forced raw-to-output rebuild (`--stage all --force`)  
**Exit status:** success

**Local-analysis extension:** 2026-08-17; official HydroBASINS levels 3–5,
figures, self-contained HTML, and validation rebuilt successfully.

## What was actually executed

This project does not use simulated rows or a demonstration subset. The forced
run read the source event catalogues, catchment metadata, boundary data, and the
daily observation CSV for every eligible catchment from the read-only
`Event_Typology` project.

The feature stage iterated over 4,150 catchments and reconstructed 1,407,121
rain-event records from daily `water_input_mm`, `streamflow_mm`, and
`soil_saturation_index` series. For every event it calculated the response-window
peak flow, event precipitation total and maximum, temporal precipitation CV,
and 1-, 3-, 7-, and 30-day antecedent SSI.

## Forced-run receipt

| Stage | Result |
|---|---|
| Source audit | 4,838 daily files; 3,770,893,799 bytes; 1,671,449 source events |
| Feature reconstruction | 1,407,121 events from 4,150 catchments; 153.93 seconds |
| Annual-maximum analysis | 100,788 events from 2,839 catchments |
| POT/Q95 sensitivity | 68,135 events from 3,206 catchments |
| Catchment binary trends | 14,087 fitted catchment–outcome rows |
| Catchment continuous trends | 14,195 fitted catchment–variable rows |
| Statistical analysis | 75.46 seconds |
| Local HydroBASINS analysis | 2,835 matched catchments; 28 eligible level-5 units; 56 primary tests; 17 high-confidence signals; 22.34 seconds |
| Figure generation | Nine PNG/SVG pairs plus synchronized report-local PNG assets |
| Browser report | Focused 2,964,009-byte HTML with four Base64-embedded core figures and click-to-enlarge lightbox; all nine canonical figure pairs remain available |
| Final validation | 20 of 20 checks passed |

The exact machine receipts are stored in:

- [`feature_build.json`](../../outputs/logs/feature_build.json)
- [`analysis_summary.json`](../../outputs/logs/analysis_summary.json)
- [`local_analysis_summary.json`](../../outputs/logs/local_analysis_summary.json)
- [`validation.json`](../../outputs/logs/validation.json)

## Executed command

```powershell
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/run_pipeline.py --stage all --force
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/validate_outputs.py
```

The 2026-08-17 extension reused the validated derived event tables and ran:

```powershell
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/run_pipeline.py --stage local
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/run_pipeline.py --stage figures
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/run_pipeline.py --stage html
& 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe' `
  src/validate_outputs.py
```

## Code-to-output trace

| Code | Responsibility | Principal output |
|---|---|---|
| `src/floodcause/audit.py` | Source inventory and integrity checks | `outputs/tables/source_*.csv` |
| `src/floodcause/features.py` | Raw daily event reconstruction | `data/derived/event_features.parquet` |
| `src/floodcause/analysis.py` | Extreme samples, classifications, panel and period estimates | derived samples and result CSVs |
| `src/floodcause/statistics.py` | Logistic, Sen, Mann–Kendall, and FDR calculations | catchment trend CSVs |
| `src/floodcause/local_analysis.py` | HydroBASINS assignment, local panel trends, paired-period and stability checks | local basin trend and robustness CSVs |
| `src/floodcause/plots.py` | Publication figures and report asset synchronization | `outputs/figures/`, `reports/assets/` |
| `src/validate_outputs.py` | Independent output checks | `outputs/logs/validation.json` |

## Reproducibility boundary

The source directory is only read. All project-owned derived data and outputs
are written beneath this project. Rerunning with `--force` replaces only those
regenerable derived products; it does not modify the source project.
