# Long-Term Changes in Rainfall-Driven Large-Flood Generating Conditions (1982–2019)

**Technical report · generated 2026-09-01**

## Technical summary

- Evidence is constructed in two stages: direct trends are estimated for every eligible catchment, and **HydroBASINS level 5** (hereafter **L5**) is then used to test whether nearby catchments form a larger coherent pattern. HydroBASINS is a globally consistent, hierarchically nested set of sub-basin boundaries organized by drainage-network topology; L5 denotes its fifth spatial level, not an administrative region or an individual gauge catchment.
- The primary sample contains **59,048 POT/Q95 floods in 2,624 long-record low-snow catchments**. At least one primary direct trend is estimable in **2,435 catchments**.
- The five continuous outcomes produce **12,163 catchment–metric tests** (the complete grid is 2,435 × 5 = 12,175; the 7-day and 30-day SSI outcomes lack 2 and 10 combinations, respectively, because valid event years or time span are insufficient, and missing combinations are not coded as zero). There are **378 directionally stable candidates**, but **no direct catchment signal passes metric-wise 5% Benjamini–Hochberg false discovery rate (BH-FDR) control**. The strict result is therefore that most catchments do not show a network-confirmed long-term shift; candidates identify locations for targeted follow-up.
- Among 1,475 L5–metric tests, **106 pass complete-family BH-FDR and 94 pass the full statistical robustness screen**. With the default **≥10% area support**, **84 strong regional signals remain in 36 L5 units**.
- Area support constrains only the regional interpretation. The explorer switches dynamically among 10%, 20%, 30%, 40%, and 50%, while all estimable catchment results remain available.

![Sample coverage](assets/figure_01_sample_coverage.png)

The map defines the observational domain. Europe and North America are much denser than Asia, so “global” means a globally distributed gauge sample rather than an area-weighted global land population.

## 1. Scientific question

The study asks whether the **conditions accompanying large rainfall-driven floods** changed through time: whether event rainfall became more concentrated or more prolonged, and whether the catchment before rainfall became wetter or drier.

## 2. Evidence order

The workflow is catchment-first:

1. construct an extreme-event sample separately in every eligible catchment;
2. estimate a continuous-time trend inside that catchment;
3. retain nulls, weak estimates, and stable candidates;
4. pool catchments whose outlets fall in the same HydroBASINS L5;
5. use polygon-area coverage to determine whether that pooled estimate has enough spatial support for an L5 interpretation.

## 3. Verified period

The common verified overlap of the flood-event catalogue, daily rainfall/runoff data, and GLASS-AVHRR soil moisture is **1982–2019**. Trends use the continuous record without a calendar breakpoint.

## 4. Catchment population

Catchments require long-term snow fraction below 0.10, both seasonal event catalogues, at least 30 observed event years, at least a 30-year record span, and at least 80% annual coverage. **2,839 catchments** pass this record screen.

## 5. Event selection is separate from condition description

Flood peak selects the extreme-event sample. Rainfall concentration and antecedent wetness are calculated only after selection, avoiding a circular definition in which the outcome also determines inclusion.

## 6. Primary population: catchment-specific POT/Q95

For catchment $i$, the retained events are:

$$
\mathcal E_i^{95}=\{e:Q_{ie}\ge Q_{0.95,i}\}.
$$

Each catchment requires at least 10 selected events spanning at least 20 years. The final primary sample contains **59,048 events in 2,624 catchments**.

**Example.** If a catchment has 100 reconstructed floods and its 95th-percentile peak is 120 mm/day, only upper-tail events at or above 120 mm/day are retained—typically about five. POT may retain more than one genuinely extreme event in a year; Section 12 then averages events within that year so it does not receive extra trend weight.

## 7. Why annual maxima are a sensitivity population

Annual maxima force one event into every year, even when that event is not particularly extreme relative to the catchment record. POT/Q95 directly targets the catchment upper tail, while annual maxima remain an important alternative definition.

## 8. Extreme-event sensitivities

The four alternatives change one setting at a time: POT/Q90 and POT/Q97.5 change only the extreme threshold, 10-day-declustered POT/Q95 changes only event separation, and annual maxima change the event-selection rule. Q95 is not uniquely in need of declustering; the Q95 branch isolates declustering sensitivity around the primary sample, and the present experiment does not fully cross threshold and declustering choices. The primary sample contains 2,194 adjacent peak pairs under 10 days; the declustered sample contains 0. Primary-sample stormflow-window overlaps equal 0.

## 9. Rainfall concentration

$$
C_{ie}=\frac{P_{\max,ie}}{P_{\mathrm{volume},ie}}.
$$

An increase means a larger share of event rainfall fell in the wettest day; a decrease means movement toward longer, volume-dominated rainfall. The continuous ratio is the inferential outcome; no binary intensity-dominated label is used.

**Example.** If total event rainfall is 80 mm and 48 mm falls on the rainiest day, then $C=48/80=0.60$: 60% of the event rainfall fell in one day. A trend of +8.83 percentage points per decade could move a fitted concentration level from 38.00% to 46.83% over ten years. It is not an 8.83% increase in flood count and not an 8.83 mm increase in daily rainfall.

## 10. Antecedent wetness

$$
SSI_{ie}^{(w)}=\frac1w\sum_{k=1}^w SSI_{i,t_{0,ie}-k},
\qquad w\in\{1,3,7,30\}.
$$

Positive slopes mean large floods occurred after increasingly wet antecedent states; negative slopes mean increasingly dry states. SSI units are normalized index units, not millimetres or flood percentages.

**Example.** If SSI on the three complete days before rainfall onset is 0.32, 0.46, and 0.52, then $SSI^{(3)}=(0.32+0.46+0.52)/3=0.433$. A 3-day SSI trend of $-0.010$ per decade means the mean antecedent state before selected large floods declined by 0.010 index units every ten years.

## 11. Physical rainfall components

Maximum daily rainfall, event rainfall total, and precipitation duration are fitted in raw physical units. Their secondary relative slopes are:

$$
r=100\frac{\widehat\beta}{\bar y}.
$$

No logarithmic trend model is used. These components aid interpretation of the concentration ratio without claiming causal attribution.

**Example.** If mean total event rainfall is 100 mm and its linear trend is +8 mm per decade, then the relative trend is $100\times8/100=8\%$ per decade. The physical result remains +8 mm per decade; 8% is only a secondary scale for comparing variables or regions with different means.

## 12. Catchment-year annualization

Multiple POT events in one catchment-year are averaged:

$$
\bar y_{it}=\frac1{n_{it}}\sum_e y_{iet}.
$$

This prevents a year with several reconstructed events from receiving extra trend weight solely because of event count.

**Example.** If one catchment has three selected floods in 2005 with concentrations of 40%, 55%, and 65%, the 2005 value used in the trend is $(40+55+65)/3=53.3\%$. The year is not entered three times. If 2006 has one event, 2005 and 2006 each contribute one annual value.

## 13. Direct catchment trend

The annual sequence uses a Theil–Sen slope:

$$
\widehat\beta_i=\operatorname{median}_{t_j>t_k}
\frac{\bar y_{it_j}-\bar y_{it_k}}{t_j-t_k}\times10,
$$

with a tie-corrected Mann–Kendall test. At least 10 event years spanning at least 20 years are required.

**Example.** If one pair of annual values rises from 0.40 in 1990 to 0.52 in 2010, that pair gives $(0.52-0.40)/(2010-1990)\times10=0.06$ per decade, or +6 concentration percentage points per decade. Theil–Sen calculates this slope for every year-pair and takes the median, so one unusual year has limited leverage.

## 14. Why direct catchment results still require network-wide multiplicity control

Every catchment–metric pair first receives its own Mann–Kendall p value. A p value could be interpreted directly if the study had prespecified only one catchment. This study instead scans about 2,435 catchments and asks whether any location shows a trend. Even when no catchment has a real trend, thousands of simultaneous tests will generate some $p<0.05$ values by chance.

Each physical metric therefore uses the **Benjamini–Hochberg false discovery rate procedure (BH-FDR)** across all estimable catchments. The family is not “the five metrics inside one catchment.” It is “one metric across the full catchment network”: rainfall concentration, 1-day SSI, and 3-day SSI each contain 2,435 tests; 7-day SSI contains 2,433; and 30-day SSI contains 2,425.

Ordering the $m$ p values for one metric, BH-FDR finds the largest $k$ satisfying:

$$
p_{(k)}\le\frac{k}{m}\alpha,
\qquad \alpha=0.05.
$$

BH-FDR controls the expected proportion of false discoveries among the catchments labelled as discoveries. It does not alter a catchment slope; it determines whether a location can be called confirmed after searching the network.

**Observed example.** Rainfall concentration has 2,435 direct catchment tests. If every null hypothesis were true, using $p<0.05$ alone would still produce about $2435\times0.05=121.75$ chance results on average; 154 unadjusted $p<0.05$ results are observed. The first BH-FDR cutoff is $0.05/2435=0.0000205$, while the smallest observed p value is 0.000367, so none passes 5% BH-FDR. The other four metrics also have zero BH-FDR discoveries.

Zero discoveries do not make BH-FDR unnecessary. They mean that the current records cannot promote any direct catchment trend to a network-confirmed discovery after a global search. Raw slopes, p values, and the 378 directionally stable sensitivity candidates remain available for follow-up; candidates and BH-FDR discoveries represent different evidence grades.

## 15. Stable local candidate

A candidate requires unadjusted $p<0.05$, sign agreement at POT/Q90 and POT/Q97.5, agreement after 10-day declustering, agreement under annual maxima, and leave-one-event-year-out sign stability. SSI candidates also require all four windows to agree. This is an exploratory evidence grade, not a BH-FDR-confirmed shift.

![Direct catchment results](assets/figure_02_mechanism_change_maps.png)

Light marks retain all estimable trends; outlined marks identify stable candidates. Color encodes effect direction and magnitude, not statistical significance.

## 16. Direct catchment results

| Metric | Estimable catchments | Unadjusted p<0.05 | Stable candidates | Across-catchment BH-FDR | Negative candidates | Positive candidates |
|---|---:|---:|---:|---:|---:|---:|
| Rainfall concentration | 2,435 | 154 | 73 | 0 | 39 | 34 |
| Antecedent SSI (1 day) | 2,435 | 184 | 78 | 0 | 48 | 30 |
| Antecedent SSI (3 days) | 2,435 | 181 | 77 | 0 | 49 | 28 |
| Antecedent SSI (7 days) | 2,433 | 164 | 81 | 0 | 48 | 33 |
| Antecedent SSI (30 days) | 2,425 | 163 | 69 | 0 | 32 | 37 |

## 17. Direct catchment conclusion

There are **378 stable candidates in opposing directions and zero across-catchment BH-FDR discoveries**. The evidence therefore supports sparse candidate locations within a predominantly non-confirmed network, not ubiquitous long-term change.

![Catchment evidence funnel](assets/figure_03_strong_signal_rankings.png)

The evidence funnel keeps unadjusted significance, sensitivity stability, and multiplicity control distinct.

## 18. HydroBASINS level 5 (L5) is a second-stage spatial question

[HydroBASINS](https://www.hydrosheds.org/products/hydrobasins) is a global polygon dataset of sub-basin boundaries derived from HydroSHEDS. River-network topology and Pfafstetter codes organize the polygons into **12 hierarchically nested levels**; higher levels generally provide finer subdivisions. This study uses level 5 from the standard HydroBASINS v1.c product and refers to each level-5 polygon as an **L5 hydrological region**. These are drainage-based units, not national or subnational administrative boundaries.

The first-stage analytical unit remains the **individual observed catchment**: trends in rainfall concentration and antecedent wetness are estimated separately for each catchment. L5 enters only as a common regional container in the second stage. Catchments are assigned by outlet location, after which the analysis asks whether their local changes have enough polygon-area support and a sufficiently coherent direction to represent a broader hydrological pattern.

**Example.** A 700 km² observed catchment may occupy only part of a larger L5 region. Its direct trend answers, “Did this catchment change?” The pooled result from observed catchments in the same L5 answers, “May this change extend across a larger connected hydrological region?” The L5 result therefore neither replaces the direct catchment result nor determines whether that result is retained.

## 19. Catchment-to-L5 membership

Catchment outlets are spatially joined to HydroBASINS v1.c level 5. **2,622 catchments** match; two Mauritius catchments remain unmatched in the reference geometry but retain direct results.

## 20. L5 area support

For L5 polygon $H_j$ and eligible catchment polygons $A_i$ assigned by their outlets:

$$
Coverage_j=
\frac{Area\left(H_j\cap\bigcup_{i\in j}A_i\right)}{Area(H_j)}.
$$

Areas use equal-area EPSG:6933. Invalid polygons are repaired, and overlapping catchments are counted once through a geometric union.

**Example.** If an L5 polygon covers 10,000 km² and the non-overlapping union of eligible catchment polygons inside it covers 2,400 km², its area support is 24%. It passes the 10% and 20% settings but not 30%, 40%, or 50%.

## 21. Dynamic threshold sensitivity

| L5 area threshold | Spatially supported L5 | L5 with trend estimates | Catchments inside passing L5 | Global catchment share | US catchment share | Strong regional signals | L5 with strong signals |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% | 156 | 152 | 2,139 | 81.6% | 63.6% | 84 | 36 |
| 20% | 85 | 82 | 1,287 | 49.1% | 34.1% | 42 | 22 |
| 30% | 50 | 48 | 660 | 25.2% | 20.1% | 28 | 16 |
| 40% | 34 | 32 | 399 | 15.2% | 15.5% | 19 | 11 |
| 50% | 19 | 18 | 145 | 5.5% | 7.0% | 10 | 6 |

The 10% default preserves a broad exploratory regional view; 20–50% thresholds test whether conclusions persist under stricter spatial representation. The threshold is a spatial interpretation condition, not a p-value rule.

![Threshold sensitivity](assets/figure_05_physical_decomposition.png)

US retention falls faster because HydroBASINS L5 units are comparatively fragmented relative to the observed catchment polygons.

## 22. Multi-catchment L5 estimator

For an L5 with at least two contributing catchments:

$$
\bar y_{it}=\alpha_i+\beta_j x_{it}+\varepsilon_{it},
\qquad x_{it}=\frac{year_{it}-2000}{10}.
$$

$\alpha_i$ controls stable catchment differences and $\beta_j$ is the shared per-decade change. Standard errors are clustered by catchment with a $t(G-1)$ reference.

**Example.** Suppose two catchments in one L5 have long-term mean concentrations of 35% and 55%, but both rise by about 2 percentage points per decade. Fixed effects retain the 35% versus 55% baseline difference and estimate the shared $\beta_j\approx+2$ percentage points per decade; the higher baseline is not mistaken for temporal change.

## 23. One-catchment representation

If one catchment alone supports an L5 polygon at the selected threshold, the L5 panel inherits that catchment's Theil–Sen estimate and is explicitly labelled as a single-catchment representation. High area support does not create multi-catchment corroboration.

## 24. Why 2000 appears

The year 2000 is only a numerical centering constant. Replacing it with 1990 or 2010 leaves the slope unchanged; no pre/post-2000 contrast or breakpoint is fitted.

**Example.** Under 2000 centering, 1990 has $x=-1$ and 2010 has $x=+1$, a two-decade separation. Under 1990 centering they become 0 and 2, still separated by two decades. The slope is unchanged; only the intercept is written differently.

## 25. Complete regional family

All 1,475 estimable L5 × five-primary-metric tests enter one BH family. This is intentionally more conservative than correcting each metric separately because the map invites inspection across both space and SSI windows.

## 26. Five regional evidence gates

The interactive regional signal must pass:

1. the currently selected area-support threshold;
2. complete regional-family 5% BH-FDR;
3. sign agreement across all four alternative extreme samples;
4. sign agreement across 1/3/7/30-day SSI windows where relevant;
5. leave-one-catchment-out sign stability, or leave-one-year-out stability for a one-catchment representation.

## 27. Regional results at the default 10% threshold

| Metric | L5 tests | Complete-family BH-FDR | Strong regional signals | Negative | Positive |
|---|---:|---:|---:|---:|---:|
| Rainfall concentration | 152 | 27 | 24 | 19 | 5 |
| Antecedent SSI (1 day) | 152 | 18 | 16 | 13 | 3 |
| Antecedent SSI (3 days) | 152 | 15 | 14 | 11 | 3 |
| Antecedent SSI (7 days) | 152 | 18 | 16 | 12 | 4 |
| Antecedent SSI (30 days) | 152 | 14 | 14 | 12 | 2 |

![Area-supported regional patterns](assets/figure_04_mechanism_trajectories.png)

Both positive and negative directions remain. The result is spatially heterogeneous regional evidence rather than one uniform global direction.

## 28. Strongest regional results

| L5 | Metric | Direction | Change per decade | 95% CI | Area support | Catchments |
|---|---|---|---:|---:|---:|---:|
| HB5-762870 | Antecedent SSI (3 days) | decrease | -0.030 | -0.043 to -0.017 | 55.5% | 9 |
| HB5-762870 | Antecedent SSI (1 day) | decrease | -0.030 | -0.042 to -0.017 | 55.5% | 9 |
| HB5-632730 | Antecedent SSI (3 days) | decrease | -0.029 | -0.042 to -0.015 | 13.3% | 11 |
| HB5-632730 | Antecedent SSI (1 day) | decrease | -0.029 | -0.042 to -0.015 | 13.3% | 11 |
| HB5-048410 | Antecedent SSI (7 days) | decrease | -0.029 | -0.043 to -0.014 | 24.8% | 8 |
| HB5-762870 | Rainfall concentration | decrease | -5.69 | -8.23 to -3.14 | 55.5% | 9 |
| HB5-502710 | Rainfall concentration | decrease | -5.40 | -6.43 to -4.36 | 60.0% | 4 |
| HB5-774200 | Antecedent SSI (1 day) | decrease | -0.027 | -0.042 to -0.011 | 80.4% | 11 |
| HB5-048410 | Antecedent SSI (3 days) | decrease | -0.027 | -0.040 to -0.013 | 24.8% | 8 |
| HB5-048620 | Antecedent SSI (3 days) | decrease | -0.026 | -0.036 to -0.016 | 45.6% | 16 |
| HB5-632730 | Antecedent SSI (7 days) | decrease | -0.025 | -0.037 to -0.014 | 13.3% | 11 |
| HB5-048620 | Antecedent SSI (1 day) | decrease | -0.025 | -0.036 to -0.015 | 45.6% | 16 |

## 29. Returning regional evidence to its catchments

![Regional and contributing catchment trends](assets/figure_06_robustness_matrix.png)

Grey circles are direct catchment slopes; diamonds and intervals are pooled L5 slopes and 95% confidence intervals. A pooled signal gains power from shared within-catchment movement and does not imply that every contributing catchment is independently significant.

## 30. Supported scientific conclusions

1. Most estimable catchments do not show network-confirmed long-term shifts.
2. The 378 stable candidates provide explicit targets for independent follow-up.
3. Some local changes align into statistically clearer L5-scale directions.
4. Stricter area support reduces the number of interpretable L5 signals while opposing regional directions persist.

## 31. Inference boundary

These trends are not changes in flood count, flood peak, or runoff volume. They do not establish attribution to anthropogenic climate change, land use, or engineering controls. Area coverage measures observational spatial support rather than population, assets, or area-weighted global representativeness.

## 32. Limitations

Long records are sparse in Asia; rainfall concentration is daily rather than sub-daily; SSI and reconstructed rainfall uncertainty enter event metrics; neighbouring L5 units may be spatially dependent; and clustered inference remains approximate with few catchments. Direct candidates require independent data or longer records for confirmation.

## 33. Next analyses

Prioritize raw-series review and independent precipitation/soil-moisture validation for stable candidates and strong L5 signals. Then test whether finer HydroBASINS levels improve spatial resolution while retaining adequate area support.

## 34. Reproduction

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage all --force
& $projectPython src/validate_outputs.py
```

The related `Event_Typology` source project is used read-only. This repository stores the method, derived evidence, figures, reports, and GitHub Pages explorer: <https://grups666.github.io/Global_Flood_Cause_Evolution/>.
