# Global Flood Cause Evolution

This repository contains a reproducible event-based analysis of how the conditions producing large rainfall-driven floods changed during 1982–2019.

The primary sample is the catchment-specific upper 5% of reconstructed flood peaks (POT/Q95): **59,048 events in 2,624 long-record, low-snow catchments**. Two continuous process dimensions are analyzed:

- rainfall organization, measured as the share of event rainfall falling in the wettest day (`Pmax/Pvolume`); and
- antecedent catchment wetness, measured by Soil Saturation Index over 1, 3, 7, and 30 days before rainfall begins.

## Main result

The evidence is local and directionally opposed, not one spatially uniform global trend. Among 28 HydroBASINS level-5 units meeting the single ≥20-catchment rule, 62 basin–metric signals in 21 units satisfy the full evidence screen. Strong rainfall-concentration trends range from −2.54 to +2.92 percentage points of event rainfall per decade.

- [Technical report](reports/global_flood_cause_evolution.md)
- [English technical report](reports/global_flood_cause_evolution_en.md)
- [Self-contained browser report](reports/global_flood_cause_evolution.html)
- [Interactive GitHub Pages explorer](https://grups666.github.io/Global_Flood_Cause_Evolution/)
- [Analysis protocol](docs/methods/analysis_protocol.md)
- [Validation report](docs/quality/validation_report.md)

The explorer's top-bar **Research overview** is the unified reading entry point: a left-hand navigation connects the research question, all six analytical figures and their interpretation, methods, inference limits, and reproducibility materials. Only the HydroBASINS and eligible-catchment datasets appear in the map's Layers panel.

## Repository structure

- `config/analysis.yaml` — declared analysis parameters and project paths.
- `data/derived/` — reproducible project-derived Parquet data; ignored by Git.
- `data/reference/` — compact map references and official HydroBASINS archives.
- `docs/background/` — literature and scientific positioning.
- `docs/meeting_notes/` — source scope notes, kept distinct from analyst choices.
- `docs/methods/` — canonical protocol and data dictionary.
- `docs/quality/` — execution, figure, web, data, and validation records.
- `src/floodcause/` — reusable analysis modules.
- `outputs/` — generated tables, figures, and logs; ignored by Git.
- `reports/` — Markdown and self-contained HTML research reports.
- `public/` — Tereon module and GitHub Pages entry point.

## Reproduce

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage all --force
& $projectPython src/validate_outputs.py
```

The source project `D:/MyPaper/papers/Event_Typology` is read-only. Large source data are referenced in place and are not duplicated in this repository.
