# Local Evolution of Rainfall-Driven Large-Flood Generating Conditions (1982–2019)

**Complete technical report | continuous process metrics, HydroBASINS L5, and reproducible inference**
**Generated: 2026-09-01**

> Main result: the observed network does not support one spatially uniform global direction. It identifies 62 reproducible local changes in 21 HydroBASINS level-5 regions. Rainfall concentration and antecedent wetness both move in opposing directions across regions, so the scientific result is where and how generating conditions moved—not an average that cancels local signals.

## Technical summary

- The primary sample contains **59,048 POT/Q95 large-flood events** in **2,624 long-record catchments**.
- Regional inference is performed only for HydroBASINS L5 units containing at least **20 eligible catchments**, leaving **28 regions**.
- The complete primary family contains 28 regions × 5 continuous metrics = **140 tests**; **80** pass Benjamini–Hochberg 5% False Discovery Rate control.
- Requiring agreement across extreme-event samples, leave-one-catchment-out sign stability, and—where relevant—all SSI windows leaves **62 strong signals**.
- Strong rainfall-concentration trends span **-2.54 to +2.92 percentage points per decade**. Seven-day SSI trends span **-0.011 to +0.010 SSI units per decade**.
- SSI is reported in both absolute units and relative to the region's catchment-equal mean; eligible regions span **-2.65% to +1.55% per decade**.

![Long-record catchment and primary-sample coverage](assets/figure_01_sample_coverage.png)

## 1. First-principles research question

The study asks whether the rainfall organization and pre-event land wetness that generate large floods changed through time and space. It does not substitute flood counts, flood-peak trends, or an analyst-chosen pre/post-2000 contrast for that question.

## 2. Why the result is local

Network density is highly uneven: Europe and North America are dense, while only one Asian catchment passes the long-record screen. A global average is neither area-weighted nor capable of retaining opposing local movements. Multi-catchment L5 regions are therefore the primary evidence scale; individual catchments preserve local inspection detail.

## 3. Spatial pattern of current results

![L5 trends for the five continuous mechanism metrics](assets/figure_02_mechanism_change_maps.png)

Only the 28 regions satisfying the ≥20-catchment rule are mapped. Color encodes direction and magnitude; cyan outlines identify strong evidence. Blank areas mean that the current network cannot support the same regional inference—not that change is absent.

## 4. Evidence counts by metric

| Continuous metric | Pass 5% BH-FDR | Strong | Strong positive | Strong negative |
|---|---:|---:|---:|---:|
| Rainfall concentration | 21 | 16 | 6 | 10 |
| Antecedent SSI (1 day) | 15 | 12 | 3 | 9 |
| Antecedent SSI (3 days) | 15 | 12 | 3 | 9 |
| Antecedent SSI (7 days) | 14 | 10 | 4 | 6 |
| Antecedent SSI (30 days) | 15 | 12 | 5 | 7 |

## 5. Largest reproducible local movements

![Strong regional trends and 95% confidence intervals](assets/figure_03_strong_signal_rankings.png)

| Region | Countries | Metric | Trend / decade | 95% CI | Catchments | BH q |
|---|---|---|---:|---:|---:|---:|
| HB5-595640 | AU | Rainfall concentration | +2.92 | +1.82 to +4.02 | 44 | 3.7e-05 |
| HB5-420340 | DE | Rainfall concentration | +2.79 | +1.96 to +3.61 | 43 | 1.18e-06 |
| HB5-023010 | DE | Rainfall concentration | +2.70 | +1.29 to +4.10 | 30 | 0.00186 |
| HB5-497340 | FR | Rainfall concentration | -2.54 | -3.54 to -1.55 | 26 | 0.000182 |
| HB5-024170 | DE | Rainfall concentration | +2.50 | +1.30 to +3.69 | 32 | 0.000897 |
| HB5-502920 | FR | Rainfall concentration | -2.10 | -3.20 to -1.01 | 22 | 0.00225 |
| HB5-020620 | FR | Rainfall concentration | -2.09 | -2.85 to -1.34 | 39 | 2.83e-05 |
| HB5-020590 | FR | Rainfall concentration | -2.05 | -2.75 to -1.35 | 65 | 3.9e-06 |
| HB5-014330 | BR | Rainfall concentration | -2.03 | -2.74 to -1.32 | 22 | 7.66e-05 |
| HB5-022150 | FR | Rainfall concentration | -1.99 | -2.74 to -1.25 | 60 | 2.07e-05 |
| HB5-441280 | DE/FR | Rainfall concentration | -1.46 | -2.25 to -0.67 | 40 | 0.00201 |
| HB5-021040 | FR | Rainfall concentration | -1.38 | -2.19 to -0.57 | 57 | 0.00365 |

## 6. Meaning of the annual trajectories

![Continuous trajectories for representative regions](assets/figure_04_mechanism_trajectories.png)

The annual points are not pooled event means. Their meaning is: **after placing every catchment on the same long-run mean level, how far above or below its own normal condition were the catchments contributing in that year, on average?** This reduces station-composition artifacts without inventing a calendar breakpoint.

## 7. Physical reading of rainfall concentration

![Raw physical components behind concentration change](assets/figure_05_physical_decomposition.png)

Wettest-day rainfall, total event rainfall, and precipitation duration are fitted in their raw units. Displayed relative values equal the raw linear slope divided by the region's catchment-equal mean. If wettest-day rain rises 2% per decade while event-total rain rises 8%, rainfall concentration falls; no logarithmic model is required for that interpretation.

## 8. Robustness to large-flood definition

![Direction across alternative extreme-event samples](assets/figure_06_robustness_matrix.png)

Strong signals keep their sign in annual maxima, POT/Q90, 10-day-declustered POT/Q95, and POT/Q97.5 samples. The requirement is directional replication, not numerically identical slopes.

## 9. Data and verified period

The analysis reuses read-only event catalogs, daily hydroclimatic observations, and SSI features from Event_Typology. The common verified period is 1982–2019. Spatial units use [HydroBASINS v1.c](https://www.hydrosheds.org/products/hydrobasins).

## 10. Long-record eligibility

A catchment must provide at least 30 annual observations, span at least 30 years, and cover at least 80% of its record span. Eligibility is established before extreme-event selection.

## 11. Primary large-flood population

For catchment $i$, the within-catchment 95th percentile of reconstructed event peaks is

$$Q_{0.95,i}=\operatorname{quantile}_{0.95}\left(Q_{i1},\ldots,Q_{in_i}\right).$$

The primary sample retains $Q_{ie}\ge Q_{0.95,i}$ and requires at least 10 selected events spanning at least 20 years in each catchment.

## 12. Why annual maxima are not the primary sample

Annual maxima force exactly one event per year and can discard multiple independent large floods in the same year. POT/Q95 retains all within-catchment exceedances; annual maxima remain a sensitivity population.

## 13. Event independence

The primary sample has a minimum adjacent-peak gap of 2 days and 0 overlapping stormflow windows. A separate 10-day-declustered sample has 0 adjacent pairs under 10 days, making independence an explicit sensitivity rather than an assumption.

## 14. Rainfall-driven scope

Event snow-water fraction must be below 0.10. Flood-peak magnitude selects events; rainfall and SSI only describe their generating conditions. Selection and mechanism measurement are never conflated.

## 15. Rainfall concentration

For event $e$ in catchment $i$,

$$C_{ie}=\frac{P_{\max,ie}}{P_{\mathrm{volume},ie}},\qquad 0<C_{ie}\le1.$$

$P_{\max}$ is wettest-day rainfall and $P_{\mathrm{volume}}$ is total event rainfall. Higher $C$ means more concentrated rain; lower $C$ means more prolonged or distributed rain.

## 16. Why intensity-dominated classes are not used

A $C>0.50$ label makes 0.51 equivalent to 0.95 and creates artificial threshold jumps. It was not a meeting-defined scientific target. Inference, reports, and the web interface therefore use continuous $C$ and do not construct a binary type share.

## 17. Antecedent Soil Saturation Index

For $w\in\{1,3,7,30\}$ complete pre-event days,

$$SSI_{w,ie}=\frac1w\sum_{d=1}^w SSI_{i,t_0-d},$$

where $t_0$ is rainfall onset. The windows represent immediate to slower antecedent memory and exclude event-day rain.

## 18. Why four SSI windows

One day captures immediate wetness, 3 and 7 days capture short memory, and 30 days captures slower background state. They are parallel continuous measurements used to test window sensitivity.

## 19. Why Dry/Moderate/Wet classes are not used

Threshold classes discard within-class movement and are not needed to answer the research question. The project retains continuous SSI and does not construct Dry/Moderate/Wet labels.

## 20. Why HydroBASINS L5 is the only regional scale

L5 supplies the interpretable local hydrological scale used for inference. L3/L4 have no core inferential role and are not included in computation, result tables, or web data. The spatial design contains only L5 regions and eligible individual catchments.

## 21. The single ≥20-catchment threshold

Catchments are the clusters in regional inference. Conventional cluster-robust variance relies on many-cluster asymptotics. [Cameron and Miller](https://escholarship.org/uc/item/1jq5d0pq) emphasize that there is no universal boundary and that “few” may mean fewer than 20 to fewer than 50 clusters; $t(G-1)$ corrections can still over-reject. [Imbens and Kolesár](https://doi.org/10.1162/REST_A_00552) show that small-sample corrections can matter even with 50 or more clusters.

Twenty is therefore a conservative minimum design choice for the present estimator, not a theorem that guarantees exact inference. Five clusters would provide only four nominal degrees of freedom. The project has one regional sample rule—≥20—and excludes smaller regional units.

## 22. Catchment fixed-effect model

For catchment $i$, event $e$, and year $t$,

$$y_{iet}=\alpha_i+\beta x_{iet}+\varepsilon_{iet},\qquad x_{iet}=\frac{year_{iet}-2000}{10}.$$

$\alpha_i$ is the catchment-specific baseline and $\beta$ is the average within-catchment change per decade.

## 23. What fixed effects do

The estimator removes each catchment's mean:

$$\widetilde y_{iet}=y_{iet}-\bar y_i,\qquad \widetilde x_{iet}=x_{iet}-\bar x_i,$$

$$\widehat\beta=\frac{\sum_{i,e,t}\widetilde x_{iet}\widetilde y_{iet}}{\sum_{i,e,t}\widetilde x_{iet}^2}.$$

A naturally wetter catchment cannot create a regional trend merely because its baseline is high; only temporal movement relative to its own baseline contributes.

## 24. Why 2000 appears in the formula

It is only a numerical centering constant. Replacing 2000 with 1990 or 2010 leaves the slope unchanged. The model has no pre/post-2000 comparison or breakpoint.

## 25. Cluster-robust uncertainty

Residuals may be arbitrarily correlated among events within a catchment. The variance uses a finite-sample scaling and $t_{G-1}$ critical values, where $G$ is the number of contributing catchments.

## 26. Unit of rainfall-concentration change

Because $C$ is a 0–1 proportion, $100\widehat\beta$ is reported as percentage points of event rainfall per decade. A value of +2.12 means the wettest-day share rises by 2.12 percentage points in ten years; it is not a 2.12% change in flood count or peak flow.

## 27. Absolute and relative SSI change

Absolute SSI slope is primary. The supplementary relative scale is

$$r_{SSI}=100\times\frac{\widehat\beta_{SSI}}{\bar y_{ref}},\qquad
\bar y_{ref}=\frac1G\sum_{i=1}^G\bar y_i.$$

For example, −0.013 SSI per decade against a 0.52 catchment-equal mean is about −2.5% per decade. Relative change aids scale perception but does not replace the absolute estimate or confidence interval.

## 28. Relative Pmax, event-total, and duration trends

Each component is fitted linearly in raw units and then divided by its catchment-equal mean:

$$r_y=100\times\frac{\widehat\beta_y}{\bar y_{ref}}.$$

No $\ln P$ model or $100(e^\beta-1)$ transformation is used.

## 29. Adjusted annual trajectory

With catchment-year event mean $v_{it}$, catchment long-run mean $\bar v_i$, and catchment-equal reference $v_{ref}$,

$$v_{it}=\frac1{n_{it}}\sum_e y_{iet},\quad v_{ref}=\frac1G\sum_i\bar v_i,$$

$$v_{it}^*=v_{it}-\bar v_i+v_{ref},\quad \bar v_t^*=\frac1{G_t}\sum_i v_{it}^*.$$

It answers how far the year's participating catchments were above or below their own normal levels after all catchments are placed on the same long-run mean.

## 30. Benjamini–Hochberg False Discovery Rate

False Discovery Rate (FDR) is

$$FDR=E\left[\frac{V}{\max(R,1)}\right],$$

where $V$ is the number of false rejections and $R$ is the number of all rejections. The [Benjamini–Hochberg procedure](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) orders $m$ p-values and finds

$$k=\max\left\{\,i:p_{(i)}\le\frac{i}{m}q\,\right\},$$

then rejects $H_{(1)},\ldots,H_{(k)}$. Here $m=140$ and $q=0.05$.

## 31. Why unadjusted p<0.05 is insufficient

If all 140 null hypotheses were true, random variation alone would still yield about

$$ 140\times0.05=7.0 $$

unadjusted p-values below 0.05 on average. This is not an estimate of actual false positives; it demonstrates the multiplicity problem.

## 32. BH-adjusted q-values

For ordered p-values,

$$q_{(i)}=\min_{j\ge i}\left(\frac{m}{j}p_{(j)}\right),$$

clipped at one and restored to the original order. The web inspector reports the q-value from the complete 140-test family, not a more favorable metric-specific subset.

## 33. Individual-catchment trends

Points use the [Theil–Sen](https://ir.cwi.nl/pub/18445) median slope,

$$\widehat\beta_{TS}=\operatorname{median}_{j>i}\frac{y_j-y_i}{t_j-t_i},$$

with a tie-corrected Mann–Kendall test. At least 10 selected events spanning at least 20 years are required. These points provide local context, not primary regional inference.

## 34. Complete strong-evidence rule

A strong primary signal must satisfy all of the following:

1. at least 20 contributing catchments;
2. 5% BH-FDR across the full 140-test primary family;
3. matching signs in annual maxima, POT/Q90, 10-day-declustered POT/Q95, and POT/Q97.5;
4. unchanged sign in every leave-one-catchment-out estimate;
5. for SSI, agreement across all four windows.

## 35. One sample threshold and three evidence grades

All mapped and tested regions satisfy the same ≥20 rule. Grades are estimate, FDR-supported, or strong; sample size does not introduce a second evidence threshold.

## 36. Supported conclusions

- Generating conditions changed reproducibly in some local hydrological regions.
- Local rainfall concentration changed by several percentage points per decade.
- Antecedent wetness moved in both wetter and drier directions.
- Spatial heterogeneity is a result, not noise to be averaged away.

## 37. Unsupported conclusions

- No spatially uniform or area-weighted global land trend is established.
- Results do not directly describe flood frequency, peak flow, or flood volume.
- The analysis does not causally attribute change to climate, land use, or infrastructure.
- Blank regions do not imply zero trend; many lack eligible long records.

## 38. Limitations

Coverage is densest in Europe and North America and nearly absent in Asia. Rainfall reconstruction and SSI uncertainty enter event metrics. Conventional clustered inference is not finite-sample exact at 20 clusters, and adjacent regions may remain spatially dependent. Twenty is a minimum, not a sufficiency guarantee.

## 39. Reproducibility map

- Configuration: `config/analysis.yaml`
- Pipeline: `src/run_pipeline.py`
- Regional model: `src/floodcause/local_analysis.py`
- Independent validation: `src/validate_outputs.py`
- Primary evidence table: `outputs/tables/hydrobasin_evidence.csv`
- Interactive data: `public/modules/flood-cause-evolution/data/flood-cause-explorer.json`
- Interactive site: [GitHub Pages](https://grups666.github.io/Global_Flood_Cause_Evolution/)

## 40. Next analytical step

Add long-record catchments in Asia and other sparse regions. For retained ≥20-cluster regions, add CR2/Bell–McCaffrey or wild-cluster bootstrap sensitivity before attempting broader spatial generalization.
