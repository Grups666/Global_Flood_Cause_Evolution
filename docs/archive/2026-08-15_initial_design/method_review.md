# Method Review

## Directly relevant literature

### Tarasova et al. (2020): process-based event typology

The framework classifies the temporal organization of an inducing event using
the ratio of maximum time-step precipitation intensity to total event
precipitation volume. A ratio above 0.5 is intensity-dominated; otherwise the
event is volume-dominated. The paper emphasizes dimensionless ratio- and
covariance-based indicators and tests threshold uncertainty.

Primary source:
https://doi.org/10.1029/2019WR026951

Open repository record:
https://gfzpublic.gfz.de/pubman/item/item_5001918_5

### Tarasova et al. (2023): changing flood-generation processes

This is the closest methodological precedent for the proposed temporal-change
study. It classifies annual maximum floods in European catchments, summarizes
process frequency by decade, and estimates catchment-wise trends with Sen's
slope and the exact Mann-Kendall test. Trend analysis is performed only when a
catchment has at least five events of the process of interest. Results are then
aggregated regionally.

Primary source:
https://doi.org/10.1038/s43247-023-00714-8

### Brunner et al. (2021): extremeness threshold and P-Q pairing

This paper selects extreme precipitation using the 99th percentile calculated
from the full daily record, including zero-precipitation days, and imposes a
minimum 10-day separation to decluster events. It then pairs each precipitation
event with the streamflow peak from event start through five days after event
end. This produces about 2-2.5 events per year in the study setting.

It supports careful threshold and independence definitions, but it does not by
itself verify the meeting phrase `annual top 5%`.

Primary source:
https://doi.org/10.1038/s43247-021-00248-x

### Tarasova et al. (2019): causative classification review

The review stresses that flood-cause classifications are sensitive to input
data, indicators, and thresholds. It recommends uncertainty analysis and
evaluation of transferability rather than treating one discrete classification
as uniquely correct.

Primary source:
https://doi.org/10.1002/wat2.1353

## Implications for this project

- The proposed global study is more directly an extension of Tarasova et al.
  (2023) than a simple extension of the current Event_Typology figures.
- Event_Typology supplies useful global data infrastructure and a compatible
  antecedent-wetness vocabulary.
- The extreme-event definition must be selected independently from the
  intensity/volume cause label.
- A global implementation needs explicit sensitivity tests because satellite
  coverage, catchment climate, and event counts vary strongly in space.
