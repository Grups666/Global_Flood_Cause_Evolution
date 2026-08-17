# Decision Record — Five-Catchment Minimum

## Decision

The formal HydroBASINS level-5 analysis uses a minimum of five eligible
catchments and 300 nonmissing annual event observations per outcome. This
criterion applies consistently to the paper, figures, output tables, and
interactive map.

## Evidence treatment

- All eligible units enter the same declared 144-test primary FDR family.
- Units with 5–19 catchments are visibly marked as limited-sample estimates;
  units with at least 20 catchments are marked as having larger cluster support.
- Effect magnitude, sample support, FDR status, and the complete robustness
  gate remain separate visual and analytical fields.
- The POT/Q95, paired-period, nested-scale, definition-sensitivity, and
  leave-one-catchment-out checks are recomputed for every included unit.

## Consequence

Seventy-two level-5 units are estimable: 44 have fewer than 20 catchments and
28 have at least 20. Thirty-six of 144 primary tests pass 5% FDR. Seventeen
signals pass the complete high-confidence screen, including two units with
fewer than 20 catchments. These two are retained but carry the limited-sample
label in the interactive map and require cautious interpretation.
