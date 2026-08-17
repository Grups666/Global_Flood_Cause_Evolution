# Research Design Blueprint

## 1. Research objective

Estimate whether and where the composition of rainfall-driven flood-generation
conditions changes through time across global catchments.

The primary analysis unit is an independent flood event within a catchment.
Catchment-level change estimates are the basis for regional summaries and the
global map.

## 2. Proposed event descriptors

For each independent event:

- `Q_peak`: maximum streamflow during the response window.
- `Q_volume`: event runoff volume.
- `P_volume`: accumulated rainfall over the inducing-event window.
- `P_max`: maximum daily rainfall during the inducing-event window.
- `intensity_fraction = P_max / P_volume`.
- `SSI_1d`: SSI on the day before event start.
- `SSI_3d`, `SSI_7d`, `SSI_30d`: mean SSI over the corresponding number of
  complete days before event start.

Continuous descriptors must be retained even if categorical event labels are
later assigned.

## 3. Rainfall organization

Recommended initial rule, following Tarasova et al. (2020):

- `intensity-dominated` if `P_max / P_volume > 0.5`.
- `volume-dominated` otherwise.

This indicator is dimensionless and states whether more than half of event
rainfall occurred in one daily time step. Duration and raw `P_max` should remain
available for sensitivity checks because a daily ratio may not distinguish all
short-duration storms at sub-daily scales.

## 4. Antecedent wetness

The current Event_Typology baseline uses global SSI terciles and the 1-day
pre-event value. For the new project:

- Compute 1-, 3-, 7-, and 30-day antecedent SSI without changing event windows.
- Use the continuous SSI values in the primary trend models where possible.
- For categorical maps, initially retain dry/moderate/wet classes based on
  documented global thresholds to preserve comparability.
- Test binary dry/wet or catchment-relative thresholds as sensitivity analyses,
  not as silent replacements.

## 5. Extreme-event sample: unresolved decision

Three definitions must be compared in a feasibility table before one is fixed:

1. `Annual maximum flood`: one independent event per catchment-year, ranked by
   `Q_peak`. This most directly matches Tarasova et al. (2023) and gives a simple
   annual categorical sequence.
2. `Peaks over threshold`: independent events exceeding a catchment-specific
   percentile of `Q_peak` over the full record. A 95th-percentile threshold is a
   plausible interpretation of `top 5%`, but it is not yet a confirmed meeting
   definition.
3. `Within-year top 5%`: rank events separately within every catchment-year.
   This is not recommended unless event counts per year are sufficient; with a
   sparse event catalogue it can reduce to an unstable zero-or-one-event rule.

Recommended primary design: annual maximum floods, with a full-record POT/95th
percentile sensitivity analysis. This recommendation should be confirmed with
the supervisor before the main computation.

## 6. Rain-only scope

The initial population should be rain-dominated catchments and rainfall-driven
events. The exact catchment threshold must be documented. Candidate screens are:

- Catchment snow fraction below the established project threshold.
- A minimum fraction of historical events classified as rainfall-driven.

At event level, exclude snowmelt, rain-on-snow, and mixed events using the
available snowmelt contribution information. Do not assume that
`water_input_mm` is pure rainfall without verifying the source columns.

## 7. Change analysis

For annual-maximum sampling:

- Build one categorical cause record per catchment-year.
- Summarize type frequencies by decade for visualization.
- Estimate catchment-wise trends in the occurrence of each cause using Sen's
  slope and an exact Mann-Kendall test as a direct literature benchmark.
- Fit a binomial or multinomial time model as a complementary analysis that
  respects the categorical response.
- Require at least five occurrences of a cause before reporting its
  catchment-level trend, then evaluate stricter thresholds in sensitivity tests.

For POT sampling:

- Model annual counts or annual type proportions while accounting for the total
  number of selected events and years with no qualifying events.
- Do not run an ordinary trend test on an unweighted list of event years.

Compare early and late fixed windows as an interpretable robustness check, not
as a substitute for the primary trend model.

## 8. Planned outputs

1. Coverage and eligibility map.
2. Event-sample diagnostic table for each selection definition.
3. Global map of catchment-level cause-change direction and evidence.
4. Regional time series of event-type composition.
5. Sensitivity panels for 1-, 3-, 7-, and 30-day antecedent windows.
6. Sensitivity table for event threshold and wetness classification.
7. Exclusion and missing-data audit by catchment, country, and year.

## 9. Immediate feasibility questions

- Can the study period be changed to 1982-2019, or is another satellite soil
  moisture record required for 1970-1981 and 2020?
- Is `top 5%` based on flood peak, flood volume, rainfall intensity, or rainfall
  volume?
- Is the percentile calculated per catchment over the full record or within
  each year?
- Should cause labels use two wetness states or the current three SSI states?
- Is daily precipitation sufficient for the intended short-duration category?
