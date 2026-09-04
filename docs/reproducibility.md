# Reproducibility guide

## Environment

The project environment is outside the repository:

```text
D:/Program Files/python-envs/Global_Flood_Cause_Evolution
```

Dependencies are declared in `pyproject.toml`; parameters and source paths are declared in `config/analysis.yaml`.

## Complete execution

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage audit --force
& $projectPython src/run_pipeline.py --stage features --force
& $projectPython src/run_pipeline.py --stage analysis --force
& $projectPython src/run_pipeline.py --stage figures --force
& $projectPython src/run_pipeline.py --stage reports --force
& $projectPython src/run_pipeline.py --stage html --force
& $projectPython src/run_pipeline.py --stage web --force
& $projectPython src/validate_outputs.py
```

`--stage all --force` runs the same stages in order.

## Data boundary

The pipeline reads but never modifies:

```text
D:/MyPaper/papers/Event_Typology/submission/data/Global Data
```

Derived Parquet files are written to `data/derived/`. Generated tables, figures and machine-readable receipts are written to `outputs/`. Both are reproducible from the declared source.

## Remote reading

`reports/global_flood_cause_evolution.html` embeds its styles and six figures in one file. The GitHub Pages explorer uses a compact point-only JSON payload, and the top-bar **Research overview** opens the same complete report with left-side navigation.
