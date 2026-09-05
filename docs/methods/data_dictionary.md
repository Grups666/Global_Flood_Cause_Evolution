# Data dictionary

## Identifiers and timing

| Field | Meaning |
|---|---|
| `event_key` | Stable season–catchment–event identifier |
| `GCIN` | Gauged Catchment Identification Number |
| `peak_year` | Calendar year of the event-window maximum daily streamflow |
| `start_precip_date`, `end_precip_date` | Reconstructed inducing-precipitation window |
| `start_stormflow_date`, `end_stormflow_date` | Reconstructed hydrological-response window |

## Flood response and selection

| Field | Meaning |
|---|---|
| `q_direct_volume_mm` | Direct stormflow volume over the response window; the primary Q95 ranking variable |
| `selection_threshold_mm` | Catchment-specific full-record quantile of `q_direct_volume_mm` |
| `q_peak_mm_day` | Maximum daily streamflow within the response window |
| `q_event_total_mm` | Total streamflow over the response window, including the source catalogue definition |
| `runoff_ratio` | Event direct stormflow volume divided by event precipitation volume |

## Generating conditions

| Field | Meaning |
|---|---|
| `p_max_daily_mm` | Maximum daily precipitation within the event |
| `p_volume_daily_mm` | Sum of daily precipitation over the event |
| `intensity_fraction` | `p_max_daily_mm / p_volume_daily_mm`; rainiest-day share of event rainfall |
| `precipitation_cv` | Temporal coefficient of variation of daily event precipitation |
| `source_ssi` | Audit-only source-catalogue SSI; verified as rainfall-start-day SSI, not used for the analytical antecedent metric |
| `antecedent_state` | `Dry`, `Moderate` or `Wet` from previous-day SSI and recalibrated pooled daily terciles; `Unknown` when missing |
| `rainfall_organization` | `Intensity` if concentration >0.50 and precipitation CV >1; otherwise `Volume` |
| `mechanism` | Cross of antecedent state and rainfall organization; `Unclassified` if antecedent SSI is missing |
| `ssi_1d` | Primary antecedent metric: daily SSI on the day before rainfall begins |
| `ssi_3d`, `ssi_7d`, `ssi_30d` | Mean SSI over complete 3-, 7- or 30-day windows ending the day before rainfall begins; sensitivity diagnostics |

## Trend outputs

| Field | Meaning |
|---|---|
| `outcome` | Physical quantity being tested |
| `display_slope_per_decade` | Primary effect in the unit shown by `display_unit`; one decade is 10 years |
| `display_ci_low_per_decade`, `display_ci_high_per_decade` | 95% interval on the display scale |
| `fitted_first`, `fitted_last` | Fitted early- and late-record levels in physical units; used for “from → to” interpretation |
| `p_value` | Two-sided p-value from the Mann–Kendall, Poisson-count or binomial-share trend, according to `outcome` |
| `relative_slope_percent_per_decade` | Secondary change relative to the local mean; absolute physical units remain primary |
| `rate_ratio_per_decade` | Poisson multiplicative rate ratio for annual count outcomes; the interface displays the corresponding absolute rate change |
| `sample_direction_stable` | Same sign under Q90, Q97.5 and annual-maximum samples |
| `classification_direction_stable` | Same sign under rainfall concentration cutoffs 0.40 and 0.60 |
| `leave_one_year_stable` | No single removed year reverses the trend sign |
| `supported_shift` | All applicable evidence screens pass |

## Missing values

Missing event windows, missing variables and insufficient process samples remain missing. They are never encoded as zero. A zero annual count is created only for an observed record year in which no selected event of the relevant process occurred.
