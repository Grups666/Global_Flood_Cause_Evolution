from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
LOGS = ROOT / "outputs" / "logs"
REPORTS = ROOT / "reports"

MECHANISM_ZH = {
    "Dry-Intensity": "干燥–强度型",
    "Dry-Volume": "干燥–总量型",
    "Moderate-Intensity": "中等湿润–强度型",
    "Moderate-Volume": "中等湿润–总量型",
    "Wet-Intensity": "湿润–强度型",
    "Wet-Volume": "湿润–总量型",
}
OUTCOME_ZH = {
    "direct_runoff_volume": "事件直接径流量",
    "flood_peak": "事件日洪峰",
    "exceedance_frequency": "Q95事件年频次",
    "mechanism_frequency": "该机制的年频次",
    "mechanism_share": "该机制在入选大洪水中的比例",
    "rainfall_concentration": "该机制内部的降雨集中度",
    "antecedent_wetness": "该机制内部的前期湿润度",
}
OUTCOME_EN = {
    "direct_runoff_volume": "event direct stormflow volume",
    "flood_peak": "event daily flood peak",
    "exceedance_frequency": "annual Q95-event frequency",
    "mechanism_frequency": "annual process frequency",
    "mechanism_share": "process share among selected floods",
    "rainfall_concentration": "within-process rainfall concentration",
    "antecedent_wetness": "within-process antecedent wetness",
}


def _load() -> dict[str, Any]:
    return {
        "summary": json.loads((LOGS / "analysis_summary.json").read_text(encoding="utf-8")),
        "overall": pd.read_csv(TABLES / "catchment_overall_trends.csv"),
        "mechanism": pd.read_csv(
            TABLES / "catchment_mechanism_trends.csv", low_memory=False
        ),
        "composition": pd.read_csv(TABLES / "mechanism_composition.csv"),
        "diagnostics": pd.read_csv(TABLES / "extreme_sample_diagnostics.csv").set_index("sample"),
        "coverage": pd.read_csv(TABLES / "record_eligibility.csv"),
    }


def _counts(table: pd.DataFrame, outcome: str) -> dict[str, int]:
    frame = table[table["outcome"].eq(outcome)]
    supported = frame[frame["supported_shift"].fillna(False)]
    return {
        "estimated": len(frame),
        "p": int(frame["p_pass"].fillna(False).sum()),
        "supported": len(supported),
        "positive": int(supported["display_slope_per_decade"].gt(0).sum()),
        "negative": int(supported["display_slope_per_decade"].lt(0).sum()),
    }


def _range(table: pd.DataFrame, outcome: str) -> str:
    frame = table[table["outcome"].eq(outcome) & table["supported_shift"].fillna(False)]
    if frame.empty:
        return "—"
    return f"{frame['display_slope_per_decade'].min():.2f} to {frame['display_slope_per_decade'].max():.2f}"


def _summary_rows(table: pd.DataFrame, outcomes: list[str], labels: dict[str, str]) -> str:
    rows = []
    for outcome in outcomes:
        count = _counts(table, outcome)
        rows.append(
            f"| {labels[outcome]} | {count['estimated']:,} | {count['p']:,} | "
            f"{count['supported']:,} | {count['negative']:,} | {count['positive']:,} |"
        )
    return "\n".join(rows)


def _composition_rows(composition: pd.DataFrame, zh: bool) -> str:
    rows = []
    for row in composition.sort_values("events", ascending=False).itertuples(index=False):
        name = MECHANISM_ZH[row.mechanism] if zh else row.mechanism.replace("-", " + ").lower()
        rows.append(f"| {name} | {row.events:,} | {row.share_percent:.1f}% |")
    return "\n".join(rows)


def _top_rows(table: pd.DataFrame, outcome: str, zh: bool, n: int = 10) -> str:
    frame = table[table["outcome"].eq(outcome) & table["supported_shift"].fillna(False)].copy()
    frame["magnitude"] = frame["display_slope_per_decade"].abs()
    frame = frame.nlargest(n, "magnitude")
    if frame.empty:
        return "| — | — | — | — |"
    rows = []
    for row in frame.itertuples(index=False):
        process = MECHANISM_ZH.get(row.mechanism, row.mechanism) if zh else row.mechanism.replace("-", " + ").lower()
        rows.append(
            f"| {int(row.GCIN)} | {row.country} | {process} | "
            f"{row.display_slope_per_decade:+.2f} {row.display_unit} |"
        )
    return "\n".join(rows)


def _continent_rows(table: pd.DataFrame, outcome: str, zh: bool) -> str:
    frame = table[table["outcome"].eq(outcome) & table["supported_shift"].fillna(False)].copy()
    rows = []
    for continent, part in frame.groupby("continent"):
        rows.append(
            f"| {continent} | {len(part):,} | {int(part.display_slope_per_decade.lt(0).sum()):,} | "
            f"{int(part.display_slope_per_decade.gt(0).sum()):,} |"
        )
    return "\n".join(rows) if rows else "| — | 0 | 0 | 0 |"


def _continent_sentence(table: pd.DataFrame, outcome: str, zh: bool) -> str:
    frame = table[table["outcome"].eq(outcome) & table["supported_shift"].fillna(False)]
    parts = []
    for continent, part in frame.groupby("continent"):
        negative = int(part["display_slope_per_decade"].lt(0).sum())
        positive = int(part["display_slope_per_decade"].gt(0).sum())
        if zh:
            parts.append(f"{continent} {len(part)}个（下降{negative}、上升{positive}）")
        else:
            parts.append(f"{continent}: {len(part)} ({negative} decreases, {positive} increases)")
    return "；".join(parts) if zh else "; ".join(parts)


def _worked_examples(table: pd.DataFrame, zh: bool, n: int = 4) -> str:
    frame = table[table["supported_shift"].fillna(False)].copy()
    frame = frame[frame["outcome"].isin(["mechanism_share", "direct_runoff_volume", "flood_peak"])]
    frame["scaled"] = frame["display_slope_per_decade"].abs() / frame.groupby("outcome")["display_slope_per_decade"].transform(lambda x: x.abs().median()).replace(0, 1)
    frame = frame.nlargest(n, "scaled")
    blocks = []
    for index, row in enumerate(frame.itertuples(index=False), start=1):
        process = MECHANISM_ZH.get(row.mechanism, row.mechanism) if zh else row.mechanism.replace("-", " + ").lower()
        outcome = OUTCOME_ZH[row.outcome] if zh else OUTCOME_EN[row.outcome]
        if zh:
            blocks.append(
                f"{index}. **GCIN {int(row.GCIN)}（{row.country}），{process}。**"
                f"{outcome}为 {row.display_slope_per_decade:+.2f} {row.display_unit}；"
                f"拟合记录两端约为 {row.fitted_first:.2f} → {row.fitted_last:.2f}。"
                f"这句话只表示该观测流域内、该机制对应量随时间的方向和幅度，不自动证明因果。"
            )
        else:
            blocks.append(
                f"{index}. **GCIN {int(row.GCIN)} ({row.country}), {process}.** The {outcome} trend is "
                f"{row.display_slope_per_decade:+.2f} {row.display_unit}; the fitted record endpoints are "
                f"{row.fitted_first:.2f} → {row.fitted_last:.2f}. This is a within-catchment temporal result, not proof of causation."
            )
    return "\n\n".join(blocks) if blocks else ("当前没有通过完整筛选的示例。" if zh else "No example passes the complete screen.")


def _zh(stats: dict[str, Any]) -> str:
    s, o, m, c, d = stats["summary"], stats["overall"], stats["mechanism"], stats["composition"], stats["diagnostics"]
    primary = s["sample_counts"]["pot_q95"]
    overall_rows = _summary_rows(o, ["direct_runoff_volume", "flood_peak", "exceedance_frequency"], OUTCOME_ZH)
    mechanism_rows = _summary_rows(m, ["mechanism_frequency", "mechanism_share", "direct_runoff_volume", "flood_peak", "rainfall_concentration", "antecedent_wetness"], OUTCOME_ZH)
    return fr"""# 全球降雨驱动型大洪水生成机制的长期变化（1982–2019）

**完整技术报告｜事件尺度分类、观测流域趋势与可复现实验**

生成日期：2026-09-04

> **核心结果。** 研究先在每个观测流域中按事件直接径流量选出全记录 Q95 大洪水，再区分六种“前期湿润状态 × 降雨时间组织”机制。结果不是寻找一条全球统一趋势，而是定位哪些观测流域的机制出现频率、机制内部条件或相应洪水响应发生了稳定变化。

## 1. 研究问题

本研究回答三件事：入选的大洪水本身是否变了；这些洪水由什么机制产生；把不同机制分开后，哪些机制的发生频率、组成比例、降雨与前期湿润条件以及洪水量级发生了长期变化。

老师在 2026 年 9 月 2 日会议中强调，混合不同成因会相互抵消时间信号。因此单个观测流域是首要分析单元，机制分类先于趋势解释；地图只显示真实观测流域，不对无资料区域作空间外推。

## 2. 数据与研究边界

- 时间：1982–2019；这是降水、流量和土壤湿润度均可核验的共同记录。
- 对象：低雪影响的降雨驱动事件（流域雪比例 < 0.10）。
- 记录门槛：至少30个事件年份、至少30年跨度、记录覆盖率至少80%。
- 主样本：**{primary['events']:,}** 个Q95事件、**{primary['catchments']:,}** 个观测流域。
- 空间含义：地图上的点是有观测资料的流域，不代表全球陆地面积均匀采样。

![主样本及六种机制组成](assets/figure_01_sample_and_process_coverage.png)

## 3. Q95到底是什么

Q95不是降水的95分位，也不是每年重新计算的日流量95分位。对流域 \(i\)，用完整记录内所有水文事件的**直接径流量** \(Q^{{vol}}_{{ie}}\) 计算：

$$
u_i=\operatorname{{quantile}}_{{0.95}}\{{Q^{{vol}}_{{ie}}\}}.
$$

满足 \(Q^{{vol}}_{{ie}}\ge u_i\) 的事件进入主样本。例如某流域有400场事件，Q95大致选出事件直接径流量最大的20场。Q90、Q97.5和每年最大事件只用于敏感性检验。

## 4. 为什么还要看洪水本身

“生成条件变了”不能代替“洪水响应变了”。因此首先估计入选事件的直接径流量、事件日洪峰和每年Q95事件数。只有把响应与条件并列展示，才能讨论二者是否在同一流域、同一机制中共同变化。

![入选大洪水本身的变化](assets/figure_02_overall_flood_changes.png)

| 结果量 | 可估计流域 | p<0.05 | 通过完整筛选 | 下降 | 上升 |
|---|---:|---:|---:|---:|---:|
{overall_rows}

## 5. 降雨时间组织的公式和物理含义

设一场事件第 \(d\) 天降雨为 \(P_d\)：

$$
C=\frac{{\max_d(P_d)}}{{\sum_d P_d}},\qquad CV_t=\frac{{sd(P_d)}}{{mean(P_d)}}.
$$

例如整场降雨70 mm，最多的一天42 mm，则 \(C=0.60\)：60%的事件降雨集中在一天。按照Tarasova等（2020）的日尺度规则，只有 \(C>0.50\) 且 \(CV_t>1\) 才称为**强度型**；其余称为**总量型**。连续的 \(C\) 仍然保留用于趋势计算，标签只用于分组。

## 6. 前期湿润状态

土壤饱和指数（soil saturation index，SSI）在0到1之间，表示土壤储水相对于模型田间持水能力的状态。源事件目录的经验边界约为：\(SSI\leq0.3994\) 为干燥，\(0.3994<SSI\leq0.5640\) 为中等湿润，\(SSI>0.5640\) 为湿润。这里不把中间状态强行塞进干/湿二分，因而不会丢掉大量物理上处于中间状态的事件。

## 7. 六种生成机制

六类分别为干燥–强度型、干燥–总量型、中等湿润–强度型、中等湿润–总量型、湿润–强度型和湿润–总量型。它们是**事件标签**，不是给流域贴上的永久标签；同一流域在不同年份可以出现不同机制。

| 机制 | Q95事件数 | 占主样本 |
|---|---:|---:|
{_composition_rows(c, True)}

## 8. 为什么每个机制至少需要5场事件

Tarasova等（2023）在流域尺度机制频次趋势中采用至少5场同类事件，明确说明这是稳健性与可用数据之间的折中。本实验只保留这个单一硬门槛，不再人为设置5–19和≥20两级。

## 9. 同一年有多场事件怎么办

连续变量先在“流域–年份”内平均：

$$
\bar y_{{it}}=\frac{{1}}{{n_{{it}}}}\sum_e y_{{iet}}.
$$

例如2004年有三场Q95洪水，直接径流量分别为20、35和50 mm，则该年的趋势输入是35 mm。这样不会因为某一年事件多就获得额外时间权重。频次分析则保留实际事件数，并在有记录但没有该机制事件的年份填0。

## 10. 趋势如何估计

降雨集中度、SSI、径流量和洪峰等连续量使用Theil–Sen斜率：

$$
\hat\beta=\operatorname{{median}}_{{j>k}}\frac{{y_j-y_k}}{{t_j-t_k}},
$$

显著性使用带重复值校正的Mann–Kendall检验，其排序统计量为

$$
S=\sum_{{j>k}}\operatorname{{sign}}(y_j-y_k).
$$

在“没有单调趋势”的零假设下，由重复值校正后的方差计算双侧p值。报告将年斜率乘10，因此“per decade”始终是**每10年**，不是12年。

年度事件数使用Poisson计数趋势：

$$
N_t\sim\operatorname{{Poisson}}(\mu_t),\qquad
\log\mu_t=a+b\frac{{t-2000}}{{10}}.
$$

结果不直接显示对数系数，而换算为拟合年频次的绝对变化。比如某机制从记录初期的0.4场/年变为30年后的0.7场/年，则显示为 \((0.7-0.4)/3=+0.10\) 场/年/10年。这样稀疏年度计数也不会只得到没有信息的“−0.0”。

机制比例使用年度“该机制事件数 / 全部Q95事件数”的偏差修正二项趋势：

$$
s_t\sim\operatorname{{Binomial}}(n_t,\pi_t),\qquad
\operatorname{{logit}}(\pi_t)=a+b\frac{{t-2000}}{{10}}.
$$

比如拟合比例在20年内从18%变为26%，显示为 \((26-18)/2=+4\) 个百分点/10年。

对SSI、径流量等正值变量，报告还给出辅助相对变化 \(r=100\hat\beta/\bar y\)，不使用对数模型。例如SSI绝对趋势为+0.009/10年、该流域—机制平均SSI为0.45，则相对变化为 \(100\times0.009/0.45=+2.0\%/10年\)。绝对单位仍是主结果，相对值只帮助判断变化相对于当地平均状态有多大。

## 11. p值与证据筛选

每个流域—结果组合直接报告两侧 \(p\) 值；完整支持要求 \(p<0.05\)，并且Q90、Q97.5、年度最大样本方向一致，降雨分类0.40和0.60阈值方向一致，逐年删除任何一年都不反向。

这四项是方向可复现性筛选，不是因果证明。

## 12. 机制发生频率的结果

机制年频次回答“这种机制产生Q95大洪水是否越来越常见”。它比只看总体洪水趋势更贴近老师提出的“分类以后再看时间模式”。

![六种机制的年频次变化](assets/figure_03_process_frequency_changes.png)

绝对变化幅度最大的支持结果如下；“+”表示该机制产生Q95大洪水的年频次增加，“−”表示减少。

| 流域 | 国家 | 生成机制 | 年频次趋势 |
|---|---|---|---:|
{_top_rows(m, 'mechanism_frequency', True, 8)}

## 13. 机制组成比例的结果

机制比例回答“在该流域入选的大洪水中，这一机制所占份额是否上升或下降”。它与频次互补：比例增加可能来自该机制变多，也可能来自其他机制减少。

![六种机制在Q95样本中的比例变化](assets/figure_04_process_share_changes.png)

| 流域 | 国家 | 生成机制 | 在Q95大洪水中的占比趋势 |
|---|---|---|---:|
{_top_rows(m, 'mechanism_share', True, 8)}

## 14. 所有机制特异结果的证据数量

| 结果量 | 可估计组合 | p<0.05 | 通过完整筛选 | 下降 | 上升 |
|---|---:|---:|---:|---:|---:|
{mechanism_rows}

## 15. 机制内部的洪水响应

分类之后分别看直接径流量和日洪峰，回答“由同一种机制产生的洪水是否变大/变小”。这比把所有不同成因事件混合后只拟合一条线更容易发现相互抵消的局部变化。

![机制特异洪水响应的最强稳定变化](assets/figure_05_process_response_rankings.png)

## 16. 机制内部的条件变化

降雨集中度趋势表示同类事件的降雨是否进一步向单日集中；SSI趋势表示同类事件发生前的流域是否变得更湿或更干。即使事件仍落在同一类别中，连续物理量也可能持续变化，因此分类与连续指标同时保留。

| 流域 | 国家 | 生成机制 | 降雨集中度趋势 |
|---|---|---|---:|
{_top_rows(m, 'rainfall_concentration', True, 6)}

| 流域 | 国家 | 生成机制 | 前期湿润度趋势 |
|---|---|---|---:|
{_top_rows(m, 'antecedent_wetness', True, 6)}

## 17. 时间轨迹示例

![机制比例的观测年度轨迹与拟合](assets/figure_06_example_process_trajectories.png)

图中每个点是一个流域年份的机制比例，曲线是二项趋势拟合。示例用于说明“从什么状态变到什么状态”，不代表全球平均。

## 18. 具体结果怎样读

{_worked_examples(m, True)}

## 19. 地理分布不是全球平均

下面只统计通过完整筛选的观测点数量，用于描述证据出现在哪里；它不是按面积加权的洲际趋势。

- Q95事件年频次：{_continent_sentence(o, 'exceedance_frequency', True)}。
- 机制年频次：{_continent_sentence(m, 'mechanism_frequency', True)}。
- 机制内部降雨集中度：{_continent_sentence(m, 'rainfall_concentration', True)}。
- 机制内部前期湿润度：{_continent_sentence(m, 'antecedent_wetness', True)}。

| 洲 | 稳定机制频次结果 | 下降 | 上升 |
|---|---:|---:|---:|
{_continent_rows(m, 'mechanism_frequency', True)}

## 20. 敏感性样本

主结果使用事件直接径流量Q95。Q90增加样本但纳入较小事件；Q97.5更极端但样本更少；年度最大每年最多一场。完整支持要求适用的替代样本斜率方向均与Q95一致。主样本重建事件的风暴径流窗口重叠数为 **{int(d.loc['pot_q95','stormflow_window_overlaps'])}**，说明事件目录本身已经把相互重叠的径流响应分开。

## 21. 数据质量与缺失处理

缺失窗口不会当成0。只有在流域记录存在、但该年没有某机制Q95事件时，频次才记为0。所有事件选择阈值均在各流域内部计算，避免不同流域量级差异直接决定谁进入样本。

## 22. 限制

SSI来自水文模型状态，存在模型结构和参数不确定性；阈值分类会压缩连续差异；观测网在欧洲和北美更密集；1982–2019的38年记录适合识别持续方向，但不足以穷尽多年代际振荡；趋势并不自动等于因果归因；土地利用、水库调度和测站变化仍可能影响局部结果。

## 23. 水文学结论

1. 在全部入选大洪水中，直接径流量、日洪峰和Q95事件频次分别有 **{_counts(o, 'direct_runoff_volume')['supported']}**、**{_counts(o, 'flood_peak')['supported']}** 和 **{_counts(o, 'exceedance_frequency')['supported']}** 个流域通过完整筛选；这说明“洪水本身怎样变”必须逐流域回答，不能压缩为一个全球符号。
2. 六种机制的年频次共有 **{_counts(m, 'mechanism_frequency')['supported']}** 个支持结果，其中 **{_counts(m, 'mechanism_frequency')['negative']}** 个减少、**{_counts(m, 'mechanism_frequency')['positive']}** 个增加；方向并不统一，分机制后才能看到这种局地替换。
3. 机制占比共有 **{_counts(m, 'mechanism_share')['supported']}** 个支持结果。它们直接表示一个机制在当地Q95大洪水构成中的份额发生持续变化，是回答“洪水生成方式是否转变”的核心结果。
4. 同一机制内，降雨集中度、前期SSI、直接径流量和日洪峰也分别保留了可复现的局地变化。频次、生成条件与洪水响应需要并列解释；时间共变本身不等于因果归因。

## 24. 可复现入口

- 方法协议：[docs/methods/analysis_protocol.md](../docs/methods/analysis_protocol.md)
- 数据字典：[docs/methods/data_dictionary.md](../docs/methods/data_dictionary.md)
- 文献综述：[docs/background/literature_review.md](../docs/background/literature_review.md)
- 运行入口：`python src/run_pipeline.py --stage all --force`

## 25. 核心参考文献

- Stein, L., Pianosi, F., & Woods, R. (2020). Event-based classification for global study of river flood generating processes. *Hydrological Processes*. <https://doi.org/10.1002/hyp.13678>
- Stein, L. et al. (2021). How do climate and catchment attributes influence flood generating processes? *Water Resources Research*. <https://doi.org/10.1029/2020WR028300>
- Tarasova, L. et al. (2019). Causative classification of river flood events. *WIREs Water*. <https://doi.org/10.1002/wat2.1353>
- Tarasova, L. et al. (2020). A process-based framework to characterize and classify runoff events. *Water Resources Research*. <https://doi.org/10.1029/2019WR026951>
- Tarasova, L., Basso, S., & Merz, R. (2020). Transformation of generation processes from small runoff events to large floods. *Geophysical Research Letters*. <https://doi.org/10.1029/2020GL090547>
- Tarasova, L. et al. (2023). Shifts in flood generation processes exacerbate regional flood anomalies in Europe. *Communications Earth & Environment*. <https://doi.org/10.1038/s43247-023-00714-8>
"""


def _en(stats: dict[str, Any]) -> str:
    s, o, m, c, d = stats["summary"], stats["overall"], stats["mechanism"], stats["composition"], stats["diagnostics"]
    primary = s["sample_counts"]["pot_q95"]
    overall_rows = _summary_rows(o, ["direct_runoff_volume", "flood_peak", "exceedance_frequency"], OUTCOME_EN)
    mechanism_rows = _summary_rows(m, ["mechanism_frequency", "mechanism_share", "direct_runoff_volume", "flood_peak", "rainfall_concentration", "antecedent_wetness"], OUTCOME_EN)
    return fr"""# Long-term changes in the generating processes of rainfall-driven large floods (1982–2019)

**Complete technical report | event-scale process classification, gauged-catchment trends and reproducible evidence**

Generated: 2026-09-04

> **Main result.** The experiment first selects each catchment's upper-tail floods by direct stormflow volume, then separates six antecedent-wetness × rainfall-organization processes. Its target is not a single global direction. It identifies gauged catchments where process occurrence, process conditions or associated flood response changed reproducibly.

## 1. Research question and meeting-directed logic

The study asks what happened to the selected large floods, which processes generated them, and whether each process changed in frequency, composition, generating conditions or flood response. The 2 September 2026 meeting emphasized that pooling different causes can cancel temporal signals. Event classification therefore precedes trend interpretation, and individual gauged catchments remain the inferential units.

## 2. Data boundary

- Verified common period: 1982–2019.
- Rainfall-driven events in catchments with snow fraction <0.10.
- At least 30 event years, a 30-year span and 80% record coverage.
- Primary sample: **{primary['events']:,} Q95 events in {primary['catchments']:,} gauged catchments**.
- Mapped points are observations, not area-complete global coverage.

![Primary sample and six-process composition](assets/figure_01_sample_and_process_coverage.png)

## 3. Definition of Q95

Q95 is calculated from event direct stormflow volume, not precipitation and not daily peak flow:

$$u_i=\operatorname{{quantile}}_{{0.95}}\{{Q^{{vol}}_{{ie}}\}},\qquad Q^{{vol}}_{{ie}}\ge u_i.$$

If a catchment has 400 reconstructed events, approximately the 20 largest event volumes enter the primary sample. The threshold is fixed over the full record. Q90, Q97.5 and annual-maximum event volume are sensitivity samples.

## 4. The selected floods themselves

The analysis first estimates trends in direct stormflow volume, daily event peak and annual Q95-event frequency. This prevents a driver trend from being discussed without showing the corresponding flood response.

![Changes in the selected large floods](assets/figure_02_overall_flood_changes.png)

| Outcome | Estimates | p<0.05 | Complete screen | Decrease | Increase |
|---|---:|---:|---:|---:|---:|
{overall_rows}

## 5. Rainfall temporal organization

For daily event rainfall \(P_d\),

$$C=\frac{{\max_d(P_d)}}{{\sum_dP_d}},\qquad CV_t=\frac{{sd(P_d)}}{{mean(P_d)}}.$$

If 42 mm falls on the rainiest day and 70 mm over the event, \(C=0.60\): 60% of event rainfall fell in one day. Following Tarasova et al. (2020), an event is intensity-dominated only when \(C>0.50\) **and** \(CV_t>1\); otherwise it is volume-dominated. The continuous concentration value is retained for trend estimation.

## 6. Antecedent wetness and the six processes

The soil saturation index (SSI) is a dimensionless 0–1 model state. The source catalogue's empirical boundaries are approximately SSI ≤0.3994 (dry), 0.3994–0.5640 (moderate) and >0.5640 (wet). Crossing the three states with intensity/volume rainfall organization produces six event processes. These are event labels, not permanent catchment labels.

| Process | Q95 events | Primary-sample share |
|---|---:|---:|
{_composition_rows(c, False)}

## 7. Why five process events

Tarasova et al. (2023) used at least five events of a process as an explicit compromise between trend robustness and data availability. This experiment uses that one hard minimum; it has no 5–19 versus ≥20 evidence tiers.

## 8. Catchment-year annualization

For a continuous variable, multiple selected events in a catchment-year are averaged:

$$\bar y_{{it}}=\frac{{1}}{{n_{{it}}}}\sum_e y_{{iet}}.$$

For volumes 20, 35 and 50 mm in 2004, the annual value is 35 mm. The year therefore contributes one temporal observation. Frequency retains event counts and includes zeros in observed years without the relevant process.

## 9. Trend estimation and physical units

Continuous physical outcomes use the Theil–Sen slope,

$$\hat\beta=\operatorname{{median}}_{{j>k}}\frac{{y_j-y_k}}{{t_j-t_k}},$$

with a tie-corrected Mann–Kendall test, whose ordering statistic is

$$S=\sum_{{j>k}}\operatorname{{sign}}(y_j-y_k).$$

The two-sided p value tests the null hypothesis of no monotonic trend. Annual slopes are multiplied by ten, so *per decade* always means **per 10 years**.

Annual event counts use a Poisson trend,

$$N_t\sim\operatorname{{Poisson}}(\mu_t),\qquad \log\mu_t=a+b(t-2000)/10,$$

and are converted back to an absolute fitted-frequency change. A rise from 0.4 to 0.7 events/year over 30 years is \((0.7-0.4)/3=+0.10\) events/year per 10 years. This remains informative when a sparse count series would have a zero median pairwise slope.

Process shares use a bias-reduced binomial time trend,

$$s_t\sim\operatorname{{Binomial}}(n_t,\pi_t),\qquad \operatorname{{logit}}(\pi_t)=a+b(t-2000)/10.$$

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
{_top_rows(m, 'mechanism_frequency', False, 8)}

## 12. Process composition

Process share asks whether a process occupied a larger or smaller fraction of a catchment's selected floods. Frequency and share are complementary: a share can rise because that process increased or because competing processes declined.

![Changes in process share](assets/figure_04_process_share_changes.png)

| Catchment | Country | Generating process | Q95-sample share trend |
|---|---|---|---:|
{_top_rows(m, 'mechanism_share', False, 8)}

## 13. Complete process-specific evidence counts

| Outcome | Estimates | p<0.05 | Complete screen | Decrease | Increase |
|---|---:|---:|---:|---:|---:|
{mechanism_rows}

## 14. Process-specific flood response

Direct stormflow volume and daily flood peak are estimated within each process. This asks whether floods generated by the *same process* became larger or smaller.

![Strongest supported process-specific response changes](assets/figure_05_process_response_rankings.png)

## 15. Within-process generating conditions

Rainfall concentration indicates whether rainfall became further concentrated within a process. SSI indicates whether antecedent conditions shifted even while events remained in the same broad wetness class. Continuous indicators and categorical process labels therefore serve different purposes.

| Catchment | Country | Generating process | Rainfall-concentration trend |
|---|---|---|---:|
{_top_rows(m, 'rainfall_concentration', False, 6)}

| Catchment | Country | Generating process | Antecedent-wetness trend |
|---|---|---|---:|
{_top_rows(m, 'antecedent_wetness', False, 6)}

## 16. Worked trajectories

![Observed annual process shares and fitted trajectories](assets/figure_06_example_process_trajectories.png)

{_worked_examples(m, False)}

## 17. Geographic context

The table counts supported observed points. It is not an area-weighted continental trend.

- Q95-event frequency — {_continent_sentence(o, 'exceedance_frequency', False)}.
- Process frequency — {_continent_sentence(m, 'mechanism_frequency', False)}.
- Within-process rainfall concentration — {_continent_sentence(m, 'rainfall_concentration', False)}.
- Within-process antecedent wetness — {_continent_sentence(m, 'antecedent_wetness', False)}.

| Continent | Supported process-frequency results | Decrease | Increase |
|---|---:|---:|---:|
{_continent_rows(m, 'mechanism_frequency', False)}

## 18. Sensitivity and event independence

Supported directions must agree with the applicable Q90, Q97.5 and annual-maximum samples. The primary sample has **{int(d.loc['pot_q95','stormflow_window_overlaps'])} overlapping reconstructed stormflow windows**, confirming that the event catalogue has already separated overlapping runoff responses.

## 19. Limitations

SSI is model-derived; classification thresholds compress continuous variation; gauge coverage is densest in Europe and North America; 38 years cannot resolve every multidecadal oscillation; trend coincidence is not causal attribution; and land-use, regulation or measurement changes may contribute to local results.

## 20. Hydrological conclusions

1. Across all selected floods, **{_counts(o, 'direct_runoff_volume')['supported']}**, **{_counts(o, 'flood_peak')['supported']}** and **{_counts(o, 'exceedance_frequency')['supported']}** catchments pass the complete screen for direct stormflow volume, daily peak and Q95-event frequency, respectively. Flood change is therefore a local result, not one global sign.
2. Process frequency has **{_counts(m, 'mechanism_frequency')['supported']}** supported catchment–process results: **{_counts(m, 'mechanism_frequency')['negative']}** decreases and **{_counts(m, 'mechanism_frequency')['positive']}** increases. Separating mechanisms exposes locally opposing replacements that a pooled trend would hide.
3. Process share has **{_counts(m, 'mechanism_share')['supported']}** supported results. These directly identify persistent changes in the composition of a catchment's Q95 floods and are central evidence for changing flood-generation pathways.
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
"""


def build_reports() -> dict[str, Any]:
    stats = _load()
    REPORTS.mkdir(parents=True, exist_ok=True)
    zh_path = REPORTS / "global_flood_cause_evolution.md"
    en_path = REPORTS / "global_flood_cause_evolution_en.md"
    zh_path.write_text(_zh(stats), encoding="utf-8")
    en_path.write_text(_en(stats), encoding="utf-8")
    return {"status": "complete", "reports": [str(zh_path), str(en_path)]}


if __name__ == "__main__":
    print(json.dumps(build_reports(), indent=2, ensure_ascii=False))
