# Long-Term Changes in Rainfall-Driven Large-Flood Generating Conditions (1982–2019)

**Technical report · generated 2026-09-01**

## Technical summary

- Evidence is constructed in two stages: direct trends are estimated for every eligible catchment, and HydroBASINS L5 is then used to test whether nearby catchments form a larger coherent pattern.
- The primary sample contains **59,048 POT/Q95 floods in 2,624 long-record low-snow catchments**. At least one primary direct trend is estimable in **2,435 catchments**.
- The five continuous outcomes produce **12,163 catchment–metric tests**. There are **378 directionally stable candidates**, but **no direct catchment signal passes metric-wide 5% FDR**. The strict result is therefore that most catchments do not show a network-confirmed long-term shift; candidates identify locations for targeted follow-up.
- Among 1,475 L5–metric tests, **106 pass complete-family FDR and 94 pass the full statistical robustness screen**. With the default **≥10% area support**, **84 strong regional signals remain in 36 L5 units**.
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

## 7. Why annual maxima are a sensitivity population

Annual maxima force one event into every year, even when that event is not particularly extreme relative to the catchment record. POT/Q95 directly targets the catchment upper tail, while annual maxima remain an important alternative definition.

## 8. Extreme-event sensitivities

The alternatives are POT/Q90, POT/Q97.5, 10-day-declustered POT/Q95, and annual maxima. The primary sample contains 2,194 adjacent peak pairs under 10 days; the declustered sample contains 0. Stormflow-window overlaps equal 0.

## 9. Rainfall concentration

$$
C_{ie}=\frac{P_{\max,ie}}{P_{\mathrm{volume},ie}}.
$$

An increase means a larger share of event rainfall fell in the wettest day; a decrease means movement toward longer, volume-dominated rainfall. The continuous ratio is the inferential outcome; no binary intensity-dominated label is used.

## 10. Antecedent wetness

$$
SSI_{ie}^{(w)}=\frac1w\sum_{k=1}^w SSI_{i,t_{0,ie}-k},
\qquad w\in\{1,3,7,30\}.
$$

Positive slopes mean large floods occurred after increasingly wet antecedent states; negative slopes mean increasingly dry states. SSI units are normalized index units, not millimetres or flood percentages.

## 11. Physical rainfall components

Maximum daily rainfall, event rainfall total, and precipitation duration are fitted in raw physical units. Their secondary relative slopes are:

$$
r=100\frac{\widehat\beta}{\bar y}.
$$

No logarithmic trend model is used. These components aid interpretation of the concentration ratio without claiming causal attribution.

## 12. Catchment-year annualization

Multiple POT events in one catchment-year are averaged:

$$
\bar y_{it}=\frac1{n_{it}}\sum_e y_{iet}.
$$

This prevents a year with several reconstructed events from receiving extra trend weight solely because of event count.

## 13. Direct catchment trend

The annual sequence uses a Theil–Sen slope:

$$
\widehat\beta_i=\operatorname{median}_{t_j>t_k}
\frac{\bar y_{it_j}-\bar y_{it_k}}{t_j-t_k}\times10,
$$

with a tie-corrected Mann–Kendall test. At least 10 event years spanning at least 20 years are required.

## 14. Catchment multiple testing

Each physical metric forms one Benjamini–Hochberg family across catchments. Ordering $m$ p-values, the procedure finds the largest $k$ satisfying:

$$
p_{(k)}\le\frac{k}{m}\alpha,
\qquad \alpha=0.05.
$$

## 15. Stable local candidate

A candidate requires unadjusted $p<0.05$, sign agreement at POT/Q90 and POT/Q97.5, agreement after 10-day declustering, agreement under annual maxima, and leave-one-event-year-out sign stability. SSI candidates also require all four windows to agree. This is an exploratory evidence grade, not an FDR-confirmed shift.

![Direct catchment results](assets/figure_02_mechanism_change_maps.png)

Light marks retain all estimable trends; outlined marks identify stable candidates. Color encodes effect direction and magnitude, not statistical significance.

## 16. Direct catchment results

| Metric | Estimable catchments | Unadjusted p<0.05 | Stable candidates | Metric-wide FDR | Negative candidates | Positive candidates |
|---|---:|---:|---:|---:|---:|---:|
| Rainfall concentration | 2,435 | 154 | 73 | 0 | 39 | 34 |
| Antecedent SSI (1 day) | 2,435 | 184 | 78 | 0 | 48 | 30 |
| Antecedent SSI (3 days) | 2,435 | 181 | 77 | 0 | 49 | 28 |
| Antecedent SSI (7 days) | 2,433 | 164 | 81 | 0 | 48 | 33 |
| Antecedent SSI (30 days) | 2,425 | 163 | 69 | 0 | 32 | 37 |

## 17. Direct catchment conclusion

There are **378 stable candidates in opposing directions and zero metric-wide FDR discoveries**. The evidence therefore supports sparse candidate locations within a predominantly non-confirmed network, not ubiquitous long-term change.

![Catchment evidence funnel](assets/figure_03_strong_signal_rankings.png)

The evidence funnel keeps unadjusted significance, sensitivity stability, and multiplicity control distinct.

## 18. L5 is a second-stage spatial question

L5 asks whether direct catchment changes may represent a larger hydrological pattern. It does not determine whether a catchment estimate is worth retaining and never removes the primary catchment layer.

## 19. Catchment-to-L5 membership

Catchment outlets are spatially joined to HydroBASINS v1.c level 5. **2,622 catchments** match; two Mauritius catchments remain unmatched in the reference geometry but retain direct results.

## 20. L5 area support

For L5 polygon $H_j$ and eligible catchment polygons $A_i$ assigned by their outlets:

$$
Coverage_j=
\frac{Area\left(H_j\cap\bigcup_{i\in j}A_i\right)}{Area(H_j)}.
$$

Areas use equal-area EPSG:6933. Invalid polygons are repaired, and overlapping catchments are counted once through a geometric union.

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

## 23. One-catchment representation

If one catchment alone supports an L5 polygon at the selected threshold, the L5 panel inherits that catchment's Theil–Sen estimate and is explicitly labelled as a single-catchment representation. High area support does not create multi-catchment corroboration.

## 24. Why 2000 appears

The year 2000 is only a numerical centering constant. Replacing it with 1990 or 2010 leaves the slope unchanged; no pre/post-2000 contrast or breakpoint is fitted.

## 25. Complete regional family

All 1,475 estimable L5 × five-primary-metric tests enter one BH family. This is intentionally more conservative than correcting each metric separately because the map invites inspection across both space and SSI windows.

## 26. Five regional evidence gates

The interactive regional signal must pass:

1. the currently selected area-support threshold;
2. complete regional-family 5% FDR;
3. sign agreement across all four alternative extreme samples;
4. sign agreement across 1/3/7/30-day SSI windows where relevant;
5. leave-one-catchment-out sign stability, or leave-one-year-out stability for a one-catchment representation.

## 27. Regional results at the default 10% threshold

| Metric | L5 tests | Complete-family FDR | Strong regional signals | Negative | Positive |
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
