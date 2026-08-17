# Literature Review and Scientific Positioning

## Research gap

Observed flood trends are difficult to interpret from discharge or extreme
precipitation alone because rainfall organization, antecedent catchment state,
snow processes, and catchment properties can amplify, offset, or reverse one
another. The defensible scientific question is therefore not simply whether
floods became larger, but whether the **composition of conditions producing
large floods** changed through time.

This project addresses that question globally for rainfall-driven floods by
separating two event attributes:

1. temporal concentration of event rainfall, represented continuously by
   maximum daily rainfall divided by event rainfall volume; and
2. antecedent wetness, represented by 1-, 3-, 7-, and 30-day Soil Saturation
   Index means before event onset.

## Direct methodological foundations

### Causative classifications must be treated as uncertain models

Tarasova et al. (2019) reviewed flood-cause classification and showed that
event labels depend on input data, indicators, thresholds, and temporal and
spatial resolution. The review recommends testing classifications rather than
treating one decision tree as physical truth. This directly motivates retaining
continuous predictors and reporting threshold sensitivity.

Source: [Tarasova et al. (2019), WIREs Water](https://doi.org/10.1002/wat2.1353).

### Dimensionless rainfall descriptors transfer better than absolute thresholds

Tarasova et al. (2020) developed a process-based typology using dimensionless
ratio and covariance indicators. Its intensity-dominated rainfall rule uses the
combination of temporal rainfall variability and the ratio of maximum intensity
to total volume; the ratio threshold alone is not the complete original rule.
The present project therefore uses `Pmax/Pvolume > 0.50` as the transparent
primary operational definition requested by the project design, then tests the
joint `CV > 1` rule and a `0.75` ratio threshold.

Source: [Tarasova et al. (2020), Water Resources Research](https://doi.org/10.1029/2019WR026951).

### Global event classification is feasible but local process mixtures remain heterogeneous

Stein et al. (2020) demonstrated a location-independent classification of more
than 113,000 flood events in 4,155 catchments. They found strong within-site
variability in flood-generating processes, supporting event-level analysis
rather than assigning a single timeless type to each catchment.

Source: [Stein et al. (2020), Hydrological Processes](https://doi.org/10.1002/hyp.13678).

### Event selection and cause classification are separate decisions

Brunner et al. (2021) showed that conclusions about precipitation–flood change
depend on the extremeness threshold. Their precipitation events used a
full-record 99th percentile and a 10-day independence rule. This does not define
the meeting phrase “annual top 5%,” but it establishes the need to separate
declustering, threshold population, ranked variable, and response pairing.

Source: [Brunner et al. (2021), Communications Earth & Environment](https://doi.org/10.1038/s43247-021-00248-x).

### Annual maxima provide the closest observed-process precedent

Tarasova et al. (2023) classified annual maximum floods in 1,353 European
catchments and estimated changes in process frequency using Sen slopes and
Mann–Kendall tests, requiring at least five events of a process at a catchment.
Their results show that changing flood-generation processes can explain flood
anomalies beyond changes in extreme rainfall alone. This is the closest direct
precedent for the present global analysis.

Source: [Tarasova et al. (2023), Communications Earth & Environment](https://doi.org/10.1038/s43247-023-00714-8).

## Broader evidence

Zhang et al. (2022) showed that mixing rainfall- and snow-related mechanisms can
mask the response of global floods to increasing extreme precipitation. The
present analysis avoids that confounding by restricting its primary population
to catchments with long-term snow fraction below 0.10.

Source: [Zhang et al. (2022), Nature Climate Change](https://doi.org/10.1038/s41558-022-01539-7).

Tramblay et al. (2025) analyzed more than ten million projected annual maximum
floods in France and used catchment-specific process classification. Their
short-rain definition used a stricter `Pmax/Pvolume > 0.75` threshold and their
results again showed spatially heterogeneous changes among soil-saturation,
rainfall, and snow processes. This supports the present 0.75 sensitivity rule
and cautions against a single global direction.

Source: [Tramblay et al. (2025), Hydrology and Earth System Sciences](https://doi.org/10.5194/hess-29-7023-2025).

## Data-method foundations

The parent event catalogue was generated with a Detrended Moving-Average
Cross-correlation event-identification method. Giani et al. (2022) developed
this approach to identify rainfall–runoff events jointly from input and output
time series without an a priori baseflow separation.

Source: [Giani et al. (2022), Water Resources Research](https://doi.org/10.1029/2021WR031283).

Antecedent wetness comes from the GLASS-AVHRR daily 5 km soil-moisture product,
which spans 1982–2021. The study period is therefore fixed to the verified
1982–2019 overlap rather than extrapolated to the meeting target of 1970–2020.

Source: [Zhang et al. (2025), Earth System Science Data](https://doi.org/10.5194/essd-17-5181-2025).

## Position of this study

The study is an observational, event-based global extension of the European
process-change literature. Its novelty is the joint analysis of rainfall
temporal concentration and multiple antecedent-wetness windows across a large
global catchment sample, with explicit event-sample, classification-threshold,
multiple-testing, and regional-coverage diagnostics.

The analysis supports claims about **temporal association and composition
change in the available gauge sample**. It does not, by itself, attribute those
changes to anthropogenic climate forcing or establish physical causality.

