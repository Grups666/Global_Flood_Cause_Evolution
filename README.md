# Global Flood Cause Evolution

This repository contains a reproducible, catchment-first analysis of long-term changes in the conditions accompanying large rainfall-driven floods during 1982–2019.

The primary POT/Q95 sample contains **59,048 events in 2,624 long-record, low-snow catchments**. It tracks two continuous process dimensions:

- rainfall concentration: the share of event rainfall falling in the wettest day (`Pmax/Pvolume`); and
- antecedent wetness: Soil Saturation Index over 1, 3, 7, and 30 days before rainfall begins.

## Main result

Direct trends are estimable for at least one main metric in **2,435 catchments**. Across **12,163 catchment–metric estimates**, **378 robust individual trends** have p<0.05, retain their direction under POT/Q90, POT/Q97.5, and annual-maximum samples, and remain stable when event years are removed one at a time; SSI additionally requires agreement across all four antecedent windows. Individual catchments are primary research results, not inputs screened for later regional analysis.

HydroBASINS L5 is a second-stage expanded regional lens. With the default **50% observed polygon-area support**, **10 strong regional signals in 6 L5 units** pass complete-family BH-FDR plus event-sample, SSI-window, and leave-one-out checks. The web explorer allows 10%, 20%, 30%, 40%, and 50% area-support thresholds; this control changes regional interpretation without removing individual catchment results.

- [Interactive GitHub Pages explorer](https://grups666.github.io/Global_Flood_Cause_Evolution/)
- [Chinese technical report](reports/global_flood_cause_evolution.md)
- [English technical report](reports/global_flood_cause_evolution_en.md)
- [Self-contained browser report](reports/global_flood_cause_evolution.html)
- [Analysis protocol](docs/methods/analysis_protocol.md)
- [Data dictionary](docs/methods/data_dictionary.md)
- [Validation report](docs/quality/validation_report.md)

The explorer's top-bar **Research overview** is the unified reading entry point. Its left navigation links the research question, headline evidence, all six figures, methods, inference boundaries, and reproducibility materials. The map exposes independently toggleable single-catchment and area-supported L5 layers.

## Repository structure

- `config/analysis.yaml` — declared parameters and project paths.
- `data/derived/` — reproducible derived Parquet data; ignored by Git.
- `data/reference/` — compact map references and HydroBASINS archives.
- `docs/` — literature, scope, methods, and quality records.
- `src/floodcause/` — analysis modules.
- `outputs/` — generated tables, figures, and logs; ignored by Git.
- `reports/` — bilingual Markdown and self-contained HTML reports.
- `public/` — Tereon module and GitHub Pages entry point.

## Reproduce

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage all --force
& $projectPython src/validate_outputs.py
```

The related source project `D:/MyPaper/papers/Event_Typology` is reused read-only; multi-gigabyte source data are not duplicated here.
