from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Circle, FancyBboxPatch, Patch


CAUSE_ORDER = [
    "Intensity-Dry",
    "Intensity-Moderate",
    "Intensity-Wet",
    "Volume-Dry",
    "Volume-Moderate",
    "Volume-Wet",
]


def _style(config: dict[str, Any]) -> dict[str, str]:
    palette = config["plotting"]["palette"]
    sns.set_theme(style="whitegrid")
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "axes.edgecolor": palette["ink"],
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": palette["grid"],
        "grid.linewidth": 0.6,
        "grid.alpha": 0.65,
        "xtick.color": palette["ink"],
        "ytick.color": palette["ink"],
        "text.color": palette["ink"],
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
    })
    return palette


def _header(fig: plt.Figure, title: str, subtitle: str, palette: dict[str, str]) -> None:
    fig.text(0.055, 0.975, title, ha="left", va="top", fontsize=15.5, fontweight="bold", color=palette["ink"])
    fig.text(0.055, 0.930, subtitle, ha="left", va="top", fontsize=8.8, color="#5D6978")
    # Small fixed research blossom mark in the top-right corner.
    centers = [(0.952, 0.963), (0.965, 0.976), (0.978, 0.963), (0.965, 0.950)]
    colors = [palette["blue"], palette["gold"], palette["orange"], palette["olive"]]
    for (x, y), color in zip(centers, colors):
        fig.add_artist(Circle((x, y), 0.008, transform=fig.transFigure, color=color, alpha=0.92, linewidth=0))


def _footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.055, 0.018, text, ha="left", va="bottom", fontsize=7.0, color="#6B7280")


def _save(fig: plt.Figure, output_base: Path, dpi: int) -> None:
    fig.savefig(output_base.with_suffix(".png"), dpi=dpi)
    fig.savefig(output_base.with_suffix(".svg"))
    plt.close(fig)


def _world(config: dict[str, Any]) -> gpd.GeoDataFrame:
    path = config["paths"]["world_boundaries"]
    return gpd.read_file(path)


def figure_sample_coverage(config: dict[str, Any]) -> None:
    palette = _style(config)
    metadata = pd.read_parquet(config["paths"]["derived_data"] / "catchment_metadata.parquet")
    features = pd.read_parquet(
        config["paths"]["derived_data"] / "event_features.parquet",
        columns=["GCIN", "longitude", "latitude", "country"],
    ).drop_duplicates("GCIN")
    annual = pd.read_parquet(
        config["paths"]["derived_data"] / "annual_maximum_events.parquet",
        columns=["GCIN", "longitude", "latitude", "continent"],
    ).drop_duplicates("GCIN")
    eligible_ids = set(annual["GCIN"])
    features["status"] = np.where(features["GCIN"].isin(eligible_ids), "Primary sample", "Screened out")
    world = _world(config)

    fig = plt.figure(figsize=(13.2, 6.8))
    grid = fig.add_gridspec(
        1, 2, width_ratios=[4.15, 1.25], left=0.055, right=0.955,
        bottom=0.14, top=0.80, wspace=0.34,
    )
    ax = fig.add_subplot(grid[0, 0])
    bar_ax = fig.add_subplot(grid[0, 1])
    world.plot(ax=ax, color="#F3F5F7", edgecolor="#C7CED7", linewidth=0.45)
    screened = features[features["status"] == "Screened out"]
    selected = features[features["status"] == "Primary sample"]
    ax.scatter(screened["longitude"], screened["latitude"], s=4, color="#B7C0CB", alpha=0.42, linewidth=0, label=f"Screened out (n={len(screened):,})")
    ax.scatter(selected["longitude"], selected["latitude"], s=6, color=palette["blue"], alpha=0.74, linewidth=0, label=f"Primary sample (n={len(selected):,})")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(False)
    ax.legend(loc="lower left", frameon=False, fontsize=7.5, handletextpad=0.5, labelspacing=0.35)

    counts = annual.groupby("continent")["GCIN"].nunique().sort_values()
    bar_ax.barh(counts.index, counts.values, color=palette["blue"], edgecolor="none", height=0.72)
    for index, value in enumerate(counts.values):
        bar_ax.text(value + counts.max() * 0.025, index, f"{value:,}", va="center", fontsize=7.5, fontweight="bold")
    bar_ax.set_xlim(0, counts.max() * 1.22)
    bar_ax.set_xlabel("Catchments")
    bar_ax.set_title("Primary sample by region", loc="left", fontweight="bold", pad=12, fontsize=10)
    bar_ax.spines[["top", "right", "left"]].set_visible(False)
    bar_ax.grid(axis="x")
    bar_ax.grid(axis="y", visible=False)
    bar_ax.tick_params(axis="y", length=0, labelsize=8, pad=5)

    _header(fig, "Coverage of the rainfall-driven flood trend sample", "Annual maxima, 1982–2019 · low-snow catchments · ≥30 observed years and ≥80% record coverage", palette)
    _footer(fig, "Source: Event_Typology catchment and event assets; Natural Earth 1:110m background. Asia contains only four eligible catchments.")
    _save(fig, config["paths"]["figures"] / "figure_01_sample_coverage", int(config["plotting"]["dpi"]))


def figure_global_composition(config: dict[str, Any]) -> None:
    palette = _style(config)
    annual = pd.read_parquet(config["paths"]["derived_data"] / "annual_maximum_events.parquet")
    annual_by_year = annual.groupby("peak_year").agg(
        intensity_share=("intensity_050", "mean"),
        wet_share=("wet_1d", "mean"),
        catchments=("GCIN", "nunique"),
    ).reset_index()
    for column in ("intensity_share", "wet_share"):
        annual_by_year[f"{column}_rolling"] = annual_by_year[column].rolling(5, center=True, min_periods=3).mean()
    panel = pd.read_csv(config["paths"]["tables"] / "panel_fixed_effect_trends.csv")
    panel = panel[(panel["sample"] == "annual_maximum") & (panel["region"] == "Global")].set_index("outcome")

    fig, axes = plt.subplots(2, 1, figsize=(11.4, 7.2), sharex=True, gridspec_kw={"hspace": 0.30})
    fig.subplots_adjust(left=0.09, right=0.96, bottom=0.11, top=0.81)
    specs = [
        (axes[0], "intensity_share", "Intensity-dominated annual maxima", palette["orange"], "intensity_050"),
        (axes[1], "wet_share", "Annual maxima following wet antecedent conditions", palette["blue"], "wet_1d"),
    ]
    for ax, column, title, color, outcome in specs:
        ax.plot(annual_by_year["peak_year"], annual_by_year[column] * 100, color=color, alpha=0.28, linewidth=1.1, marker="o", markersize=2.7)
        ax.plot(annual_by_year["peak_year"], annual_by_year[f"{column}_rolling"] * 100, color=color, linewidth=2.7, label="5-year centered mean")
        estimate = panel.loc[outcome]
        ax.text(
            0.985,
            0.12,
            f"{estimate.slope_per_decade:+.2f} pp / decade\n95% CI {estimate.ci_low:+.2f} to {estimate.ci_high:+.2f}",
            transform=ax.transAxes,
            ha="right",
            fontsize=8,
            color=palette["ink"],
            bbox={"boxstyle": "round,pad=0.38", "facecolor": "#F7F9FA", "edgecolor": "#D8DEE6", "linewidth": 0.6},
        )
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_ylabel("Share of annual maxima (%)")
        ax.set_ylim(0, max(55, float((annual_by_year[column] * 100).max()) + 5))
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].set_xlabel("Year")
    _header(fig, "Global composition of annual maximum flood conditions", "Thin lines show observed annual composition; bold lines show centered five-year means", palette)
    _footer(fig, "Source: 100,788 reconstructed annual maxima from 2,839 catchments. Slopes use catchment fixed effects and catchment-clustered uncertainty.")
    _save(fig, config["paths"]["figures"] / "figure_02_global_composition", int(config["plotting"]["dpi"]))


def figure_regional_panel_trends(config: dict[str, Any]) -> None:
    palette = _style(config)
    panel = pd.read_csv(config["paths"]["tables"] / "panel_fixed_effect_trends.csv")
    panel = panel[(panel["sample"] == "annual_maximum") & panel["outcome"].isin(["intensity_050", "wet_1d"])].copy()
    region_order = ["Global", "Africa", "Europe", "North America", "Oceania", "South America"]
    panel = panel[panel["region"].isin(region_order)]

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 6.15), sharey=True)
    fig.subplots_adjust(left=0.18, right=0.96, bottom=0.14, top=0.79, wspace=0.17)
    specs = [
        ("intensity_050", "Intensity-dominated share", palette["orange"]),
        ("wet_1d", "Wet antecedent share (1 day)", palette["blue"]),
    ]
    positions = np.arange(len(region_order))[::-1]
    for ax, (outcome, title, color) in zip(axes, specs):
        subset = panel[panel["outcome"] == outcome].set_index("region").reindex(region_order)
        ax.axhspan(positions[0] - 0.34, positions[0] + 0.34, color="#F4F6F8", zorder=0)
        ax.axvline(0, color=palette["ink"], linewidth=0.9)
        for position, (region, row) in zip(positions, subset.iterrows()):
            is_global = region == "Global"
            marker_color = palette["ink"] if is_global else color
            ax.plot([row.ci_low, row.ci_high], [position, position], color=marker_color, linewidth=2.2 if is_global else 1.5)
            ax.scatter(row.slope_per_decade, position, s=55 if is_global else 34, color=marker_color, edgecolor="white", linewidth=0.7, zorder=3)
            ax.text(row.ci_high + 0.15, position, f"{row.slope_per_decade:+.2f}", va="center", fontsize=8, fontweight="bold" if is_global else "normal")
        ax.set_yticks(positions, region_order)
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Within-catchment change (percentage points/decade)")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x")
        ax.grid(axis="y", visible=False)
    _header(fig, "Regional fixed-effect trends in flood conditions", "Dots are within-catchment slopes; lines are 95% catchment-clustered confidence intervals", palette)
    _footer(fig, "Asia is omitted because only four catchments pass the primary record screen. Regional estimates describe the available gauge sample, not area-weighted continents.")
    _save(fig, config["paths"]["figures"] / "figure_03_regional_panel_trends", int(config["plotting"]["dpi"]))


def figure_catchment_trend_maps(config: dict[str, Any]) -> None:
    palette = _style(config)
    trends = pd.read_csv(config["paths"]["tables"] / "catchment_continuous_trends.csv")
    world = _world(config)
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 8.55))
    fig.subplots_adjust(left=0.055, right=0.94, bottom=0.085, top=0.82, hspace=0.29)
    specs = [
        ("intensity_fraction", "Rainfall concentration ratio", "Change in Pmax / event rainfall per decade"),
        ("ssi_1d", "Antecedent soil saturation index", "Change in one-day antecedent SSI per decade"),
    ]
    cmap = mpl.colors.LinearSegmentedColormap.from_list("change", [palette["blue"], "#F7F7F5", palette["orange"]])
    for ax, (variable, title, subtitle) in zip(axes, specs):
        subset = trends[trends["variable"] == variable].copy()
        limit = float(np.nanquantile(np.abs(subset["sen_slope_per_decade"]), 0.95))
        norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
        world.plot(ax=ax, color="#F3F5F7", edgecolor="#CBD2D9", linewidth=0.4)
        scatter = ax.scatter(
            subset["longitude"], subset["latitude"], c=subset["sen_slope_per_decade"],
            cmap=cmap, norm=norm, s=8, alpha=0.82, linewidth=0,
        )
        significant = subset[subset["fdr_significant"]]
        if not significant.empty:
            ax.scatter(significant["longitude"], significant["latitude"], facecolors="none", edgecolors=palette["ink"], linewidth=0.8, s=25)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 85)
        ax.set_title(title, loc="left", fontweight="bold", pad=19)
        ax.text(0, 1.006, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5, color="#606B78")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(False)
        colorbar = fig.colorbar(scatter, ax=ax, orientation="vertical", fraction=0.018, pad=0.012)
        colorbar.set_label("Sen slope per decade")
    _header(fig, "Catchment-scale trend magnitudes", "Color limits use the 95th percentile of absolute slopes; outlined points pass 5% FDR", palette)
    _footer(fig, "Source: annual maximum events, 1982–2019. Nearly all individual trends do not survive FDR correction; maps are descriptive spatial evidence.")
    _save(fig, config["paths"]["figures"] / "figure_04_catchment_trend_maps", int(config["plotting"]["dpi"]))


def figure_sensitivity_matrix(config: dict[str, Any]) -> None:
    palette = _style(config)
    panel = pd.read_csv(config["paths"]["tables"] / "panel_fixed_effect_trends.csv")
    outcomes = ["intensity_050", "intensity_joint_050_cv1", "intensity_075", "wet_1d", "wet_3d", "wet_7d", "wet_30d"]
    labels = ["Pmax/Pvol\n> 0.50", "Joint rule\n> 0.50 & CV > 1", "Pmax/Pvol\n> 0.75", "Wet\n1 day", "Wet\n3 days", "Wet\n7 days", "Wet\n30 days"]
    subset = panel[(panel["region"] == "Global") & panel["outcome"].isin(outcomes)].copy()
    matrix = subset.pivot(index="sample", columns="outcome", values="slope_per_decade").reindex(index=["annual_maximum", "pot_q95"], columns=outcomes)
    p_matrix = subset.pivot(index="sample", columns="outcome", values="cluster_robust_p").reindex(index=["annual_maximum", "pot_q95"], columns=outcomes)
    annotations = matrix.copy().astype(object)
    for row in matrix.index:
        for column in matrix.columns:
            star = "*" if p_matrix.loc[row, column] < 0.05 else ""
            annotations.loc[row, column] = f"{matrix.loc[row, column]:+.2f}{star}"

    fig, ax = plt.subplots(figsize=(12.0, 4.75))
    fig.subplots_adjust(left=0.18, right=0.91, bottom=0.23, top=0.73)
    limit = float(np.nanmax(np.abs(matrix.to_numpy())))
    cmap = mpl.colors.LinearSegmentedColormap.from_list("change", [palette["blue"], "#FAFAF8", palette["orange"]])
    sns.heatmap(
        matrix, ax=ax, cmap=cmap, center=0, vmin=-limit, vmax=limit,
        annot=annotations, fmt="", annot_kws={"fontsize": 9},
        linewidths=1.5, linecolor="white",
        cbar_kws={"label": "Percentage points per decade", "shrink": 0.88, "pad": 0.035},
    )
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_yticklabels(["Annual maximum", "POT / Q95"], rotation=0)
    ax.set_xlabel("")
    ax.set_ylabel("")
    _header(fig, "Sensitivity of global composition trends", "Values are within-catchment fixed-effect slopes; * denotes cluster-robust p < 0.05", palette)
    _footer(fig, "Intensity conclusions change with the classification rule; shorter antecedent-wetness windows show a consistent decline across both event samples.")
    _save(fig, config["paths"]["figures"] / "figure_05_sensitivity_matrix", int(config["plotting"]["dpi"]))


def figure_cause_composition(config: dict[str, Any]) -> None:
    palette = _style(config)
    composition = pd.read_csv(config["paths"]["tables"] / "cause_composition_by_region.csv")
    annual = pd.read_parquet(config["paths"]["derived_data"] / "annual_maximum_events.parquet", columns=["GCIN", "continent"])
    sample_sizes = annual.groupby("continent").agg(events=("GCIN", "size"), catchments=("GCIN", "nunique"))
    region_order = ["Africa", "Asia", "Europe", "North America", "Oceania", "South America"]
    pivot = composition.pivot(index="continent", columns="cause_primary", values="proportion").reindex(index=region_order, columns=CAUSE_ORDER).fillna(0)
    colors = [palette["orange"], "#E9A376", "#F3C8B0", palette["blue"], "#7EA4C0", "#BDD1E0"]

    fig, ax = plt.subplots(figsize=(11.8, 6.15))
    fig.subplots_adjust(left=0.19, right=0.96, bottom=0.25, top=0.78)
    left = np.zeros(len(pivot))
    for cause, color in zip(CAUSE_ORDER, colors):
        values = pivot[cause].to_numpy() * 100
        ax.barh(np.arange(len(pivot)), values, left=left, color=color, edgecolor="white", linewidth=0.8, label=cause)
        left += values
    labels = [f"{region}\n{sample_sizes.loc[region, 'catchments']:,} catchments" for region in pivot.index]
    ax.set_yticks(np.arange(len(pivot)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of annual maximum events (%)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    legend_labels = ["Intensity · dry", "Intensity · moderate", "Intensity · wet", "Volume · dry", "Volume · moderate", "Volume · wet"]
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles, legend_labels, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False, fontsize=7.5, columnspacing=1.6, handlelength=1.5)
    _header(fig, "Regional composition of flood-generating conditions", "Rainfall organization crossed with one-day antecedent dry, moderate, and wet states", palette)
    _footer(fig, "Event-weighted descriptive composition of the primary annual-max sample. Asia estimates are unstable because only four catchments qualify.")
    _save(fig, config["paths"]["figures"] / "figure_06_regional_cause_composition", int(config["plotting"]["dpi"]))


def figure_analysis_flow(config: dict[str, Any]) -> None:
    palette = _style(config)
    diagnostics = pd.read_csv(config["paths"]["tables"] / "sample_diagnostics.csv").set_index("stage")
    nodes = [
        (0.07, 0.36, 0.23, 0.28, "Rain-event feature set", f"{int(diagnostics.loc['source event catalogue', 'events']):,} events\n{int(diagnostics.loc['source event catalogue', 'catchments']):,} catchments", palette["pale"]),
        (0.385, 0.36, 0.24, 0.28, "Reconstructed and checked", f"{int(diagnostics.loc['valid reconstructed event features', 'events']):,} complete events\nDaily P and Q verified", "#E7F0F6"),
        (0.70, 0.58, 0.23, 0.28, "Primary annual maxima", f"{int(diagnostics.loc['primary annual-max sample', 'events']):,} events\n{int(diagnostics.loc['primary annual-max sample', 'catchments']):,} catchments", "#F6E7DE"),
        (0.70, 0.14, 0.23, 0.28, "POT / Q95 sensitivity", f"{int(diagnostics.loc['POT/Q95 sensitivity sample', 'events']):,} events\n{int(diagnostics.loc['POT/Q95 sensitivity sample', 'catchments']):,} catchments", "#E5EDF4"),
    ]
    fig, ax = plt.subplots(figsize=(12.0, 4.45))
    fig.subplots_adjust(left=0.03, right=0.97, bottom=0.10, top=0.80)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for x, y, width, height, title, body, fill in nodes:
        patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.012,rounding_size=0.018", facecolor=fill, edgecolor="#AAB4C0", linewidth=0.9)
        ax.add_patch(patch)
        ax.text(x + 0.025, y + height * 0.68, title, ha="left", va="center", fontsize=9.5, fontweight="bold")
        ax.text(x + 0.025, y + height * 0.34, body, ha="left", va="center", fontsize=8.8, color="#596573", linespacing=1.35)
    arrow = {"arrowstyle": "-|>", "color": "#778391", "linewidth": 1.4, "mutation_scale": 13}
    ax.annotate("", xy=(0.385, 0.50), xytext=(0.30, 0.50), arrowprops=arrow)
    ax.annotate("", xy=(0.70, 0.72), xytext=(0.625, 0.53), arrowprops=arrow)
    ax.annotate("", xy=(0.70, 0.28), xytext=(0.625, 0.47), arrowprops=arrow)
    _header(fig, "Event selection and analysis branches", "The extreme-event definition is separated from the rainfall/wetness classification", palette)
    _footer(fig, "All exclusions and missing windows are retained in CSV audit tables; the two event samples are analyzed as primary and sensitivity branches.")
    _save(fig, config["paths"]["figures"] / "figure_07_analysis_flow", int(config["plotting"]["dpi"]))


def figure_local_hydrobasin_maps(config: dict[str, Any]) -> None:
    from .local_analysis import _load_hydrobasins

    palette = _style(config)
    level = int(config["local_analysis"]["primary_level"])
    trends = pd.read_csv(config["paths"]["tables"] / "local_hydrobasin_trends.csv")
    trends = trends[
        (trends["sample"] == "annual_maximum")
        & (trends["level"] == level)
        & trends["outcome"].isin(["intensity_050", "wet_1d"])
    ].copy()
    robustness = pd.read_csv(
        config["paths"]["tables"] / "local_hydrobasin_robustness.csv"
    )
    robustness = robustness[
        (robustness["level"] == level)
        & robustness["outcome"].isin(["intensity_050", "wet_1d"])
    ][["HYBAS_ID", "outcome", "high_confidence_local_signal"]]
    trends = trends.merge(robustness, on=["HYBAS_ID", "outcome"], how="left")
    basins = _load_hydrobasins(config["paths"]["hydrobasins"], level)
    world = _world(config)
    catchments = pd.read_csv(
        config["paths"]["tables"] / "hydrobasin_catchment_membership.csv"
    )

    fig = plt.figure(figsize=(12.8, 10.8))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 0.025],
        left=0.06,
        right=0.94,
        bottom=0.075,
        top=0.83,
        hspace=0.22,
        wspace=0.035,
    )
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[1, 0])]
    colorbar_ax = fig.add_subplot(grid[:, 1])
    specs = [
        ("intensity_050", "Intensity-dominated annual maxima"),
        ("wet_1d", "Wet one-day antecedent conditions"),
    ]
    limit = float(np.nanmax(np.abs(trends["slope_per_decade"])))
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "local_change", [palette["blue"], "#F7F7F5", palette["orange"]]
    )
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    scatter_for_colorbar = None
    for ax, (outcome, title) in zip(axes, specs):
        subset = trends[trends["outcome"] == outcome]
        mapped = basins.merge(subset, on="HYBAS_ID", how="inner")
        world.plot(ax=ax, color="#F3F5F7", edgecolor="#CDD4DC", linewidth=0.35)
        mapped.plot(
            ax=ax,
            column="slope_per_decade",
            cmap=cmap,
            norm=norm,
            edgecolor="white",
            linewidth=0.55,
        )
        replicated = mapped[mapped["high_confidence_local_signal"].fillna(False)]
        if not replicated.empty:
            replicated.boundary.plot(ax=ax, color=palette["ink"], linewidth=1.25)
        ax.scatter(
            catchments["longitude"],
            catchments["latitude"],
            s=2.2,
            color="#6F7B88",
            alpha=0.28,
            linewidth=0,
        )
        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 85)
        ax.set_title(title, loc="left", fontweight="bold", pad=8)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(False)
        scatter_for_colorbar = ax.scatter([], [], c=[], cmap=cmap, norm=norm)
    colorbar = fig.colorbar(scatter_for_colorbar, cax=colorbar_ax, orientation="vertical")
    colorbar.set_label("Percentage points per decade")
    axes[0].legend(
        handles=[Patch(facecolor="white", edgecolor=palette["ink"], linewidth=1.25, label="High-confidence local signal")],
        loc="lower left",
        frameon=False,
        fontsize=7.5,
    )
    _header(
        fig,
        f"HydroBASINS level-{level} fixed-effect trends",
        "Only units with at least 20 catchments are estimated; outlines mark high-confidence local signals",
        palette,
    )
    _footer(
        fig,
        "Source: HydroBASINS v1.c and reconstructed annual maxima, 1982–2019. Colors are within-catchment slopes, not spatially area-weighted trends.",
    )
    _save(
        fig,
        config["paths"]["figures"] / "figure_08_local_hydrobasin_trend_maps",
        int(config["plotting"]["dpi"]),
    )


def figure_local_hydrobasin_ranked(config: dict[str, Any]) -> None:
    palette = _style(config)
    robustness = pd.read_csv(
        config["paths"]["tables"] / "local_hydrobasin_robustness.csv"
    )
    level = int(config["local_analysis"]["primary_level"])
    selected = robustness[
        (robustness["level"] == level)
        & robustness["high_confidence_local_signal"].fillna(False)
        & robustness["outcome"].isin(["intensity_050", "wet_1d"])
    ].copy()

    fig, axes = plt.subplots(2, 1, figsize=(12.4, 8.4))
    fig.subplots_adjust(left=0.30, right=0.94, bottom=0.10, top=0.80, hspace=0.46)
    specs = [
        ("intensity_050", "Intensity-dominated annual maxima", palette["orange"], 9),
        ("wet_1d", "Wet one-day antecedent conditions", palette["blue"], 6),
    ]
    for ax, (outcome, title, color, limit_rows) in zip(axes, specs):
        subset = selected[selected["outcome"] == outcome].copy()
        subset = subset.loc[
            subset["slope_per_decade"].abs().sort_values(ascending=False).index
        ].head(limit_rows)
        subset = subset.sort_values("slope_per_decade")
        positions = np.arange(len(subset))
        ax.axvline(0, color=palette["ink"], linewidth=0.9)
        ax.hlines(
            positions,
            subset["ci_low"],
            subset["ci_high"],
            color=color,
            linewidth=1.8,
        )
        ax.scatter(
            subset["slope_per_decade"],
            positions,
            color=color,
            s=42,
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        for position, row in zip(positions, subset.itertuples()):
            offset = 0.18 if row.slope_per_decade >= 0 else -0.18
            alignment = "left" if row.slope_per_decade >= 0 else "right"
            ax.text(
                row.slope_per_decade + offset,
                position,
                f"{row.slope_per_decade:+.2f}",
                va="center",
                ha=alignment,
                fontsize=7.5,
                fontweight="bold",
            )
        labels = [f"{row.basin_label}  ·  {row.basin_code}" for row in subset.itertuples()]
        ax.set_yticks(positions, labels)
        ax.set_title(title, loc="left", fontweight="bold", pad=8)
        ax.set_xlabel("Within-catchment change (percentage points/decade)")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x")
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", length=0, labelsize=7.5, pad=7)
        extent = max(abs(subset["ci_low"].min()), abs(subset["ci_high"].max())) + 1.2
        ax.set_xlim(-extent, extent)
    _header(
        fig,
        f"Replicated HydroBASINS level-{level} trend estimates",
        "Largest effects also stable across definitions, paired-period and POT/Q95 checks, and leave-one-catchment-out tests",
        palette,
    )
    _footer(
        fig,
        "Bars show 95% catchment-clustered confidence intervals. Basin labels use dominant country codes and median gauge coordinates because HydroBASINS units are unnamed.",
    )
    _save(
        fig,
        config["paths"]["figures"] / "figure_09_local_hydrobasin_ranked_trends",
        int(config["plotting"]["dpi"]),
    )


def build_all_figures(config: dict[str, Any]) -> None:
    figure_sample_coverage(config)
    figure_global_composition(config)
    figure_regional_panel_trends(config)
    figure_catchment_trend_maps(config)
    figure_sensitivity_matrix(config)
    figure_cause_composition(config)
    figure_analysis_flow(config)
    figure_local_hydrobasin_maps(config)
    figure_local_hydrobasin_ranked(config)
    report_assets = config["paths"]["report_assets"]
    report_assets.mkdir(parents=True, exist_ok=True)
    for source in config["paths"]["figures"].glob("figure_*.png"):
        shutil.copy2(source, report_assets / source.name)
