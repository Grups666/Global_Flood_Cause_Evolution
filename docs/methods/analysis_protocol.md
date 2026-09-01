# Analysis protocol

## Scientific question

The analysis asks whether the conditions accompanying large rainfall-driven floods changed during 1982–2019. Two continuous dimensions are retained: rainfall organization within an event and antecedent catchment wetness. The intended result is a catchment-first map of local long-term shifts followed by a second-stage test of whether neighboring catchments form a larger HydroBASINS L5 pattern.

The meeting establishes this scientific question and the two process dimensions. It does not prescribe a calendar split, estimator, HydroBASINS level, or numerical class threshold.

## Population and event sample

- Catchments have long-term snow fraction below 0.10, both seasonal event catalogues, a matching daily record, at least 30 observed event years, at least a 30-year first-to-last span, and at least 80% annual coverage.
- The primary sample is the catchment-specific upper 5% of reconstructed event flood peaks (POT/Q95).
- A catchment enters the primary event sample with at least 10 selected events spanning at least 20 years.
- Sensitivity samples are POT/Q90, POT/Q97.5, 10-day-declustered POT/Q95, and annual maxima.

Flood peak determines sample membership. Rainfall organization and antecedent wetness are calculated after selection, so condition description does not determine which events are called extreme.

## Continuous outcomes

### Rainfall concentration

For event $e$ in catchment $i$,

$$
C_{ie}=\frac{P_{\max,ie}}{P_{\mathrm{volume},ie}}.
$$

$P_{\max}$ is the wettest daily rainfall in the event window and $P_{\mathrm{volume}}$ is event rainfall total. An increasing $C$ means more rainfall was allocated to the wettest day; a decreasing $C$ means movement toward more prolonged rainfall. The fitted display slope is in percentage points of event rainfall per decade. No binary intensity-dominated label is used.

### Antecedent wetness

For rainfall-start date $t_0$ and window $w\in\{1,3,7,30\}$,

$$
SSI_{ie}^{(w)}=\frac{1}{w}\sum_{k=1}^{w}SSI_{i,t_0-k}.
$$

Positive trends indicate wetter states before selected floods; negative trends indicate drier states. SSI remains continuous. The analysis does not construct Dry/Moderate/Wet categories.

### Physical rainfall components

Maximum daily rainfall, event rainfall total, and precipitation duration are fitted in their raw units. A secondary relative change is obtained without a logarithmic model:

$$
r=100\frac{\widehat\beta}{\bar y}.
$$

These components explain why rainfall concentration moved; they do not establish causal attribution.

## First stage: direct catchment trends

Multiple selected events in one catchment-year are first averaged:

$$
\bar y_{it}=\frac{1}{n_{it}}\sum_e y_{iet}.
$$

This gives every observed event year equal time weight. For each catchment and metric, a Theil–Sen slope is estimated from the annualized series and reported per decade:

$$
\widehat\beta_i=\operatorname{median}_{t_j>t_k}
\left(\frac{\bar y_{it_j}-\bar y_{it_k}}{t_j-t_k}\right)\times10.
$$

A tie-corrected Mann–Kendall test evaluates monotonic trend. At least 10 distinct event years spanning at least 20 years are required.

The Benjamini–Hochberg false discovery rate procedure (BH-FDR) is applied separately across catchments for each physical metric. This is needed because the analysis searches the full catchment network for locations with a trend; it is not a correction of the five metrics within one prespecified catchment. If ordered p-values are $p_{(1)}\le\cdots\le p_{(m)}$, the largest $k$ satisfying

$$
p_{(k)}\le\frac{k}{m}\alpha,\qquad\alpha=0.05
$$

defines the rejected set.

A stable local candidate requires unadjusted $p<0.05$, sign agreement under POT/Q90 and POT/Q97.5, agreement after 10-day declustering, agreement under annual maxima, and leave-one-event-year-out sign stability. SSI candidates also require the four wetness windows to agree. Candidate status is exploratory; it never substitutes for BH-FDR.

## Second stage: area-supported L5 patterns

Each primary-sample catchment is assigned to HydroBASINS v1.c level 5 by its outlet. For L5 polygon $H_j$ and assigned catchment polygons $A_i$, observed area support is

$$
Coverage_j=\frac{Area\left(H_j\cap\bigcup_{i\in j}A_i\right)}{Area(H_j)}.
$$

Areas are calculated in equal-area EPSG:6933. Invalid polygons are repaired and overlap is counted once through a geometric union. The web explorer offers one regional-support rule with selectable values 10%, 20%, 30%, 40%, and 50%; 10% is the default. This threshold changes L5 interpretation only and never removes direct catchment results.

For at least two contributing catchments, annualized values are fitted with a catchment fixed effect:

$$
\bar y_{it}=\alpha_i+\beta_j\frac{year_{it}-2000}{10}+\varepsilon_{it}.
$$

$\alpha_i$ removes stable level differences and $\beta_j$ estimates a shared within-catchment change per decade. Standard errors are clustered by catchment with a $t(G-1)$ reference. The number 2000 is only a centering constant and is not a breakpoint.

If one catchment alone reaches the selected area threshold, the L5 panel inherits that catchment's Theil–Sen estimate and is explicitly marked as a single-catchment representation. It is not described as multi-catchment corroboration.

All estimable L5 × five-primary-metric tests form one complete Benjamini–Hochberg family. A strong regional pattern must pass:

1. the selected area-support threshold;
2. complete regional-family 5% BH-FDR;
3. sign agreement across the four alternative extreme-event samples;
4. sign agreement across SSI windows where applicable; and
5. leave-one-catchment-out sign stability, or leave-one-year-out stability for a single-catchment representation.

## Interpretation limits

- Results describe temporal association in flood-generating conditions, not changes in flood count, flood peak, or runoff volume.
- They do not attribute trends to anthropogenic climate change, land use, or engineering controls.
- Rainfall concentration has daily rather than sub-daily resolution.
- Area support measures observed polygon coverage, not population, assets, or area-weighted global representativeness.
- Null and weak results are retained; the research question does not require a universal or globally averaged direction.
