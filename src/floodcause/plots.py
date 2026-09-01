from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from .local_analysis import load_hydrobasins


BLUE = "#315F7D"
ORANGE = "#D66A3D"
GOLD = "#D6A52C"
CYAN = "#12CFE3"
INK = "#243142"
MUTED = "#667587"
PALE = "#EEF2F4"
GRID = "#D8E0E6"
NEUTRAL = "#F3EFE6"
CMAP = LinearSegmentedColormap.from_list("condition_shift", [BLUE, NEUTRAL, ORANGE])
PRIMARY_METRICS = ["intensity_fraction", "ssi_1d", "ssi_3d", "ssi_7d", "ssi_30d"]
METRIC_LABELS = {
    "intensity_fraction": "Rainfall concentration",
    "ssi_1d": "SSI · 1 day",
    "ssi_3d": "SSI · 3 days",
    "ssi_7d": "SSI · 7 days",
    "ssi_30d": "SSI · 30 days",
}
METRIC_LIMITS = {
    "intensity_fraction": 3.0,
    "ssi_1d": 0.015,
    "ssi_3d": 0.015,
    "ssi_7d": 0.015,
    "ssi_30d": 0.015,
}


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.edgecolor": GRID,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.055, 0.968, title, ha="left", va="top", fontsize=17, weight="bold")
    fig.text(0.055, 0.925, subtitle, ha="left", va="top", fontsize=9.5, color=MUTED)


def _footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.055, 0.023, text, ha="left", va="bottom", fontsize=7.5, color=MUTED)


def _save(fig: plt.Figure, base: Path, dpi: int) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".png"), dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _world(config: dict[str, Any]) -> gpd.GeoDataFrame:
    return gpd.read_file(f"zip://{config['paths']['world_boundaries'].as_posix()}")


def _base_map(ax: plt.Axes, world: gpd.GeoDataFrame) -> None:
    world.plot(ax=ax, color="#F7F9FA", edgecolor="#C9D3DA", linewidth=0.32)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.set_axis_off()


def _spatial_support(config: dict[str, Any]) -> pd.DataFrame:
    return pd.read_csv(
        config["paths"]["tables"] / "spatial_support" / "l5_spatial_support_audit.csv"
    ).rename(columns={"hybas_id_l5": "HYBAS_ID"})


def figure_sample_coverage(config: dict[str, Any]) -> None:
    sample = pd.read_parquet(config["paths"]["derived_data"] / "primary_extreme_events.parquet")
    catchments = sample[["GCIN", "continent", "longitude", "latitude"]].drop_duplicates("GCIN")
    counts = catchments.groupby("continent")["GCIN"].nunique().sort_values()
    diagnostics = pd.read_csv(config["paths"]["tables"] / "extreme_sample_diagnostics.csv")
    primary = diagnostics[diagnostics["sample"].eq("pot_q95")].iloc[0]
    world = _world(config)

    fig = plt.figure(figsize=(13.5, 7.4))
    grid = fig.add_gridspec(
        1, 2, width_ratios=[3.8, 1.2], left=0.055, right=0.96,
        bottom=0.10, top=0.83, wspace=0.08,
    )
    ax = fig.add_subplot(grid[0, 0])
    _base_map(ax, world)
    ax.scatter(
        catchments["longitude"], catchments["latitude"], s=4.1,
        color=BLUE, alpha=0.72, linewidths=0, rasterized=True,
    )
    ax.text(
        -174, -53,
        f"{len(sample):,} selected events\n{catchments['GCIN'].nunique():,} primary-sample catchments",
        fontsize=8.5, color=INK, va="bottom",
    )

    bars = fig.add_subplot(grid[0, 1])
    bars.barh(counts.index, counts.values, color=BLUE, height=0.62)
    for y, value in enumerate(counts.values):
        bars.text(value + counts.max() * 0.025, y, f"{value:,}", va="center", fontsize=8.5, weight="bold")
    bars.set_title("Primary sample by continent", loc="left", pad=12)
    bars.set_xlabel("Catchments")
    bars.set_xlim(0, counts.max() * 1.24)
    bars.spines[["top", "right", "left"]].set_visible(False)
    bars.tick_params(axis="y", length=0)
    bars.grid(axis="x", color=GRID, linewidth=0.6)
    bars.set_axisbelow(True)

    _header(
        fig,
        "Coverage of the catchment-first extreme-flood analysis",
        "Catchment-specific POT/Q95 events · 1982–2019 · long-record, low-snow rainfall-driven sample",
    )
    _footer(
        fig,
        f"Source network is not area-uniform. Primary event windows have {int(primary.stormflow_window_overlaps)} overlaps; peak-spacing sensitivity uses a separate 10-day-declustered sample.",
    )
    _save(fig, config["paths"]["figures"] / "figure_01_sample_coverage", int(config["plotting"]["dpi"]))


def _catchment_map_panel(
    ax: plt.Axes,
    world: gpd.GeoDataFrame,
    evidence: pd.DataFrame,
    metric: str,
) -> None:
    _base_map(ax, world)
    data = evidence[evidence["variable"].eq(metric)].copy()
    limit = METRIC_LIMITS[metric]
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    ax.scatter(
        data["longitude"], data["latitude"], c=data["display_slope_per_decade"],
        cmap=CMAP, norm=norm, s=6.5, alpha=0.46, linewidths=0, rasterized=True,
    )
    candidates = data[data["potential_local_shift"]]
    if not candidates.empty:
        ax.scatter(
            candidates["longitude"], candidates["latitude"],
            c=candidates["display_slope_per_decade"], cmap=CMAP, norm=norm,
            s=24, alpha=0.98, edgecolors="#17212B", linewidths=0.55,
            rasterized=True,
        )
    ax.set_title(
        f"{METRIC_LABELS[metric]} · {len(candidates)} stable candidates",
        loc="left", pad=5,
    )


def figure_mechanism_change_maps(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "catchment_mechanism_trends.csv")
    world = _world(config)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.8))
    fig.subplots_adjust(left=0.045, right=0.965, bottom=0.09, top=0.84, wspace=0.025, hspace=0.12)
    for ax, metric in zip(axes.flat[:5], PRIMARY_METRICS):
        _catchment_map_panel(ax, world, evidence, metric)

    legend = axes.flat[5]
    legend.set_axis_off()
    legend.text(0.02, 0.90, "How to read the catchment layer", fontsize=11, weight="bold", transform=legend.transAxes)
    gradient = np.linspace(-1, 1, 256).reshape(1, -1)
    inset = legend.inset_axes([0.03, 0.71, 0.78, 0.08])
    inset.imshow(gradient, aspect="auto", cmap=CMAP, extent=[-1, 1, 0, 1])
    inset.set_xticks([-1, 0, 1], ["negative", "near zero", "positive"], fontsize=8)
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_visible(False)
    legend.scatter([0.07], [0.53], s=28, color=ORANGE, edgecolors="#17212B", linewidths=0.6, transform=legend.transAxes)
    legend.text(0.13, 0.53, "Stable unadjusted candidate", va="center", fontsize=8.5, transform=legend.transAxes)
    legend.scatter([0.07], [0.42], s=12, color=BLUE, alpha=0.45, linewidths=0, transform=legend.transAxes)
    legend.text(0.13, 0.42, "Other estimable catchment", va="center", fontsize=8.5, transform=legend.transAxes)
    legend.text(
        0.03, 0.20,
        "Candidate means p < 0.05 plus agreement across\nevent-threshold, declustering, annual-maximum,\nleave-one-year-out, and SSI-window checks.\nIt is not an FDR-confirmed signal.",
        fontsize=8, color=MUTED, linespacing=1.5, transform=legend.transAxes,
    )

    _header(
        fig,
        "Direct catchment trends in flood-generating conditions",
        "Annualized Theil–Sen slopes; all estimable catchments remain visible and stable candidates are outlined",
    )
    _footer(
        fig,
        "Rainfall concentration is in percentage points per decade; SSI is in index units per decade. Color is effect direction and magnitude, not a significance claim.",
    )
    _save(fig, config["paths"]["figures"] / "figure_02_mechanism_change_maps", int(config["plotting"]["dpi"]))


def figure_strong_signal_rankings(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "catchment_mechanism_trends.csv")
    evidence = evidence[evidence["variable"].isin(PRIMARY_METRICS)].copy()
    summary = evidence.groupby("variable").agg(
        tests=("GCIN", "size"),
        unadjusted=("mk_p", lambda values: int((values < 0.05).sum())),
        stable=("potential_local_shift", "sum"),
        fdr=("metric_fdr_supported", "sum"),
    ).reindex(PRIMARY_METRICS)
    candidates = evidence[evidence["potential_local_shift"]].copy()
    directions = candidates.assign(direction=np.where(candidates["display_slope_per_decade"] >= 0, "positive", "negative")).pivot_table(
        index="variable", columns="direction", values="GCIN", aggfunc="size", fill_value=0
    ).reindex(PRIMARY_METRICS).fillna(0)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.2))
    fig.subplots_adjust(left=0.13, right=0.95, bottom=0.20, top=0.80, wspace=0.34)
    labels = [METRIC_LABELS[metric] for metric in PRIMARY_METRICS]
    y = np.arange(len(labels))
    axes[0].barh(y + 0.18, summary["unadjusted"], height=0.32, color="#AAB8C2", label="Unadjusted p < 0.05")
    axes[0].barh(y - 0.18, summary["stable"], height=0.32, color=GOLD, label="Stable candidate")
    for index, row in enumerate(summary.itertuples()):
        axes[0].text(row.unadjusted + 5, index + 0.18, f"{int(row.unadjusted)}", va="center", fontsize=8)
        axes[0].text(row.stable + 5, index - 0.18, f"{int(row.stable)}", va="center", fontsize=8, weight="bold")
    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Catchment–metric estimates")
    axes[0].set_title("Candidate evidence funnel", loc="left")
    axes[0].grid(axis="x", color=GRID, linewidth=0.6)
    axes[0].spines[["top", "right", "left"]].set_visible(False)
    axes[0].tick_params(axis="y", length=0)
    axes[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2)
    axes[0].text(
        0.98, 0.97,
        f"FDR-supported: {int(summary['fdr'].sum())}",
        transform=axes[0].transAxes, ha="right", va="top", fontsize=9, weight="bold", color=BLUE,
    )

    negative = directions.get("negative", pd.Series(0, index=PRIMARY_METRICS)).to_numpy(float)
    positive = directions.get("positive", pd.Series(0, index=PRIMARY_METRICS)).to_numpy(float)
    axes[1].barh(y, -negative, color=BLUE, height=0.56, label="Negative direction")
    axes[1].barh(y, positive, color=ORANGE, height=0.56, label="Positive direction")
    axes[1].axvline(0, color=INK, linewidth=0.8)
    for index, value in enumerate(negative):
        axes[1].text(-value - 2, index, f"{int(value)}", ha="right", va="center", fontsize=8, color=INK)
    for index, value in enumerate(positive):
        axes[1].text(value + 2, index, f"{int(value)}", ha="left", va="center", fontsize=8, color=INK)
    axes[1].set_yticks(y, labels)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Stable candidates by direction")
    axes[1].set_title("Opposing local directions are retained", loc="left")
    axes[1].grid(axis="x", color=GRID, linewidth=0.6)
    axes[1].spines[["top", "right", "left"]].set_visible(False)
    axes[1].tick_params(axis="y", length=0)
    axes[1].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2)

    _header(
        fig,
        "Most catchments do not show strict network-wide trend evidence",
        "Stable candidates are useful locations for follow-up, but none passes metric-wide 5% FDR",
    )
    _footer(
        fig,
        f"Primary family contains {len(evidence):,} estimable catchment–metric trends. Stability never substitutes for multiple-testing control; both are reported separately.",
    )
    _save(fig, config["paths"]["figures"] / "figure_03_strong_signal_rankings", int(config["plotting"]["dpi"]))


def _regional_map_panel(
    ax: plt.Axes,
    world: gpd.GeoDataFrame,
    basins: gpd.GeoDataFrame,
    evidence: pd.DataFrame,
    metric: str,
) -> None:
    _base_map(ax, world)
    data = evidence[evidence["metric"].eq(metric)]
    layer = basins.merge(data, on="HYBAS_ID", how="inner")
    norm = TwoSlopeNorm(vmin=-METRIC_LIMITS[metric], vcenter=0, vmax=METRIC_LIMITS[metric])
    layer.plot(
        ax=ax, column="slope_per_decade", cmap=CMAP, norm=norm,
        edgecolor="#354553", linewidth=0.28, alpha=0.80,
    )
    strong = layer[layer["strong_evidence"]]
    if not strong.empty:
        strong.boundary.plot(ax=ax, color=CYAN, linewidth=1.25, alpha=1)
    ax.set_title(f"{METRIC_LABELS[metric]} · {len(strong)} supported", loc="left", pad=5)


def figure_mechanism_trajectories(config: dict[str, Any]) -> None:
    threshold = int(config["local_analysis"]["default_area_coverage_threshold_percent"])
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    support = _spatial_support(config)[["HYBAS_ID", "coverage_pct"]]
    evidence = evidence.merge(support, on="HYBAS_ID", how="left")
    evidence = evidence[
        evidence["metric"].isin(PRIMARY_METRICS) & evidence["coverage_pct"].ge(threshold)
    ]
    basin_ids = set(evidence["HYBAS_ID"].astype(int))
    basins = load_hydrobasins(config["paths"]["hydrobasins"], 5).to_crs("EPSG:4326")
    basins = basins[basins["HYBAS_ID"].isin(basin_ids)]
    world = _world(config)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.8))
    fig.subplots_adjust(left=0.045, right=0.965, bottom=0.09, top=0.84, wspace=0.025, hspace=0.12)
    for ax, metric in zip(axes.flat[:5], PRIMARY_METRICS):
        _regional_map_panel(ax, world, basins, evidence, metric)
    legend = axes.flat[5]
    legend.set_axis_off()
    legend.text(0.02, 0.96, "Second-stage regional lens", fontsize=11, weight="bold", transform=legend.transAxes)
    legend.text(
        0.03, 0.62,
        f"Shown L5 units have ≥{threshold}% polygon-area support.\nColors are pooled within-catchment annual slopes.\nCyan boundaries pass regional FDR, alternative\nevent samples, SSI-window, and leave-one-out checks.",
        fontsize=8.5, color=MUTED, linespacing=1.55, transform=legend.transAxes,
    )
    legend.add_patch(plt.Rectangle((0.03, 0.29), 0.12, 0.07, facecolor="#D78A68", edgecolor=CYAN, linewidth=1.5, transform=legend.transAxes))
    legend.text(0.18, 0.315, "Supported regional pattern", fontsize=8.5, transform=legend.transAxes)
    legend.add_patch(plt.Rectangle((0.03, 0.16), 0.12, 0.07, facecolor="#DDE3E6", edgecolor="#354553", linewidth=0.5, transform=legend.transAxes))
    legend.text(0.18, 0.185, "Area-supported regional context", fontsize=8.5, transform=legend.transAxes)

    _header(
        fig,
        "Area-supported HydroBASINS L5 patterns",
        f"Default ≥{threshold}% observed polygon coverage · catchment-year fixed effects · complete regional evidence screen",
    )
    _footer(
        fig,
        "The area threshold determines whether an L5 interpretation is shown. It does not remove, recolor, or change the underlying single-catchment estimates.",
    )
    _save(fig, config["paths"]["figures"] / "figure_04_mechanism_trajectories", int(config["plotting"]["dpi"]))


def figure_physical_decomposition(config: dict[str, Any]) -> None:
    table = pd.read_csv(
        config["paths"]["tables"] / "spatial_support" / "l5_spatial_support_threshold_sensitivity.csv"
    )
    table = table[
        table["scope"].isin(["Global", "United States"])
        & table["metric"].eq("coverage_fraction")
    ].copy()
    colors = {"Global": BLUE, "United States": ORANGE}
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.7))
    fig.subplots_adjust(left=0.08, right=0.95, bottom=0.15, top=0.78, wspace=0.27)
    for scope, frame in table.groupby("scope"):
        frame = frame.sort_values("threshold_pct")
        axes[0].plot(frame["threshold_pct"], frame["passing_l5"], color=colors[scope], marker="o", linewidth=2.4, label=scope)
        axes[1].plot(frame["threshold_pct"], frame["passing_catchment_share_pct"], color=colors[scope], marker="o", linewidth=2.4, label=scope)
        for x, y in zip(frame["threshold_pct"], frame["passing_l5"]):
            axes[0].text(x, y + 4, f"{int(y)}", ha="center", va="bottom", fontsize=8, color=colors[scope])
        for x, y in zip(frame["threshold_pct"], frame["passing_catchment_share_pct"]):
            axes[1].text(x, y + 2.2, f"{y:.0f}%", ha="center", va="bottom", fontsize=8, color=colors[scope])
    axes[0].set_title("L5 regions meeting the selected support", loc="left")
    axes[0].set_ylabel("Passing HydroBASINS L5 units")
    axes[1].set_title("Catchments located in passing L5 regions", loc="left")
    axes[1].set_ylabel("Share of matched catchments (%)")
    for ax in axes:
        ax.set_xlabel("Minimum observed L5 area coverage (%)")
        ax.set_xticks([10, 20, 30, 40, 50])
        ax.grid(color=GRID, linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="upper right")
    axes[1].set_ylim(0, 100)

    _header(
        fig,
        "Regional coverage is an explicit, adjustable sensitivity",
        "10–50% thresholds trade broad spatial inclusion for stricter L5 representation; single-catchment trends are unaffected",
    )
    _footer(
        fig,
        "Coverage = area of the L5 polygon intersected by the union of eligible catchment polygons assigned through their outlets ÷ total L5 polygon area.",
    )
    _save(fig, config["paths"]["figures"] / "figure_05_physical_decomposition", int(config["plotting"]["dpi"]))


def _coherence_panel(
    ax: plt.Axes,
    evidence: pd.DataFrame,
    catchments: pd.DataFrame,
    membership: pd.DataFrame,
    metric: str,
    limit_rows: int = 7,
) -> None:
    selected = evidence[
        evidence["metric"].eq(metric) & evidence["strong_evidence"]
    ].copy()
    selected = selected.reindex(selected["slope_per_decade"].abs().sort_values(ascending=False).index).head(limit_rows)
    selected = selected.sort_values("slope_per_decade")
    for y, row in enumerate(selected.itertuples(index=False)):
        ids = membership.loc[membership["hybas_id_l5"].eq(row.HYBAS_ID), "GCIN"]
        local = catchments[
            catchments["GCIN"].isin(ids) & catchments["variable"].eq(metric)
        ]
        ax.scatter(
            local["display_slope_per_decade"], np.full(len(local), y),
            s=18, facecolor="#D5DEE3", edgecolor="#8696A2", linewidth=0.45,
            alpha=0.88, zorder=2,
        )
        ax.hlines(y, row.ci_low, row.ci_high, color="#4A5B69", linewidth=1.3, zorder=3)
        ax.scatter(
            row.slope_per_decade, y, marker="D", s=42,
            color=ORANGE if row.slope_per_decade > 0 else BLUE,
            edgecolor="white", linewidth=0.7, zorder=4,
        )
    ax.axvline(0, color=INK, linewidth=0.8)
    labels = [f"{row.basin_code} · {row.coverage_pct:.0f}%" for row in selected.itertuples(index=False)]
    ax.set_yticks(np.arange(len(selected)), labels, fontsize=8)
    ax.set_title(METRIC_LABELS[metric], loc="left")
    ax.set_xlabel("Percentage points / decade" if metric == "intensity_fraction" else "SSI units / decade")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)


def figure_robustness_matrix(config: dict[str, Any]) -> None:
    threshold = int(config["local_analysis"]["default_area_coverage_threshold_percent"])
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    support = _spatial_support(config)[["HYBAS_ID", "coverage_pct"]]
    evidence = evidence.merge(support, on="HYBAS_ID", how="left")
    evidence = evidence[evidence["coverage_pct"].ge(threshold)]
    catchments = pd.read_csv(config["paths"]["tables"] / "catchment_mechanism_trends.csv")
    membership = pd.read_csv(config["paths"]["tables"] / "hydrobasin_catchment_membership.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.5))
    fig.subplots_adjust(left=0.17, right=0.96, bottom=0.19, top=0.79, wspace=0.42)
    _coherence_panel(axes[0], evidence, catchments, membership, "intensity_fraction")
    _coherence_panel(axes[1], evidence, catchments, membership, "ssi_7d")
    axes[0].scatter([], [], s=18, facecolor="#D5DEE3", edgecolor="#8696A2", label="Individual catchment trend")
    axes[0].scatter([], [], marker="D", s=42, color=ORANGE, edgecolor="white", label="Pooled L5 estimate")
    fig.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.075), ncol=2)
    _header(
        fig,
        "Regional patterns remain traceable to their contributing catchments",
        f"Strongest L5 signals at ≥{threshold}% area support · grey circles are direct catchment slopes · diamonds and lines are pooled estimates and 95% CIs",
    )
    _footer(
        fig,
        "Labels report L5 code and observed area support. A regional estimate summarizes a shared within-catchment direction; it does not imply that every contributing catchment is individually significant.",
    )
    _save(fig, config["paths"]["figures"] / "figure_06_robustness_matrix", int(config["plotting"]["dpi"]))


def build_all_figures(config: dict[str, Any]) -> None:
    _style()
    figure_sample_coverage(config)
    figure_mechanism_change_maps(config)
    figure_strong_signal_rankings(config)
    figure_mechanism_trajectories(config)
    figure_physical_decomposition(config)
    figure_robustness_matrix(config)

    destination = config["paths"]["report_assets"]
    destination.mkdir(parents=True, exist_ok=True)
    expected = {
        "figure_01_sample_coverage",
        "figure_02_mechanism_change_maps",
        "figure_03_strong_signal_rankings",
        "figure_04_mechanism_trajectories",
        "figure_05_physical_decomposition",
        "figure_06_robustness_matrix",
    }
    expected_assets = {f"{stem}.png" for stem in expected}
    for existing in destination.glob("figure_*.*"):
        if existing.name not in expected_assets:
            existing.unlink()
    for stem in expected:
        source = config["paths"]["figures"] / f"{stem}.png"
        shutil.copy2(source, destination / source.name)
