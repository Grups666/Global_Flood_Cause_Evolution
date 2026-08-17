# Source Code

## Entry point

`run_pipeline.py` provides five explicit stages: `audit`, `features`, `analysis`,
`figures`, and `html`.

## Package modules

- `config.py`: configuration loading and output paths.
- `io.py`: canonical source loading, geography, and FDR utilities.
- `audit.py`: source inventory, missingness, integrity, and identifier checks.
- `features.py`: daily reconstruction of peak flow, rainfall organization, and antecedent SSI.
- `statistics.py`: logistic trends, Sen slopes, tie-corrected Mann–Kendall, and FDR.
- `analysis.py`: extreme-event samples, labels, panel trends, paired comparisons, and tables.
- `plots.py`: publication-ready PNG/SVG figures.
- `validate_outputs.py`: independent sample, trend, FDR, link, encoding, and
  figure checks; writes `outputs/logs/validation.json`.
- `build_html_report.py`: self-contained, responsive HTML report with all
  figures embedded as data URIs.

The code is intentionally script- and table-oriented rather than notebook-only,
so every manuscript number can be traced to a saved result table.

Run the validation suite after the four pipeline stages:

```powershell
python src/validate_outputs.py
```
