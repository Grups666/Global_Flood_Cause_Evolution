# Decision Record — Local HydroBASINS Focus

## Decision

The paper narrative will treat global and continental estimates as context and
will use HydroBASINS level-5 units as the primary spatial grain for identifying
localized changes. Levels 3 and 4 are retained as nested scale sensitivities.

## Rationale

The meeting objective emphasizes where flood causes changed and a global map of
change directions. Global or continental averaging can cancel nearby signals
of opposite direction, while independent single-catchment tests have low power
after multiple-testing correction. Pooling at least 20 neighboring catchments
inside a standard hydrologic unit provides a reproducible middle scale.

## Guardrails

- The main intensity definition remains `Pmax/Pvolume > 0.50`; alternative
  definitions are sensitivity checks rather than silent replacements.
- All 28 eligible level-5 units and both primary outcomes enter one declared
  56-test FDR family.
- Large effects are reported only after paired-period, POT/Q95, definition, and
  leave-one-catchment-out checks.
- Spatially correlated uncertainty remains an explicit limitation.

