# Interactive visualization map

The GitHub Pages site loads a custom Tereon module with two independently toggleable layers:

1. HydroBASINS level-5 polygons for multi-catchment estimates; and
2. eligible individual-catchment points for local Theil–Sen trends.

## Metrics

- rainfall concentration (`Pmax/Pvolume`);
- thresholded intensity-type share as an interpretive view;
- antecedent SSI at 1, 3, 7, and 30 days.

## Interaction

- Hover shows the basin or catchment identifier, plain-language direction, and slope.
- Hover and selection use a broad cyan glow with a thin cyan core line; normal basin boundaries are thin black lines.
- Basin selection opens a continuous-time trajectory, confidence interval, complete-family q-value, sample sensitivity, rainfall-component decomposition, and evidence gates.
- Catchment selection shows the Theil–Sen slope, time span, event count, Mann–Kendall statistic, and FDR status.
- The overview explains the scientific question, two process dimensions, sample counts, and ranked strong signals.

Only long-record catchments with at least 10 selected events spanning at least 20 years are included. Regions with 5–19 catchments are visibly lower-opacity and cannot receive the strongest evidence grade.
