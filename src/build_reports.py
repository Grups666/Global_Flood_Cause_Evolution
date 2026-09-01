from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
REPORTS = ROOT / "reports"
PRIMARY_METRICS = ["intensity_fraction", "ssi_1d", "ssi_3d", "ssi_7d", "ssi_30d"]
METRIC_LABELS_ZH = {
    "intensity_fraction": "降雨集中度",
    "ssi_1d": "前期 SSI（1 日）",
    "ssi_3d": "前期 SSI（3 日）",
    "ssi_7d": "前期 SSI（7 日）",
    "ssi_30d": "前期 SSI（30 日）",
}
METRIC_LABELS_EN = {
    "intensity_fraction": "Rainfall concentration",
    "ssi_1d": "Antecedent SSI (1 day)",
    "ssi_3d": "Antecedent SSI (3 days)",
    "ssi_7d": "Antecedent SSI (7 days)",
    "ssi_30d": "Antecedent SSI (30 days)",
}


def _top_table(frame: pd.DataFrame, labels: dict[str, str], language: str) -> str:
    chosen = frame[frame["strong_evidence"]].copy()
    chosen["magnitude"] = chosen["slope_per_decade"].abs()
    chosen = chosen.sort_values("magnitude", ascending=False).head(12)
    if language == "zh":
        lines = [
            "| 水文区 | 国家 | 指标 | 趋势/十年 | 95% CI | 流域数 | BH q 值 |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    else:
        lines = [
            "| Region | Countries | Metric | Trend / decade | 95% CI | Catchments | BH q |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    for row in chosen.itertuples(index=False):
        digits = 2 if row.metric == "intensity_fraction" else 3
        lines.append(
            f"| {row.basin_code} | {row.dominant_countries} | {labels[row.metric]} | "
            f"{row.slope_per_decade:+.{digits}f} | {row.ci_low:+.{digits}f} to "
            f"{row.ci_high:+.{digits}f} | {int(row.catchments)} | {row.primary_family_q:.3g} |"
        )
    return "\n".join(lines)


def _metric_counts(frame: pd.DataFrame, labels: dict[str, str]) -> str:
    rows = []
    for metric in PRIMARY_METRICS:
        part = frame[frame["metric"].eq(metric)]
        rows.append(
            f"| {labels[metric]} | {int(part.primary_family_fdr_supported.sum())} | "
            f"{int(part.strong_evidence.sum())} | "
            f"{int((part.strong_evidence & part.slope_per_decade.gt(0)).sum())} | "
            f"{int((part.strong_evidence & part.slope_per_decade.lt(0)).sum())} |"
        )
    return "\n".join(rows)


def _stats() -> dict[str, object]:
    evidence = pd.read_csv(TABLES / "hydrobasin_evidence.csv")
    primary = evidence[
        evidence["sample"].eq("pot_q95")
        & evidence["level"].eq(5)
        & evidence["metric"].isin(PRIMARY_METRICS)
    ].copy()
    diagnostics = pd.read_csv(TABLES / "extreme_sample_diagnostics.csv")
    diag = diagnostics.set_index("sample")
    concentration = primary[primary["metric"].eq("intensity_fraction") & primary["strong_evidence"]]
    ssi7 = primary[primary["metric"].eq("ssi_7d") & primary["strong_evidence"]]
    ssi = primary[primary["metric"].str.startswith("ssi_")]
    return {
        "evidence": evidence,
        "primary": primary,
        "events": int(diag.loc["pot_q95", "events"]),
        "catchments": int(diag.loc["pot_q95", "catchments"]),
        "basins": int(primary["HYBAS_ID"].nunique()),
        "tests": len(primary),
        "fdr": int(primary["primary_family_fdr_supported"].sum()),
        "strong": int(primary["strong_evidence"].sum()),
        "strong_basins": int(primary.loc[primary["strong_evidence"], "HYBAS_ID"].nunique()),
        "min_catchments": int(primary["catchments"].min()),
        "min_observations": int(primary["observations"].min()),
        "conc_min": float(concentration["slope_per_decade"].min()),
        "conc_max": float(concentration["slope_per_decade"].max()),
        "ssi7_min": float(ssi7["slope_per_decade"].min()),
        "ssi7_max": float(ssi7["slope_per_decade"].max()),
        "ssi_relative_min": float(ssi["relative_slope_percent_per_decade"].min()),
        "ssi_relative_max": float(ssi["relative_slope_percent_per_decade"].max()),
        "unadjusted_false": len(primary) * 0.05,
        "diagnostics": diag,
    }


def build_chinese(s: dict[str, object]) -> str:
    p = s["primary"]
    d = s["diagnostics"]
    counts = _metric_counts(p, METRIC_LABELS_ZH)
    top = _top_table(p, METRIC_LABELS_ZH, "zh")
    return fr"""# 全球降雨型大洪水生成条件的局地演变（1982–2019）

**完整技术报告｜连续机制指标、HydroBASINS L5 与可复现实验**
**生成日期：2026-09-01**

> 核心结论：观测网络不支持一个空间一致的全球变化方向，但在 {s['strong_basins']} 个 HydroBASINS L5 水文区中识别出 {s['strong']} 个可重复的局地机制变化。降雨集中度与前期土壤湿润度均同时存在增强和减弱方向，因此研究重点是“哪些局地生成条件如何移动”，而不是把相反信号平均成一个全球结论。

## 技术摘要

- 主样本含 **{s['events']:,} 场 POT/Q95 大洪水事件**和 **{s['catchments']:,} 个长记录流域**。
- 只对至少 **20 个有效流域**的 HydroBASINS L5 单元进行区域推断，共保留 **{s['basins']} 个水文区**。
- 完整主检验族为 {s['basins']} 个水文区 × 5 个连续指标 = **{s['tests']} 项检验**；其中 **{s['fdr']} 项**通过 Benjamini–Hochberg 5% 假发现率控制。
- 进一步要求极端样本方向一致、留一流域方向稳定，以及 SSI 指标在 1/3/7/30 日窗方向一致后，得到 **{s['strong']} 个强证据信号**。
- 强证据降雨集中度趋势范围为 **{s['conc_min']:+.2f} 至 {s['conc_max']:+.2f} 个百分点/十年**；7 日 SSI 趋势范围为 **{s['ssi7_min']:+.3f} 至 {s['ssi7_max']:+.3f} SSI/十年**。
- SSI 的绝对斜率数值较小，因此同时报告相对于水文区“流域等权平均 SSI”的变化；全部合格区域范围为 **{s['ssi_relative_min']:+.2f}% 至 {s['ssi_relative_max']:+.2f}%/十年**。

![长期记录流域与主样本覆盖](assets/figure_01_sample_coverage.png)

## 1. 研究最终要回答什么

导师原意对应的第一性问题是：**造成大洪水的降雨组织方式和前期下垫面湿润状态，是否在时间和空间上发生了可辨认的变化？** 本项目不把研究对象偷换成洪水数量、洪峰大小或人为指定的 2000 年前后差异。

## 2. 为什么结果必须聚焦局地水文区

欧洲、北美、南美、非洲和大洋洲的观测密度明显不同，亚洲仅有 1 个通过长记录筛选的流域。全局平均既不是面积加权全球陆地结论，也可能抵消方向相反的局地变化。因此多流域 L5 水文区是主证据尺度，单流域点只用于定位局地细节。

## 3. 当前结果的空间图景

![五个连续机制指标的 L5 空间趋势](assets/figure_02_mechanism_change_maps.png)

图中只显示满足 ≥20 流域门槛的 28 个 L5 水文区。颜色表示斜率方向与大小；青色边界表示通过完整强证据筛选。没有颜色的地区表示当前观测网络不足以支持同等口径的区域推断，而不是“没有变化”。

## 4. 各指标证据数量

| 连续指标 | 通过 5% BH-FDR | 强证据 | 强证据正向 | 强证据负向 |
|---|---:|---:|---:|---:|
{counts}

## 5. 最强局地信号及其不确定性

![强证据局地趋势及95%置信区间](assets/figure_03_strong_signal_rankings.png)

{top}

## 6. 年度轨迹展示了什么

![代表性水文区的连续年度轨迹](assets/figure_04_mechanism_trajectories.png)

轨迹不是简单的全事件逐年平均。它表达的是：**假设所有流域都被放到相同的长期平均水平以后，当年参与流域相对于自身正常水平平均偏高或偏低多少。** 这种构造降低了年份间测站组成变化造成的假趋势，而且没有人为设置日历断点。

## 7. 降雨集中度变化的物理解读

![降雨集中度变化的原始物理分量](assets/figure_05_physical_decomposition.png)

Pmax、事件总降雨和降雨历时均在原始单位上拟合线性趋势。图中相对值等于“原始斜率 ÷ 该水文区流域等权平均水平 × 100%”。例如若 Pmax 为 +2%/十年、事件总降雨为 +8%/十年，则最湿日增长慢于事件总量，降雨集中度会下降；无需引入对数模型才能解释这一关系。

## 8. 结论能否跨事件定义复现

![不同极端事件样本下的方向稳健性](assets/figure_06_robustness_matrix.png)

强证据信号在年度最大值、POT/Q90、10 日去簇 POT/Q95 和 POT/Q97.5 中保持同方向。这里检验的是结论方向是否依赖某一种“大洪水”定义，而不是要求不同样本产生完全相同的斜率。

## 9. 数据与研究时段

数据来自相关项目 Event_Typology 的只读事件目录、日尺度水文气象记录与 SSI 特征。共同可验证时段为 1982–2019；不能把会议中的目标年份误写成实际覆盖。空间分区使用 [HydroBASINS v1.c](https://www.hydrosheds.org/products/hydrobasins)。

## 10. 长记录资格

一个流域必须同时满足：年度最大样本中至少 30 个观测年、记录跨度至少 30 年、记录覆盖率至少 80%。这一筛选发生在极端事件选择之前，避免短记录流域凭少数极值进入趋势分析。

## 11. 大洪水事件如何选择

对每个合格流域，在 1982–2019 的重建事件洪峰中计算自身 95% 分位数：

$$Q_{{0.95,i}}=\operatorname{{quantile}}_{{0.95}}\left(Q_{{i1}},\ldots,Q_{{in_i}}\right).$$

主样本保留 $Q_{{ie}}\ge Q_{{0.95,i}}$ 的事件，并要求每个流域至少 10 个所选事件、所选事件跨度至少 20 年。

## 12. 为什么主样本不是每年只取一个洪水

年度最大值每年固定取一个事件，可能遗漏同一年中的多个独立大洪水。POT/Q95 允许保留多个超过流域自身阈值的事件，更符合“研究大洪水生成条件”的目的；年度最大值仍作为敏感性样本而非主样本。

## 13. 事件独立性如何处理

主样本的相邻峰值最小间隔为 {int(d.loc['pot_q95','minimum_peak_gap_days'])} 日，风暴径流窗口重叠数为 {int(d.loc['pot_q95','stormflow_window_overlaps'])}；另建立 10 日去簇样本，其中小于 10 日的相邻峰对为 {int(d.loc['pot_q95_gap10','pairs_under_10_days'])}。因此独立性不是默认假设，而是显式敏感性检查。

## 14. 只研究降雨驱动洪水

事件雪水比例必须小于 0.10，且降雨量来自事件降雨窗口的日尺度水输入。事件选择与机制分类严格分开：洪峰只决定“事件是否够大”，降雨与 SSI 只描述“它在什么条件下发生”。

## 15. 降雨集中度公式

对事件 $e$：

$$C_{{ie}}=\frac{{P_{{\max,ie}}}}{{P_{{\mathrm{{volume}},ie}}}},\qquad 0<C_{{ie}}\le1.$$

$P_{{\max}}$ 是事件降雨窗口内最湿一天的降雨量，$P_{{\mathrm{{volume}}}}$ 是整个事件窗口的降雨总量。$C$ 越高，降雨越集中在单日；$C$ 越低，降雨越分散或持续时间更长。

## 16. 为什么不采用 intensity-dominated

把 $C>0.50$ 定义为 intensity-dominated 会让 0.51 与 0.95 看起来相同，也会人为制造跨阈值跳变。该阈值不是导师指定的研究目标，因此统计推断、网页与报告只使用连续 $C$，不构造二元类型占比。

## 17. SSI 是什么

SSI 是 0–1 范围的 Soil Saturation Index，用于表示事件前流域土壤相对饱和程度。对窗口 $w\in\{{1,3,7,30\}}$：

$$SSI_{{w,ie}}=\frac1w\sum_{{d=1}}^w SSI_{{i,t_0-d}},$$

其中 $t_0$ 是事件降雨开始日，只使用开始日前的完整日，避免把事件本身降雨混入前期湿润度。

## 18. 为什么使用四个 SSI 时间窗

1 日表示即时湿润状态，3 日和 7 日表示短期记忆，30 日表示较慢的流域湿润背景。四窗不是四种类别；它们用于判断结论是否依赖任意选择的记忆长度。

## 19. 为什么不采用 Dry/Moderate/Wet

固定阈值分类会丢失连续信息，并使同一类别内部的真实变化不可见。导师关心的是生成条件如何移动，因此项目只分析连续 SSI，不构造 Dry/Moderate/Wet 类别。

## 20. 分析尺度为什么只设 HydroBASINS L5

L5 在当前站网中提供可解释的局地水文分区。L3/L4 不承担核心推断作用，因而不进入计算、结果表或前端数据；研究空间尺度只有 L5 区域与合格单流域两层。

## 21. 唯一区域纳入门槛为什么是 20 个流域

区域固定效应模型把流域作为聚类。常规聚类稳健方差依赖聚类数增加的渐近理论；[Cameron 与 Miller](https://escholarship.org/uc/item/1jq5d0pq) 指出“少聚类”没有唯一界线，视情形可指少于 20 到少于 50 个聚类，而且即便使用 $t(G-1)$ 仍可能过度拒绝原假设。[Imbens 与 Kolesár](https://doi.org/10.1162/REST_A_00552) 也表明小样本修正问题甚至可能延续到 50 个聚类以上。

因此 20 不是“理论证明充分”的神奇常数，而是当前常规聚类稳健实现下的**保守最低设计值**。5 个聚类只有 4 个名义自由度，无法支撑与当前网页证据等级相称的区域推断。项目只有 ≥20 这一条区域样本门槛；低于 20 的单元不进入区域结果。

## 22. 区域固定效应模型

对水文区内流域 $i$、事件 $e$、年份 $t$：

$$y_{{iet}}=\alpha_i+\beta x_{{iet}}+\varepsilon_{{iet}},\qquad x_{{iet}}=\frac{{year_{{iet}}-2000}}{{10}}.$$

$y$ 是降雨集中度、某一 SSI 窗口或物理降雨量；$\alpha_i$ 是每个流域自己的固定基线；$\beta$ 是在控制稳定流域差异后的每十年平均变化。

## 23. 固定效应到底做了什么

模型先对每个流域分别减去自身均值：

$$\widetilde y_{{iet}}=y_{{iet}}-\bar y_i,\qquad \widetilde x_{{iet}}=x_{{iet}}-\bar x_i,$$

再用所有流域的“流域内部偏离”估计共同斜率：

$$\widehat\beta=\frac{{\sum_{{i,e,t}}\widetilde x_{{iet}}\widetilde y_{{iet}}}}{{\sum_{{i,e,t}}\widetilde x_{{iet}}^2}}.$$

所以某个天然更湿或降雨集中度更高的流域不会仅凭高基线把区域趋势推高；只有它随时间相对自身发生的变化参与斜率。

## 24. 为什么公式中出现 2000

2000 只是时间变量的中心化常数，使截距与数值计算更稳定。把它换成 1990 或 2010 不会改变 $\widehat\beta$。模型没有把 2000 年当作断点，也没有比较 2000 年前后。

## 25. 聚类稳健不确定性

允许同一流域内不同事件残差任意相关，流域之间视为独立聚类。报告使用带有限样本缩放的聚类稳健方差，并用 $t_{{G-1}}$ 临界值构造 95% 置信区间；其中 $G$ 是水文区内贡献流域数。

## 26. 降雨集中度斜率的单位

因为 $C$ 本身是 0–1 比例，主图将 $100\widehat\beta$ 表示为“事件降雨占比的百分点/十年”。例如 +2.12 表示最湿日占事件总降雨的比例每十年增加 2.12 个百分点，不表示洪水次数或洪峰增加 2.12%。

## 27. SSI 如何同时给出绝对与相对变化

绝对斜率仍是主统计量。为改善可读性，再计算：

$$r_{{SSI}}=100\times\frac{{\widehat\beta_{{SSI}}}}{{\bar y_{{ref}}}},\qquad
\bar y_{{ref}}=\frac1G\sum_{{i=1}}^G\bar y_i.$$

例如 $\widehat\beta=-0.013$ SSI/十年、流域等权均值为 0.52，则相对变化约为 $-2.5\%$/十年。相对值是尺度辅助，不能替代原始 SSI 斜率和置信区间。

## 28. Pmax、事件总雨量和历时的相对变化

三个物理分量均直接在原始量上拟合固定效应线性趋势，再用同一流域等权均值换算相对百分比：

$$r_y=100\times\frac{{\widehat\beta_y}}{{\bar y_{{ref}}}}.$$

这里没有拟合 $\ln P$，也不使用 $100(e^\beta-1)$。网页同时保存原始斜率和相对斜率，主界面使用更易比较的相对值。

## 29. 年度调整轨迹的公式

先计算流域—年份事件平均 $v_{{it}}$ 与流域长期平均 $\bar v_i$，再定义流域等权参考水平 $v_{{ref}}$：

$$v_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}},\qquad
v_{{ref}}=\frac1G\sum_i\bar v_i,$$

$$v_{{it}}^*=v_{{it}}-\bar v_i+v_{{ref}},\qquad
\bar v_t^*=\frac1{{G_t}}\sum_i v_{{it}}^*.$$

它的直接含义就是：假设所有流域被放到相同长期平均水平后，当年参与流域相对自身正常水平平均偏高或偏低多少。

## 30. Benjamini–Hochberg 假发现率是什么

False Discovery Rate（FDR，假发现率）定义为被判定为发现的结果中，假阳性比例的期望：

$$FDR=E\left[\frac{{V}}{{\max(R,1)}}\right],$$

其中 $V$ 是错误拒绝的原假设数，$R$ 是全部拒绝数。[Benjamini–Hochberg 方法](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) 将 $m$ 个 p 值从小到大排序 $p_{{(1)}}\le\cdots\le p_{{(m)}}$，寻找

$$k=\max\left\{{\,i:p_{{(i)}}\le\frac{{i}}{{m}}q\,\right\}},$$

并拒绝 $H_{{(1)}},\ldots,H_{{(k)}}$。本项目把 28 个 L5 水文区 × 5 个主指标的 {s['tests']} 项检验作为一个预先定义的完整检验族，控制水平 $q=0.05$。

## 31. 为什么不能逐项使用 p<0.05

假设 {s['tests']} 项指标实际上全部没有真实趋势，即所有 $H_0$ 都成立。仅因随机波动，每一项仍有约 5% 的概率偶然得到 $p<0.05$，所以平均可能出现：

$$ {s['tests']}\times0.05={s['unadjusted_false']:.1f} $$

个偶然“显著”结果。这个数不是实际假阳性数，而是说明为什么多重检验必须整体控制。

## 32. BH q 值如何计算

对排序后的 p 值，调整值为：

$$q_{{(i)}}=\min_{{j\ge i}}\left(\frac{{m}}{{j}}p_{{(j)}}\right),$$

并截断在 1 以内，再恢复原顺序。网页中的 complete-family q 即来自这一完整检验族，而不是每个指标分别挑选最有利的检验族。

## 33. 单流域趋势如何估计

单流域点使用 [Theil–Sen](https://ir.cwi.nl/pub/18445) 中位斜率：

$$\widehat\beta_{{TS}}=\operatorname{{median}}_{{j>i}}\frac{{y_j-y_i}}{{t_j-t_i}},$$

并用带并列值修正的 Mann–Kendall 检验判断单调趋势。单流域必须至少有 10 个所选事件且跨度至少 20 年；它们用于局地检查，不替代区域固定效应推断。

## 34. 强证据的完整定义

一个主指标被标记为强证据必须同时满足：

1. 所在 L5 水文区至少 20 个贡献流域；
2. 通过 {s['tests']} 项完整主检验族的 5% BH-FDR；
3. 年度最大值、POT/Q90、10 日去簇 POT/Q95 与 POT/Q97.5 的斜率方向都与主样本一致；
4. 留一流域重估时斜率方向不改变；
5. 若为 SSI，1/3/7/30 日窗方向一致。

## 35. 单一样本门槛与证据等级

所有进入区域图和检验表的单元都满足同一个 ≥20 流域门槛。证据等级只区分 estimate、FDR-supported 与 strong；样本量不另外引入第二条等级门槛。

## 36. 当前结论支持什么

- 一些局地水文区的大洪水生成条件发生了方向稳定、可重复的变化；
- 局地降雨集中度变化可达到每十年数个百分点；
- 前期湿润度在不同地区同时向更湿与更干方向移动；
- 这些变化具有显著空间异质性，不宜压缩成一个全球方向。

## 37. 当前结论不支持什么

- 不支持空间均匀或面积加权的全球陆地趋势；
- 不直接说明洪水发生次数、洪峰或洪量趋势；
- 不构成对气候变化、土地利用或工程调控的因果归因；
- 无结果地区不能解释为“趋势为零”，很多地区只是没有合格长期记录流域。

## 38. 主要局限

站网在欧洲和北美最密集，亚洲几乎没有可用样本；SSI 与降雨重建误差会进入事件级指标；聚类稳健方法即使在 20 个聚类时也不是有限样本精确推断；空间相邻水文区之间仍可能存在相关性。因而 20 是最低纳入门槛，不是充分保证。

## 39. 可复现文件

- 配置：`config/analysis.yaml`
- 主入口：`src/run_pipeline.py`
- 区域模型：`src/floodcause/local_analysis.py`
- 独立验证：`src/validate_outputs.py`
- 主结果：`outputs/tables/hydrobasin_evidence.csv`
- 交互数据：`public/modules/flood-cause-evolution/data/flood-cause-explorer.json`
- 在线交互图：[GitHub Pages](https://grups666.github.io/Global_Flood_Cause_Evolution/)

## 40. 下一步

优先补充亚洲及其他稀疏区域的长记录流域，并考虑对 ≥20 聚类区域增加 CR2/Bell–McCaffrey 或 wild-cluster bootstrap 作为额外有限样本推断敏感性；在此之前，不应把当前局地网络结果外推为全球陆地过程。
"""


def build_english(s: dict[str, object]) -> str:
    p = s["primary"]
    d = s["diagnostics"]
    counts = _metric_counts(p, METRIC_LABELS_EN)
    top = _top_table(p, METRIC_LABELS_EN, "en")
    return fr"""# Local Evolution of Rainfall-Driven Large-Flood Generating Conditions (1982–2019)

**Complete technical report | continuous process metrics, HydroBASINS L5, and reproducible inference**
**Generated: 2026-09-01**

> Main result: the observed network does not support one spatially uniform global direction. It identifies {s['strong']} reproducible local changes in {s['strong_basins']} HydroBASINS level-5 regions. Rainfall concentration and antecedent wetness both move in opposing directions across regions, so the scientific result is where and how generating conditions moved—not an average that cancels local signals.

## Technical summary

- The primary sample contains **{s['events']:,} POT/Q95 large-flood events** in **{s['catchments']:,} long-record catchments**.
- Regional inference is performed only for HydroBASINS L5 units containing at least **20 eligible catchments**, leaving **{s['basins']} regions**.
- The complete primary family contains {s['basins']} regions × 5 continuous metrics = **{s['tests']} tests**; **{s['fdr']}** pass Benjamini–Hochberg 5% False Discovery Rate control.
- Requiring agreement across extreme-event samples, leave-one-catchment-out sign stability, and—where relevant—all SSI windows leaves **{s['strong']} strong signals**.
- Strong rainfall-concentration trends span **{s['conc_min']:+.2f} to {s['conc_max']:+.2f} percentage points per decade**. Seven-day SSI trends span **{s['ssi7_min']:+.3f} to {s['ssi7_max']:+.3f} SSI units per decade**.
- SSI is reported in both absolute units and relative to the region's catchment-equal mean; eligible regions span **{s['ssi_relative_min']:+.2f}% to {s['ssi_relative_max']:+.2f}% per decade**.

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
{counts}

## 5. Largest reproducible local movements

![Strong regional trends and 95% confidence intervals](assets/figure_03_strong_signal_rankings.png)

{top}

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

$$Q_{{0.95,i}}=\operatorname{{quantile}}_{{0.95}}\left(Q_{{i1}},\ldots,Q_{{in_i}}\right).$$

The primary sample retains $Q_{{ie}}\ge Q_{{0.95,i}}$ and requires at least 10 selected events spanning at least 20 years in each catchment.

## 12. Why annual maxima are not the primary sample

Annual maxima force exactly one event per year and can discard multiple independent large floods in the same year. POT/Q95 retains all within-catchment exceedances; annual maxima remain a sensitivity population.

## 13. Event independence

The primary sample has a minimum adjacent-peak gap of {int(d.loc['pot_q95','minimum_peak_gap_days'])} days and {int(d.loc['pot_q95','stormflow_window_overlaps'])} overlapping stormflow windows. A separate 10-day-declustered sample has {int(d.loc['pot_q95_gap10','pairs_under_10_days'])} adjacent pairs under 10 days, making independence an explicit sensitivity rather than an assumption.

## 14. Rainfall-driven scope

Event snow-water fraction must be below 0.10. Flood-peak magnitude selects events; rainfall and SSI only describe their generating conditions. Selection and mechanism measurement are never conflated.

## 15. Rainfall concentration

For event $e$ in catchment $i$,

$$C_{{ie}}=\frac{{P_{{\max,ie}}}}{{P_{{\mathrm{{volume}},ie}}}},\qquad 0<C_{{ie}}\le1.$$

$P_{{\max}}$ is wettest-day rainfall and $P_{{\mathrm{{volume}}}}$ is total event rainfall. Higher $C$ means more concentrated rain; lower $C$ means more prolonged or distributed rain.

## 16. Why intensity-dominated classes are not used

A $C>0.50$ label makes 0.51 equivalent to 0.95 and creates artificial threshold jumps. It was not a meeting-defined scientific target. Inference, reports, and the web interface therefore use continuous $C$ and do not construct a binary type share.

## 17. Antecedent Soil Saturation Index

For $w\in\{{1,3,7,30\}}$ complete pre-event days,

$$SSI_{{w,ie}}=\frac1w\sum_{{d=1}}^w SSI_{{i,t_0-d}},$$

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

$$y_{{iet}}=\alpha_i+\beta x_{{iet}}+\varepsilon_{{iet}},\qquad x_{{iet}}=\frac{{year_{{iet}}-2000}}{{10}}.$$

$\alpha_i$ is the catchment-specific baseline and $\beta$ is the average within-catchment change per decade.

## 23. What fixed effects do

The estimator removes each catchment's mean:

$$\widetilde y_{{iet}}=y_{{iet}}-\bar y_i,\qquad \widetilde x_{{iet}}=x_{{iet}}-\bar x_i,$$

$$\widehat\beta=\frac{{\sum_{{i,e,t}}\widetilde x_{{iet}}\widetilde y_{{iet}}}}{{\sum_{{i,e,t}}\widetilde x_{{iet}}^2}}.$$

A naturally wetter catchment cannot create a regional trend merely because its baseline is high; only temporal movement relative to its own baseline contributes.

## 24. Why 2000 appears in the formula

It is only a numerical centering constant. Replacing 2000 with 1990 or 2010 leaves the slope unchanged. The model has no pre/post-2000 comparison or breakpoint.

## 25. Cluster-robust uncertainty

Residuals may be arbitrarily correlated among events within a catchment. The variance uses a finite-sample scaling and $t_{{G-1}}$ critical values, where $G$ is the number of contributing catchments.

## 26. Unit of rainfall-concentration change

Because $C$ is a 0–1 proportion, $100\widehat\beta$ is reported as percentage points of event rainfall per decade. A value of +2.12 means the wettest-day share rises by 2.12 percentage points in ten years; it is not a 2.12% change in flood count or peak flow.

## 27. Absolute and relative SSI change

Absolute SSI slope is primary. The supplementary relative scale is

$$r_{{SSI}}=100\times\frac{{\widehat\beta_{{SSI}}}}{{\bar y_{{ref}}}},\qquad
\bar y_{{ref}}=\frac1G\sum_{{i=1}}^G\bar y_i.$$

For example, −0.013 SSI per decade against a 0.52 catchment-equal mean is about −2.5% per decade. Relative change aids scale perception but does not replace the absolute estimate or confidence interval.

## 28. Relative Pmax, event-total, and duration trends

Each component is fitted linearly in raw units and then divided by its catchment-equal mean:

$$r_y=100\times\frac{{\widehat\beta_y}}{{\bar y_{{ref}}}}.$$

No $\ln P$ model or $100(e^\beta-1)$ transformation is used.

## 29. Adjusted annual trajectory

With catchment-year event mean $v_{{it}}$, catchment long-run mean $\bar v_i$, and catchment-equal reference $v_{{ref}}$,

$$v_{{it}}=\frac1{{n_{{it}}}}\sum_e y_{{iet}},\quad v_{{ref}}=\frac1G\sum_i\bar v_i,$$

$$v_{{it}}^*=v_{{it}}-\bar v_i+v_{{ref}},\quad \bar v_t^*=\frac1{{G_t}}\sum_i v_{{it}}^*.$$

It answers how far the year's participating catchments were above or below their own normal levels after all catchments are placed on the same long-run mean.

## 30. Benjamini–Hochberg False Discovery Rate

False Discovery Rate (FDR) is

$$FDR=E\left[\frac{{V}}{{\max(R,1)}}\right],$$

where $V$ is the number of false rejections and $R$ is the number of all rejections. The [Benjamini–Hochberg procedure](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) orders $m$ p-values and finds

$$k=\max\left\{{\,i:p_{{(i)}}\le\frac{{i}}{{m}}q\,\right\}},$$

then rejects $H_{{(1)}},\ldots,H_{{(k)}}$. Here $m={s['tests']}$ and $q=0.05$.

## 31. Why unadjusted p<0.05 is insufficient

If all {s['tests']} null hypotheses were true, random variation alone would still yield about

$$ {s['tests']}\times0.05={s['unadjusted_false']:.1f} $$

unadjusted p-values below 0.05 on average. This is not an estimate of actual false positives; it demonstrates the multiplicity problem.

## 32. BH-adjusted q-values

For ordered p-values,

$$q_{{(i)}}=\min_{{j\ge i}}\left(\frac{{m}}{{j}}p_{{(j)}}\right),$$

clipped at one and restored to the original order. The web inspector reports the q-value from the complete 140-test family, not a more favorable metric-specific subset.

## 33. Individual-catchment trends

Points use the [Theil–Sen](https://ir.cwi.nl/pub/18445) median slope,

$$\widehat\beta_{{TS}}=\operatorname{{median}}_{{j>i}}\frac{{y_j-y_i}}{{t_j-t_i}},$$

with a tie-corrected Mann–Kendall test. At least 10 selected events spanning at least 20 years are required. These points provide local context, not primary regional inference.

## 34. Complete strong-evidence rule

A strong primary signal must satisfy all of the following:

1. at least 20 contributing catchments;
2. 5% BH-FDR across the full {s['tests']}-test primary family;
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
"""


def build_reports() -> dict[str, object]:
    s = _stats()
    REPORTS.mkdir(parents=True, exist_ok=True)
    zh = REPORTS / "global_flood_cause_evolution.md"
    en = REPORTS / "global_flood_cause_evolution_en.md"
    zh.write_text(build_chinese(s), encoding="utf-8")
    en.write_text(build_english(s), encoding="utf-8")
    result = {
        "status": "complete",
        "chinese": str(zh),
        "english": str(en),
        "primary_tests": s["tests"],
        "strong_signals": s["strong"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    build_reports()
