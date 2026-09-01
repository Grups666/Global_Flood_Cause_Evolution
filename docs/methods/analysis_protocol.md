# Analysis protocol

## Scientific question

The analysis asks whether the hydrometeorological conditions associated with
extreme rainfall-driven floods changed through time, where those changes occur,
and whether the direction is toward short concentrated rainfall, long
volume-dominated rainfall, wetter antecedent conditions, or drier antecedent
conditions.

The meeting record establishes this question, the rainfall-organization and
antecedent-wetness dimensions, and the need for a global change-direction map.
It does not prescribe a year split, statistical estimator, HydroBASINS level,
or numerical classification threshold.

## Population

- Study period: the verified common record, 1982–2019.
- Catchments: long-term snow fraction below 0.10, both seasonal event
  catalogues present, a matching daily record, at least 30 observed event years,
  a first-to-last span of at least 30 years, and at least 80% annual coverage.
- Events: reconstructed rainfall-runoff events with complete precipitation and
  response windows and a valid observed daily flood peak.
- Inference: the available long-record gauge sample, not an area-weighted global
  land estimate and not snowmelt or rain-on-snow floods.

## Extreme-event selection

Event selection is kept separate from mechanism description.

### Primary sample: catchment-specific POT/Q95

For each eligible catchment, calculate the 95th percentile of reconstructed
event peak flow over its full record and retain events at or above the
threshold. Require at least 10 selected events and a selected-event span of at
least 20 years. Source events are independently delineated rainfall-runoff
windows; overlap and peak-spacing diagnostics are reported explicitly.

This is the most direct operational interpretation of the meeting phrase
“top 5%”. The phrase remains methodologically ambiguous because the meeting did
not specify the ranked variable or percentile population; the report therefore
describes the operational definition rather than attributing it to the
supervisor.

### Sensitivity samples

- catchment-specific POT/Q90;
- catchment-specific POT/Q97.5;
- POT/Q95 with a 10-day peak-separation declustering rule;
- one annual maximum flood per catchment-year.

These branches test whether mapped directions depend on event extremeness,
declustering, or using one event per year.

## Mechanism descriptors

### Rainfall organization

Primary continuous metric:

```text
rainfall concentration = maximum daily event rainfall / total event rainfall
```

An increase means that a larger share of event rainfall is concentrated in one
day, consistent with movement toward short/intensity-dominated rainfall. A
decrease means movement toward longer, volume-dominated rainfall. The metric is
a daily-resolution organization descriptor, not a measurement of sub-daily
rainfall intensity.

No binary intensity-dominated label is constructed. Thresholding would discard
within-category movement and was not specified by the meeting; the continuous
ratio is the sole inferential rainfall-organization target.

### Antecedent wetness

Primary continuous metrics are mean Soil Saturation Index values over the 1,
3, 7, and 30 complete days before event rainfall begins. All four windows are
reported. A wetness signal is called window-consistent only when the estimated
direction is the same at all four windows.

### Physical decomposition

For every extreme event, retain:

- maximum daily rainfall;
- total event rainfall;
- precipitation duration;
- flood peak and event runoff volume;
- antecedent SSI at all four windows.

Maximum daily rainfall, event rainfall, and duration are fitted directly in
their raw physical units. For comparison, each raw linear slope is divided by
the HydroBASINS unit's catchment-equal mean and reported as percent per decade.
No logarithmic model is used. These variables explain why the
rainfall-concentration ratio moved; they are not extra definitions of cause.

## Continuous-time trend estimation

No arbitrary early/late period split is used.

For each HydroBASINS unit and metric, fit a catchment fixed-effect linear trend:

```text
mechanism_metric_it = catchment_i + beta * calendar_decade_t + error_it
```

Uncertainty is clustered by catchment and uses a small-cluster t reference.
The estimator answers whether the same contributing catchments moved through
time, while controlling stable differences between catchments.

- Concentration slopes are reported as percentage points of event rainfall per
  decade.
- SSI slopes are reported as SSI index units per decade and, secondarily, as a
  percentage of the catchment-equal mean per decade.
- Physical rainfall-driver slopes retain raw units and a derived relative
  percentage scale.

## Spatial analysis

HydroBASINS level 5 is the only regional inference grain. A level-5 estimate
requires at least 20 contributing catchments; smaller regional units are
excluded. This is the sole regional sample-size threshold. It is a conservative
design choice for conventional catchment-clustered inference, not a theorem of
finite-sample sufficiency: published guidance notes that the boundary for
“few” clusters is context-dependent and can extend from fewer than 20 to fewer
than 50 clusters.

All level-5 tests for the five continuous primary metrics enter one declared
Benjamini–Hochberg family. Colour represents effect direction and magnitude;
it is never used alone as a significance claim.

## Evidence grades

A basin–metric estimate is labelled strong evidence only when:

1. it passes the complete level-5 primary-family 5% FDR;
2. its direction agrees across annual maxima, POT/Q90, POT/Q95 with 10-day
   declustering, and POT/Q97.5 whenever those estimates are available;
3. its sign is unchanged when each contributing catchment is removed in turn;
4. for antecedent wetness, all four SSI windows have the same direction.

## Catchment layer

Individual-catchment trends use Theil–Sen slopes and tie-corrected
Mann–Kendall tests on the primary POT/Q95 sample. A point is displayed only if
the catchment passes the long-record screen, has at least 10 selected events,
and those events span at least 20 years. Catchment-level FDR is applied by
metric. These points provide local context; the main inferential scale remains
the multi-catchment hydrological unit.

## Interpretation limits

- Results describe temporal association and changing composition of generating
  conditions, not causal attribution to anthropogenic climate change.
- Rainfall concentration is resolved daily and cannot identify hourly
  convective intensity.
- HydroBASINS pooling does not eliminate residual spatial dependence.
- A mechanism trend is not a trend in flood count, flood peak, or flood volume;
  those response variables are reported separately.
- Null results are retained. The analysis does not require significant change
  to satisfy the research question.
