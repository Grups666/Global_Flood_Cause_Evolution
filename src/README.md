# Source code

`run_pipeline.py` exposes `audit`, `features`, `analysis`, `conditions`, `figures`, `reports`, `html`, `web` and `all` stages.

- `floodcause/config.py` — configuration and output paths.
- `floodcause/io.py` — canonical source loading and geography labels.
- `floodcause/audit.py` — source inventory, missingness and integrity checks.
- `floodcause/features.py` — daily rainfall, streamflow and antecedent-state reconstruction.
- `floodcause/analysis.py` — record screening, Q95/Q90/Q97.5/annual-maximum samples, six-process classification, trends and sensitivity checks.
- `floodcause/conditions.py` — full-sample continuous concentration/SSI trends, annual observations and explicit metric eligibility audit.
- `floodcause/statistics.py` — Theil–Sen, tie-corrected Mann–Kendall and bias-reduced binomial trends.
- `floodcause/plots.py` — six current publication figures in PNG and SVG.
- `build_reports.py` — bilingual Markdown reports generated from result tables.
- `build_html_report.py` — self-contained, navigable and zoomable HTML report.
- `build_web_data.py` — compact point-only interactive-map JSON.
- `validate_outputs.py` — independent sample, classification, evidence, report and web checks.

Every reported number is generated from saved result tables; exploratory notebooks are not required to reproduce the experiment.
