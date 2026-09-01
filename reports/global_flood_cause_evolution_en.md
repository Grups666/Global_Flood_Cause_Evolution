# Long-term changes in rainfall-driven large-flood generating conditions (1982–2019)

**Complete technical report · generated 2026-09-02**

> **Main result.** Individual catchments are the first-level research objects. Among 12,163 estimable catchment–metric trends, 378 satisfy the p-value, alternative-extreme-sample, and leave-one-year-out checks; SSI additionally requires agreement across all antecedent windows. HydroBASINS level 5 (L5) is a separate, expanded regional analysis. At the default ≥50% area support, 10 strong regional signals occur in 6 L5 units. Local increases and decreases coexist; the result is not one spatially uniform global direction.

## Technical summary

- The primary sample contains **59,048 POT/Q95 large-flood events** from **2,624** eligible long-record, low-snow catchments.
- At least one continuous condition trend is estimable in **2,435 catchments**, producing **12,163 catchment–metric estimates**. A complete grid would contain 2,435 × 5 = 12,175; the 12 missing combinations lack 10 valid event years or a 20-year first-to-last span and are not coded as zero.
- Catchment results report slopes, confidence intervals, p values, fitted endpoints, and stability checks.
- L5 is the second-level expanded analysis. All **1,475 estimable L5–metric results** enter one complete regional testing family with Benjamini–Hochberg false discovery rate control (BH-FDR).
- The default L5 polygon-area support is **50%**. The web explorer also exposes 10%, 20%, 30%, and 40% to show the coverage–availability trade-off without removing individual results.

![Sample coverage](assets/figure_01_sample_coverage.png)

## 1. Research question

The study asks two sequential questions: which individual catchments show persistent changes in the conditions that generate selected large floods, and do some nearby catchments form a reproducible larger hydrological pattern?

## 2. Two analysis levels

The first level analyses each catchment directly. The second level pools catchments within HydroBASINS L5 units. L5 does not screen or define the value of an individual result; it is an expanded spatial question.

## 3. Period and observational boundary

The reusable overlapping record is 1982–2019. “Global” describes the geographical spread of the observed network, not uniform area-weighted land coverage. Long records are especially sparse in Asia.

## 4. Catchment eligibility

A catchment requires at least 30 observed years, at least 80% record coverage, at least 10 selected event years for a fitted metric, and at least 20 years from the first to last selected year. Insufficient combinations are omitted rather than treated as zero trends.

## 5. Event selection is separate from condition description

Flood-peak magnitude selects large-flood events. Rainfall concentration and antecedent wetness then describe how the selected events formed. The explanatory rainfall condition therefore does not define the event population.

## 6. Primary POT/Q95 population

POT means Peaks Over Threshold. Within each catchment, events above the 95th percentile of flood peaks are retained. Unlike annual maxima, POT can retain more than one large flood in a year and therefore uses the event record more fully.

## 7. Event independence

The source event catalogue already separates hydrological events. Primary-sample stormflow-window overlaps equal **0**. A peak interval shorter than 10 days does not by itself prove that two reconstructed hydrological events are dependent, so a 10-day gap is not retained as an additional evidence gate.

## 8. Alternative extreme-sample sensitivity

One combined check compares POT/Q90, POT/Q97.5, and annual maxima with the primary POT/Q95 result. Passing means that all three alternatives preserve the main slope direction. This directly asks whether the conclusion depends on one particular definition of a large flood.

## 9. Rainfall concentration

For event $e$:

$$C_e=\frac{P_{\max,e}}{P_{\mathrm{volume},e}}$$

$P_{\max,e}$ is rainfall on the wettest day and $P_{\mathrm{volume},e}$ is total event rainfall. If an event contains 100 mm and its wettest day supplies 42 mm, $C_e=0.42=42\%$. A trend of +8.83 percentage points per 10 years with a fitted starting level of 30% implies a fitted ending level near 38.83%. Physically, a larger share of event rainfall falls on the wettest day; it is not an 8.83% change in flood count or peak discharge.

## 10. Antecedent Soil Saturation Index (SSI)

For an antecedent window $w$:

$$SSI_{e,w}=\frac1w\sum_{d=1}^w SSI_{e,-d},\qquad w\in\{1,3,7,30\}$$

One day represents immediate pre-event wetness; 30 days represents longer memory. If mean 7-day SSI is 0.45 and the slope is +0.009 per 10 years, selected floods occur after conditions that become 0.009 SSI units wetter per decade. The auxiliary relative change is $100\times0.009/0.45=2.0\%$ per 10 years.

## 11. Supporting rainfall components

Maximum daily rainfall, total event rainfall, and precipitation duration are fitted in raw units. Their auxiliary relative slope is:

$$r=100\frac{\hat\beta}{\bar y}$$

For example, +2 mm per 10 years around a 50 mm mean equals +4% per 10 years. If total rainfall increases by 8% while the daily maximum increases by 2%, total rainfall grows faster and concentration tends to decline. No logarithmic trend model is needed.

## 12. Catchment-year annualization

Multiple selected events in one catchment-year are averaged:

$$\bar y_{it}=\frac1{n_{it}}\sum_e y_{iet}$$

For example, three events with concentrations of 30%, 45%, and 60% produce one annual value of 45%. The year does not receive three times the trend weight merely because it contains three events.

## 13. Individual-catchment trend

The Theil–Sen median slope is:

$$\hat\beta_i=\mathrm{median}_{t_2>t_1}\frac{\bar y_{it_2}-\bar y_{it_1}}{t_2-t_1}\times10$$

Mann–Kendall supplies the p value. A concentration slope of −4.2 percentage points per 10 years means that the fraction of event rainfall falling on the wettest day decreases by 4.2 points per decade: selected large floods are shifting toward longer, more evenly distributed rainfall.

## 14. Robust individual trend

Rainfall concentration requires p value < 0.05, direction agreement under POT/Q90, POT/Q97.5, and annual maxima, and direction stability after removing every observed event year in turn. SSI additionally requires agreement across the 1-, 3-, 7-, and 30-day windows. Results passing these conditions are “robust individual trends”; all other estimable results remain “individual trend estimates.”

## 15. Individual results overview

| Metric | Estimable catchments | p < 0.05 | Robust individual trends | Negative | Positive |
|---|---:|---:|---:|---:|---:|
| Rainfall concentration | 2,435 | 154 | 73 | 39 | 34 |
| Antecedent SSI (1 day) | 2,435 | 184 | 78 | 48 | 30 |
| Antecedent SSI (3 days) | 2,435 | 181 | 77 | 49 | 28 |
| Antecedent SSI (7 days) | 2,433 | 164 | 81 | 48 | 33 |
| Antecedent SSI (30 days) | 2,425 | 163 | 69 | 32 | 37 |

![Individual catchment trend maps](assets/figure_02_mechanism_change_maps.png)

![Individual robustness checks and directions](assets/figure_03_strong_signal_rankings.png)

## 16. Representative individual results

The fitted start → end column gives each per-decade slope a direct physical interpretation.

| GCIN | Country | Metric | Change per 10 years | Fitted start → end | p value |
|---:|---|---|---:|---:|---:|
| 2590 | US | Antecedent SSI (7 days) | -0.075 SSI | 0.655 → 0.421 | 0.0487 |
| 4052 | CL | Rainfall concentration | -15.06 pp | 69.91 → 26.23 | 0.0060 |
| 466 | DE | Rainfall concentration | +13.91 pp | 14.57 → 66.05 | 0.0095 |
| 2177 | MU | Antecedent SSI (1 day) | +0.060 SSI | 0.603 → 0.808 | 0.0274 |
| 2177 | MU | Antecedent SSI (3 days) | +0.060 SSI | 0.596 → 0.799 | 0.0116 |
| 2772 | US | Rainfall concentration | +11.24 pp | 28.74 → 69.20 | 0.0008 |
| 2438 | US | Rainfall concentration | -10.96 pp | 69.40 → 39.80 | 0.0297 |
| 3336 | ZA | Rainfall concentration | -10.89 pp | 57.07 → 23.30 | 0.0280 |
| 3708 | BR | Antecedent SSI (3 days) | -0.054 SSI | 0.726 → 0.574 | 0.0285 |
| 312 | DE | Rainfall concentration | +10.70 pp | 22.32 → 57.63 | 0.0343 |
| 1734 | AU | Rainfall concentration | +10.68 pp | 46.61 → 77.59 | 0.0004 |
| 3708 | BR | Antecedent SSI (1 day) | -0.053 SSI | 0.721 → 0.571 | 0.0285 |

## 17. Geographical distribution of individual trends

| Country | Metric | Direction | Robust catchments |
|---|---|---|---:|
| FR | Antecedent SSI (30 days) | increase | 20 |
| FR | Rainfall concentration | decrease | 19 |
| US | Rainfall concentration | increase | 19 |
| US | Antecedent SSI (1 day) | decrease | 17 |
| FR | Antecedent SSI (7 days) | increase | 17 |
| US | Antecedent SSI (3 days) | decrease | 17 |
| US | Antecedent SSI (7 days) | decrease | 17 |
| FR | Antecedent SSI (1 day) | increase | 16 |
| FR | Antecedent SSI (3 days) | increase | 14 |
| FR | Antecedent SSI (7 days) | decrease | 11 |
| DE | Rainfall concentration | increase | 11 |
| DE | Antecedent SSI (1 day) | decrease | 11 |
| DE | Antecedent SSI (7 days) | increase | 11 |
| DE | Antecedent SSI (30 days) | increase | 10 |
| DE | Antecedent SSI (3 days) | decrease | 10 |

Increasing and decreasing directions coexist across countries and metrics. These are catchment-scale hydrological observations and cannot be extrapolated by national land area.

## 18. What L5 means

HydroBASINS is a nested global hydrological partition. Level 5 (L5) is its fifth, river-network-defined intermediate spatial level. Here L5 asks whether individual changes form a larger hydrological pattern.

## 19. Assigning catchments to L5

Catchment polygons are spatially matched to L5 polygons. Catchments assigned to the same unit enter the regional model, while every catchment remains independently available in the primary map layer.

## 20. Area support

$$A_h=100\frac{\operatorname{area}(\bigcup_i B_i\cap H_h)}{\operatorname{area}(H_h)}$$

If an L5 unit covers 10,000 km² and observed catchment polygons cover a 5,600 km² union inside it, support is 56% and passes the default 50% threshold. One catchment covering 90% can represent most of the L5 area, but is explicitly labelled as a single-catchment representation rather than multi-catchment corroboration.

## 21. Area-threshold sensitivity

| Area-support threshold | L5 with estimates | Catchments represented | Global catchment share | US catchment share | Strong regional signals | L5 involved |
|---:|---:|---:|---:|---:|---:|---:|
| 10% | 152 | 2,139 | 81.6% | 63.6% | 84 | 36 |
| 20% | 82 | 1,287 | 49.1% | 34.1% | 42 | 22 |
| 30% | 48 | 660 | 25.2% | 20.1% | 28 | 16 |
| 40% | 32 | 399 | 15.2% | 15.5% | 19 | 11 |
| 50% | 18 | 145 | 5.5% | 7.0% | 10 | 6 |

![Area-threshold sensitivity](assets/figure_05_physical_decomposition.png)

Fifty percent is the default interpretation threshold. The lower controls expose the spatial-coverage trade-off; they never remove underlying individual trends.

## 22. L5 regional trend model

For a multi-catchment L5 unit:

$$y_{it}=\alpha_i+\beta_h\frac{t-2000}{10}+\varepsilon_{it}$$

$\alpha_i$ absorbs each catchment's persistent mean level and $\beta_h$ estimates their common within-catchment change per 10 years. If upstream concentration averages 30% and downstream concentration 55%, their baseline difference is not mistaken for temporal change.

## 23. Single-catchment L5 representation

When one observed catchment alone covers at least 50% of an L5 unit, the regional value inherits that catchment trend and is labelled `single-catchment representation`. It supports spatial representation of most of the polygon, not multi-catchment agreement.

## 24. Centering the year

$x=(t-2000)/10$ expresses time in decades from 2000. The constant stabilizes calculation and interpretation of the intercept. It is not a breakpoint, and replacing 2000 with 1990 or 2010 does not change the slope.

## 25. L5 BH-FDR

Only the L5 layer applies the Benjamini–Hochberg false discovery rate procedure (BH-FDR). Sort the complete regional family's $m$ p values and find the largest $k$ satisfying:

$$p_{(k)}\le\frac{k}{m}\alpha,\qquad\alpha=0.05$$

If 490 tests were all null and each used p<0.05 alone, about $490\times0.05=24.5$ chance-positive tests would be expected. BH-FDR limits the expected false proportion among reported regional discoveries.

## 26. Complete conditions for a strong regional signal

Rainfall concentration must pass the selected area support, complete-family L5 BH-FDR, direction agreement across the three alternative extreme samples, and leave-one-catchment-out stability. SSI additionally requires direction agreement across all four antecedent windows. The number of checks follows the metric rather than being forced into a fixed “five-gate” label.

## 27. Regional results at the default 50% threshold

| Metric | L5 tests | Complete-family BH-FDR | Strong regional signals | Negative | Positive |
|---|---:|---:|---:|---:|---:|
| Rainfall concentration | 18 | 4 | 4 | 3 | 1 |
| Antecedent SSI (1 day) | 18 | 2 | 2 | 2 | 0 |
| Antecedent SSI (3 days) | 18 | 1 | 1 | 1 | 0 |
| Antecedent SSI (7 days) | 18 | 1 | 1 | 1 | 0 |
| Antecedent SSI (30 days) | 18 | 2 | 2 | 2 | 0 |

![L5 regional trends](assets/figure_04_mechanism_trajectories.png)

## 28. Where the strong regional signals occur

| L5 | Dominant country | Centroid | Metric | Change per 10 years | Area support | Catchments |
|---|---|---:|---|---:|---:|---:|
| HB5-762870 | BR | -24.1°, -51.5° | Antecedent SSI (3 days) | -0.030 | 55.5% | 9 |
| HB5-762870 | BR | -24.1°, -51.5° | Antecedent SSI (1 day) | -0.030 | 55.5% | 9 |
| HB5-762870 | BR | -24.1°, -51.5° | Rainfall concentration | -5.69 | 55.5% | 9 |
| HB5-502710 | FR | 47.1°, 1.1° | Rainfall concentration | -5.40 | 60.0% | 4 |
| HB5-774200 | BR | -24.6°, -53.1° | Antecedent SSI (1 day) | -0.027 | 80.4% | 11 |
| HB5-774200 | BR | -24.6°, -53.1° | Antecedent SSI (7 days) | -0.021 | 80.4% | 11 |
| HB5-757580 | BR | -23.6°, -50.2° | Antecedent SSI (30 days) | -0.018 | 69.1% | 4 |
| HB5-762870 | BR | -24.1°, -51.5° | Antecedent SSI (30 days) | -0.018 | 55.5% | 9 |
| HB5-497340 | FR | 48.0°, 0.0° | Rainfall concentration | -3.26 | 74.1% | 26 |
| HB5-420340 | DE | 50.0°, 7.9° | Rainfall concentration | +2.84 | 70.2% | 43 |

Positive and negative signs respectively mean more concentrated/more distributed rainfall or wetter/drier antecedent conditions. Opposing directions remain, supporting regional heterogeneity rather than one global trend.

## 29. Tracing L5 results back to catchments

![Regional estimates and contributing catchments](assets/figure_06_robustness_matrix.png)

Every regional estimate remains traceable to its contributing catchments. Multi-catchment results show shared within-catchment movement; single-catchment representations explicitly show their area coverage. The two interpretations are kept distinct.

## 30. Hydrological conclusions

1. Most observed catchments do not satisfy the complete robustness conditions for a persistent shift, so change is neither ubiquitous nor spatially uniform.
2. The 378 robust individual trends identify locally meaningful changes: selected large floods become more concentrated in some catchments and more evenly distributed in others, while antecedent conditions become wetter in some places and drier in others.
3. At 50% area support, 6 L5 units show reproducible larger-scale patterns, demonstrating that some local changes are not isolated gauge phenomena.
4. The scientifically useful result is where, in which condition, and in which direction a catchment or L5 changes—not a global mean that cancels opposing signals.

## 31. Limitations

The network is spatially uneven and especially sparse in Asia; daily concentration cannot resolve sub-daily rainfall structure; SSI and event reconstruction contain measurement error; neighbouring L5 units may be dependent; and area support measures hydrological polygon coverage rather than population, assets, or global land representativeness. These trends describe generating conditions, not flood counts, peaks, or runoff volume, and do not alone establish attribution to climate change, land use, or engineering controls.
