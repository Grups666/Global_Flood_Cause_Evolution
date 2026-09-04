# Global Flood Cause Evolution

This repository contains a reproducible, catchment-first study of how the generating processes and hydrological response of large rainfall-driven floods changed during 1982–2019.

The primary sample selects each catchment's upper 5% of reconstructed events by **event direct stormflow volume**. It contains **58,991 events in 2,637 long-record catchments**. Each event is then assigned to one of six processes formed by:

- antecedent state: dry, moderate or wet; and
- rainfall temporal organization: intensity or volume.

The analysis estimates, for each observed catchment, changes in flood volume, daily flood peak, large-flood frequency, process frequency, process share, rainfall concentration and antecedent wetness. The web map contains observed catchment points only; no trend is assigned to ungauged areas.

- [Interactive GitHub Pages explorer](https://grups666.github.io/Global_Flood_Cause_Evolution/)
- [Chinese technical report](reports/global_flood_cause_evolution.md)
- [English technical report](reports/global_flood_cause_evolution_en.md)
- [Self-contained browser report](reports/global_flood_cause_evolution.html)
- [Analysis protocol](docs/methods/analysis_protocol.md)
- [Literature review](docs/background/literature_review.md)
- [Validation report](docs/quality/validation_report.md)

The explorer has two reading levels: **All selected floods** first shows what happened to the upper-tail floods themselves; **By generating process** then separates occurrence, composition, conditions and flood response for the six mechanisms. `All estimates` retains pale directional context, while `Supported focus` emphasizes results that pass the declared significance and sensitivity checks.

## Repository structure

- `config/analysis.yaml` — declared parameters and project paths.
- `data/derived/` — reproducible derived Parquet data; ignored by Git.
- `docs/` — literature, meeting scope, methods and quality records.
- `src/floodcause/` — sample construction, classification, statistics and figures.
- `outputs/` — generated tables, figures and logs; ignored by Git.
- `reports/` — bilingual Markdown and self-contained HTML reports.
- `public/` — interactive explorer and GitHub Pages entry point.

## Reproduce

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage all --force
& $projectPython src/validate_outputs.py
```

The related source project `D:/MyPaper/papers/Event_Typology` is reused read-only; its multi-gigabyte source data are not duplicated here.
