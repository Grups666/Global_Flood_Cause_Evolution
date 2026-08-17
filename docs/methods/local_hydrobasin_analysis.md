# Local HydroBASINS Trend Analysis

## Analytical question

The global and continental models estimate average within-catchment change, but
they can cancel spatially adjacent signals with opposite directions. This
analysis asks whether groups of nearby catchments inside standard nested river
basin units show larger and internally coherent changes in flood-generating
conditions.

## Spatial reference and assignment

- Reference: HydroBASINS standard polygons, version 1.c.
- Official source: <https://www.hydrosheds.org/products/hydrobasins>.
- Tested Pfafstetter levels: 3, 4, and 5.
- Primary spatial grain: level 5, the finest tested level that still retains a
  useful number of units under the declared sample-support requirements.
- Assignment: each gauge coordinate is spatially joined to its containing
  polygon. If a point lies on a shared boundary, the smallest matching polygon
  is selected deterministically.

The assignment matches 2,835 of 2,839 primary-sample catchments. The unmatched
locations are three gauges on Mauritius and one gauge on Hawaii. They are not
silently reassigned to a nearest mainland polygon.

## Eligibility and estimand

A basin unit is estimated only when it contains:

- at least 5 eligible catchments; and
- at least 300 nonmissing event observations for the outcome.

The 300-observation requirement means the smallest realized units contain nine
catchments. Units with 5–19 catchments are retained in the formal test family
but are marked as limited-sample estimates in the interactive map; units with
at least 20 catchments have stronger cluster support.

The estimator is the same within-catchment fixed-effect linear probability
model used for the global and continental results. Time is measured in decades,
and uncertainty is clustered by catchment. The estimand is the average
within-catchment change in event-type proportion, expressed as percentage points
per decade; it is not an area-weighted basin trend.

## Primary and exploratory test families

The primary HydroBASINS level-5 family contains two project-defined outcomes:

1. intensity-dominated events under `Pmax/Pvolume > 0.50`; and
2. wet one-day antecedent conditions under `SSI > 0.56`.

With 72 eligible level-5 units, this produces 144 primary tests. Benjamini–
Hochberg adjustment is applied across the complete 144-test family. Outcome-wise
and all-outcome adjusted values are retained as diagnostics but do not replace
the primary-family adjustment.

The joint intensity/CV rule, the 0.75 intensity threshold, 3-, 7-, and 30-day
wetness windows, and six crossed cause classes form the exploratory/sensitivity
family.

## Replication and stability gates

A `locally_replicated_signal` must:

1. pass the level-5 primary-family 5% FDR;
2. retain the same direction in the POT/Q95 event sample;
3. retain the same direction in the catchment-paired 1982–2000 versus
   2001–2019 comparison; and
4. have that paired comparison pass the corresponding primary-family FDR.

A `high_confidence_local_signal` additionally must:

5. preserve direction across the three rainfall-organization definitions or,
   for wetness, across the 1-, 3-, and 7-day windows; and
6. preserve direction in every leave-one-catchment-out refit.

Level-3 and level-4 parent estimates are reported separately as a spatial-scale
diagnostic. A level-5 signal is not rejected merely because it disappears or
reverses after aggregation: that pattern is evidence that the signal is
spatially localized. Signals that keep the same direction at all three levels
are marked as multiscale-replicated.

## Interpretation boundary

The analysis supports statements about coherent change in the available gauge
sample inside a HydroBASINS unit. It does not establish land-area-weighted basin
change or causal attribution. Catchment-clustered uncertainty does not fully
model residual correlation among neighboring catchments; spatial block
bootstrap or Conley-type uncertainty remains a required publication-stage
extension.
