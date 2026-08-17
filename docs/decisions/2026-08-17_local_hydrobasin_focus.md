# Decision Record — Local HydroBASINS Focus

## Decision

The paper narrative will treat global and continental estimates as context and
will use HydroBASINS level-5 units as the primary spatial grain for identifying
localized changes. Levels 3 and 4 are retained as nested scale sensitivities.

## Rationale

The meeting objective emphasizes where flood causes changed and a global map of
change directions. Global or continental averaging can cancel nearby signals
of opposite direction, while independent single-catchment tests have low power
after multiple-testing correction. Pooling neighboring catchments inside a
standard hydrologic unit provides a reproducible middle scale. The formal
minimum is five catchments and 300 observations; the interface separately
identifies units with fewer than 20 catchments as limited-sample estimates.

## Guardrails

- The main intensity definition remains `Pmax/Pvolume > 0.50`; alternative
  definitions are sensitivity checks rather than silent replacements.
- All 72 eligible level-5 units and both primary outcomes enter one declared
  144-test FDR family.
- Large effects are reported only after paired-period, POT/Q95, definition, and
  leave-one-catchment-out checks.
- Spatially correlated uncertainty remains an explicit limitation.
