# Reproducibility Guide

## Environment

The run used Python 3.14 with project dependencies installed at:

```text
D:/Program Files/python-envs/Global_Flood_Cause_Evolution
```

Declared dependencies are recorded in `pyproject.toml`. Analysis parameters and
all project paths are recorded in `config/analysis.yaml`.

## Execution order

```powershell
$python = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $python src/run_pipeline.py --stage audit
& $python src/run_pipeline.py --stage features
& $python src/run_pipeline.py --stage analysis
& $python src/run_pipeline.py --stage local
& $python src/run_pipeline.py --stage figures
& $python src/run_pipeline.py --stage html
& $python src/validate_outputs.py
```

Use `--force` to rebuild a stage whose reusable output already exists.

For remote browser reading across the Lenovo-to-Tsinghua SSH boundary, serve
the self-contained HTML over the Tailscale interface:

```powershell
$tailscaleIp = tailscale ip -4
& $python -m http.server 8787 --bind $tailscaleIp --directory reports
```

## Source-data boundary

The pipeline reads but never modifies:

```text
D:/MyPaper/papers/Event_Typology/submission/data/Global Data
```

Large source datasets are not copied into this repository. Project-owned
derived Parquet files are written to `data/derived/` and can be regenerated.

## Reference geography

The map background is Natural Earth 1:110m admin-0 countries:

```text
https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip
```

The downloaded archive is stored under `data/reference/` with its source named
explicitly; analytical catchment locations come from the source metadata.

Local spatial analysis additionally uses the official HydroBASINS v1.c standard
polygon archives for levels 3, 4, and 5:

```text
https://www.hydrosheds.org/products/hydrobasins
```

The unmodified ZIP files and a source README are stored under
`data/reference/hydrobasins/`; exact SHA-256 values are generated in
`outputs/logs/hydrobasins_reference_sha256.csv`.

## Execution receipts

JSON receipts in `outputs/logs/` record source audit, feature construction,
analysis counts, and final validation. CSV tables under `outputs/tables/`
contain the result-level audit trail. A successful final validation exits with
status zero and records all checks in `outputs/logs/validation.json`.
