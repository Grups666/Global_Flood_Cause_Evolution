# Interactive visualization contract

The GitHub Pages site loads a custom Tereon module with two independent analytical layers:

1. **Individual catchment trends** — the first-stage scientific result;
2. **Area-supported HydroBASINS L5 patterns** — the second-stage regional lens.

## Visual hierarchy

- The default map keeps all estimable catchment polygons available. Stable candidates receive stronger color and outline; other catchments remain light context.
- L5 fill shows the selected metric's shared regional slope. Cyan outlines identify signals passing complete regional-family Benjamini–Hochberg false discovery rate (BH-FDR), alternative-event, SSI-window, and leave-one-out checks.
- Normal boundaries are thin dark lines. Hover/selection uses a wider cyan glow with transparent interior and is repainted above every neighboring boundary.
- Opaque hover cards are placed above canvas layers and report identifier, physical direction, slope, unit, support, and evidence state.

## Dynamic area support

The toolbar offers 10%, 20%, 30%, 40%, and 50% observed polygon-area thresholds. The threshold is

```text
area(L5 intersect union of assigned eligible catchment polygons) / area(L5)
```

and only controls whether an L5 interpretation is shown. Individual catchment estimates never disappear when the regional threshold changes. The default is 10% to preserve broad exploration; higher choices provide a direct spatial-support sensitivity analysis.

## Inspectors

- A catchment inspector reports Theil–Sen slope, 95% CI, Mann–Kendall p, metric-wide q, selected event years, polygon area, L5 membership, five stability checks, and alternative-sample slopes.
- An L5 inspector reports observed area coverage, observed area, contributing catchments, event and catchment-year counts, estimator type, pooled slope and CI, complete-family q, and all five regional evidence gates.
- One-catchment L5 representations are explicitly labelled; their area support does not imply multi-catchment corroboration.
- Rainfall concentration is explained as percentage-point change in the wettest-day share of event rainfall. SSI is explained in normalized index units. Neither is described as flood frequency, peak, or volume.

## Reading hub

The top-bar **Research overview** is not duplicated in the Layers panel. Its left navigation integrates the question, headline result, six figures with interpretation, methods, evidence boundaries, reports, protocol, data dictionary, literature, validation, result tables, and code. Every figure opens in a full-screen viewer.

The module requests an immediate render, first-frame resize, second-frame render, delayed fallback render, and `ResizeObserver` updates so the host canvas does not remain blank after loading.
