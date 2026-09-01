# Reproducibility guide

## Environment

The project environment is located outside the repository:

```text
D:/Program Files/python-envs/Global_Flood_Cause_Evolution
```

Dependencies are declared in `pyproject.toml`; parameters and paths are declared in `config/analysis.yaml`.

## Complete execution

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage audit --force
& $projectPython src/run_pipeline.py --stage features --force
& $projectPython src/run_pipeline.py --stage analysis --force
& $projectPython src/run_pipeline.py --stage local --force
& $projectPython src/run_pipeline.py --stage figures --force
& $projectPython src/run_pipeline.py --stage reports --force
& $projectPython src/run_pipeline.py --stage html --force
& $projectPython src/run_pipeline.py --stage web --force
& $projectPython src/validate_outputs.py
```

`--stage all --force` runs the same stages in sequence.

## Data boundary

The pipeline reads but never modifies:

```text
D:/MyPaper/papers/Event_Typology/submission/data/Global Data
```

Derived Parquet files are written to `data/derived/`. Generated tables, figures, and receipts are written to `outputs/`. Both directories can be rebuilt from source.

## Reference geography

Map context uses Natural Earth 1:110m admin-0 boundaries. Hydrological-region analysis uses official HydroBASINS v1.c level 5 only. Reference archive checksums are recorded in `outputs/logs/hydrobasins_reference_sha256.csv`.

## Reading remotely

`reports/global_flood_cause_evolution.html` embeds its styles and six figures in one file. It can be opened directly through the remote Codex workspace without copying an asset folder to the client computer.
