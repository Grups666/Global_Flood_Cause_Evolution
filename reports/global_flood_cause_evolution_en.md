# Long-term changes in the generating processes of rainfall-driven large floods (1982–2019)

**Complete technical report | event-scale process classification, gauged-catchment trends and reproducible evidence**

Generated: 2026-09-05

> **Main result.** The experiment first selects each catchment's upper-tail floods by direct stormflow volume, then separates six antecedent-wetness × rainfall-organization processes. Its target is not a single global direction. It identifies gauged catchments where process occurrence, process conditions or associated flood response changed reproducibly.

## 1. Research question and meeting-directed logic

The study asks what happened to the selected large floods and how their generating conditions changed. The 2 September 2026 meeting noted that pooling causes can cancel temporal signals and suggested event grouping. The analysis retains both full-sample continuous trends and grouped results: the former describe overall conditions, while the latter describe composition and within-group changes. Individual gauged catchments remain the analytical units.

### Reading the map: choose a physical quantity before an optional group

Under **Object → Flood-generating conditions**, select **Rainfall concentration** or **Antecedent wetness (SSI)**. Both wetness and rainfall-forcing filters default to **All**, using all valid events in the same Q95 sample.

The two metrics each have **2,497** estimable catchments; **85** rainfall-concentration trends and **87** SSI trends pass the project's complete local screen (p<0.05, alternative-sample direction agreement, and leave-one-year-out direction stability). Each metric requires at least 10 valid event-years and a first-to-last span of at least 20 years inclusive. Years without valid selected events are not filled with zeros.

In the catchment inspector, grey points are annual event means and the blue line is the Theil–Sen fit. Fitted endpoint levels are labelled with their years; they are not the observed values in those years. For illustration, a fitted concentration change from 30% to 40% means that the share of event rainfall falling on its rainiest day rises by 10 percentage points, not that the flood peak rises by 10%.

**Object** determines the metric family. **Antecedent wetness** and **Rainfall forcing** independently filter events; **All** leaves that axis unrestricted. Wet + All pools wet-soil events across both rainfall types; All + Intensity-led pools intensity-led events across all wetness states. Trends are refitted from matching events, not averaged from class slopes. **Flood characteristics** contains volume, daily peak and Q95 frequency. **Flood-generating conditions** contains concentration and SSI, plus Process share when filtered (matching events' share of all Q95 events). A wetness-only filter does not depend on rainfall-class cutoffs, so that stability check is not applied. Events are classified individually; a catchment has no permanent class. A within-group trend is not the full-sample trend, and crossing a class boundary alone is not proof of physical mechanism conversion.

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

The soil saturation index (SSI) is a dimensionless 0–1 model state. The source catalogue's empirical boundaries are approximately SSI ≤0.3994 (dry), 0.3994–0.5640 (moderate) and >0.5640 (wet). Crossing the three states with intensity/volume rainfall organization produces six event processes. These are event labels, not permanent catchment labels.

| Process | Q95 events | Primary-sample share |
|---|---:|---:|
| wet + volume | 25,973 | 44.0% |
| moderate + volume | 15,960 | 27.1% |
| dry + volume | 11,325 | 19.2% |
| wet + intensity | 2,920 | 4.9% |
| moderate + intensity | 1,776 | 3.0% |
| dry + intensity | 1,037 | 1.8% |

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
| 2810 | US | wet + volume | -0.55 events per year per decade |
| 887 | DK | moderate + volume | +0.55 events per year per decade |
| 955 | DK | dry + volume | +0.51 events per year per decade |
| 520 | DE | wet + volume | -0.46 events per year per decade |
| 51 | DE | wet + volume | +0.45 events per year per decade |
| 3813 | BR | wet + volume | +0.44 events per year per decade |
| 682 | DE | dry + volume | -0.43 events per year per decade |
| 648 | AU | moderate + volume | -0.43 events per year per decade |

## 12. Process composition

Process share asks whether a process occupied a larger or smaller fraction of a catchment's selected floods. Frequency and share are complementary: a share can rise because that process increased or because competing processes declined.

![Changes in process share](assets/figure_04_process_share_changes.png)

| Catchment | Country | Generating process | Q95-sample share trend |
|---|---|---|---:|
| 1076 | FR | moderate + volume | +27.35 percentage points per decade |
| 3587 | AU | wet + volume | -23.87 percentage points per decade |
| 548 | AU | wet + volume | +23.13 percentage points per decade |
| 1216 | FR | moderate + volume | -22.82 percentage points per decade |
| 1216 | FR | dry + volume | +22.82 percentage points per decade |
| 703 | AU | moderate + intensity | +22.54 percentage points per decade |
| 703 | AU | moderate + volume | -22.54 percentage points per decade |
| 1734 | AU | moderate + volume | -21.90 percentage points per decade |

## 13. Complete process-specific evidence counts

| Outcome | Estimates | p<0.05 | Complete screen | Decrease | Increase |
|---|---:|---:|---:|---:|---:|
| annual process frequency | 3,562 | 337 | 132 | 93 | 39 |
| process share among selected floods | 2,102 | 47 | 19 | 13 | 6 |
| event direct stormflow volume | 3,409 | 155 | 63 | 29 | 34 |
| event daily flood peak | 3,409 | 170 | 90 | 54 | 36 |
| within-process rainfall concentration | 3,409 | 162 | 102 | 69 | 33 |
| within-process antecedent wetness | 3,409 | 186 | 117 | 46 | 71 |

## 14. Process-specific flood response

Direct stormflow volume and daily flood peak are estimated within each process. This asks whether floods generated by the *same process* became larger or smaller.

![Strongest supported process-specific response changes](assets/figure_05_process_response_rankings.png)

## 15. Within-process generating conditions

Rainfall concentration indicates whether rainfall became further concentrated within a process. SSI indicates whether antecedent conditions shifted even while events remained in the same broad wetness class. Continuous indicators and categorical process labels therefore serve different purposes.

| Catchment | Country | Generating process | Rainfall-concentration trend |
|---|---|---|---:|
| 3060 | US | wet + volume | -18.28 percentage points per decade |
| 2981 | US | wet + volume | +14.46 percentage points per decade |
| 1311 | FR | wet + volume | -13.17 percentage points per decade |
| 896 | DK | dry + volume | +13.02 percentage points per decade |
| 3332 | ZA | dry + volume | -11.68 percentage points per decade |
| 3181 | US | moderate + volume | -11.61 percentage points per decade |

| Catchment | Country | Generating process | Antecedent-wetness trend |
|---|---|---|---:|
| 2791 | US | wet + volume | +0.06 SSI units per decade |
| 3145 | US | moderate + volume | +0.06 SSI units per decade |
| 3118 | US | moderate + volume | -0.05 SSI units per decade |
| 3756 | BR | wet + volume | -0.05 SSI units per decade |
| 2953 | US | wet + volume | -0.05 SSI units per decade |
| 3761 | BR | wet + volume | -0.04 SSI units per decade |

## 16. Worked trajectories

![Observed annual process shares and fitted trajectories](assets/figure_06_example_process_trajectories.png)

1. **GCIN 2771 (US), moderate + volume.** The event direct stormflow volume trend is -39.72 mm per decade; the fitted record endpoints are 110.71 → 0.00. This is a within-catchment temporal result, not proof of causation.

2. **GCIN 2677 (US), moderate + volume.** The event daily flood peak trend is -18.21 mm/day per decade; the fitted record endpoints are 83.13 → 23.02. This is a within-catchment temporal result, not proof of causation.

3. **GCIN 3756 (BR), wet + volume.** The event daily flood peak trend is -15.10 mm/day per decade; the fitted record endpoints are 60.93 → 11.11. This is a within-catchment temporal result, not proof of causation.

4. **GCIN 348 (AU), moderate + volume.** The event direct stormflow volume trend is +22.07 mm per decade; the fitted record endpoints are 1.93 → 61.52. This is a within-catchment temporal result, not proof of causation.

## 17. Geographic context

The table counts supported observed points. It is not an area-weighted continental trend.

- Q95-event frequency — Africa: 6 (0 decreases, 6 increases); Europe: 83 (49 decreases, 34 increases); North America: 30 (24 decreases, 6 increases); Oceania: 21 (18 decreases, 3 increases); South America: 24 (18 decreases, 6 increases).
- Process frequency — Africa: 2 (0 decreases, 2 increases); Europe: 66 (43 decreases, 23 increases); North America: 26 (22 decreases, 4 increases); Oceania: 22 (20 decreases, 2 increases); South America: 16 (8 decreases, 8 increases).
- Within-process rainfall concentration — Africa: 7 (6 decreases, 1 increases); Europe: 67 (49 decreases, 18 increases); North America: 14 (5 decreases, 9 increases); Oceania: 7 (3 decreases, 4 increases); South America: 7 (6 decreases, 1 increases).
- Within-process antecedent wetness — Africa: 3 (1 decreases, 2 increases); Europe: 73 (16 decreases, 57 increases); North America: 18 (10 decreases, 8 increases); Oceania: 15 (13 decreases, 2 increases); South America: 8 (6 decreases, 2 increases).

| Continent | Supported process-frequency results | Decrease | Increase |
|---|---:|---:|---:|
| Africa | 2 | 0 | 2 |
| Europe | 66 | 43 | 23 |
| North America | 26 | 22 | 4 |
| Oceania | 22 | 20 | 2 |
| South America | 16 | 8 | 8 |

## 18. Sensitivity and event independence

Supported directions must agree with the applicable Q90, Q97.5 and annual-maximum samples. The primary sample has **0 overlapping reconstructed stormflow windows**, confirming that the event catalogue has already separated overlapping runoff responses.

## 19. Limitations

SSI is model-derived; classification thresholds compress continuous variation; gauge coverage is densest in Europe and North America; 38 years cannot resolve every multidecadal oscillation; trend coincidence is not causal attribution; and land-use, regulation or measurement changes may contribute to local results.

## 20. Hydrological conclusions

1. Across all selected floods, **46**, **54** and **164** catchments pass the complete screen for direct stormflow volume, daily peak and Q95-event frequency, respectively. Flood change is therefore a local result, not one global sign.
2. Process frequency has **132** supported catchment–process results: **93** decreases and **39** increases. Separating mechanisms exposes locally opposing replacements that a pooled trend would hide.
3. Process share has **19** supported results. These directly identify persistent changes in the composition of a catchment's Q95 floods and are central evidence for changing flood-generation pathways.
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
