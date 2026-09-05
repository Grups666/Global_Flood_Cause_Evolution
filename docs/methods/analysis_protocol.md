# Analysis protocol

## 1. Scientific question

For each gauged catchment, the experiment asks:

1. Did the occurrence or magnitude of large rainfall-driven floods change from 1982 to 2019?
2. Which flood-generating process produced those large floods?
3. Did the frequency, generating conditions or flood response of a particular process change through time?

Every inference is catchment-specific. The map connects observed results geographically but does not fill or extrapolate to ungauged areas.

## 2. Eligible event record

Only rainfall-driven events from catchments with snow fraction below 0.10 are used. A catchment must have at least 30 observed event years, a span of at least 30 years and event-year coverage of at least 80% within that span. Incomplete precipitation or streamflow windows are excluded from the affected calculation rather than converted to zero.

## 3. Primary large-flood sample

The meeting defined the upper tail using event-scale stormflow volume. For catchment \(i\), let \(Q^{vol}_{ie}\) be direct stormflow volume for event \(e\). The fixed full-record threshold is

\[
u_i=\operatorname{quantile}_{0.95}\{Q^{vol}_{ie}\}.
\]

The primary sample contains events satisfying

\[
Q^{vol}_{ie}\ge u_i.
\]

Example: if a catchment has 400 reconstructed hydrological events, its Q95 threshold is the 95th percentile of those 400 event volumes. Roughly the largest 20 events enter the primary sample. The threshold is fixed once for the full record; it is not recalculated each year.

Q90, Q97.5 and the annual maximum stormflow-volume event are alternative samples. The primary result must keep the same direction in all three alternatives.

## 4. Rainfall temporal organization

For an event with daily rainfall \(P_{ied}\), define

\[
P_{\max,ie}=\max_d(P_{ied}),
\qquad
P_{\mathrm{event},ie}=\sum_d P_{ied},
\]

and rainfall concentration

\[
C_{ie}=\frac{P_{\max,ie}}{P_{\mathrm{event},ie}}.
\]

Example: 42 mm falls on the rainiest day and 70 mm falls over the whole event, so \(C=42/70=0.60\). Sixty percent of the event rainfall was concentrated in one day.

The temporal coefficient of variation is

\[
CV_{t,ie}=\frac{\operatorname{sd}_d(P_{ied})}{\operatorname{mean}_d(P_{ied})}.
\]

Following Tarasova et al. (2020), an event is **Intensity** when

\[
C_{ie}>0.50\quad\text{and}\quad CV_{t,ie}>1.
\]

All other rainfall events are **Volume**. The concentration threshold is repeated at 0.40 and 0.60 as a classification sensitivity check.

## 5. Antecedent wetness

SSI is a normalized 0–1 soil-wetness index, not soil-water depth in millimetres. The analytical event value is daily SSI on the calendar day before rainfall begins: `ssi_1d = SSI(start_precip_date − 1 day)`. The cutoffs are recalculated by pooling all 35,918,563 valid daily SSI values from the 2,637 primary-sample catchments over 1982–2019, including non-event days. Each valid catchment-day has equal weight. The pooled one-third and two-thirds quantiles (linear interpolation) give:

\[
SSI\leq0.404690:\ Dry,\qquad
0.404690<SSI\leq0.576339:\ Moderate,\qquad
SSI>0.576339:\ Wet.
\]

For example, rainfall starting on 10 June uses SSI on 9 June; values of 0.30, 0.50 and 0.70 correspond to Dry, Moderate and Wet. Full-precision cutoffs are stored in the calibration receipt and frozen across all years and extreme-event sensitivity samples. Continuous SSI remains the primary wetness quantity; classes only form event groups. These network-relative terciles are not universal physical thresholds.

Seven Q95 events begin on 1 January 1982 and lack previous-day SSI. They remain in flood/rainfall analysis but receive `Unknown` wetness and `Unclassified` joint labels. Wetness-group shares exclude them from the denominator; wetness-group frequency excludes the affected catchment-years to avoid false zero counts. Forcing-only groups do not require wetness classification.

Diagnostics repeat wetness classification at pooled 25/75 and 40/60 percentiles, and repeat full-sample continuous SSI trends with complete 3-, 7- and 30-day pre-rainfall means. These are reported sensitivity diagnostics, not additional support gates. Outputs include per-catchment/day coverage, event-time alignment and per-catchment/year event missingness.

## 6. Six rainfall-driven processes

Crossing antecedent state with rainfall organization yields:

| Process | Physical interpretation |
|---|---|
| Dry–Intensity | strongly peaked rainfall over initially dry soil |
| Dry–Volume | prolonged/distributed rainfall over initially dry soil |
| Moderate–Intensity | strongly peaked rainfall over moderately wet soil |
| Moderate–Volume | prolonged/distributed rainfall over moderately wet soil |
| Wet–Intensity | strongly peaked rainfall over wet soil |
| Wet–Volume | prolonged/distributed rainfall over wet soil |

These are event types, not permanent catchment labels. A catchment can experience several types in different years.

## 7. Annualization

Several Q95 events may occur in one catchment-year. For any continuous event variable \(y\), the catchment-year value is

\[
\bar y_{it}=\frac{1}{n_{it}}\sum_{e=1}^{n_{it}}y_{iet}.
\]

Example: if a catchment has three selected floods in 2004 with volumes 20, 35 and 50 mm, the 2004 value is \((20+35+50)/3=35\) mm. Thus 2004 receives one temporal observation, not three times the weight of a year with one flood.

## 8. Trends in all selected large floods

The map's continuous-conditions view uses the same Q95 sample without a class
filter. It fits rainfall concentration and source-catalogue antecedent SSI
separately in each catchment, using at least 10 valid event-years and a span of
at least 20 years inclusive. Annual points are event means; absent event-years
are missing, not zeros. The existing Theil–Sen/Mann–Kendall, alternative-sample
direction and leave-one-year-out checks are reused. Classification-threshold
checks do not apply to this unclassified population. Reproduce this view with
`python src/run_pipeline.py --stage conditions`, then the `web` stage.

Full-sample condition trends, changes in class proportions and within-class
condition trends answer different questions. Every event receives its own
class; no permanent catchment class is assigned. A small continuous change near
a boundary can change a label, and conditioning on that label changes the
population being compared. Read class trends alongside the unclassified
continuous series; neither view alone establishes causal attribution.

Three outcomes describe what happened to the selected floods:

- direct stormflow volume (mm per decade);
- maximum daily streamflow during the event (mm/day per decade);
- number of Q95 exceedances per year (events/year per decade).

The first two use the annualized values above. The frequency series includes zero-event years.

## 9. Process-specific trends

For each of the six processes, the experiment estimates:

- annual process frequency;
- process share among selected large floods;
- direct stormflow volume of that process;
- maximum daily streamflow of that process;
- rainfall concentration within that process;
- antecedent SSI within that process.

A process is fitted only when at least five selected events are available. Five is the single hard minimum, following the compromise used by Tarasova et al. (2023). No additional 20-event category is used.

Process frequency answers “did this mechanism produce large floods more often?” Process share answers “did this mechanism occupy a larger fraction of the upper-tail sample?” Flood volume and peak answer “did the floods produced by this mechanism become larger or smaller?” The last two condition metrics show how rainfall organization and antecedent wetness evolved *within* the process.

## 10. Trend estimator and test

For an annual sequence of a continuous physical variable \(y_t\), the Theil–Sen slope is the median of all pairwise slopes:

\[
\hat\beta_{TS}=\operatorname{median}_{j>k}\left(\frac{y_j-y_k}{t_j-t_k}\right).
\]

The reported slope is multiplied by 10 and therefore always means change over **10 years**. `Per decade` never means 12 years.

Example: a fitted concentration slope of +0.035 per decade is displayed as **+3.5 percentage points per decade**. If the fitted early-record concentration is 0.32, the corresponding ten-year value is approximately 0.355: the rainiest-day contribution changes from 32.0% to 35.5% of total event rainfall.

For a positive physical variable, a secondary relative effect is reported without a logarithmic model:

\[
r=100\frac{\hat\beta}{\bar y}.
\]

Example: if antecedent SSI has \(\hat\beta=+0.009\) per decade and its catchment–process mean is 0.45, then \(r=100(0.009/0.45)=+2.0\%\) of the mean per decade. The primary effect remains **+0.009 SSI units per 10 years**; the relative value only provides scale context.

The Mann–Kendall statistic is

\[
S=\sum_{j>k}\operatorname{sign}(y_j-y_k),
\]

with tie-corrected variance. Its two-sided \(p\)-value tests the null hypothesis of no monotonic trend. Individual catchment results use \(p<0.05\), followed by the direction-stability checks below.

Annual event counts use a Poisson trend with a log link:

\[
N_t\sim\operatorname{Poisson}(\mu_t),
\qquad
\log \mu_t=a+b\frac{t-2000}{10}.
\]

The standard error uses a sandwich covariance so modest count overdispersion does not rely on the exact Poisson variance. The reader-facing effect is converted back to an absolute rate change:

\[
\Delta f=\frac{\hat\mu_{last}-\hat\mu_{first}}{(t_{last}-t_{first})/10}.
\]

Example: if fitted frequency rises from 0.4 to 0.7 selected floods per year over 30 years, \(\Delta f=(0.7-0.4)/3=+0.10\) events/year per 10 years. This avoids an uninformative zero median slope in sparse annual count series.

Process shares are fitted to annual successes \(s_t\) out of selected events \(n_t\) with a bias-reduced binomial time trend:

\[
s_t\sim\operatorname{Binomial}(n_t,\pi_t),
\qquad
\operatorname{logit}(\pi_t)=a+b\frac{t-2000}{10}.
\]

The interface converts the coefficient to fitted probability change in percentage points per decade. Example: an increase from a fitted 18% to 26% over two decades is \((26-18)/2=+4\) percentage points per decade.

## 11. Evidence screen

A displayed result is marked **supported** when all of the following hold:

1. two-sided \(p<0.05\);
2. the direction agrees for Q90, Q97.5 and annual-maximum samples;
3. for process-specific results, the direction agrees at concentration cutoffs 0.40 and 0.60;
4. removing any one observed year does not reverse the direction.

The screens test reproducibility of direction, not truth of a causal claim. The “all estimates” map retains every estimable slope in pale directional colours; “supported focus” emphasizes the subset passing the complete screen.

## 12. Interpretation boundary

The study can state that a particular flood-generating process became more or less frequent, that its rainfall/soil conditions changed, or that floods associated with that process changed in volume or peak. It cannot, from trend coincidence alone, state that the driver trend caused the flood-response trend. Land-use change, regulation, modelled SSI uncertainty and remaining event-classification uncertainty are possible alternatives.
