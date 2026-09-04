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

from .analysis import MECHANISMS
from .statistics import binomial_probability_trend


BLUE = "#2F6688"
ORANGE = "#D96B3F"
GOLD = "#D9A928"
CYAN = "#19C9DE"
INK = "#233143"
MUTED = "#66778A"
GRID = "#D9E1E7"
LAND = "#F4F7F8"
NEUTRAL = "#ECEBE6"
CMAP = LinearSegmentedColormap.from_list("process_shift", [BLUE, NEUTRAL, ORANGE])

MECHANISM_LABELS = {
    "Dry-Intensity": "Dry + intensity",
    "Dry-Volume": "Dry + volume",
    "Moderate-Intensity": "Moderate + intensity",
    "Moderate-Volume": "Moderate + volume",
    "Wet-Intensity": "Wet + intensity",
    "Wet-Volume": "Wet + volume",
}
MECHANISM_COLORS = {
    "Dry-Intensity": "#D96B3F",
    "Dry-Volume": "#E6AA76",
    "Moderate-Intensity": "#D9A928",
    "Moderate-Volume": "#A8A36A",
    "Wet-Intensity": "#4C8EA6",
    "Wet-Volume": "#2F6688",
}
OUTCOME_LABELS = {
    "direct_runoff_volume": "Direct stormflow volume",
    "flood_peak": "Daily flood peak",
    "exceedance_frequency": "Q95-event frequency",
    "mechanism_frequency": "Process frequency",
    "mechanism_share": "Process share",
    "rainfall_concentration": "Rainfall concentration",
    "antecedent_wetness": "Antecedent wetness",
}


def _style() -> None:
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": GRID,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.055, 0.972, title, ha="left", va="top", fontsize=17, weight="bold")
    fig.text(0.055, 0.928, subtitle, ha="left", va="top", fontsize=9.5, color=MUTED)


def _footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.055, 0.024, text, ha="left", va="bottom", fontsize=7.5, color=MUTED)


def _save(fig: plt.Figure, destination: Path, dpi: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination.with_suffix(".png"), dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(destination.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _world(config: dict[str, Any]) -> gpd.GeoDataFrame:
    return gpd.read_file(f"zip://{config['paths']['world_boundaries'].as_posix()}")


def _base_map(ax: plt.Axes, world: gpd.GeoDataFrame) -> None:
    world.plot(ax=ax, color=LAND, edgecolor="#C9D4DB", linewidth=0.35)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.set_axis_off()


def _limit(values: pd.Series) -> float:
    finite = pd.to_numeric(values, errors="coerce").dropna().abs()
    if finite.empty:
        return 1.0
    value = float(finite.quantile(0.95))
    return value if value > 0 else 1.0


def _map_estimates(
    ax: plt.Axes,
    world: gpd.GeoDataFrame,
    frame: pd.DataFrame,
    title: str,
    limit: float | None = None,
) -> mpl.cm.ScalarMappable:
    _base_map(ax, world)
    values = pd.to_numeric(frame["display_slope_per_decade"], errors="coerce")
    limit = limit or _limit(values)
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    unsupported = frame[~frame["supported_shift"].fillna(False)]
    supported = frame[frame["supported_shift"].fillna(False)]
    if len(unsupported):
        ax.scatter(
            unsupported["longitude"], unsupported["latitude"],
            c=unsupported["display_slope_per_decade"], cmap=CMAP, norm=norm,
            s=10, alpha=0.28, linewidths=0, rasterized=True,
        )
    if len(supported):
        ax.scatter(
            supported["longitude"], supported["latitude"],
            c=supported["display_slope_per_decade"], cmap=CMAP, norm=norm,
            s=27, alpha=0.98, linewidths=0, zorder=5,
        )
    ax.set_title(f"{title}\n{len(supported):,} supported of {len(frame):,} estimates", loc="left")
    return mpl.cm.ScalarMappable(norm=norm, cmap=CMAP)


def figure_sample_and_process_coverage(config: dict[str, Any]) -> None:
    sample = pd.read_parquet(config["paths"]["derived_data"] / "primary_extreme_events.parquet")
    catchments = sample[["GCIN", "continent", "longitude", "latitude"]].drop_duplicates("GCIN")
    composition = pd.read_csv(config["paths"]["tables"] / "mechanism_composition.csv")
    world = _world(config)

    fig = plt.figure(figsize=(13.5, 7.2))
    grid = fig.add_gridspec(1, 2, width_ratios=[3.25, 1.35], left=0.055, right=0.96,
                            bottom=0.11, top=0.84, wspace=0.10)
    ax = fig.add_subplot(grid[0, 0])
    _base_map(ax, world)
    ax.scatter(catchments["longitude"], catchments["latitude"], s=5.8,
               color=BLUE, alpha=0.72, linewidths=0, rasterized=True)
    ax.text(-174, -53, f"{len(sample):,} Q95 events\n{len(catchments):,} gauged catchments",
            fontsize=9, va="bottom")

    bars = fig.add_subplot(grid[0, 1])
    composition["label"] = composition["mechanism"].map(MECHANISM_LABELS)
    composition = composition.sort_values("events")
    bars.barh(composition["label"], composition["events"],
              color=[MECHANISM_COLORS[x] for x in composition["mechanism"]], height=0.62)
    for y, row in enumerate(composition.itertuples(index=False)):
        bars.text(row.events + composition["events"].max() * 0.025, y,
                  f"{row.events:,}  ({row.share_percent:.1f}%)", va="center", fontsize=8.5)
    bars.set_title("Large-flood process composition", loc="left")
    bars.set_xlabel("Selected events")
    bars.grid(axis="x", color=GRID, linewidth=0.6)
    bars.spines[["top", "right", "left"]].set_visible(False)
    bars.tick_params(axis="y", length=0)

    _header(fig, "The primary sample is global; its process mixture is not",
            "Catchment-specific Q95 of direct stormflow volume · rainfall-driven low-snow events · 1982–2019")
    _footer(fig, "Points are observed catchments, not an area-complete global sample. Process = antecedent state × rainfall temporal organization.")
    _save(fig, config["paths"]["figures"] / "figure_01_sample_and_process_coverage", config["plotting"]["dpi"])


def figure_overall_flood_changes(config: dict[str, Any]) -> None:
    table = pd.read_csv(config["paths"]["tables"] / "catchment_overall_trends.csv")
    world = _world(config)
    outcomes = ["direct_runoff_volume", "flood_peak", "exceedance_frequency"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    mappables = []
    for ax, outcome in zip(axes, outcomes):
        frame = table[table["outcome"].eq(outcome)]
        mappables.append(_map_estimates(ax, world, frame, OUTCOME_LABELS[outcome]))
    for ax, mapping, outcome in zip(axes, mappables, outcomes):
        cbar = fig.colorbar(mapping, ax=ax, orientation="horizontal", fraction=0.045, pad=0.035)
        unit = table.loc[table["outcome"].eq(outcome), "display_unit"].dropna()
        cbar.set_label(unit.iloc[0] if len(unit) else "change per decade", fontsize=8)
        cbar.ax.tick_params(labelsize=7)
    fig.subplots_adjust(left=0.04, right=0.985, top=0.80, bottom=0.12, wspace=0.08)
    _header(fig, "What happened to the selected large floods themselves?",
            "Pale points are estimable trends; larger saturated points pass the complete direction-stability screen")
    _footer(fig, "Q95 is defined from full-record event direct stormflow volume. A decade is 10 years.")
    _save(fig, config["paths"]["figures"] / "figure_02_overall_flood_changes", config["plotting"]["dpi"])


def _six_process_maps(config: dict[str, Any], outcome: str, filename: str, title: str) -> None:
    table = pd.read_csv(
        config["paths"]["tables"] / "catchment_mechanism_trends.csv",
        low_memory=False,
    )
    table = table[table["outcome"].eq(outcome)]
    world = _world(config)
    limit = _limit(table["display_slope_per_decade"])
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 7.8))
    mapping = None
    for ax, mechanism in zip(axes.ravel(), MECHANISMS):
        frame = table[table["mechanism"].eq(mechanism)]
        mapping = _map_estimates(ax, world, frame, MECHANISM_LABELS[mechanism], limit)
    fig.subplots_adjust(left=0.04, right=0.97, top=0.83, bottom=0.10, hspace=0.18, wspace=0.05)
    if mapping is not None:
        cbar = fig.colorbar(mapping, ax=axes.ravel().tolist(), orientation="horizontal",
                            fraction=0.028, pad=0.035, aspect=48)
        unit = table["display_unit"].dropna()
        cbar.set_label(unit.iloc[0] if len(unit) else "change per decade", fontsize=8.5)
    _header(fig, title,
            "Each panel follows one flood-generating process within each gauged catchment; opposing local directions are retained")
    _footer(fig, "A process is estimated with ≥5 selected events. Supported points pass p<0.05, alternative-sample, classification-threshold and leave-one-year checks.")
    _save(fig, config["paths"]["figures"] / filename, config["plotting"]["dpi"])


def figure_process_frequency(config: dict[str, Any]) -> None:
    _six_process_maps(
        config, "mechanism_frequency", "figure_03_process_frequency_changes",
        "Where did particular large-flood processes become more or less frequent?",
    )


def figure_process_share(config: dict[str, Any]) -> None:
    _six_process_maps(
        config, "mechanism_share", "figure_04_process_share_changes",
        "How did the composition of the local upper tail change?",
    )


def figure_process_response_rankings(config: dict[str, Any]) -> None:
    table = pd.read_csv(
        config["paths"]["tables"] / "catchment_mechanism_trends.csv",
        low_memory=False,
    )
    outcomes = ["direct_runoff_volume", "flood_peak"]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.2))
    for ax, outcome in zip(axes, outcomes):
        frame = table[table["outcome"].eq(outcome) & table["supported_shift"].fillna(False)].copy()
        frame["magnitude"] = frame["display_slope_per_decade"].abs()
        frame = frame.nlargest(14, "magnitude").sort_values("display_slope_per_decade")
        labels = [f"GCIN {int(row.GCIN)} · {MECHANISM_LABELS[row.mechanism]}" for row in frame.itertuples()]
        colors = np.where(frame["display_slope_per_decade"].ge(0), ORANGE, BLUE)
        ax.barh(labels, frame["display_slope_per_decade"], color=colors, height=0.64)
        ax.axvline(0, color=INK, linewidth=0.8)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=7.5)
        unit = frame["display_unit"].dropna()
        ax.set_xlabel(unit.iloc[0] if len(unit) else "change per decade")
        ax.set_title(OUTCOME_LABELS[outcome], loc="left")
    fig.subplots_adjust(left=0.15, right=0.98, top=0.82, bottom=0.12, wspace=0.44)
    _header(fig, "The strongest reproducible changes in process-specific flood response",
            "Ranked by absolute trend magnitude; ranking is descriptive, not a cross-catchment causal comparison")
    _footer(fig, "Direct stormflow volume and daily flood peak answer what happened to floods generated by each process.")
    _save(fig, config["paths"]["figures"] / "figure_05_process_response_rankings", config["plotting"]["dpi"])


def figure_example_trajectories(config: dict[str, Any]) -> None:
    table = pd.read_csv(
        config["paths"]["tables"] / "catchment_mechanism_trends.csv",
        low_memory=False,
    )
    candidates = table[
        table["outcome"].eq("mechanism_share") & table["supported_shift"].fillna(False)
    ].copy()
    candidates["magnitude"] = candidates["display_slope_per_decade"].abs()
    examples = candidates.nlargest(3, "magnitude")
    sample = pd.read_parquet(config["paths"]["derived_data"] / "primary_extreme_events.parquet")
    fig, axes = plt.subplots(1, max(1, len(examples)), figsize=(13.5, 4.8), squeeze=False)
    for ax, row in zip(axes.ravel(), examples.itertuples(index=False)):
        catchment = sample[sample["GCIN"].eq(row.GCIN)]
        totals = catchment.groupby("peak_year").size().rename("total")
        yes = catchment[catchment["mechanism"].eq(row.mechanism)].groupby("peak_year").size().rename("success")
        annual = pd.concat([totals, yes], axis=1).fillna(0).reset_index()
        estimate = binomial_probability_trend(
            annual["peak_year"].to_numpy(float), annual["success"].to_numpy(float), annual["total"].to_numpy(float)
        )
        share = 100 * annual["success"] / annual["total"]
        ax.scatter(annual["peak_year"], share, s=24, color=MECHANISM_COLORS[row.mechanism], alpha=0.75)
        if estimate:
            years = np.linspace(annual["peak_year"].min(), annual["peak_year"].max(), 100)
            beta = estimate["raw_slope_per_decade"]
            p0 = estimate["fitted_first"] / 100
            x0 = (annual["peak_year"].min() - 2000) / 10
            intercept = np.log(p0 / max(1e-9, 1 - p0)) - beta * x0
            fitted = 100 / (1 + np.exp(-(intercept + beta * ((years - 2000) / 10))))
            ax.plot(years, fitted, color=INK, linewidth=2)
        ax.set_ylim(-3, 103)
        ax.set_title(f"GCIN {int(row.GCIN)} · {MECHANISM_LABELS[row.mechanism]}\n{row.display_slope_per_decade:+.2f} pp / 10 years", loc="left")
        ax.set_xlabel("Year")
        ax.set_ylabel("Share of selected floods (%)")
        ax.grid(color=GRID, linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.16, wspace=0.25)
    _header(fig, "Examples of process composition emerging through time",
            "Dots are observed annual shares; curves are bias-reduced binomial fits used for the percentage-point effect")
    _footer(fig, "Examples are selected by supported absolute process-share trend and are not presented as globally representative.")
    _save(fig, config["paths"]["figures"] / "figure_06_example_process_trajectories", config["plotting"]["dpi"])


def build_all_figures(config: dict[str, Any]) -> None:
    _style()
    figure_sample_and_process_coverage(config)
    figure_overall_flood_changes(config)
    figure_process_frequency(config)
    figure_process_share(config)
    figure_process_response_rankings(config)
    figure_example_trajectories(config)

    destination = config["paths"]["report_assets"]
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(config["paths"]["figures"].glob("figure_0[1-6]_*.png")):
        shutil.copy2(path, destination / path.name)
    for path in sorted(config["paths"]["figures"].glob("figure_0[1-6]_*.svg")):
        shutil.copy2(path, destination / path.name)
