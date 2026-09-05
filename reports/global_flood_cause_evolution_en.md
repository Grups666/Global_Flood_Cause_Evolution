# Long-term changes in the generating processes of rainfall-driven large floods (1982–2019)

**Complete technical report | event-scale process classification, gauged-catchment trends and reproducible evidence**

Generated: 2026-09-05

> **Main result.** The experiment first selects each catchment's upper-tail floods by direct stormflow volume, then separates six antecedent-wetness × rainfall-organization processes. Its target is not a single global direction. It identifies gauged catchments where process occurrence, process conditions or associated flood response changed reproducibly.

## 1. Research question and meeting-directed logic

The study asks what happened to the selected large floods and how their generating conditions changed. The 2 September 2026 meeting noted that pooling causes can cancel temporal signals and suggested event grouping. The analysis retains both full-sample continuous trends and grouped results: the former describe overall conditions, while the latter describe composition and within-group changes. Individual gauged catchments remain the analytical units.

### Reading the map: choose a physical quantity before an optional group

Under **Object → Flood-generating conditions**, select **Rainfall concentration** or **Antecedent wetness (SSI)**. Both wetness and rainfall-forcing filters default to **All**, using all valid events in the same Q95 sample.

The two metrics each have **2,497** estimable catchments; **85** rainfall-concentration trends and **89** SSI trends pass the project's complete local screen (p<0.05, alternative-sample direction agreement, and leave-one-year-out direction stability). Each metric requires at least 10 valid event-years and a first-to-last span of at least 20 years inclusive. Years without valid selected events are not filled with zeros.

In the catchment inspector, grey points are annual event means and the blue line is the Theil–Sen fit. Fitted endpoint levels are labelled with their years; they are not the observed values in those years. For illustration, a fitted concentration change from 30% to 40% means that the share of event rainfall falling on its rainiest day rises by 10 percentage points, not that the flood peak rises by 10%.

**Object** determines the metric family. **Antecedent wetness** and **Rainfall forcing** independently filter events; **All** leaves that axis unrestricted. Wet + All pools wet-soil events across both rainfall types; All + Intensity-led pools intensity-led events across all antecedent states, including events with missing SSI but known rainfall class. Trends are refitted from matching events, not averaged from class slopes. **Flood characteristics** contains volume, daily peak and Q95 frequency. **Flood-generating conditions** contains concentration and SSI, plus Process share when filtered (matching events' share of Q95 events with the required classification observed). A wetness-only filter does not depend on rainfall-class cutoffs, so that stability check is not applied. Events are classified individually; a catchment has no permanent class. A within-group trend is not the full-sample trend, and crossing a class boundary alone is not proof of physical mechanism conversion.

## 2. Data boundary

- Verified common period: 1982–2019.
- Rainfall-driven events in catchments with snow fraction <0.10.
- At least 30 event years, a 30-year span and 80% record coverage.
- Primary sample: **58,991 Q95 events in 2,637 gauged catchments**.
- Mapped points are observations, not area-complete global coverage.

![Primary sample and six-process composition](assets/figure_01_sample_and_process_coverage.png)

## 3. Definition of Q95

Q95 is calculated from event direct stormflow volume, not precipitation and not daily peak flow:

$$u_i=\operatorname{quantile}_{0.95}\{Q^{vol}_{ie}\},\qquad Q^{vol}_{ie}\ge u_i.$$

If a catchment has 400 reconstructed events, approximately the 20 largest event volumes enter the primary sample. The threshold is fixed over the full record. Q90, Q97.5 and annual-maximum event volume are sensitivity samples.

## 4. The selected floods themselves

The analysis first estimates trends in direct stormflow volume, daily event peak and annual Q95-event frequency. This prevents a driver trend from being discussed without showing the corresponding flood response.

![Changes in the selected large floods](assets/figure_02_overall_flood_changes.png)

| Outcome | Estimates | p<0.05 | Complete screen | Decrease | Increase |
|---|---:|---:|---:|---:|---:|
| event direct stormflow volume | 2,497 | 123 | 46 | 24 | 22 |
| event daily flood peak | 2,497 | 141 | 54 | 31 | 23 |
| annual Q95-event frequency | 2,637 | 250 | 164 | 109 | 55 |

## 5. Rainfall temporal organization

For daily event rainfall \(P_d\),

$$C=\frac{\max_d(P_d)}{\sum_dP_d},\qquad CV_t=\frac{sd(P_d)}{mean(P_d)}.$$

If 42 mm falls on the rainiest day and 70 mm over the event, \(C=0.60\): 60% of event rainfall fell in one day. Following Tarasova et al. (2020), an event is intensity-dominated only when \(C>0.50\) **and** \(CV_t>1\); otherwise it is volume-dominated. The continuous concentration value is retained for trend estimation.

## 6. Antecedent wetness and the six processes

The soil saturation index (SSI) is a normalized 0–1 soil-wetness indicator, not a water depth in millimetres. This study uses **daily SSI on the day before rainfall begins**:

$$SSI_e=SSI_i(t_{\mathrm{rain,start},e}-1\ \mathrm{day}).$$

If rainfall starts on 10 June, use SSI on 9 June—not rainfall-start-day SSI or the day before the flood peak.

Cutoffs are recalibrated from the **2,637 included catchments**: pool all **35,918,563 valid catchment-day SSI values** throughout 1982–2019, including non-flood days, giving each valid catchment-day equal weight. Missing dates are not filled with zero. The pooled 1/3 and 2/3 quantiles are **0.404690** and **0.576339**.

$$q_L=Q_{1/3}(SSI_{\mathrm{all\ valid\ days}}),\quad q_U=Q_{2/3}(SSI_{\mathrm{all\ valid\ days}}).$$

Dry means SSI ≤ 0.404690; Moderate means 0.404690 < SSI ≤ 0.576339; Wet means SSI > 0.576339. SSI values of 0.30, 0.50 and 0.70 illustrate the three groups. These are relative wetness groups for this observational network, not universal saturation thresholds. Continuous SSI is retained. The same cutoffs apply to every year and to Q90, Q97.5 and annual-maximum samples.

**7 selected events** lack previous-day SSI because their rainfall starts on 1 January 1982. They remain in flood and rainfall analyses but receive no wetness class. Six-process composition therefore uses **58,984 classifiable events**. Wetness-group shares likewise use events with the required classification observed; wetness-group frequency excludes catchment-years containing an unclassifiable selected event rather than treating unknown membership as zero.

**Wetness-cutoff sensitivity.** with 25%/75% quantiles, 907 of 1038 primary-screen-supported wetness-dependent group trends remain estimable and 894 retain their direction; with 40%/60% quantiles, 991 of 1038 primary-screen-supported wetness-dependent group trends remain estimable and 980 retain their direction. These counts include overlapping one-axis and joint filters; they count trend estimates, not independent catchments.

**Antecedent-window sensitivity.** Replacing the previous-day value with the mean over complete days preceding rainfall: the 3-day window retains the direction in 89 of 89 supported primary SSI catchments (89 estimable); the 7-day window retains the direction in 89 of 89 supported primary SSI catchments (89 estimable); the 30-day window retains the direction in 85 of 89 supported primary SSI catchments (89 estimable). These diagnostics describe sensitivity, not additional support gates; direction agreement does not imply identical magnitudes or significance.

Crossing the three wetness states with intensity/volume rainfall organization produces six event processes. These are event labels, not permanent catchment labels.

| Process | Q95 events | Share of classifiable primary events |
|---|---:|---:|
| wet + volume | 21,704 | 36.8% |
| moderate + volume | 18,491 | 31.3% |
| dry + volume | 13,057 | 22.1% |
| wet + intensity | 2,528 | 4.3% |
| moderate + intensity | 1,936 | 3.3% |
| dry + intensity | 1,268 | 2.1% |

## 7. Why five process events

Tarasova et al. (2023) used at least five events of a process as an explicit compromise between trend robustness and data availability. This experiment uses that one hard minimum; it has no 5–19 versus ≥20 evidence tiers.

## 8. Catchment-year annualization

For a continuous variable, multiple selected events in a catchment-year are averaged:

$$\bar y_{it}=\frac{1}{n_{it}}\sum_e y_{iet}.$$

For volumes 20, 35 and 50 mm in 2004, the annual value is 35 mm. The year therefore contributes one temporal observation. Frequency retains event counts and includes zeros in observed years without the relevant process.

## 9. Trend estimation and physical units

Continuous physical outcomes use the Theil–Sen slope,

$$\hat\beta=\operatorname{median}_{j>k}\frac{y_j-y_k}{t_j-t_k},$$

with a tie-corrected Mann–Kendall test, whose ordering statistic is

$$S=\sum_{j>k}\operatorname{sign}(y_j-y_k).$$

The two-sided p value tests the null hypothesis of no monotonic trend. Annual slopes are multiplied by ten, so *per decade* always means **per 10 years**.

Annual event counts use a Poisson trend,

$$N_t\sim\operatorname{Poisson}(\mu_t),\qquad \log\mu_t=a+b(t-2000)/10,$$

and are converted back to an absolute fitted-frequency change. A rise from 0.4 to 0.7 events/year over 30 years is \((0.7-0.4)/3=+0.10\) events/year per 10 years. This remains informative when a sparse count series would have a zero median pairwise slope.

Process shares use a bias-reduced binomial time trend,

$$s_t\sim\operatorname{Binomial}(n_t,\pi_t),\qquad \operatorname{logit}(\pi_t)=a+b(t-2000)/10.$$

A fitted change from 18% to 26% over 20 years is \((26-18)/2=+4\) percentage points per decade.

For positive-valued variables, the report also gives a secondary relative effect \(r=100\hat\beta/\bar y\), without fitting a logarithmic model. If SSI changes by +0.009 per 10 years around a catchment–process mean of 0.45, the relative effect is \(100(0.009/0.45)=+2.0\%\) of the mean per 10 years. The absolute physical unit remains primary.

## 10. Evidence screen and p values

Each catchment–outcome combination reports a two-sided \(p\) value. A supported result requires \(p<0.05\) and additionally retains its direction under Q90, Q97.5 and annual maxima, rainfall-concentration cutoffs 0.40 and 0.60, and every leave-one-year-out refit.

## 11. Process frequency

Annual process frequency asks whether a given process produced Q95 floods more or less often.

![Changes in annual process frequency](assets/figure_03_process_frequency_changes.png)

The largest supported absolute changes are listed below. A plus sign means that the process produced Q95 floods more often; a minus sign means less often.

| Catchment | Country | Generating process | Annual-frequency trend |
|---|---|---|---:|
| 3968 | AU | moderate + volume | -0.58 events per year per decade |
| 2810 | US | wet + volume | -0.55 events per year per decade |
| 1325 | FR | moderate + volume | -0.51 events per year per decade |
| 955 | DK | dry + volume | +0.51 events per year per decade |
| 51 | DE | wet + volume | +0.47 events per year per decade |
| 603 | AU | moderate + volume | -0.46 events per year per decade |
| 520 | DE | wet + volume | -0.46 events per year per decade |
| 682 | DE | dry + volume | -0.43 events per year per decade |

## 12. Process composition

Process share asks whether a process occupied a larger or smaller fraction of a catchment's selected floods. Frequency and share are complementary: a share can rise because that process increased or because competing processes declined.

![Changes in process share](assets/figure_04_process_share_changes.png)

| Catchment | Country | Generating process | Q95-sample share trend |
|---|---|---|---:|
| 537 | AU | dry + volume | +24.55 percentage points per decade |
| 3353 | ZA | moderate + volume | -24.44 percentage points per decade |
| 1383 | FR | wet + volume | +23.65 percentage points per decade |
| 2878 | US | wet + volume | -23.08 percentage points per decade |
| 3415 | ZA | wet + volume | -23.04 percentage points per decade |
| 703 | AU | moderate + volume | -22.54 percentage points per decade |
| 3353 | ZA | dry + volume | +22.45 percentage points per decade |
| 1606 | FR | moderate + volume | -20.49 percentage points per decade |

## 13. Complete process-specific evidence counts

| Outcome | Estimates | p<0.05 | Complete screen | Decrease | Increase |
|---|---:|---:|---:|---:|---:|
| annual process frequency | 3,652 | 363 | 135 | 87 | 48 |
| process share among selected floods | 2,272 | 54 | 15 | 6 | 9 |
| event direct stormflow volume | 3,491 | 144 | 51 | 24 | 27 |
| event daily flood peak | 3,491 | 171 | 89 | 58 | 31 |
| within-process rainfall concentration | 3,491 | 168 | 110 | 73 | 37 |
| within-process antecedent wetness | 3,491 | 191 | 119 | 54 | 65 |

## 14. Process-specific flood response

Direct stormflow volume and daily flood peak are estimated within each process. This asks whether floods generated by the *same process* became larger or smaller.

![Strongest supported process-specific response changes](assets/figure_05_process_response_rankings.png)

## 15. Within-process generating conditions

Rainfall concentration indicates whether rainfall became further concentrated within a process. SSI indicates whether antecedent conditions shifted even while events remained in the same broad wetness class. Continuous indicators and categorical process labels therefore serve different purposes.

| Catchment | Country | Generating process | Rainfall-concentration trend |
|---|---|---|---:|
| 2981 | US | wet + volume | +14.46 percentage points per decade |
| 2571 | US | wet + volume | -14.18 percentage points per decade |
| 896 | DK | dry + volume | +13.02 percentage points per decade |
| 1212 | FR | wet + volume | -12.37 percentage points per decade |
| 3332 | ZA | dry + volume | -12.32 percentage points per decade |
| 600 | DE | moderate + volume | -11.88 percentage points per decade |

| Catchment | Country | Generating process | Antecedent-wetness trend |
|---|---|---|---:|
| 2953 | US | wet + volume | -0.07 SSI units per decade |
| 3757 | BR | wet + volume | -0.06 SSI units per decade |
| 2956 | US | wet + volume | -0.06 SSI units per decade |
| 2952 | US | wet + volume | -0.06 SSI units per decade |
| 1431 | FR | wet + volume | +0.06 SSI units per decade |
| 2936 | US | wet + volume | -0.05 SSI units per decade |

## 16. Worked trajectories

![Observed annual process shares and fitted trajectories](assets/figure_06_example_process_trajectories.png)

1. **GCIN 2677 (US), moderate + volume.** The event daily flood peak trend is -18.21 mm/day per decade; the fitted record endpoints are 83.13 → 23.02. This is a within-catchment temporal result, not proof of causation.

2. **GCIN 3329 (ZA), dry + volume.** The event daily flood peak trend is -8.09 mm/day per decade; the fitted record endpoints are 26.47 → 3.82. This is a within-catchment temporal result, not proof of causation.

3. **GCIN 3085 (US), wet + volume.** The event daily flood peak trend is +8.08 mm/day per decade; the fitted record endpoints are 15.97 → 40.21. This is a within-catchment temporal result, not proof of causation.

4. **GCIN 2566 (US), wet + volume.** The event daily flood peak trend is +7.81 mm/day per decade; the fitted record endpoints are 28.50 → 50.38. This is a within-catchment temporal result, not proof of causation.

## 17. Geographic context

The table counts supported observed points. It is not an area-weighted continental trend.

- Q95-event frequency — Africa: 6 (0 decreases, 6 increases); Europe: 83 (49 decreases, 34 increases); North America: 30 (24 decreases, 6 increases); Oceania: 21 (18 decreases, 3 increases); South America: 24 (18 decreases, 6 increases).
- Process frequency — Africa: 3 (0 decreases, 3 increases); Europe: 80 (45 decreases, 35 increases); North America: 26 (20 decreases, 6 increases); Oceania: 14 (14 decreases, 0 increases); South America: 12 (8 decreases, 4 increases).
- Within-process rainfall concentration — Africa: 8 (7 decreases, 1 increases); Europe: 76 (53 decreases, 23 increases); North America: 14 (4 decreases, 10 increases); Oceania: 6 (3 decreases, 3 increases); South America: 6 (6 decreases, 0 increases).
- Within-process antecedent wetness — Africa: 5 (3 decreases, 2 increases); Europe: 82 (26 decreases, 56 increases); North America: 22 (16 decreases, 6 increases); Oceania: 1 (1 decreases, 0 increases); South America: 9 (8 decreases, 1 increases).

| Continent | Supported process-frequency results | Decrease | Increase |
|---|---:|---:|---:|
| Africa | 3 | 0 | 3 |
| Europe | 80 | 45 | 35 |
| North America | 26 | 20 | 6 |
| Oceania | 14 | 14 | 0 |
| South America | 12 | 8 | 4 |

## 18. Sensitivity and event independence

Supported directions must agree with the applicable Q90, Q97.5 and annual-maximum samples. The primary sample has **0 overlapping reconstructed stormflow windows**, confirming that the event catalogue has already separated overlapping runoff responses.

## 19. Limitations

SSI has soil-moisture-product and normalization uncertainty; classification thresholds compress continuous variation, with cutoff sensitivity reported in the wetness section; gauge coverage is densest in Europe and North America; 38 years cannot resolve every multidecadal oscillation; trend coincidence is not causal attribution; and land-use, regulation or measurement changes may contribute to local results.

## 20. Hydrological conclusions

1. Across all selected floods, **46**, **54** and **164** catchments pass the complete screen for direct stormflow volume, daily peak and Q95-event frequency, respectively. Flood change is therefore a local result, not one global sign.
2. Process frequency has **135** supported catchment–process results: **87** decreases and **48** increases. Separating mechanisms exposes locally opposing replacements that a pooled trend would hide.
3. Process share has **15** supported results. These directly identify persistent changes in the composition of a catchment's Q95 floods and are central evidence for changing flood-generation pathways.
4. Rainfall concentration, antecedent SSI, direct stormflow volume and daily peak also retain reproducible within-process changes. Occurrence, generating conditions and flood response should be interpreted together; temporal co-change alone is not causal attribution.

## 21. Reproducibility

- [Analysis protocol](../docs/methods/analysis_protocol.md)
- [Data dictionary](../docs/methods/data_dictionary.md)
- [Literature review](../docs/background/literature_review.md)
- Entry point: `python src/run_pipeline.py --stage all --force`

## 22. Core references

- Stein, Pianosi & Woods (2020), <https://doi.org/10.1002/hyp.13678>
- Stein et al. (2021), <https://doi.org/10.1029/2020WR028300>
- Tarasova et al. (2019), <https://doi.org/10.1002/wat2.1353>
- Tarasova et al. (2020), <https://doi.org/10.1029/2019WR026951>
- Tarasova, Basso & Merz (2020), <https://doi.org/10.1029/2020GL090547>
- Tarasova et al. (2023), <https://doi.org/10.1038/s43247-023-00714-8>
