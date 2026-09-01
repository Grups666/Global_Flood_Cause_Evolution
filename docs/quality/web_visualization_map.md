# Interactive visualization map

The GitHub Pages site loads a custom Tereon module with two independently toggleable layers:

1. HydroBASINS level-5 polygons for multi-catchment estimates; and
2. individual-catchment points for secondary local diagnostics.

## Visualization contract

- **Question:** for the selected continuous flood-generating-condition metric, which HydroBASINS L5 units changed, in which direction, and which estimates clear every prespecified evidence gate?
- **Main visual takeaway:** strong evidence is local and directionally opposed. The current metric's five-gate L5 units must lead the visual hierarchy; eligible estimates and single-catchment trends provide context rather than competing with the regional result.
- **Form:** signed L5 choropleth with a five-gate evidence lens, an explicit current-metric evidence count, and a unit inspector. Individual catchments are available but off by default.
- **Encoding:** blue and orange encode negative and positive continuous slopes. Five-gate units also receive a crisp dark boundary and higher opacity, so evidence is not communicated by color alone. Context units use a neutral fill in the default focus view.
- **Evidence states:** the map distinguishes five-gate strong evidence from eligible regional context; opening a unit reveals all five gate decisions rather than compressing them into a generic significance label.

## Metrics

- rainfall concentration (`Pmax/Pvolume`);
- antecedent SSI at 1, 3, 7, and 30 days.

## Interaction

- Hover shows the region or catchment identifier, plain-language direction, slope, explicit unit, sample size, and either the five-gate count or record coverage in an opaque DOM tooltip above every canvas map layer.
- Normal basin boundaries are drawn first as thin black lines; selection is redrawn above them, and the cyan hover outline is drawn last so no neighboring boundary can cover it.
- L5 selection opens a continuous-time trajectory, confidence interval, complete-family q-value, sample sensitivity, rainfall-component decomposition, and a numbered five-gate audit.
- Catchment selection shows the Theil–Sen slope, time span, event count, Mann–Kendall statistic, and FDR status.
- The inspector translates each slope into its physical quantity and explicitly distinguishes percentage-point changes in within-event rainfall allocation from rainfall amount, discharge, and flood frequency.
- The top-bar overview is a research reading hub rather than a map layer. Its left navigation connects the scientific question, headline evidence, all six report figures, figure-level interpretation, analysis design, inference limits, and project materials.
- Every overview figure opens in a full-screen viewer. Project-material links expose the complete browser report, protocol, data dictionary, literature positioning, validation report, result tables, and code.

The module performs an immediate draw, a canvas resize after the first layout frame, a second-frame draw, and a delayed fallback draw. A `ResizeObserver` requests another render whenever the map container changes size. This prevents the host canvas from retaining only its background after module loading.

Only long-record catchments with at least 10 selected events spanning at least 20 years are included. Every mapped HydroBASINS region contains at least 20 contributing catchments; smaller regional units are absent rather than shown with a secondary sample grade. SSI inspectors show both the absolute slope and its percentage relative to the catchment-equal regional mean. Rainfall-component cards use raw linear slopes converted to the same relative scale, without logarithmic models.
