# Interactive visualization map

## Information architecture

The compact **Object** selector has two choices:

1. **Flood-generating conditions** — rainfall concentration and antecedent SSI; a selected process also exposes its share of the Q95-event sample.
2. **Flood characteristics** — direct stormflow volume, daily flood peak and annual Q95-event frequency, for all selected floods or a selected process.

**Object** determines the metric family. **Antecedent wetness** (All, Dry,
Moderate, Wet) and **Rainfall forcing** (All, Intensity-led, Volume-led) independently
filter contributing events. All + All uses every selected Q95 flood; a single
restriction pools matching events across the unrestricted axis before fitting.
There is no separate event-sample control. Process share always has all selected
Q95 floods as its denominator, including for a one-axis filter.
The default is unclassified, continuous generating conditions. Changing the
event population never moves flood-response metrics into generating conditions.

Choosing a continuous quantity never requires choosing a qualitative category.
The quantitative map shows a fitted change, not proof of a causal mechanism.

Every mark is an observed catchment point. Point size increases with zoom. Supported results are drawn after other estimates so they remain visible.

## Evidence views

- **All estimates** retains the directional colour of every estimable trend; less-supported results use paler colour.
- **Supported focus** keeps unsupported estimates as neutral context and emphasizes the results passing all declared checks.

This toggle changes emphasis, not the underlying analysis or available catchments.

## Interaction

- Hover uses a cyan glow with no solid marker border. The opaque tooltip is fixed above page content and anchored to the actual pointer position.
- Selection retains the same cyan visual language.
- The inspector combines direction, magnitude and physical meaning in one result block, then shows fitted start and end levels, interval, p value, sample size and sensitivity checks.
- Full-sample condition panels plot annual event means and the exact Theil–Sen line; fitted endpoints are explicitly labelled by year and unit.
- Percentage-point outcomes include the `pp` suffix; every “per decade” label explicitly means per 10 years.
- The top-bar **Research overview** opens the complete browser report. A persistent left navigation provides access to the question, data, methods, figures, results, limitations and references.

## Annual trajectory chart contract

- Question: how did the selected-event physical condition vary within this catchment across its record?
- Family: temporal observations plus fitted line, in the map inspector's native SVG surface. At least 10 annual points; no interpolation of missing event-years.
- Source: `primary_extreme_events.parquet` → `catchment_conditions_annual.csv` and `catchment_conditions_trends.csv` → `conditions` in the interactive JSON. Observation grain is one catchment–metric–event-year; point detail retains valid event count.
- Units: concentration in percent, SSI in dimensionless index units; slope in percentage points or SSI units per 10 years. No inferred zero baseline, arbitrary early/late split, or extrapolation beyond the record.
- Marks: grey annual dots and a blue fitted line (two distinct mark types); measured-range y-axis with explicit ticks. No decorative logo.
- Footprint: responsive 340×210 viewBox in the catchment inspector. Validate numeric reconciliation and line endpoints, and inspect the published page at desktop and narrow widths.
