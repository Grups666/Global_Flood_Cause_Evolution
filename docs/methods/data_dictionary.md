# Data Dictionary

## Source assets

| Asset | Role | Important fields |
|---|---|---|
| `events_dormant.csv`, `events_growing.csv` | Independent runoff-event windows and source descriptors | `GCIN`, precipitation/response dates, volumes, source SSI, snow contribution, event type |
| `daily_data/observations/*.csv` | Daily event reconstruction | `date`, `water_input_mm`, `streamflow_mm`, `soil_saturation_index` |
| `metadata_dormant.csv`, `metadata_growing.csv` | Catchment screening and coordinates | `GCIN`, country, longitude, latitude, snow fraction |
| `Gauged_Catchments_Boundaries.gpkg` | Mapping support | `GCIN`, geometry |
| `data/reference/hydrobasins/hybas_*_lev{03,04,05}_v1c.zip` | Standard nested basin units | `HYBAS_ID`, `PFAF_ID`, sub-basin area, geometry |

`streamflow_mm` in the event tables is the sum of daily streamflow over the
response window, not the event peak. The pipeline reconstructs the peak from
daily records.

## Derived event features

File: `data/derived/event_features.parquet`

| Field | Definition |
|---|---|
| `event_key` | Season-prefixed source event identifier |
| `GCIN` | Catchment identifier |
| `season` | Dormant or growing catalogue |
| `q_peak_date` | Date of maximum daily streamflow within the response window |
| `peak_year` | Calendar year of `q_peak_date` |
| `q_peak_mm_day` | Maximum daily streamflow in the response window |
| `q_event_total_mm` | Source event-table sum of daily streamflow |
| `q_direct_volume_mm` | Source event direct stormflow volume |
| `p_volume_table_mm` | Source event rainfall/water-input volume |
| `p_volume_daily_mm` | Reconstructed sum of daily event water input |
| `p_max_daily_mm` | Maximum daily event water input |
| `intensity_fraction` | `p_max_daily_mm / p_volume_daily_mm` |
| `precipitation_cv` | Population standard deviation divided by mean daily event rainfall |
| `ssi_1d`, `ssi_3d`, `ssi_7d`, `ssi_30d` | Mean SSI over complete antecedent days |
| `p_volume_absolute_error_mm` | Absolute difference between source and reconstructed event rainfall volume |
| `precip_window_complete` | Exact date coverage and nonmissing precipitation for the event window |
| `streamflow_window_complete` | Exact date coverage and nonmissing streamflow for the response window |

## Analysis samples

- `data/derived/annual_maximum_events.parquet`: one reconstructed peak event per
  eligible catchment-year after the record screen.
- `data/derived/pot_q95_events.parquet`: events at or above each catchment's
  full-record 95th peak-flow percentile.

Both files contain the categorical analysis variables added after continuous
feature reconstruction.

## Main result tables

| Table | Grain | Purpose |
|---|---|---|
| `annual_sample_coverage.csv` | Catchment | Year count, span, coverage, and eligibility |
| `sample_diagnostics.csv` | Analysis stage | Sample-size flow |
| `daily_event_feature_audit.csv` | Catchment | Daily completeness and event-window reconstruction |
| `source_quality_issues.csv` | Quality check | Source inconsistencies and analysis action |
| `panel_fixed_effect_trends.csv` | Sample × region × outcome | Primary within-catchment global/regional slopes |
| `period_comparison_paired.csv` | Sample × region × outcome | Catchment-paired early/late sensitivity |
| `period_comparison_pooled.csv` | Sample × region × outcome | Descriptive event-weighted early/late comparison |
| `catchment_binary_trends.csv` | Catchment × binary outcome | Logistic trends and FDR |
| `catchment_continuous_trends.csv` | Catchment × continuous variable | Sen/Mann–Kendall trends and FDR |
| `regional_annual_composition.csv` | Region × year × cause | Annual composition and five-year smoothing |
| `cause_composition_by_region.csv` | Region × cause | Descriptive regional composition |
| `hydrobasin_catchment_membership.csv` | Catchment | Level-3/4/5 HydroBASINS assignment and basin areas |
| `hydrobasin_sample_summary.csv` | HydroBASINS unit | Sample counts, dominant countries, and median gauge coordinates |
| `local_hydrobasin_trends.csv` | Sample × level × unit × outcome | Fixed-effect slopes, confidence intervals, and three FDR families |
| `local_hydrobasin_period_comparison.csv` | Level-5 unit × outcome | Catchment-paired early/late changes and FDR |
| `local_hydrobasin_robustness.csv` | Level-5 unit × outcome | Event-sample, scale, definition, paired-period, and jackknife diagnostics |
