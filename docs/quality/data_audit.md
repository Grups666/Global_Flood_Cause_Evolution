# Data Audit

## Overall assessment

**Usable with explicit exclusions.** All retained rain-event precipitation and
response windows can be reconstructed from the daily files, and reconstructed
event rainfall volumes agree with the source tables to floating-point precision.
The source package nevertheless contains identifier, geometry, and coverage
issues that must remain visible.

## Source inventory

- 4,838 dormant metadata rows and 4,797 growing metadata rows.
- 758,163 dormant events and 913,286 growing events.
- 4,838 daily files totaling approximately 3.51 GiB.
- Event dates span 1982-01-01 through 2019-12-29.
- 97.71% of source events have a `Rain-*` label.

## Material issues and treatment

### GCIN 2391 has events but no daily file

The union of event and metadata tables contains 4,839 identifiers, but only
4,838 daily files. `GCIN=2391` contributes four growing-season events and cannot
be independently reconstructed. It is excluded.

### Boundary file contains 41 rows with missing GCIN

The GeoPackage has 4,881 rows, 41 of which have no GCIN. Nonmissing GCIN values
are unique. Mapping joins use only nonmissing identifiers and the primary maps
use audited gauge coordinates.

### Event-table `streamflow_mm` is not peak flow

Spot checks and exact daily sums show that `streamflow_mm` is total streamflow
over the response window. The analysis does not rank events by this field; it
reconstructs `q_peak_mm_day` from the daily maximum.

### Missing daily streamflow is common outside selected event windows

Across the 4,150 retained low-snow, both-season catchments, 3,307 contain some
missing daily streamflow and the total number of missing streamflow days is
11,155,952. Every retained source event response window is complete, but
annual-max inference is protected by the explicit 30-year, 30-year-span, and
80%-coverage screen.

## Reconstruction results

- 1,407,121 retained rain events from 4,150 catchments.
- All 1,407,121 have valid reconstructed peak flow and rainfall concentration.
- Maximum source-versus-daily rainfall-volume discrepancy:
  `5.68e-13 mm`.
- SSI missing fraction by antecedent window:
  - 1 day: 0.0046%;
  - 3 days: 0.0114%;
  - 7 days: 0.0255%;
  - 30 days: 0.1662%.
- 1,407,056 events have complete peak, rainfall, and 1-day SSI features.

## Analysis samples

- Primary annual maximum: 100,788 events, 2,839 catchments.
- POT/Q95 sensitivity: 68,135 events, 3,206 catchments.

Primary regional catchment counts are Europe 1,469; North America 543; South
America 493; Oceania 198; Africa 132; and Asia 4. The sample is not spatially
balanced. Asia is excluded from regional trend inference because fewer than
five catchments qualify.

## Machine-readable evidence

See `outputs/tables/source_inventory.csv`, `source_missingness.csv`,
`source_quality_issues.csv`, `daily_event_feature_audit.csv`, and
`annual_sample_coverage.csv`.

