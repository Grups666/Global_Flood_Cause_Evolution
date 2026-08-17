# Interactive web visualization contract

## Purpose

The GitHub Pages artifact is an exploratory companion to the technical report.
It is implemented as a Tereon module and keeps the two evidence scales visibly
separate.

## Layer contract

| Layer | Visual mark | Analytical field | Question answered | Interaction |
|---|---|---|---|---|
| HydroBASINS L5 regions | Filled polygons with solid or dashed outline | Catchment fixed-effect slope, percentage points per decade | Which sampled hydrological subregions show coherent changes? | Click for slope, confidence interval, FDR, alternative sample, paired-period and stability gates |
| Individual catchments | Semi-transparent points | Catchment Sen slope, percentage points per decade | What is the fine-grained spatial context inside and outside eligible regions? | Click for record length, odds ratio, q value, FDR status and HydroBASINS assignment |

Both layers support `intensity_050` and `wet_1d`. A common zero-centered blue–sand–orange
scale is used from −7 to +7 percentage points per decade. The basin outline, not
the fill magnitude, encodes whether the full high-confidence evidence gate is met.

## Interpretation boundary

The regional layer is the primary inferential result. Catchment points are
descriptive context because very few single-catchment trends survive multiple
testing. The interface repeats this distinction in the overview, legend and
feature inspectors.

## Data and deployment

- Web data are rebuilt by `src/build_web_data.py` from auditable output tables
  and official HydroBASINS v1.c geometry.
- Only 28 eligible level-5 polygons are exported and geometries are simplified
  with topology preserved. The 2,839 primary catchments are exported as points.
- Source parquet files and HydroBASINS archives are not copied into the website.
- `.github/workflows/pages.yml` publishes `public/` after changes reach `main`.
