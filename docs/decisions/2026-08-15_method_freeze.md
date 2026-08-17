# Method Freeze — 2026-08-15

## Decisions fixed for the analysis

1. The verified study period is 1982–2019. The meeting target of approximately
   1970–2020 is not imputed or inferred.
2. The population is restricted to rainfall-driven events in catchments with
   long-term snow fraction below 0.10.
3. Annual maximum reconstructed daily peak flow is the primary extreme-event
   sample. Catchment-specific event Q95 is a sensitivity branch.
4. `Pmax/Pvolume > 0.50` is the transparent primary rainfall-organization rule.
   The joint `CV > 1` rule and `0.75` threshold are mandatory sensitivities.
5. One-day antecedent SSI is the primary wetness state for comparability with
   the parent project; 3-, 7-, and 30-day windows are mandatory sensitivities.
6. Catchment fixed-effect slopes with catchment-clustered uncertainty are the
   primary global/regional estimator.
7. Catchment-specific results use explicit minimum event counts and
   outcome-family Benjamini–Hochberg FDR.
8. No climate attribution or causal claim is permitted from this design alone.

## Reason for the freeze

The decisions separate the extreme-event population from the cause labels,
retain continuous descriptors, align the primary sample with the closest
observational precedent, and preserve the ambiguity of the meeting phrase
“annual top 5%” as a documented sensitivity question rather than silently
choosing an interpretation.
