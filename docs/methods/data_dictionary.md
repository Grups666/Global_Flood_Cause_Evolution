# Data dictionary

## Source assets

| Asset | Role | Key fields |
|---|---|---|
| `events_dormant.csv`, `events_growing.csv` | Reconstructed rainfall–runoff event windows | `GCIN`, precipitation/response dates, source volumes, snow contribution |
| `daily_data/observations/*.csv` | Daily reconstruction | `date`, `water_input_mm`, `streamflow_mm`, `soil_saturation_index` |
| seasonal metadata | Catchment screen and outlet location | `GCIN`, country, longitude, latitude, snow fraction |
| catchment shapefile | Observed drainage polygons | `GCIN`, geometry |
| HydroBASINS v1.c level 5 | Regional polygons | `HYBAS_ID`, area, geometry |

## Event features

File: `data/derived/event_features.parquet`

| Field | Definition |
|---|---|
| `event_key` | Season-prefixed source event identifier |
| `GCIN` | Catchment identifier |
| `q_peak_date`, `peak_year` | Date and year of maximum daily streamflow in the response window |
| `q_peak_mm_day` | Event-window maximum daily streamflow |
| `q_event_total_mm` | Event-response-window streamflow sum |
| `p_volume_daily_mm` | Event rainfall total |
| `p_max_daily_mm` | Wettest daily event rainfall |
| `intensity_fraction` | `p_max_daily_mm / p_volume_daily_mm` |
| `ssi_1d`, `ssi_3d`, `ssi_7d`, `ssi_30d` | Mean SSI over complete antecedent days |
| `precip_window_complete`, `streamflow_window_complete` | Exact coverage checks |

## Event populations

| File | Definition |
|---|---|
| `primary_extreme_events.parquet` | Catchment-specific POT/Q95 after record, count, and span screens |
| `sensitivity_annual_maximum_events.parquet` | One maximum reconstructed flood per catchment-year |
| `sensitivity_pot_q90_events.parquet` | Catchment-specific POT/Q90 |
| `sensitivity_pot_q975_events.parquet` | Catchment-specific POT/Q97.5 |

## Result tables

| Table | Grain | Main contents |
|---|---|---|
| `record_eligibility.csv` | catchment | record years, span, coverage, eligibility |
| `extreme_sample_diagnostics.csv` | sample | events, catchments, independence diagnostics |
| `catchment_mechanism_trends.csv` | catchment × metric | annualized Theil–Sen slope, Mann–Kendall p value, fitted endpoints, alternative-sample/window/leave-one-year checks, robust individual-trend grade |
| `catchment_sensitivity_trends.csv` | sample × catchment × metric | alternative-sample direct trends |
| `hydrobasin_catchment_membership.csv` | catchment | L5 membership from outlet |
| `hydrobasin_mechanism_trends.csv` | sample × L5 × metric | fixed-effect or single-catchment estimate and uncertainty |
| `hydrobasin_evidence.csv` | L5 × metric | complete-family Benjamini–Hochberg false discovery rate (BH-FDR), sample/window/leave-one-out checks, evidence grade |
| `hydrobasin_trajectories.csv` | L5 × metric × year | adjusted annual trajectory and fitted trend |
| `spatial_support/l5_spatial_support_audit.csv` | L5 | polygon areas, observed union, coverage, largest contributing catchment |
| `spatial_support/l5_spatial_support_threshold_sensitivity.csv` | scope × threshold | retained L5 and catchment counts at 10–50% support |

Important catchment evidence fields are `robust_local_trend`, `alternative_sample_direction_stable`, `wetness_window_stable`, `leave_one_year_out_stable`, `local_check_count`, and `local_check_total`. Important regional fields are `estimator_type`, `primary_family_q`, `sample_direction_stable`, `wetness_window_stable`, `jackknife_sign_stable`, and `strong_evidence`.

The complete calculation and evidence rules are in [`analysis_protocol.md`](analysis_protocol.md).
