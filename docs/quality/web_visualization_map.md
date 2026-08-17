# Interactive web visualization contract

## Purpose

The GitHub Pages artifact is an exploratory companion to the technical report.
It is implemented as a Tereon module and keeps the two evidence scales visibly
separate.

## Layer contract

| Layer | Visual mark | Analytical field | Question answered | Interaction |
|---|---|---|---|---|
| HydroBASINS L5 regions | Filled polygons with thin or emphasized solid boundary | Catchment fixed-effect slope, percentage points per decade | Which sampled hydrological subregions show coherent changes? | Hover for fluorescent highlight, region, trend, and sample tier; click for slope, confidence interval, FDR, alternative sample, paired-period and stability gates |
| Individual catchments | Semi-transparent points | Fitted logistic probability change from 2000 to 2010, percentage points per decade | What is the fine-grained spatial context inside and outside eligible regions? | Hover for identifier and change; click for record length, odds ratio, q value, FDR status and HydroBASINS assignment |

Both layers support `intensity_050` and `wet_1d`. A common zero-centered blue–sand–orange
palette is used, with separate scales appropriate to each estimator: −7 to +7
percentage points per decade for HydroBASINS estimates and −20 to +20 for
catchment probability changes. Values outside the displayed range are clipped.
Every included basin uses a quiet, thin, dark solid boundary. A thicker dark
boundary identifies a high-confidence signal. Sample support is stated directly
in the hover label and inspector rather than encoded with dashed or dotted
lines. Hover is intentionally omitted from the legend because it is an
interaction state rather than an analytical encoding. A thin cyan keyline and
soft luminous halo emphasize a region edge without a heavy solid under-stroke;
catchments use a separate outer halo that preserves the point fill.

Selected regions use a 1.25 px deep-cyan edge with a restrained glow rather
than a heavy black outline. Basin paths use round joins and caps with a limited
miter length; this prevents complex coastlines and small polygon fragments from
producing dark spikes at high zoom. High-confidence boundaries remain distinct
at 1.2 px, compared with 0.7 px for other included regions.

Interface typography keeps secondary labels at 11 px or larger. The module also
raises the host layer list, legend card, toolbar, hover label, and inspector
content sizes so that supporting text remains legible without flattening the
hierarchy between labels, values, and headings.

## Interpretation boundary

The regional layer is the primary inferential result. A level-5 unit enters the
formal family with at least 5 catchments and 300 outcome observations. The
300-observation gate makes the smallest realized unit nine catchments. Units
with fewer than 20 catchments remain formally included but carry a persistent
limited-sample label in the hover text, legend, and inspector. Catchment points are
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
- Only 72 eligible level-5 polygons are exported and geometries are simplified
  with topology preserved. The 2,839 primary catchments are exported as points.
- Source parquet files and HydroBASINS archives are not copied into the website.
- `.github/workflows/pages.yml` publishes `public/` after changes reach `main`.
