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

For plain-language interpretation, events with a concentration ratio above
0.50 are labelled intensity-dominated and the rest volume-dominated. The 0.50
rule is literature-derived, not a meeting instruction. The continuous ratio is
the inferential target; thresholded shares are secondary.

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

Within-catchment trends in log maximum daily rainfall, log event rainfall, and
log duration are converted to approximate percent change per decade. They are
used to explain why the rainfall-concentration ratio moved; they are not added
as extra definitions of flood cause.

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
- SSI slopes are reported as SSI index units per decade.
- Binary interpretation slopes are reported as percentage points of selected
  extreme events per decade.
- Log-driver slopes are reported as approximate percent change per decade.

## Spatial analysis

HydroBASINS levels 3, 4, and 5 are estimated; level 5 is the interactive map
grain and levels 3–4 provide nested spatial context. A level-5 estimate requires
at least 5 catchments and 100 nonmissing event observations. Units with 5–19
catchments remain exploratory; strong regional evidence requires at least 20
catchments.

All level-5 tests for the five continuous primary metrics enter one declared
Benjamini–Hochberg family. Colour represents effect direction and magnitude;
it is never used alone as a significance claim.

## Evidence grades

A basin–metric estimate is labelled strong evidence only when:

1. it passes the complete level-5 primary-family 5% FDR;
2. at least 20 catchments contribute;
3. its direction agrees across annual maxima, POT/Q90, POT/Q95 with 10-day
   declustering, and POT/Q97.5 whenever those estimates are available;
4. its sign is unchanged when each contributing catchment is removed in turn;
5. for antecedent wetness, all four SSI windows have the same direction.

Nested-scale agreement is displayed as context rather than required, because a
genuinely local change can disappear when averaged into a larger basin.

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
