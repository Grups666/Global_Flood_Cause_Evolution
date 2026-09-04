# Data audit

## Source boundary

The project reuses the related Event Typology data tree read-only. The feature build scans 4,838 daily observation files (about 37.77 GB), processes 4,150 catchments and reconstructs 1,407,121 hydrological events.

## Verified common record

The reusable precipitation, streamflow and modelled soil-saturation data support 1982–2019. The analysis does not infer an earlier or later record. Catchments must have at least 30 event years, a 30-year span and 80% event-year coverage; 2,839 catchments satisfy this record gate.

## Event quantities

- `q_direct_volume_mm` is event direct stormflow volume and defines the Q95/Q90/Q97.5 samples.
- `q_peak_mm_day` is the maximum daily streamflow inside the reconstructed event-response window.
- `p_volume_daily_mm` and `p_max_daily_mm` are independently reconstructed from daily water input.
- `intensity_fraction = p_max_daily_mm / p_volume_daily_mm`.
- `precipitation_cv` is the daily temporal coefficient of variation within the event.
- `source_ssi` and the dry/moderate/wet state come from the audited event catalogue.

Missing precipitation, streamflow or antecedent-state values are excluded from the affected calculation; they are never replaced by zero. Zero is used only for annual event-frequency series when a catchment has an observed year but no selected event of the relevant type.

## Independence

The reconstructed Q95 sample has no overlapping stormflow-response windows. Adjacent peaks can be fewer than ten days apart without representing overlapping response windows, so independence is checked from the event windows themselves.
