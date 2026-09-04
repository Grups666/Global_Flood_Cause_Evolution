# Interactive visualization map

## Information architecture

The explorer follows the scientific analysis in two levels:

1. **All selected floods** — direct stormflow volume, daily flood peak and annual Q95-event frequency.
2. **By generating process** — process frequency, process share, rainfall concentration, antecedent wetness, direct stormflow volume and daily peak for each of six mechanisms.

Every mark is an observed catchment point. Point size increases with zoom. Supported results are drawn after other estimates so they remain visible.

## Evidence views

- **All estimates** retains the directional colour of every estimable trend; less-supported results use paler colour.
- **Supported focus** keeps unsupported estimates as neutral context and emphasizes the results passing all declared checks.

This toggle changes emphasis, not the underlying analysis or available catchments.

## Interaction

- Hover uses a cyan glow with no solid marker border. The opaque tooltip is fixed above page content and anchored to the actual pointer position.
- Selection retains the same cyan visual language.
- The inspector combines direction, magnitude and physical meaning in one result block, then shows fitted start and end levels, interval, p value, sample size and sensitivity checks.
- Percentage-point outcomes include the `pp` suffix; every “per decade” label explicitly means per 10 years.
- The top-bar **Research overview** opens the complete browser report. A persistent left navigation provides access to the question, data, methods, figures, results, limitations and references.
