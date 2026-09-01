# Data audit

## Verified scope

- Common usable time period: 1982–2019.
- Source event catalogues: dormant and growing season files.
- Daily inputs: water input, streamflow, and Soil Saturation Index.
- Primary population: low-snow catchments with at least 30 observed event years, at least a 30-year span, and at least 80% annual coverage.

## Reconstruction checks

- Daily rainfall sums reproduce event-window rainfall volume.
- Daily rainfall maxima provide `Pmax`.
- Daily streamflow maxima provide the event peak used to rank extremes.
- Antecedent SSI uses complete days before rainfall begins and never includes the event day.
- Event selection is performed after continuous feature reconstruction.

## Primary event sample

- 59,048 POT/Q95 events in 2,624 catchments.
- Minimum 10 selected events and minimum 20-year selected-event span.
- No overlapping reconstructed stormflow windows in the primary sample.
- 2,194 adjacent peak pairs are less than 10 days apart; a separately declustered sensitivity sample removes all such pairs.

## Geography

Official HydroBASINS v1.c level 5 is used without modifying the source archives. All 8 continental level-5 archives are checked against recorded byte sizes and SHA-256 values during validation.
