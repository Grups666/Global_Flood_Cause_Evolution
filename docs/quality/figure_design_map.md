# Figure design map

This document records the purpose and presentation rules of the nine canonical
figures. It is the single reference for future visual revisions; figure files
are not versioned through suffixes such as `v1`, `v2`, or `final`.

| Figure | Analytical question | Visual form | Main fields | Intended takeaway | Presentation rule |
|---|---|---|---|---|---|
| `figure_01_sample_coverage` | Where is the primary gauge sample, and how is it distributed across regions? | Catchment map + horizontal bars | longitude, latitude, eligibility, continent | The sample is concentrated in Europe and the Americas; Asia has only four eligible catchments. | Keep the map and regional ranking in separate columns; labels must remain inside the ranking panel. |
| `figure_02_global_composition` | Did the global composition of annual maxima change over time? | Annual series + centered five-year mean | peak year, intensity share, one-day wet share | Intensity-dominated events rise while wet-antecedent events decline in the primary sample. | Use thin observed lines, one bold smoother, and a quiet direct estimate box. |
| `figure_03_regional_panel_trends` | Do within-catchment trends differ by region? | Two confidence-interval dot plots | fixed-effect slope, 95% CI, region | Regional directions differ; the global result is an aggregation of heterogeneous signals. | Highlight the global row in neutral ink and retain color only for regional estimates. |
| `figure_04_catchment_trend_maps` | Where are catchment-level changes located? | Two diverging point maps | Sen slope, FDR significance, coordinates | Spatial changes are descriptive; very few individual trends survive multiple-testing correction. | Use symmetric color limits and outlined markers only for FDR-significant catchments. |
| `figure_05_sensitivity_matrix` | Are global conclusions robust to alternative event and classification rules? | Annotated heat map | sample, outcome, slope, p-value | Wetness results are more stable than intensity results across definitions. | Keep labels horizontal and concise; print signed slopes directly in cells. |
| `figure_06_regional_cause_composition` | How do the six causal-condition classes vary by region? | 100% stacked horizontal bars | region, primary cause, proportion | Regions have distinct background compositions even under one global classification rule. | Use warm colors for intensity classes and cool colors for volume classes; keep the legend below the plot. |
| `figure_07_analysis_flow` | How do raw events become the primary and sensitivity samples? | Four-node flow diagram | event and catchment counts by stage | Reconstruction is shared, after which annual maxima and POT/Q95 form separate analysis branches. | Use one reading direction, short labels, and no decorative connectors. |
| `figure_08_local_hydrobasin_trend_maps` | Where do coherent local trends appear after aggregating nearby catchments into hydrological units? | Two diverging HydroBASINS maps | level-5 basin slope, confidence gate, location | Several small hydrological regions change by multiple percentage points per decade even though global averages are weak. | Use one common diverging scale per outcome; outline only high-confidence local signals, center the map panels on a tall canvas, and reserve a separate right column for the shared color scale. |
| `figure_09_local_hydrobasin_ranked_trends` | Which high-confidence local changes are largest, and how uncertain are they? | Two ranked confidence-interval plots | fixed-effect slope, cluster-robust 95% CI, basin label | The strongest reproducible local signals range from roughly two to seven percentage points per decade and occur in opposing directions. | Rank by signed magnitude within outcome; label with country, median coordinates, and stable basin code; do not show unsupported point estimates. |

## Shared visual system

- Typography: one sans-serif family, sentence-case titles, compact explanatory subtitles.
- Palette: restrained blue/orange analytical contrast, neutral grey geography and grid lines,
  and pale fills only for hierarchy.
- Labels: direct values where they reduce lookup; legends only when multiple encoded classes
  must be compared.
- Layout: fixed header and footer bands, generous panel separation, and no text outside its
  assigned subplot.
- Output: every canonical figure is generated as both PNG and SVG from
  `src/floodcause/plots.py`. The focused main report uses figures 01, 07, 08,
  and 09; the remaining synchronized assets are retained for supporting analysis
  and supplementary-material use.
