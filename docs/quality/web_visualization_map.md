# Interactive visualization map

The GitHub Pages site loads a custom Tereon module with two independently toggleable layers:

1. HydroBASINS level-5 polygons for multi-catchment estimates; and
2. eligible individual-catchment points for local Theil–Sen trends.

## Metrics

- rainfall concentration (`Pmax/Pvolume`);
- antecedent SSI at 1, 3, 7, and 30 days.

## Interaction

- Hover shows the basin or catchment identifier, plain-language direction, slope, and explicit unit in an opaque DOM tooltip above every canvas map layer.
- Normal basin boundaries are drawn first as thin black lines; selection is redrawn above them, and the cyan hover outline is drawn last so no neighboring boundary can cover it.
- Basin selection opens a continuous-time trajectory, confidence interval, complete-family q-value, sample sensitivity, rainfall-component decomposition, and evidence gates.
- Catchment selection shows the Theil–Sen slope, time span, event count, Mann–Kendall statistic, and FDR status.
- The inspector translates each slope into its physical quantity and explicitly distinguishes percentage-point changes in within-event rainfall allocation from rainfall amount, discharge, and flood frequency.
- The top-bar overview is a research reading hub rather than a map layer. Its left navigation connects the scientific question, headline evidence, all six report figures, figure-level interpretation, analysis design, inference limits, and project materials.
- Every overview figure opens in a full-screen viewer. Project-material links expose the complete browser report, protocol, data dictionary, literature positioning, validation report, result tables, and code.

Only long-record catchments with at least 10 selected events spanning at least 20 years are included. Every mapped HydroBASINS region contains at least 20 contributing catchments; smaller regional units are absent rather than shown with a secondary sample grade. SSI inspectors show both the absolute slope and its percentage relative to the catchment-equal regional mean. Rainfall-component cards use raw linear slopes converted to the same relative scale, without logarithmic models.
