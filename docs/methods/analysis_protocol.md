# Canonical Analysis Protocol

## Objective

Estimate whether the composition of hydrometeorological conditions associated
with large rainfall-driven floods changed during 1982–2019, globally and by
continental region.

## Population and exclusions

- Source catchments and events are reused read-only from `Event_Typology`.
- Retain catchments with long-term snow fraction `< 0.10`.
- Require the catchment to occur in both dormant and growing event catalogues
  and to have a matching daily file.
- Retain source event labels beginning with `Rain-`.
- Exclude events whose precipitation or response windows cannot be reconstructed
  exactly from daily records.
- The primary trend sample requires at least 30 annual observations, at least a
  30-year first-to-last span, and at least 80% annual coverage within that span.

These rules define a low-snow rainfall-driven population. They do not support
inference about snowmelt or rain-on-snow floods.

## Reconstructed event variables

For every retained event:

- `q_peak_mm_day`: maximum daily observed streamflow from response start through
  response end.
- `p_volume_daily_mm`: sum of daily water input over the inducing-event window.
- `p_max_daily_mm`: maximum daily water input over the inducing-event window.
- `intensity_fraction`: `p_max_daily_mm / p_volume_daily_mm`.
- `precipitation_cv`: population coefficient of variation of daily event rainfall.
- `ssi_1d`, `ssi_3d`, `ssi_7d`, `ssi_30d`: mean SSI over complete days before
  precipitation-event onset; the event day is excluded.

Continuous variables are retained in the derived Parquet file before any labels
are assigned.

## Extreme-event samples

### Primary: annual maximum

Within every catchment and calendar year, select the independent source event
with the largest reconstructed daily peak streamflow. The year is the year of
the reconstructed peak date.

### Sensitivity: POT/Q95

Within each catchment, calculate the 95th percentile of reconstructed event
peak streamflow over the full record and retain events at or above it. Event
independence is inherited from the source DMCA event delineation. Require at
least ten selected events per catchment.

The POT branch addresses sample-definition sensitivity; it is not described as
the settled interpretation of “annual top 5%.”

## Cause descriptors

### Rainfall organization

Primary categorical rule:

```text
Intensity-dominated if Pmax / Pvolume > 0.50
Volume-dominated otherwise
```

Sensitivity rules:

1. `Pmax/Pvolume > 0.50` and rainfall `CV > 1`;
2. `Pmax/Pvolume > 0.75`.

### Antecedent wetness

Apply the parent study's globally pooled SSI thresholds to each antecedent
window:

- Dry: `SSI <= 0.39`;
- Moderate: `0.39 < SSI <= 0.56`;
- Wet: `SSI > 0.56`.

The primary composite label crosses the 0.50 rainfall rule with 1-day wetness,
yielding six categories. The 3-, 7-, and 30-day windows are sensitivity analyses.

## Trend estimators

### Global and regional inference

Use a linear probability panel model with catchment fixed effects:

```text
cause_indicator_it = catchment_i + beta * decade_t + error_it
```

Uncertainty is clustered by catchment. `beta` is reported as percentage points
per decade. This is the primary estimator for global and regional changes
because it removes time-invariant between-catchment differences and avoids
letting changes in the annual gauge mix determine the trend.

Continuous intensity fraction and SSI are analyzed with the same within-
catchment estimator in index units per decade.

### Catchment-level inference

- Binary cause occurrence: logistic time trend, reported as odds ratio per
  decade.
- Continuous descriptors: Sen slope and tie-corrected asymptotic
  Mann–Kendall test.
- A binary outcome is fitted only with at least five occurrences and five
  non-occurrences.
- Benjamini–Hochberg false-discovery-rate adjustment is applied separately to
  each outcome family across catchments.

### Early/late robustness comparison

Compare 1982–2000 with 2001–2019 within each catchment first, requiring at least
five observations per period, then summarize catchment differences. This check
does not replace the time-trend model.

## Interpretation rules

- Report effect sizes and confidence intervals before p-values.
- Treat `p < 0.05` panel results as sample-level evidence, not causal attribution.
- Treat catchment maps as descriptive unless the point passes outcome-specific
  5% FDR.
- Do not call a rainfall-organization trend robust unless its direction is
  stable across defensible classification and event-sample choices.
- Explicitly flag regions with fewer than five catchments; Asia is not assigned
  a regional trend in the baseline run.

