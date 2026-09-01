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
    support = pd.read_csv(
        TABLES / "spatial_support" / "l5_spatial_support_audit.csv"
    ).rename(columns={"hybas_id_l5": "HYBAS_ID"})
    regions = regions.merge(
        support[["HYBAS_ID", "coverage_pct", "observed_union_inside_km2"]],
        on="HYBAS_ID",
        how="left",
    )
    sensitivity = pd.read_csv(
        TABLES / "spatial_support" / "l5_spatial_support_threshold_sensitivity.csv"
    )
    thresholds = list(local["area_coverage_threshold_options_percent"])
    threshold_rows = []
    global_area = sensitivity[
        sensitivity["scope"].eq("Global")
        & sensitivity["metric"].eq("coverage_fraction")
    ].set_index("threshold_pct")
    us_area = sensitivity[
        sensitivity["scope"].eq("United States")
        & sensitivity["metric"].eq("coverage_fraction")
    ].set_index("threshold_pct")
    for threshold in thresholds:
        available = regions[regions["coverage_pct"].ge(threshold)]
        threshold_rows.append(
            {
                "threshold": threshold,
                "audit_l5": int(global_area.loc[threshold, "passing_l5"]),
                "mappable_l5": int(available["HYBAS_ID"].nunique()),
                "catchments": int(global_area.loc[threshold, "passing_catchments"]),
                "catchment_share": float(
                    global_area.loc[threshold, "passing_catchment_share_pct"]
                ),
                "us_catchment_share": float(
                    us_area.loc[threshold, "passing_catchment_share_pct"]
                ),
                "strong_signals": int(available["strong_evidence"].sum()),
                "strong_regions": int(
                    available.loc[available["strong_evidence"], "HYBAS_ID"].nunique()
                ),
            }
        )
    default_threshold = int(local["default_area_coverage_threshold_percent"])
    default_regions = regions[regions["coverage_pct"].ge(default_threshold)]
    return {
        "analysis": analysis,
        "local": local,
        "diagnostics": diagnostics,
        "catchments": catchments,
        "regions": regions,
        "support": support,
        "threshold_rows": threshold_rows,
        "default_threshold": default_threshold,
        "default_regions": default_regions,
    }


def _threshold_table(s: dict[str, Any], language: str) -> str:
    if language == "zh":
        header = "| L5面积覆盖阈值 | 有空间支持的L5 | 有趋势结果的L5 | 位于这些L5的流域 | 全球流域占比 | 美国流域占比 | 强区域信号 | 涉及L5 |\n|---:|---:|---:|---:|---:|---:|---:|---:|"
    else:
        header = "| L5 area threshold | Spatially supported L5 | L5 with trend estimates | Catchments inside passing L5 | Global catchment share | US catchment share | Strong regional signals | L5 with strong signals |\n|---:|---:|---:|---:|---:|---:|---:|---:|"
    rows = [header]
    for row in s["threshold_rows"]:
        rows.append(
            f"| {row['threshold']}% | {row['audit_l5']} | {row['mappable_l5']} | "
            f"{row['catchments']:,} | {row['catchment_share']:.1f}% | "
            f"{row['us_catchment_share']:.1f}% | {row['strong_signals']} | "
            f"{row['strong_regions']} |"
        )
    return "\n".join(rows)


def _local_table(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    frame = s["catchments"]
    if language == "zh":
        rows = ["| 指标 | 可估计流域 | 未校正 p<0.05 | 稳定候选 | 变量内FDR | 候选负向 | 候选正向 |\n|---|---:|---:|---:|---:|---:|---:|"]
    else:
        rows = ["| Metric | Estimable catchments | Unadjusted p<0.05 | Stable candidates | Metric-wide FDR | Negative candidates | Positive candidates |\n|---|---:|---:|---:|---:|---:|---:|"]
    for metric in PRIMARY_METRICS:
        part = frame[frame["variable"].eq(metric)]
        candidate = part[part["potential_local_shift"]]
        rows.append(
            f"| {labels[metric]} | {len(part):,} | {int(part['mk_p'].lt(0.05).sum())} | "
            f"{int(candidate.shape[0])} | {int(part['metric_fdr_supported'].sum())} | "
            f"{int(candidate['display_slope_per_decade'].lt(0).sum())} | "
            f"{int(candidate['display_slope_per_decade'].gt(0).sum())} |"
        )
    return "\n".join(rows)


def _regional_table(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    frame = s["default_regions"]
    if language == "zh":
        rows = ["| 指标 | L5检验 | 完整区域族FDR | 强区域信号 | 负向 | 正向 |\n|---|---:|---:|---:|---:|---:|"]
    else:
        rows = ["| Metric | L5 tests | Complete-family FDR | Strong regional signals | Negative | Positive |\n|---|---:|---:|---:|---:|---:|"]
    for metric in PRIMARY_METRICS:
        part = frame[frame["metric"].eq(metric)]
        strong = part[part["strong_evidence"]]
        rows.append(
            f"| {labels[metric]} | {len(part)} | {int(part['primary_family_fdr_supported'].sum())} | "
            f"{len(strong)} | {int(strong['slope_per_decade'].lt(0).sum())} | "
            f"{int(strong['slope_per_decade'].gt(0).sum())} |"
        )
    return "\n".join(rows)


def _top_regions(s: dict[str, Any], language: str) -> str:
    labels = LABELS_ZH if language == "zh" else LABELS_EN
    frame = s["default_regions"]
    frame = frame[frame["strong_evidence"]].copy()
    scale = frame["metric"].map(
        {"intensity_fraction": 3.0, "ssi_1d": 0.015, "ssi_3d": 0.015, "ssi_7d": 0.015, "ssi_30d": 0.015}
    )
    frame["score"] = frame["slope_per_decade"].abs() / scale
    frame = frame.sort_values("score", ascending=False).head(12)
    if language == "zh":
        rows = ["| L5 | 指标 | 方向 | 每十年变化 | 95% CI | 面积支持 | 流域数 |\n|---|---|---|---:|---:|---:|---:|"]
        direction = lambda value: "增加" if value > 0 else "减少"
    else:
        rows = ["| L5 | Metric | Direction | Change per decade | 95% CI | Area support | Catchments |\n|---|---|---|---:|---:|---:|---:|"]
        direction = lambda value: "increase" if value > 0 else "decrease"
    for row in frame.itertuples(index=False):
        digits = 2 if row.metric == "intensity_fraction" else 3
        rows.append(
            f"| {row.basin_code} | {labels[row.metric]} | {direction(row.slope_per_decade)} | "
            f"{row.slope_per_decade:+.{digits}f} | {row.ci_low:+.{digits}f} to {row.ci_high:+.{digits}f} | "
            f"{row.coverage_pct:.1f}% | {int(row.catchments)} |"
        )
    return "\n".join(rows)


def build_chinese(s: dict[str, Any]) -> str:
    a = s["analysis"]
    l = s["local"]
    d = s["diagnostics"]
    c = s["catchments"]
    threshold = s["default_threshold"]
    default = next(row for row in s["threshold_rows"] if row["threshold"] == threshold)
    return (fr"""# 全球降雨型大洪水生成条件的长期变化（1982–2019）

**技术报告 · 生成日期：2026-09-01**

## 技术摘要

- 研究首先在单个流域内判断大洪水生成条件是否发生持续变化，再检验这些局地信号是否在 HydroBASINS L5 内形成更大尺度的一致模式。
- 主样本包含 **{a['sample_counts']['pot_q95']['events']:,} 场** POT/Q95 大洪水和 **{a['sample_counts']['pot_q95']['catchments']:,} 个**长记录低雪流域；其中 **{c['GCIN'].nunique():,} 个流域**具有足够的所选事件年份，可估计至少一个主指标的单流域趋势。
- 五个连续主指标形成 **{len(c):,} 个流域—指标检验**。共有 **{int(c['potential_local_shift'].sum()):,} 个稳定候选**，但 **没有单流域信号通过变量内5% FDR**。因此目前的严格结论是：多数流域没有可由该观测网络稳定确认的长期生成条件变化；候选位置用于后续复核，而不是确证清单。
- 区域层在全部 {l['primary_family_tests']:,} 个 L5—指标检验中有 **{l['primary_family_fdr_signals']} 个**通过完整区域族 FDR，**{l['strong_evidence_signals']} 个**同时通过事件样本、SSI时间窗和留一检验。默认 **≥{threshold}%** 面积支持后，保留 **{default['strong_signals']} 个强区域信号，分布于 {default['strong_regions']} 个 L5**。
- 面积阈值只限制区域解释，不删除单流域结果。网页允许在 10%、20%、30%、40% 和 50% 之间动态切换。

![样本覆盖](assets/figure_01_sample_coverage.png)

该图给出研究能够回答问题的观测范围。欧洲和北美明显更密集，因此“全球”指全球分布的可用测站网络，不等于按全球陆地面积加权的总体。

## 1. 研究问题

研究对象是**大洪水发生时的生成条件是否随时间改变**。具体观察两条连续过程维度：事件降雨是否变得更集中或更持久，以及事件开始前流域是否变得更湿或更干。

## 2. 推断顺序

证据按以下顺序形成：

1. 对每个合格流域分别构建大洪水事件样本；
2. 在该流域内部估计连续时间趋势；
3. 保留无趋势、弱证据和稳定候选，不以颜色替代显著性；
4. 将出口位于同一 L5 的流域作为区域汇总；
5. 用面积覆盖率判断该汇总是否有足够空间支持被解释为 L5 模式。

## 3. 已验证的研究时段

洪水事件、日降雨/径流和 GLASS-AVHRR 土壤湿度共同可用的时段为 **1982–2019**。所有时间趋势均使用这一连续记录，不人为设置年份断点。

## 4. 流域总体

流域需满足长期雪贡献小于 0.10、两个季节事件目录均存在、至少30个观测事件年、记录跨度至少30年且年度覆盖率至少80%。通过记录筛选的流域有 **{a['eligible_record_catchments']:,} 个**。

## 5. 事件选择与条件描述相互独立

事件是否进入极端样本由洪峰决定；进入样本以后，才计算降雨集中度和前期湿润度。因此较大的降雨集中度不会提高事件被选中的概率，也不会构成循环定义。

## 6. 主事件样本：流域自身 POT/Q95

对流域 $i$ 的全部重建事件洪峰 $Q_{{ie}}$ 计算长期95%分位数 $Q_{{0.95,i}}$：

$$
\\mathcal E_i^{{95}}=\{{e:Q_{{ie}}\\ge Q_{{0.95,i}}\}}.
$$

每个流域至少需要10场所选事件，且最早和最晚所选事件相距至少20年。主样本最终为 **{a['sample_counts']['pot_q95']['events']:,} 场、{a['sample_counts']['pot_q95']['catchments']:,} 个流域**。

## 7. 为什么不只使用年最大洪水

年最大值强制每年贡献一场事件，可能把相对普通年份的最大洪水与真正极端洪水放在同一总体。POT/Q95更直接地对应每个流域的上尾事件；年最大样本仍作为敏感性分支。

## 8. 极端样本敏感性

四个替代样本为 POT/Q90、POT/Q97.5、10日去簇 POT/Q95 和年最大洪水。主样本中有 {int(d.loc['pot_q95','pairs_under_10_days']):,} 对相邻洪峰间隔小于10日；去簇样本将该数量降为 {int(d.loc['pot_q95_gap10','pairs_under_10_days'])}。事件风暴径流窗口重叠数为 {int(d.loc['pot_q95','stormflow_window_overlaps'])}。

## 9. 降雨集中度

对事件 $e$：

$$
C_{{ie}}=\frac{{P_{{\max,ie}}}}{{P_{{\mathrm{{volume}},ie}}}}.
$$

$P_{{\max}}$ 是事件降雨窗口内最大日降雨，$P_{{\mathrm{{volume}}}}$ 是整个事件降雨总量。$C$ 增加表示更多事件降雨集中在最湿一天；$C$ 减少表示事件降雨更持久、总量相对更重要。主推断始终使用连续 $C$，不使用二元“强度主导型”标签。

## 10. 前期湿润度 SSI

设 $SSI_{{i,t-k}}$ 为降雨开始前第 $k$ 个完整日的土壤饱和指数，则窗口 $w$ 的指标为：

$$
SSI_{{ie}}^{{(w)}}=\frac1w\sum_{{k=1}}^w SSI_{{i,t_{{0,ie}}-k}},
\qquad w\in\{{1,3,7,30\}}.
$$

正趋势表示大洪水发生前的流域状态长期变湿，负趋势表示长期变干。它不是降雨量、洪峰或体积含水率百分比。

## 11. 降雨物理分量

最大日降雨、事件总降雨和降雨持续时间直接以毫米或日为单位拟合。其相对变化仅由原始线性斜率除以相应长期均值获得：

$$
r=100\frac{{\widehat\beta}}{{\bar y}}.
$$

这里不使用对数模型。分量用于解释降雨集中度为何变化，不单独承担“洪水原因”的因果归因。

## 12. 为什么先按流域—年份汇总

同一流域一年可能出现多场 POT 事件。首先计算：

$$
\bar y_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}}.
$$

这样每个有观测的事件年获得相同时间权重，避免某一年因为事件较多而主导趋势。

## 13. 单流域趋势

对每个流域的年度序列使用 Theil–Sen 斜率：

$$
\widehat\beta_i=\operatorname{{median}}_{{t_j>t_k}}
\frac{{\bar y_{{it_j}}-\bar y_{{it_k}}}}{{t_j-t_k}}\times10.
$$

并使用含并列值修正的 Mann–Kendall 检验判断是否存在单调趋势。至少需要10个有事件的年份，且这些年份跨度至少20年。

## 14. 单流域多重检验

每个物理指标分别形成一个跨流域的 Benjamini–Hochberg 检验族。将 $m$ 个 p 值排序为 $p_{{(1)}}\le\cdots\le p_{{(m)}}$，寻找最大的 $k$ 满足：

$$
p_{{(k)}}\le\frac{{k}}{{m}}\alpha,
\qquad \alpha=0.05.
$$

该步骤控制同一指标地图中被拒绝原假设集合的预期错误发现比例。

## 15. 单流域稳定候选

“稳定候选”同时要求主样本未校正 $p<0.05$，POT/Q90 与 POT/Q97.5 方向一致，10日去簇方向一致，年最大样本方向一致，留一年后方向不变；SSI 还需四个时间窗方向一致。候选是有针对性的后续研究对象，不等于通过 FDR 的严格信号。

![单流域空间结果](assets/figure_02_mechanism_change_maps.png)

图中浅色位置是可估计的单流域趋势，描边位置是稳定候选。所有方向均保留；没有用分类阈值把连续变化压缩成“有/无机制”。

## 16. 单流域结果

{_local_table(s, 'zh')}

## 17. 单流域主要结论

共有 **{int(c['potential_local_shift'].sum()):,} 个稳定候选**，同时包含增加和减少方向；**变量内 FDR 通过数为0**。因此本研究不支持“全球大多数流域都存在长期生成条件变化”，而支持“多数流域缺少严格长期证据，少数位置值得进一步核验”。

![单流域证据漏斗](assets/figure_03_strong_signal_rankings.png)

该图将未校正显著、稳定候选和 FDR 证据分开，避免把稳健性和多重检验混为同一概念。

## 18. L5 是第二层空间问题

L5 分析回答：多个局地流域的变化是否可能属于同一个更大尺度水文现象。它不决定一个单流域结果是否有价值，也不覆盖或删除单流域图层。

## 19. 流域到 L5 的对应

每个流域通过出口经纬度对应到 HydroBASINS v1.c L5。主样本中 {l['matched_catchments']:,} 个流域匹配成功；2个毛里求斯流域没有匹配到当前 L5 参考边界，但仍保留单流域结果。

## 20. L5 面积支持率

设 $H_j$ 为 L5 多边形，$A_i$ 为出口落在该 L5 的合格流域多边形，则：

$$
Coverage_j=
\frac{{Area\left(H_j\cap\bigcup_{{i\in j}}A_i\right)}}{{Area(H_j)}}.
$$

计算使用 EPSG:6933 等面积投影，并先修复无效 polygon。重叠流域通过几何并集只计一次。

## 21. 动态面积阈值

{_threshold_table(s, 'zh')}

10%门槛用于网页默认视图，以保留较广的区域探索范围；20%–50%允许读者检验结论如何随空间代表性要求收紧。阈值是空间解释条件，不是统计显著性条件。

![面积阈值敏感性](assets/figure_05_physical_decomposition.png)

图中下降曲线定量展示区域代表性与样本保留之间的取舍。美国的 L5 划分较碎，因此相同阈值下保留比例低于全球观测网络。

## 22. 多流域 L5 模型

对至少两个贡献流域的 L5，拟合流域固定效应趋势：

$$
\bar y_{{it}}=\alpha_i+\beta_j x_{{it}}+\varepsilon_{{it}},
\qquad x_{{it}}=\frac{{year_{{it}}-2000}}{{10}}.
$$

$\alpha_i$ 控制不同流域长期水平差异，$\beta_j$ 表示该 L5 内共同的每十年变化。标准误按流域聚类并使用 $t(G-1)$ 参考。

## 23. 单流域占据一个 L5 的情况

若一个 L5 只有一个贡献流域但面积支持率达到所选阈值，则区域面板直接继承该流域的 Theil–Sen 结果，并标记为“单流域代表”。它说明该流域覆盖该 L5 的空间比例足够高，但不构成多个流域相互验证。

## 24. 年份中心化中的2000

2000只用于将时间变量中心化。替换为1990或2010不会改变斜率；模型没有把2000年视为突变点，也没有进行2000年前后分段比较。

## 25. 完整区域检验族

全部 {l['primary_family_tests']:,} 个“可估计 L5 × 五个主指标”共同进入一个 BH FDR 检验族。完整族比按指标分别校正更保守，目的是避免从多个空间单元和多个湿润度时间窗中挑选偶然显著结果。

## 26. 五个区域证据门

网页中的强区域信号同时满足：

1. 当前所选 L5 面积支持率；
2. 完整区域族 5% FDR；
3. 四个替代极端事件样本方向一致；
4. SSI 的1/3/7/30日时间窗方向一致（降雨集中度该项自动满足）；
5. 多流域 L5 留一流域后方向不变；单流域代表则使用留一年检验。

## 27. 默认10%面积支持下的区域结果

{_regional_table(s, 'zh')}

![面积支持后的区域模式](assets/figure_04_mechanism_trajectories.png)

区域层同时出现正向和负向结果。它说明一些局地变化在空间上可以聚合为共享方向，但不支持统一的全球平均变化方向。

## 28. 最强区域结果

{_top_regions(s, 'zh')}

## 29. 区域结果如何回到单流域

![区域与贡献流域](assets/figure_06_robustness_matrix.png)

灰点是同一 L5 内各单流域斜率，菱形及区间是 L5 共同斜率和95%置信区间。区域显著不要求每一个单流域独立显著；它利用方向相近的多流域年度变化提高检验能力。

## 30. 支持的科学结论

1. 多数可估计单流域没有通过网络范围的严格长期趋势证据；
2. 378个稳定候选提供了明确的后续复核位置；
3. 一些候选及弱单流域变化在 L5 中形成统计上更清晰的共享方向；
4. 区域信号随面积支持阈值收紧而减少，但方向相反的局地模式始终并存。

## 31. 不能由当前设计推出的结论

结果不能直接解释为洪水发生次数、洪峰或洪量的变化，也不能直接归因于人为气候变化、土地利用或工程调控。面积覆盖率衡量观测空间支持，不衡量人口、资产或全球陆地代表性。

## 32. 主要限制

亚洲长期流域明显不足；降雨集中度只有日尺度分辨率；SSI 和重建降雨误差会进入事件指标；L5 之间可能存在空间相关；聚类稳健推断在流域数很少时仍不精确。单流域候选尤其需要独立数据或更长记录复核。

## 33. 下一步

优先对稳定候选和强 L5 信号开展原始时间序列复核、独立降雨/土壤湿度产品验证和局地机制解释；随后再评估更细 HydroBASINS 层级是否能在保持较高面积支持率的同时提高空间分辨率。

## 34. 可复现入口

```powershell
$projectPython = 'D:/Program Files/python-envs/Global_Flood_Cause_Evolution/Scripts/python.exe'
& $projectPython src/run_pipeline.py --stage all --force
& $projectPython src/validate_outputs.py
```

源项目 `Event_Typology` 按只读路径复用；本仓库保存方法、派生结果、图表、报告和 GitHub Pages 数据。交互网页：<https://grups666.github.io/Global_Flood_Cause_Evolution/>。
""").replace(chr(92) * 2, chr(92))


def build_english(s: dict[str, Any]) -> str:
    a = s["analysis"]
    l = s["local"]
    d = s["diagnostics"]
    c = s["catchments"]
    threshold = s["default_threshold"]
    default = next(row for row in s["threshold_rows"] if row["threshold"] == threshold)
    return (fr"""# Long-Term Changes in Rainfall-Driven Large-Flood Generating Conditions (1982–2019)

**Technical report · generated 2026-09-01**

## Technical summary

- Evidence is constructed in two stages: direct trends are estimated for every eligible catchment, and HydroBASINS L5 is then used to test whether nearby catchments form a larger coherent pattern.
- The primary sample contains **{a['sample_counts']['pot_q95']['events']:,} POT/Q95 floods in {a['sample_counts']['pot_q95']['catchments']:,} long-record low-snow catchments**. At least one primary direct trend is estimable in **{c['GCIN'].nunique():,} catchments**.
- The five continuous outcomes produce **{len(c):,} catchment–metric tests**. There are **{int(c['potential_local_shift'].sum()):,} directionally stable candidates**, but **no direct catchment signal passes metric-wide 5% FDR**. The strict result is therefore that most catchments do not show a network-confirmed long-term shift; candidates identify locations for targeted follow-up.
- Among {l['primary_family_tests']:,} L5–metric tests, **{l['primary_family_fdr_signals']} pass complete-family FDR and {l['strong_evidence_signals']} pass the full statistical robustness screen**. With the default **≥{threshold}% area support**, **{default['strong_signals']} strong regional signals remain in {default['strong_regions']} L5 units**.
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

Catchments require long-term snow fraction below 0.10, both seasonal event catalogues, at least 30 observed event years, at least a 30-year record span, and at least 80% annual coverage. **{a['eligible_record_catchments']:,} catchments** pass this record screen.

## 5. Event selection is separate from condition description

Flood peak selects the extreme-event sample. Rainfall concentration and antecedent wetness are calculated only after selection, avoiding a circular definition in which the outcome also determines inclusion.

## 6. Primary population: catchment-specific POT/Q95

For catchment $i$, the retained events are:

$$
\\mathcal E_i^{{95}}=\{{e:Q_{{ie}}\\ge Q_{{0.95,i}}\}}.
$$

Each catchment requires at least 10 selected events spanning at least 20 years. The final primary sample contains **{a['sample_counts']['pot_q95']['events']:,} events in {a['sample_counts']['pot_q95']['catchments']:,} catchments**.

## 7. Why annual maxima are a sensitivity population

Annual maxima force one event into every year, even when that event is not particularly extreme relative to the catchment record. POT/Q95 directly targets the catchment upper tail, while annual maxima remain an important alternative definition.

## 8. Extreme-event sensitivities

The alternatives are POT/Q90, POT/Q97.5, 10-day-declustered POT/Q95, and annual maxima. The primary sample contains {int(d.loc['pot_q95','pairs_under_10_days']):,} adjacent peak pairs under 10 days; the declustered sample contains {int(d.loc['pot_q95_gap10','pairs_under_10_days'])}. Stormflow-window overlaps equal {int(d.loc['pot_q95','stormflow_window_overlaps'])}.

## 9. Rainfall concentration

$$
C_{{ie}}=\frac{{P_{{\max,ie}}}}{{P_{{\mathrm{{volume}},ie}}}}.
$$

An increase means a larger share of event rainfall fell in the wettest day; a decrease means movement toward longer, volume-dominated rainfall. The continuous ratio is the inferential outcome; no binary intensity-dominated label is used.

## 10. Antecedent wetness

$$
SSI_{{ie}}^{{(w)}}=\frac1w\sum_{{k=1}}^w SSI_{{i,t_{{0,ie}}-k}},
\qquad w\in\{{1,3,7,30\}}.
$$

Positive slopes mean large floods occurred after increasingly wet antecedent states; negative slopes mean increasingly dry states. SSI units are normalized index units, not millimetres or flood percentages.

## 11. Physical rainfall components

Maximum daily rainfall, event rainfall total, and precipitation duration are fitted in raw physical units. Their secondary relative slopes are:

$$
r=100\frac{{\widehat\beta}}{{\bar y}}.
$$

No logarithmic trend model is used. These components aid interpretation of the concentration ratio without claiming causal attribution.

## 12. Catchment-year annualization

Multiple POT events in one catchment-year are averaged:

$$
\bar y_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}}.
$$

This prevents a year with several reconstructed events from receiving extra trend weight solely because of event count.

## 13. Direct catchment trend

The annual sequence uses a Theil–Sen slope:

$$
\widehat\beta_i=\operatorname{{median}}_{{t_j>t_k}}
\frac{{\bar y_{{it_j}}-\bar y_{{it_k}}}}{{t_j-t_k}}\times10,
$$

with a tie-corrected Mann–Kendall test. At least 10 event years spanning at least 20 years are required.

## 14. Catchment multiple testing

Each physical metric forms one Benjamini–Hochberg family across catchments. Ordering $m$ p-values, the procedure finds the largest $k$ satisfying:

$$
p_{{(k)}}\le\frac{{k}}{{m}}\alpha,
\qquad \alpha=0.05.
$$

## 15. Stable local candidate

A candidate requires unadjusted $p<0.05$, sign agreement at POT/Q90 and POT/Q97.5, agreement after 10-day declustering, agreement under annual maxima, and leave-one-event-year-out sign stability. SSI candidates also require all four windows to agree. This is an exploratory evidence grade, not an FDR-confirmed shift.

![Direct catchment results](assets/figure_02_mechanism_change_maps.png)

Light marks retain all estimable trends; outlined marks identify stable candidates. Color encodes effect direction and magnitude, not statistical significance.

## 16. Direct catchment results

{_local_table(s, 'en')}

## 17. Direct catchment conclusion

There are **{int(c['potential_local_shift'].sum()):,} stable candidates in opposing directions and zero metric-wide FDR discoveries**. The evidence therefore supports sparse candidate locations within a predominantly non-confirmed network, not ubiquitous long-term change.

![Catchment evidence funnel](assets/figure_03_strong_signal_rankings.png)

The evidence funnel keeps unadjusted significance, sensitivity stability, and multiplicity control distinct.

## 18. L5 is a second-stage spatial question

L5 asks whether direct catchment changes may represent a larger hydrological pattern. It does not determine whether a catchment estimate is worth retaining and never removes the primary catchment layer.

## 19. Catchment-to-L5 membership

Catchment outlets are spatially joined to HydroBASINS v1.c level 5. **{l['matched_catchments']:,} catchments** match; two Mauritius catchments remain unmatched in the reference geometry but retain direct results.

## 20. L5 area support

For L5 polygon $H_j$ and eligible catchment polygons $A_i$ assigned by their outlets:

$$
Coverage_j=
\frac{{Area\left(H_j\cap\bigcup_{{i\in j}}A_i\right)}}{{Area(H_j)}}.
$$

Areas use equal-area EPSG:6933. Invalid polygons are repaired, and overlapping catchments are counted once through a geometric union.

## 21. Dynamic threshold sensitivity

{_threshold_table(s, 'en')}

The 10% default preserves a broad exploratory regional view; 20–50% thresholds test whether conclusions persist under stricter spatial representation. The threshold is a spatial interpretation condition, not a p-value rule.

![Threshold sensitivity](assets/figure_05_physical_decomposition.png)

US retention falls faster because HydroBASINS L5 units are comparatively fragmented relative to the observed catchment polygons.

## 22. Multi-catchment L5 estimator

For an L5 with at least two contributing catchments:

$$
\bar y_{{it}}=\alpha_i+\beta_j x_{{it}}+\varepsilon_{{it}},
\qquad x_{{it}}=\frac{{year_{{it}}-2000}}{{10}}.
$$

$\alpha_i$ controls stable catchment differences and $\beta_j$ is the shared per-decade change. Standard errors are clustered by catchment with a $t(G-1)$ reference.

## 23. One-catchment representation

If one catchment alone supports an L5 polygon at the selected threshold, the L5 panel inherits that catchment's Theil–Sen estimate and is explicitly labelled as a single-catchment representation. High area support does not create multi-catchment corroboration.

## 24. Why 2000 appears

The year 2000 is only a numerical centering constant. Replacing it with 1990 or 2010 leaves the slope unchanged; no pre/post-2000 contrast or breakpoint is fitted.

## 25. Complete regional family

All {l['primary_family_tests']:,} estimable L5 × five-primary-metric tests enter one BH family. This is intentionally more conservative than correcting each metric separately because the map invites inspection across both space and SSI windows.

## 26. Five regional evidence gates

The interactive regional signal must pass:

1. the currently selected area-support threshold;
2. complete regional-family 5% FDR;
3. sign agreement across all four alternative extreme samples;
4. sign agreement across 1/3/7/30-day SSI windows where relevant;
5. leave-one-catchment-out sign stability, or leave-one-year-out stability for a one-catchment representation.

## 27. Regional results at the default 10% threshold

{_regional_table(s, 'en')}

![Area-supported regional patterns](assets/figure_04_mechanism_trajectories.png)

Both positive and negative directions remain. The result is spatially heterogeneous regional evidence rather than one uniform global direction.

## 28. Strongest regional results

{_top_regions(s, 'en')}

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
""").replace(chr(92) * 2, chr(92))


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
        "catchment_candidates": int(s["catchments"]["potential_local_shift"].sum()),
        "regional_strong_signals": int(s["local"]["strong_evidence_signals"]),
    }


if __name__ == "__main__":
    print(json.dumps(build_reports(), indent=2, ensure_ascii=False))
