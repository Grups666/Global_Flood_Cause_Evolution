# Data dictionary

## Source assets

| Asset | Role | Key fields |
|---|---|---|
| `events_dormant.csv`, `events_growing.csv` | Reconstructed rainfall–runoff event windows | `GCIN`, precipitation and response dates, source volumes, snow contribution |
| `daily_data/observations/*.csv` | Daily event reconstruction | `date`, `water_input_mm`, `streamflow_mm`, `soil_saturation_index` |
| seasonal metadata files | Catchment screen and coordinates | `GCIN`, country, longitude, latitude, snow fraction |
| HydroBASINS level-5 archives | Local hydrological regions | `HYBAS_ID`, area, polygon geometry |

## Derived event features

File: `data/derived/event_features.parquet`

| Field | Definition |
|---|---|
| `event_key` | Season-prefixed source event identifier |
| `GCIN` | Catchment identifier |
| `q_peak_date`, `peak_year` | Date and calendar year of maximum daily streamflow in the response window |
| `q_peak_mm_day` | Maximum daily streamflow in the response window |
| `q_event_total_mm` | Sum of daily streamflow over the event response window |
| `p_volume_daily_mm` | Sum of daily event water input |
| `p_max_daily_mm` | Maximum daily event water input |
| `intensity_fraction` | `p_max_daily_mm / p_volume_daily_mm` |
| `precipitation_cv` | Population standard deviation divided by mean daily event rainfall |
| `ssi_1d`, `ssi_3d`, `ssi_7d`, `ssi_30d` | Mean SSI over complete antecedent days |
| `precip_window_complete`, `streamflow_window_complete` | Exact date coverage and nonmissing values for event windows |

## Analysis samples

| File | Definition |
|---|---|
| `primary_extreme_events.parquet` | Catchment-specific POT/Q95 events after the long-record, event-count, and selected-span screens |
| `sensitivity_annual_maximum_events.parquet` | One maximum reconstructed flood per eligible catchment-year |
| `sensitivity_pot_q90_events.parquet` | Catchment-specific POT/Q90 events |
| `sensitivity_pot_q95_gap10_events.parquet` | POT/Q95 after 10-day peak declustering |
| `sensitivity_pot_q975_events.parquet` | Catchment-specific POT/Q97.5 events |

## Current result tables

| Table | Grain | Purpose |
|---|---|---|
| `record_eligibility.csv` | Catchment | Event-year count, span, coverage, and long-record eligibility |
| `extreme_sample_diagnostics.csv` | Sample | Event and catchment counts plus independence diagnostics |
| `global_regional_trends.csv` | Sample × region × metric | Continuous within-catchment slopes and confidence intervals |
| `global_regional_trajectories.csv` | Region × metric × year | Adjusted annual means for the primary sample |
| `catchment_mechanism_trends.csv` | Catchment × metric | Theil–Sen trends, Mann–Kendall tests, and FDR |
| `hydrobasin_catchment_membership.csv` | Catchment | Level-5 HydroBASINS membership |
| `hydrobasin_sample_summary.csv` | HydroBASINS unit | Assigned catchments, countries, and map centers |
| `hydrobasin_mechanism_trends.csv` | Sample × L5 basin × metric | Multi-catchment fixed-effect estimates, raw slopes, and catchment-equal relative slopes |
| `hydrobasin_evidence.csv` | Level-5 basin × metric | Complete-family FDR, alternative-sample, SSI-window, jackknife, and evidence grades |
| `hydrobasin_trajectories.csv` | Basin × metric × year | Adjusted annual trajectory and fitted trend |
| `hydrobasin_mechanism_summary.csv` | Level-5 basin | Plain-language rainfall and wetness directions |

The complete variable definitions and evidence rules are specified in [`analysis_protocol.md`](analysis_protocol.md).
