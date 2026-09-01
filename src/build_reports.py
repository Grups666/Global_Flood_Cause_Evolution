from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
LOGS = ROOT / "outputs" / "logs"
REPORTS = ROOT / "reports"
PRIMARY_METRICS = ["intensity_fraction", "ssi_1d", "ssi_3d", "ssi_7d", "ssi_30d"]
LABELS_ZH = {
    "intensity_fraction": "降雨集中度",
    "ssi_1d": "前期湿润度 SSI（1日）",
    "ssi_3d": "前期湿润度 SSI（3日）",
    "ssi_7d": "前期湿润度 SSI（7日）",
    "ssi_30d": "前期湿润度 SSI（30日）",
}
LABELS_EN = {
    "intensity_fraction": "Rainfall concentration",
    "ssi_1d": "Antecedent SSI (1 day)",
    "ssi_3d": "Antecedent SSI (3 days)",
    "ssi_7d": "Antecedent SSI (7 days)",
    "ssi_30d": "Antecedent SSI (30 days)",
}


def _stats() -> dict[str, Any]:
    analysis = json.loads((LOGS / "analysis_summary.json").read_text(encoding="utf-8"))
    local = json.loads((LOGS / "local_analysis_summary.json").read_text(encoding="utf-8"))
    diagnostics = pd.read_csv(TABLES / "extreme_sample_diagnostics.csv").set_index("sample")
    catchments = pd.read_csv(TABLES / "catchment_mechanism_trends.csv")
    catchments = catchments[catchments["variable"].isin(PRIMARY_METRICS)].copy()
    regions = pd.read_csv(TABLES / "hydrobasin_evidence.csv")
    regions = regions[regions["metric"].isin(PRIMARY_METRICS)].copy()
    support = pd.read_csv(TABLES / "spatial_support" / "l5_spatial_support_audit.csv").rename(
        columns={"hybas_id_l5": "HYBAS_ID"}
    )
    regions = regions.merge(
        support[["HYBAS_ID", "coverage_pct", "observed_union_inside_km2"]],
        on="HYBAS_ID",
        how="left",
    )
    sensitivity = pd.read_csv(
        TABLES / "spatial_support" / "l5_spatial_support_threshold_sensitivity.csv"
    )
    thresholds = list(local["area_coverage_threshold_options_percent"])
    threshold_rows: list[dict[str, Any]] = []
    global_area = sensitivity[
        sensitivity["scope"].eq("Global") & sensitivity["metric"].eq("coverage_fraction")
    ].set_index("threshold_pct")
    us_area = sensitivity[
        sensitivity["scope"].eq("United States") & sensitivity["metric"].eq("coverage_fraction")
    ].set_index("threshold_pct")
    for threshold in thresholds:
        available = regions[regions["coverage_pct"].ge(threshold)]
        threshold_rows.append(
            {
                "threshold": int(threshold),
                "audit_l5": int(global_area.loc[threshold, "passing_l5"]),
                "mappable_l5": int(available["HYBAS_ID"].nunique()),
                "catchments": int(global_area.loc[threshold, "passing_catchments"]),
                "catchment_share": float(global_area.loc[threshold, "passing_catchment_share_pct"]),
                "us_catchment_share": float(us_area.loc[threshold, "passing_catchment_share_pct"]),
                "strong_signals": int(available["strong_evidence"].sum()),
                "strong_regions": int(
                    available.loc[available["strong_evidence"], "HYBAS_ID"].nunique()
                ),
            }
        )
    default_threshold = int(local["default_area_coverage_threshold_percent"])
    return {
        "analysis": analysis,
        "local": local,
        "diagnostics": diagnostics,
        "catchments": catchments,
        "regions": regions,
        "support": support,
        "threshold_rows": threshold_rows,
        "default_threshold": default_threshold,
        "default_regions": regions[regions["coverage_pct"].ge(default_threshold)].copy(),
    }


def _local_table(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    if language == "zh":
        rows = ["| 指标 | 可估计流域 | p < 0.05 | 稳健单流域趋势 | 负向 | 正向 |\n|---|---:|---:|---:|---:|---:|"]
    else:
        rows = ["| Metric | Estimable catchments | p < 0.05 | Robust individual trends | Negative | Positive |\n|---|---:|---:|---:|---:|---:|"]
    for metric in PRIMARY_METRICS:
        part = s["catchments"][s["catchments"]["variable"].eq(metric)]
        robust = part[part["robust_local_trend"]]
        rows.append(
            f"| {labels[metric]} | {len(part):,} | {int(part['mk_p'].lt(0.05).sum()):,} | "
            f"{len(robust):,} | {int(robust['display_slope_per_decade'].lt(0).sum()):,} | "
            f"{int(robust['display_slope_per_decade'].gt(0).sum()):,} |"
        )
    return "\n".join(rows)


def _top_individual(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    frame = s["catchments"][s["catchments"]["robust_local_trend"]].copy()
    scale = frame["variable"].map(
        {"intensity_fraction": 8.0, "ssi_1d": 0.04, "ssi_3d": 0.04, "ssi_7d": 0.04, "ssi_30d": 0.04}
    )
    frame["score"] = frame["display_slope_per_decade"].abs() / scale
    frame = frame.sort_values("score", ascending=False).head(12)
    if language == "zh":
        rows = ["| GCIN | 国家 | 指标 | 每10年变化 | 拟合起点 → 终点 | p value |\n|---:|---|---|---:|---:|---:|"]
    else:
        rows = ["| GCIN | Country | Metric | Change per 10 years | Fitted start → end | p value |\n|---:|---|---|---:|---:|---:|"]
    for row in frame.itertuples(index=False):
        rain = row.variable == "intensity_fraction"
        digits = 2 if rain else 3
        factor = 100 if rain else 1
        rows.append(
            f"| {int(row.GCIN)} | {row.country} | {labels[row.variable]} | "
            f"{row.display_slope_per_decade:+.{digits}f}{' pp' if rain else ' SSI'} | "
            f"{row.fitted_first_level * factor:.{digits}f} → {row.fitted_last_level * factor:.{digits}f} | "
            f"{row.mk_p:.4f} |"
        )
    return "\n".join(rows)


def _country_table(s: dict[str, Any], language: str) -> str:
    frame = s["catchments"][s["catchments"]["robust_local_trend"]].copy()
    frame["direction"] = frame["display_slope_per_decade"].gt(0).map({True: "positive", False: "negative"})
    grouped = (
        frame.groupby(["country", "variable", "direction"]).size().rename("n").reset_index()
        .sort_values("n", ascending=False).head(15)
    )
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    if language == "zh":
        rows = ["| 国家 | 指标 | 方向 | 稳健单流域数 |\n|---|---|---|---:|"]
        direction = {"positive": "增加", "negative": "减少"}
    else:
        rows = ["| Country | Metric | Direction | Robust catchments |\n|---|---|---|---:|"]
        direction = {"positive": "increase", "negative": "decrease"}
    for row in grouped.itertuples(index=False):
        rows.append(f"| {row.country} | {labels[row.variable]} | {direction[row.direction]} | {row.n} |")
    return "\n".join(rows)


def _threshold_table(s: dict[str, Any], language: str) -> str:
    if language == "zh":
        rows = ["| 面积支持阈值 | 有趋势结果的L5 | 被这些L5覆盖的流域 | 全球流域占比 | 美国流域占比 | 强区域信号 | 涉及L5 |\n|---:|---:|---:|---:|---:|---:|---:|"]
    else:
        rows = ["| Area-support threshold | L5 with estimates | Catchments represented | Global catchment share | US catchment share | Strong regional signals | L5 involved |\n|---:|---:|---:|---:|---:|---:|---:|"]
    for row in s["threshold_rows"]:
        rows.append(
            f"| {row['threshold']}% | {row['mappable_l5']} | {row['catchments']:,} | "
            f"{row['catchment_share']:.1f}% | {row['us_catchment_share']:.1f}% | "
            f"{row['strong_signals']} | {row['strong_regions']} |"
        )
    return "\n".join(rows)


def _regional_table(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    if language == "zh":
        rows = ["| 指标 | L5检验 | 完整区域族BH-FDR | 强区域信号 | 负向 | 正向 |\n|---|---:|---:|---:|---:|---:|"]
    else:
        rows = ["| Metric | L5 tests | Complete-family BH-FDR | Strong regional signals | Negative | Positive |\n|---|---:|---:|---:|---:|---:|"]
    for metric in PRIMARY_METRICS:
        part = s["default_regions"][s["default_regions"]["metric"].eq(metric)]
        strong = part[part["strong_evidence"]]
        rows.append(
            f"| {labels[metric]} | {len(part)} | {int(part['primary_family_fdr_supported'].sum())} | "
            f"{len(strong)} | {int(strong['slope_per_decade'].lt(0).sum())} | "
            f"{int(strong['slope_per_decade'].gt(0).sum())} |"
        )
    return "\n".join(rows)


def _top_regions(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    frame = s["default_regions"][s["default_regions"]["strong_evidence"]].copy()
    scale = frame["metric"].map(
        {"intensity_fraction": 3.0, "ssi_1d": 0.015, "ssi_3d": 0.015, "ssi_7d": 0.015, "ssi_30d": 0.015}
    )
    frame["score"] = frame["slope_per_decade"].abs() / scale
    frame = frame.sort_values("score", ascending=False).head(15)
    if language == "zh":
        rows = ["| L5 | 主要国家 | 中心经纬度 | 指标 | 每10年变化 | 面积支持 | 流域数 |\n|---|---|---:|---|---:|---:|---:|"]
    else:
        rows = ["| L5 | Dominant country | Centroid | Metric | Change per 10 years | Area support | Catchments |\n|---|---|---:|---|---:|---:|---:|"]
    for row in frame.itertuples(index=False):
        digits = 2 if row.metric == "intensity_fraction" else 3
        rows.append(
            f"| {row.basin_code} | {row.dominant_countries} | {row.centroid_latitude:.1f}°, {row.centroid_longitude:.1f}° | "
            f"{labels[row.metric]} | {row.slope_per_decade:+.{digits}f} | {row.coverage_pct:.1f}% | {int(row.catchments)} |"
        )
    return "\n".join(rows)


def build_chinese(s: dict[str, Any]) -> str:
    a = s["analysis"]
    c = s["catchments"]
    r = s["regions"]
    d = s["diagnostics"]
    threshold = s["default_threshold"]
    default = next(row for row in s["threshold_rows"] if row["threshold"] == threshold)
    events = int(a["sample_counts"]["pot_q95"]["events"])
    primary_catchments = int(a["sample_counts"]["pot_q95"]["catchments"])
    robust = int(c["robust_local_trend"].sum())
    missing = c["GCIN"].nunique() * len(PRIMARY_METRICS) - len(c)
    return rf"""# 全球降雨型大洪水生成条件的长期变化（1982–2019）

**完整技术报告 · 生成日期：2026-09-02**

> **核心结果：** 单个流域是第一层研究对象。{len(c):,} 个可估计的“流域—指标”趋势中，{robust:,} 个同时满足 p value、替代极端样本方向和留一年检验；SSI 还要求四个前期时间窗方向一致。HydroBASINS 5级分区（L5）只作为扩展的区域尺度分析；在默认 ≥{threshold}% 面积支持下，得到 {default['strong_signals']} 个强区域信号，分布于 {default['strong_regions']} 个 L5。结果呈现局地增加与减少并存，而不是一个空间一致的全球方向。

## 技术摘要

- 主样本为 **{events:,} 场 POT/Q95 大洪水**，来自 **{primary_catchments:,} 个**满足长记录条件的低雪流域。
- **{c['GCIN'].nunique():,} 个流域**可估计至少一个连续生成条件指标，共得到 **{len(c):,} 项**流域—指标趋势。理论完整数为 {c['GCIN'].nunique():,} × 5 = {c['GCIN'].nunique() * 5:,}；实际少 {missing} 项，是因为部分 SSI 组合不足10个有效事件年份或首末跨度不足20年，缺失项没有被当作零趋势。
- 单流域报告斜率、95%置信区间、p value、拟合起点与终点及稳定性检验。
- L5 是第二层扩展分析。全部 **{len(r):,} 个可估计 L5—指标结果**进入一个完整区域检验族，并使用 Benjamini–Hochberg 假发现率控制（BH-FDR）。
- 默认采用 **50% L5多边形面积支持**；网页仍可选择10%、20%、30%、40%和50%，但该阈值只改变区域解释，不删除单流域结果。

![样本覆盖](assets/figure_01_sample_coverage.png)

## 1. 研究问题

研究不是寻找一个全球平均趋势，而是回答两个递进问题：哪些单个流域的大洪水生成条件发生了持续改变？这些改变是否在相邻流域之间形成更大尺度、可复核的水文空间格局？

## 2. 两层分析结构

第一层直接研究每个流域；第二层才把同一 HydroBASINS L5 内的流域汇总，检验是否出现区域共同方向。L5 不负责“筛选”单流域，也不取代单流域结论。

## 3. 研究时段与观测边界

可复用数据的共同时间范围是1982–2019。这里的“全球”指全球分布的观测网络，不表示对全球陆地面积均匀抽样；亚洲等区域的长记录站点明显偏少。

## 4. 流域入选条件

流域需有至少30个观测年份、记录覆盖率至少80%、研究期内至少10个入选事件年份，并且首末入选年份跨度至少20年。有效记录不足的流域—指标组合不展示、不检验，也不记为0。

## 5. 事件选择与生成条件分开

洪峰大小只用于选择“大洪水事件”；降雨集中度和前期土壤湿润度用于描述这些事件怎样形成。这样不会用待解释的降雨变量反过来定义事件。

## 6. POT/Q95 主样本

POT 是 Peaks Over Threshold（超阈值峰值法）。对每个流域，以该流域洪峰分布的95分位数为阈值，保留超过阈值的事件。它允许一年有多场大洪水，比每年只保留一个最大值更充分地利用事件信息。

## 7. 事件独立性

原始事件目录已经完成水文事件分离。主样本风暴径流窗口重叠数为 **{int(d.loc['pot_q95', 'stormflow_window_overlaps'])}**。相邻洪峰小于10日并不自动等于同一水文事件，因此10日间隔不再作为额外门槛。

## 8. 替代极端样本敏感性

稳健性统一比较三种替代事件样本：POT/Q90、POT/Q97.5和年度最大洪水。三者与主样本方向一致时，记为“替代极端样本方向稳定”。它把“阈值变化”和“每年一个最大值”合并为一个物理问题：结论是否依赖某一种大洪水定义？

## 9. 降雨集中度

对事件 $e$：

$$C_e=\frac{{P_{{\max,e}}}}{{P_{{\mathrm{{volume}},e}}}}$$

$P_{{\max,e}}$ 是事件期间降雨最多那一天的降雨量，$P_{{\mathrm{{volume}},e}}$ 是整场事件降雨总量。例：总降雨100 mm，其中最多的一天为42 mm，则 $C_e=0.42=42\%$。若趋势为 +8.83 个百分点/10年，且拟合起点为30%，则拟合终点约为38.83%。物理含义是：入选大洪水事件的降雨逐渐更加集中，整场降雨中落在降雨最多那一天的比例，每10年增加约8.83个百分点；不是洪水次数增加8.83%，也不是洪峰增加8.83%。

## 10. 前期土壤湿润度 SSI

事件开始前 $w$ 日的流域平均土壤饱和指数为：

$$SSI_{{e,w}}=\frac{{1}}{{w}}\sum_{{d=1}}^w SSI_{{e,-d}},\qquad w\in\{{1,3,7,30\}}$$

1日反映紧邻事件的湿润状态，30日反映较长记忆。例：某流域7日SSI均值为0.45，趋势为 +0.009/10年，表示入选大洪水发生前7日的平均湿润指数每10年增加0.009；相对于0.45约为 $100\times0.009/0.45=2.0\%$ 每10年。绝对值负责保持物理尺度，相对值仅辅助比较。

## 11. 降雨组成辅助量

同时估计最大日降雨量、事件总降雨量和降雨持续时间的原始线性趋势。相对趋势为：

$$r=100\frac{{\hat\beta}}{{\bar y}}$$

例：最大日降雨每10年增加2 mm、长期均值50 mm，则相对变化为4%/10年。若事件总降雨增加8%、最大日降雨增加2%，可以直接解释为总量增长更快，降雨集中度倾向下降；不需要对数模型。

## 12. 流域—年份年度化

同一流域同一年可能有多场POT事件，先求当年事件均值：

$$\bar y_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}}$$

例：某年3场事件的集中度为30%、45%和60%，年度值为45%，而不是让这一年因为有3场事件获得3倍趋势权重。

## 13. 单流域趋势

对每个流域的年度序列使用 Theil–Sen 中位斜率：

$$\hat\beta_i=\mathrm{{median}}_{{t_2>t_1}}\frac{{\bar y_{{it_2}}-\bar y_{{it_1}}}}{{t_2-t_1}}\times10$$

Mann–Kendall 检验给出 p value。例：$\hat\beta_i=-4.2$ 个百分点/10年表示该流域入选大洪水中“最大日降雨占整场降雨的比例”每10年下降4.2个百分点，即降雨过程趋向更长、更均匀。

## 14. 稳健单流域趋势

降雨集中度需同时满足：p value < 0.05；POT/Q90、POT/Q97.5和年度最大洪水方向都与主样本一致；逐一删除每个事件年份后方向不变。SSI 还要求1、3、7和30日窗口方向一致。满足这些条件的结果称为“稳健单流域趋势”，其余仍作为“单流域趋势估计”保留。

## 15. 单流域结果总览

{_local_table(s, 'zh')}

![单流域趋势地图](assets/figure_02_mechanism_change_maps.png)

![单流域稳健性检验与方向](assets/figure_03_strong_signal_rankings.png)

## 16. 代表性单流域结果

下表同时给出“每10年变化”和拟合起点→终点，使斜率具有直观物理含义。

{_top_individual(s, 'zh')}

## 17. 单流域空间格局

{_country_table(s, 'zh')}

这些计数显示增加与减少方向在不同国家和指标中并存。它们是观测网络中的流域级水文信号，不能按国家面积外推。

## 18. L5 是什么

HydroBASINS 是全球分级水文分区体系；level 5（L5）是其中第5级、由河网拓扑划分的中尺度水文单元。这里使用L5回答扩展问题：多个单流域变化是否共同指向一个更大水文区的变化。

## 19. 单流域怎样归入L5

用流域多边形与L5多边形的空间关系确定归属，并将落在同一L5的流域用于区域模型。单流域多边形仍在前端独立展示；归入L5不会改变其自身趋势。

## 20. 面积支持率

$$A_h=100\frac{{\operatorname{{area}}(\bigcup_i B_i\cap H_h)}}{{\operatorname{{area}}(H_h)}}$$

$B_i$ 是被观测流域多边形，$H_h$ 是L5多边形。例：L5面积10,000 km²，观测流域在其内部的并集面积为5,600 km²，则面积支持率为56%，通过默认50%阈值。若一个大流域独自覆盖90%，它可以代表该L5的大部分面积，但区域面板会明确标记为“单流域代表”，而非多流域共同佐证。

## 21. 面积阈值敏感性

{_threshold_table(s, 'zh')}

![面积阈值敏感性](assets/figure_05_physical_decomposition.png)

50%是默认解释门槛；10%–40%用于交互式查看覆盖—数量权衡。没有进入区域层的流域仍完整保留在单流域层。

## 22. L5 区域趋势模型

对包含多个流域的L5拟合：

$$y_{{it}}=\alpha_i+\beta_h\frac{{t-2000}}{{10}}+\varepsilon_{{it}}$$

$\alpha_i$ 吸收每个流域长期平均水平的差异，$\beta_h$ 表示同一L5中各流域相对于自身常态的共同每10年变化。例：上游流域平均集中度30%、下游55%，固定效应不会把两者基线差异误当成时间趋势，只利用各自随时间的变化。

## 23. 单流域代表的L5

若一个观测流域独自覆盖L5的至少50%，区域趋势直接继承该流域趋势，并标记为 single-catchment representation。该结果说明“大部分L5面积由这个已观测流域代表”，不声称存在多流域一致性。

## 24. 年份中心化

$x=(t-2000)/10$ 只是把年份换算为“相距2000年多少个十年”，使截距和数值计算更稳定。2000不是断点，模型没有比较2000年前后；换成1990或2010不会改变斜率。

## 25. L5 的 BH-FDR

只有L5层使用 Benjamini–Hochberg false discovery rate（BH-FDR）。将完整区域检验族的 $m$ 个 p values 排序，找最大 $k$ 满足：

$$p_{{(k)}}\le\frac{{k}}{{m}}\alpha,\qquad\alpha=0.05$$

并把 $p_{{(1)}}\ldots p_{{(k)}}$ 判为通过。例：若490个实际无趋势的检验都单独用 p<0.05，平均可能出现 $490\times0.05=24.5$ 个偶然显著；BH-FDR用于控制被报告区域发现中的预期错误比例。

## 26. 强区域信号的完整条件

降雨集中度需通过：当前面积支持阈值、完整L5检验族BH-FDR、三种替代极端样本方向一致、留一流域方向稳定。SSI 再增加四个湿润时间窗方向一致。条件数量随指标而定，不人为凑成固定“五门”。

## 27. 默认50%阈值下的区域结果

{_regional_table(s, 'zh')}

![L5区域趋势](assets/figure_04_mechanism_trajectories.png)

## 28. 强区域信号位于哪里

{_top_regions(s, 'zh')}

表中的正负号分别表示降雨更集中/更分散，或洪水发生前更湿/更干。区域信号仍有相反方向，因此结论是局地和区域异质性，而非全球统一变化。

## 29. 从L5回看贡献流域

![区域与贡献流域](assets/figure_06_robustness_matrix.png)

区域估计必须能追溯到贡献流域。多流域区域信号说明若干流域相对于自身常态共同移动；单流域代表则明确显示其面积覆盖率。两者不会被混写。

## 30. 水文学结论

1. 全球观测网络中的多数流域没有满足完整稳健性条件的长期生成条件变化，说明变化并非普遍或空间一致。
2. {robust:,} 个稳健单流域趋势揭示了真正值得关注的局地改变：部分流域的大洪水降雨变得更集中，部分变得更均匀；前期土壤状态也同时存在变湿和变干。
3. 在默认50%面积支持下，{default['strong_regions']} 个L5表现出可复核的较大尺度共同格局，说明其中一些变化不是孤立测站现象。
4. 科学结果应回答“哪些流域、哪些L5、哪种生成条件、向什么方向改变”，而不是用相反方向互相抵消后的全球平均。

## 31. 局限性

观测网络空间不均匀，亚洲尤其稀疏；日尺度降雨集中度不能表示小时级峰值结构；SSI和事件重建存在测量误差；L5之间可能空间相关；面积支持率衡量的是水文空间覆盖，不是人口、资产或全球面积代表性。趋势描述生成条件，不等于洪水次数、洪峰或径流量趋势，也不单独证明气候变化、土地利用或工程调控的因果作用。
"""


def build_english(s: dict[str, Any]) -> str:
    a = s["analysis"]
    c = s["catchments"]
    r = s["regions"]
    d = s["diagnostics"]
    threshold = s["default_threshold"]
    default = next(row for row in s["threshold_rows"] if row["threshold"] == threshold)
    events = int(a["sample_counts"]["pot_q95"]["events"])
    primary_catchments = int(a["sample_counts"]["pot_q95"]["catchments"])
    robust = int(c["robust_local_trend"].sum())
    missing = c["GCIN"].nunique() * len(PRIMARY_METRICS) - len(c)
    return rf"""# Long-term changes in rainfall-driven large-flood generating conditions (1982–2019)

**Complete technical report · generated 2026-09-02**

> **Main result.** Individual catchments are the first-level research objects. Among {len(c):,} estimable catchment–metric trends, {robust:,} satisfy the p-value, alternative-extreme-sample, and leave-one-year-out checks; SSI additionally requires agreement across all antecedent windows. HydroBASINS level 5 (L5) is a separate, expanded regional analysis. At the default ≥{threshold}% area support, {default['strong_signals']} strong regional signals occur in {default['strong_regions']} L5 units. Local increases and decreases coexist; the result is not one spatially uniform global direction.

## Technical summary

- The primary sample contains **{events:,} POT/Q95 large-flood events** from **{primary_catchments:,}** eligible long-record, low-snow catchments.
- At least one continuous condition trend is estimable in **{c['GCIN'].nunique():,} catchments**, producing **{len(c):,} catchment–metric estimates**. A complete grid would contain {c['GCIN'].nunique():,} × 5 = {c['GCIN'].nunique() * 5:,}; the {missing} missing combinations lack 10 valid event years or a 20-year first-to-last span and are not coded as zero.
- Catchment results report slopes, confidence intervals, p values, fitted endpoints, and stability checks.
- L5 is the second-level expanded analysis. All **{len(r):,} estimable L5–metric results** enter one complete regional testing family with Benjamini–Hochberg false discovery rate control (BH-FDR).
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

The source event catalogue already separates hydrological events. Primary-sample stormflow-window overlaps equal **{int(d.loc['pot_q95', 'stormflow_window_overlaps'])}**. A peak interval shorter than 10 days does not by itself prove that two reconstructed hydrological events are dependent, so a 10-day gap is not retained as an additional evidence gate.

## 8. Alternative extreme-sample sensitivity

One combined check compares POT/Q90, POT/Q97.5, and annual maxima with the primary POT/Q95 result. Passing means that all three alternatives preserve the main slope direction. This directly asks whether the conclusion depends on one particular definition of a large flood.

## 9. Rainfall concentration

For event $e$:

$$C_e=\frac{{P_{{\max,e}}}}{{P_{{\mathrm{{volume}},e}}}}$$

$P_{{\max,e}}$ is rainfall on the wettest day and $P_{{\mathrm{{volume}},e}}$ is total event rainfall. If an event contains 100 mm and its wettest day supplies 42 mm, $C_e=0.42=42\%$. A trend of +8.83 percentage points per 10 years with a fitted starting level of 30% implies a fitted ending level near 38.83%. Physically, a larger share of event rainfall falls on the wettest day; it is not an 8.83% change in flood count or peak discharge.

## 10. Antecedent Soil Saturation Index (SSI)

For an antecedent window $w$:

$$SSI_{{e,w}}=\frac1w\sum_{{d=1}}^w SSI_{{e,-d}},\qquad w\in\{{1,3,7,30\}}$$

One day represents immediate pre-event wetness; 30 days represents longer memory. If mean 7-day SSI is 0.45 and the slope is +0.009 per 10 years, selected floods occur after conditions that become 0.009 SSI units wetter per decade. The auxiliary relative change is $100\times0.009/0.45=2.0\%$ per 10 years.

## 11. Supporting rainfall components

Maximum daily rainfall, total event rainfall, and precipitation duration are fitted in raw units. Their auxiliary relative slope is:

$$r=100\frac{{\hat\beta}}{{\bar y}}$$

For example, +2 mm per 10 years around a 50 mm mean equals +4% per 10 years. If total rainfall increases by 8% while the daily maximum increases by 2%, total rainfall grows faster and concentration tends to decline. No logarithmic trend model is needed.

## 12. Catchment-year annualization

Multiple selected events in one catchment-year are averaged:

$$\bar y_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}}$$

For example, three events with concentrations of 30%, 45%, and 60% produce one annual value of 45%. The year does not receive three times the trend weight merely because it contains three events.

## 13. Individual-catchment trend

The Theil–Sen median slope is:

$$\hat\beta_i=\mathrm{{median}}_{{t_2>t_1}}\frac{{\bar y_{{it_2}}-\bar y_{{it_1}}}}{{t_2-t_1}}\times10$$

Mann–Kendall supplies the p value. A concentration slope of −4.2 percentage points per 10 years means that the fraction of event rainfall falling on the wettest day decreases by 4.2 points per decade: selected large floods are shifting toward longer, more evenly distributed rainfall.

## 14. Robust individual trend

Rainfall concentration requires p value < 0.05, direction agreement under POT/Q90, POT/Q97.5, and annual maxima, and direction stability after removing every observed event year in turn. SSI additionally requires agreement across the 1-, 3-, 7-, and 30-day windows. Results passing these conditions are “robust individual trends”; all other estimable results remain “individual trend estimates.”

## 15. Individual results overview

{_local_table(s, 'en')}

![Individual catchment trend maps](assets/figure_02_mechanism_change_maps.png)

![Individual robustness checks and directions](assets/figure_03_strong_signal_rankings.png)

## 16. Representative individual results

The fitted start → end column gives each per-decade slope a direct physical interpretation.

{_top_individual(s, 'en')}

## 17. Geographical distribution of individual trends

{_country_table(s, 'en')}

Increasing and decreasing directions coexist across countries and metrics. These are catchment-scale hydrological observations and cannot be extrapolated by national land area.

## 18. What L5 means

HydroBASINS is a nested global hydrological partition. Level 5 (L5) is its fifth, river-network-defined intermediate spatial level. Here L5 asks whether individual changes form a larger hydrological pattern.

## 19. Assigning catchments to L5

Catchment polygons are spatially matched to L5 polygons. Catchments assigned to the same unit enter the regional model, while every catchment remains independently available in the primary map layer.

## 20. Area support

$$A_h=100\frac{{\operatorname{{area}}(\bigcup_i B_i\cap H_h)}}{{\operatorname{{area}}(H_h)}}$$

If an L5 unit covers 10,000 km² and observed catchment polygons cover a 5,600 km² union inside it, support is 56% and passes the default 50% threshold. One catchment covering 90% can represent most of the L5 area, but is explicitly labelled as a single-catchment representation rather than multi-catchment corroboration.

## 21. Area-threshold sensitivity

{_threshold_table(s, 'en')}

![Area-threshold sensitivity](assets/figure_05_physical_decomposition.png)

Fifty percent is the default interpretation threshold. The lower controls expose the spatial-coverage trade-off; they never remove underlying individual trends.

## 22. L5 regional trend model

For a multi-catchment L5 unit:

$$y_{{it}}=\alpha_i+\beta_h\frac{{t-2000}}{{10}}+\varepsilon_{{it}}$$

$\alpha_i$ absorbs each catchment's persistent mean level and $\beta_h$ estimates their common within-catchment change per 10 years. If upstream concentration averages 30% and downstream concentration 55%, their baseline difference is not mistaken for temporal change.

## 23. Single-catchment L5 representation

When one observed catchment alone covers at least 50% of an L5 unit, the regional value inherits that catchment trend and is labelled `single-catchment representation`. It supports spatial representation of most of the polygon, not multi-catchment agreement.

## 24. Centering the year

$x=(t-2000)/10$ expresses time in decades from 2000. The constant stabilizes calculation and interpretation of the intercept. It is not a breakpoint, and replacing 2000 with 1990 or 2010 does not change the slope.

## 25. L5 BH-FDR

Only the L5 layer applies the Benjamini–Hochberg false discovery rate procedure (BH-FDR). Sort the complete regional family's $m$ p values and find the largest $k$ satisfying:

$$p_{{(k)}}\le\frac{{k}}{{m}}\alpha,\qquad\alpha=0.05$$

If 490 tests were all null and each used p<0.05 alone, about $490\times0.05=24.5$ chance-positive tests would be expected. BH-FDR limits the expected false proportion among reported regional discoveries.

## 26. Complete conditions for a strong regional signal

Rainfall concentration must pass the selected area support, complete-family L5 BH-FDR, direction agreement across the three alternative extreme samples, and leave-one-catchment-out stability. SSI additionally requires direction agreement across all four antecedent windows. The number of checks follows the metric rather than being forced into a fixed “five-gate” label.

## 27. Regional results at the default 50% threshold

{_regional_table(s, 'en')}

![L5 regional trends](assets/figure_04_mechanism_trajectories.png)

## 28. Where the strong regional signals occur

{_top_regions(s, 'en')}

Positive and negative signs respectively mean more concentrated/more distributed rainfall or wetter/drier antecedent conditions. Opposing directions remain, supporting regional heterogeneity rather than one global trend.

## 29. Tracing L5 results back to catchments

![Regional estimates and contributing catchments](assets/figure_06_robustness_matrix.png)

Every regional estimate remains traceable to its contributing catchments. Multi-catchment results show shared within-catchment movement; single-catchment representations explicitly show their area coverage. The two interpretations are kept distinct.

## 30. Hydrological conclusions

1. Most observed catchments do not satisfy the complete robustness conditions for a persistent shift, so change is neither ubiquitous nor spatially uniform.
2. The {robust:,} robust individual trends identify locally meaningful changes: selected large floods become more concentrated in some catchments and more evenly distributed in others, while antecedent conditions become wetter in some places and drier in others.
3. At 50% area support, {default['strong_regions']} L5 units show reproducible larger-scale patterns, demonstrating that some local changes are not isolated gauge phenomena.
4. The scientifically useful result is where, in which condition, and in which direction a catchment or L5 changes—not a global mean that cancels opposing signals.

## 31. Limitations

The network is spatially uneven and especially sparse in Asia; daily concentration cannot resolve sub-daily rainfall structure; SSI and event reconstruction contain measurement error; neighbouring L5 units may be dependent; and area support measures hydrological polygon coverage rather than population, assets, or global land representativeness. These trends describe generating conditions, not flood counts, peaks, or runoff volume, and do not alone establish attribution to climate change, land use, or engineering controls.
"""


def build_reports() -> dict[str, Any]:
    s = _stats()
    REPORTS.mkdir(parents=True, exist_ok=True)
    zh = REPORTS / "global_flood_cause_evolution.md"
    en = REPORTS / "global_flood_cause_evolution_en.md"
    zh.write_text(build_chinese(s), encoding="utf-8")
    en.write_text(build_english(s), encoding="utf-8")
    return {
        "status": "complete",
        "chinese": str(zh),
        "english": str(en),
        "robust_catchment_trends": int(s["catchments"]["robust_local_trend"].sum()),
        "regional_strong_signals": int(s["default_regions"]["strong_evidence"].sum()),
    }


if __name__ == "__main__":
    print(json.dumps(build_reports(), indent=2, ensure_ascii=False))
