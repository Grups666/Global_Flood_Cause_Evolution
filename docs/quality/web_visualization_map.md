# Interactive web visualization contract

## Purpose

The GitHub Pages artifact is an exploratory companion to the technical report.
It is implemented as a Tereon module and keeps the two evidence scales visibly
separate.

## Layer contract

| Layer | Visual mark | Analytical field | Question answered | Interaction |
|---|---|---|---|---|
| HydroBASINS L5 regions | Filled polygons with solid or dashed outline | Catchment fixed-effect slope, percentage points per decade | Which sampled hydrological subregions show coherent changes? | Click for slope, confidence interval, FDR, alternative sample, paired-period and stability gates |
| Individual catchments | Semi-transparent points | Fitted logistic probability change from 2000 to 2010, percentage points per decade | What is the fine-grained spatial context inside and outside eligible regions? | Hover for identifier and change; click for record length, odds ratio, q value, FDR status and HydroBASINS assignment |

Both layers support `intensity_050` and `wet_1d`. A common zero-centered blue–sand–orange
palette is used, with separate scales appropriate to each estimator: −7 to +7
percentage points per decade for HydroBASINS estimates and −20 to +20 for
catchment probability changes. Values outside the displayed range are clipped.
The basin outline, not the fill magnitude, encodes whether the full
high-confidence evidence gate is met.

## Interpretation boundary

The regional layer is the primary inferential result. Catchment points are
descriptive context because very few single-catchment trends survive multiple
testing. The probability change contrasts fitted probabilities in 2000 and
2010. The model intercept is recovered from the saved log-odds slope, positive
count and the catchment's actual observation years, exactly satisfying the
logistic intercept score equation. This replaces the binary-series Sen slope,
which is exactly zero for nearly all eligible catchments and is therefore not a
useful color encoding. The interface repeats this distinction in the overview,
legend and feature inspectors.

Catchments without a fitted trend for the active indicator are excluded from
rendering and hit testing. Consequently the map shows 2,516 catchments for
`intensity_050` and 837 for `wet_1d`, rather than displaying insufficient records
as uninformative gray points.

## Data and deployment

- Web data are rebuilt by `src/build_web_data.py` from auditable output tables
  and official HydroBASINS v1.c geometry.
- Only 28 eligible level-5 polygons are exported and geometries are simplified
  with topology preserved. The 2,839 primary catchments are exported as points.
- Source parquet files and HydroBASINS archives are not copied into the website.
- `.github/workflows/pages.yml` publishes `public/` after changes reach `main`.
