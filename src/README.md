# Source code

`run_pipeline.py` exposes the stages `audit`, `features`, `analysis`, `local`, `figures`, `reports`, `html`, `web`, and `all`.

## Package modules

- `config.py` — configuration and output paths.
- `io.py` — canonical source loading and geography helpers.
- `audit.py` — source inventory, missingness, and integrity checks.
- `features.py` — daily flood peak, rainfall organization, and antecedent SSI reconstruction.
- `analysis.py` — record screening, POT and sensitivity samples, continuous trends, and trajectories.
- `statistics.py` — Theil–Sen, tie-corrected Mann–Kendall, and FDR utilities.
- `local_analysis.py` — HydroBASINS assignment, multi-catchment trends, evidence gates, and mechanism summaries.
- `plots.py` — the six publication figures in PNG and SVG.
- `build_reports.py` — bilingual Markdown technical reports generated from result tables.
- `build_html_report.py` — self-contained clickable HTML report.
- `build_web_data.py` — compact interactive-map JSON.
- `validate_outputs.py` — independent sample, FDR, evidence, figure, report, and web checks.

The workflow is script- and table-oriented so every reported number can be traced to a saved result table.
