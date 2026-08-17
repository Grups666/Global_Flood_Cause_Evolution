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
CYAN = "#12CFE3"
INK = "#243142"
MUTED = "#667587"
PALE = "#EEF2F4"
GRID = "#D8E0E6"
NEUTRAL = "#F3EFE6"
CMAP = LinearSegmentedColormap.from_list("mechanism", [BLUE, NEUTRAL, ORANGE])


def _style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
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
    fig.text(0.055, 0.966, title, ha="left", va="top", fontsize=16, weight="bold")
    fig.text(0.055, 0.925, subtitle, ha="left", va="top", fontsize=9, color=MUTED)
    for x, y, color in [
        (0.944, 0.955, BLUE),
        (0.957, 0.968, "#D6A52C"),
        (0.970, 0.955, ORANGE),
        (0.957, 0.941, "#6B7D3E"),
    ]:
        fig.add_artist(plt.Circle((x, y), 0.007, transform=fig.transFigure, color=color))


def _footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.055, 0.025, text, ha="left", va="bottom", fontsize=7.2, color=MUTED)


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


def figure_sample_coverage(config: dict[str, Any]) -> None:
    sample = pd.read_parquet(
        config["paths"]["derived_data"] / "primary_extreme_events.parquet"
    )
    catchments = sample[
        ["GCIN", "continent", "longitude", "latitude"]
    ].drop_duplicates("GCIN")
    counts = catchments.groupby("continent")["GCIN"].nunique().sort_values()
    diagnostics = pd.read_csv(config["paths"]["tables"] / "extreme_sample_diagnostics.csv")
    primary = diagnostics[diagnostics["sample"].eq("pot_q95")].iloc[0]
    world = _world(config)

    fig = plt.figure(figsize=(13.5, 7.4))
    grid = fig.add_gridspec(1, 2, width_ratios=[3.8, 1.2], left=0.055, right=0.96, bottom=0.10, top=0.83, wspace=0.08)
    ax = fig.add_subplot(grid[0, 0])
    _base_map(ax, world)
    ax.scatter(
        catchments["longitude"], catchments["latitude"], s=3.6, color=BLUE,
        alpha=0.72, linewidths=0, rasterized=True,
    )
    ax.text(
        -174, -53,
        f"{len(sample):,} Q95 extreme events\n{catchments['GCIN'].nunique():,} long-record catchments",
        fontsize=8, color=INK, va="bottom",
    )

    bars = fig.add_subplot(grid[0, 1])
    bars.barh(counts.index, counts.values, color=BLUE, height=0.62)
    for y, value in enumerate(counts.values):
        bars.text(value + counts.max() * 0.025, y, f"{value:,}", va="center", fontsize=8, weight="bold")
    bars.set_title("Primary sample by region", loc="left", pad=12)
    bars.set_xlabel("Catchments")
    bars.set_xlim(0, counts.max() * 1.24)
    bars.spines[["top", "right", "left"]].set_visible(False)
    bars.tick_params(axis="y", length=0)
    bars.grid(axis="x", color=GRID, linewidth=0.6)
    bars.set_axisbelow(True)

    _header(
        fig,
        "Coverage of the extreme-flood mechanism sample",
        "Catchment-specific upper 5% of reconstructed event peaks · 1982–2019 · low-snow long records",
    )
    _footer(
        fig,
        f"Primary event windows have {int(primary.stormflow_window_overlaps)} overlaps; {int(primary.pairs_under_10_days):,} adjacent pairs are <10 days apart and are tested in a declustered sensitivity branch.",
    )
    _save(fig, config["paths"]["figures"] / "figure_01_sample_coverage", int(config["plotting"]["dpi"]))


def _map_panel(
    ax: plt.Axes,
    world: gpd.GeoDataFrame,
    basins: gpd.GeoDataFrame,
    evidence: pd.DataFrame,
    metric: str,
    title: str,
    limit: float,
) -> None:
    _base_map(ax, world)
    values = evidence[evidence["metric"].eq(metric)]
    layer = basins.merge(values, on="HYBAS_ID", how="inner")
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
    layer.plot(
        ax=ax, column="slope_per_decade", cmap=CMAP, norm=norm,
        edgecolor="#17212B", linewidth=0.22, alpha=0.94,
    )
    strong = layer[layer["strong_evidence"]]
    if not strong.empty:
        strong.boundary.plot(ax=ax, color=CYAN, linewidth=1.15, alpha=0.98)
    ax.set_title(title, loc="left", pad=5)


def figure_mechanism_change_maps(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    evidence = evidence[evidence["level"].eq(int(config["local_analysis"]["primary_level"]))]
    basins = load_hydrobasins(
        config["paths"]["hydrobasins"], int(config["local_analysis"]["primary_level"])
    ).to_crs("EPSG:4326")
    world = _world(config)
    panels = [
        ("intensity_fraction", "Rainfall concentration", 3.0),
        ("ssi_1d", "Antecedent SSI · 1 day", 0.015),
        ("ssi_3d", "Antecedent SSI · 3 days", 0.015),
        ("ssi_7d", "Antecedent SSI · 7 days", 0.015),
        ("ssi_30d", "Antecedent SSI · 30 days", 0.015),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.8))
    fig.subplots_adjust(left=0.045, right=0.965, bottom=0.09, top=0.84, wspace=0.025, hspace=0.12)
    for ax, (metric, title, limit) in zip(axes.flat[:5], panels):
        _map_panel(ax, world, basins, evidence, metric, title, limit)

    legend = axes.flat[5]
    legend.set_axis_off()
    legend.text(0.02, 0.90, "Direction of mechanism movement", fontsize=11, weight="bold", transform=legend.transAxes)
    gradient = np.linspace(-1, 1, 256).reshape(1, -1)
    inset = legend.inset_axes([0.03, 0.72, 0.78, 0.08])
    inset.imshow(gradient, aspect="auto", cmap=CMAP, extent=[-1, 1, 0, 1])
    inset.set_xticks([-1, 0, 1], ["lower", "no change", "higher"], fontsize=8)
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_visible(False)
    legend.text(0.03, 0.58, "Rainfall concentration", weight="bold", fontsize=9, transform=legend.transAxes)
    legend.text(0.03, 0.50, "Blue: toward long/volume-dominated rainfall\nOrange: toward short/concentrated rainfall", fontsize=8, color=MUTED, linespacing=1.5, transform=legend.transAxes)
    legend.text(0.03, 0.34, "Antecedent SSI", weight="bold", fontsize=9, transform=legend.transAxes)
    legend.text(0.03, 0.26, "Blue: toward drier antecedent states\nOrange: toward wetter antecedent states", fontsize=8, color=MUTED, linespacing=1.5, transform=legend.transAxes)
    legend.add_patch(plt.Rectangle((0.03, 0.10), 0.10, 0.06, fill=False, edgecolor=CYAN, linewidth=1.5, transform=legend.transAxes))
    legend.text(0.16, 0.105, "Strong evidence", fontsize=8, transform=legend.transAxes)

    _header(
        fig,
        "Local movement of extreme-flood generating conditions",
        "HydroBASINS level 5 · continuous-time within-catchment trends in the primary POT/Q95 sample",
    )
    _footer(
        fig,
        "Colour shows effect direction and magnitude; cyan outlines require complete-family FDR, ≥20 catchments, event-sample agreement, leave-one-catchment-out stability, and—where relevant—agreement across all SSI windows.",
    )
    _save(fig, config["paths"]["figures"] / "figure_02_mechanism_change_maps", int(config["plotting"]["dpi"]))


def _rank_panel(ax: plt.Axes, frame: pd.DataFrame, title: str, unit: str) -> None:
    ordered = frame.sort_values("slope_per_decade")
    y = np.arange(len(ordered))
    labels = ordered["basin_code"] + " · " + ordered["dominant_countries"]
    ax.hlines(y, ordered["ci_low"], ordered["ci_high"], color="#8493A1", linewidth=1.2)
    colors = np.where(ordered["slope_per_decade"] < 0, BLUE, ORANGE)
    ax.scatter(ordered["slope_per_decade"], y, c=colors, s=38, zorder=3, edgecolor="white", linewidth=0.7)
    ax.axvline(0, color="#263645", linewidth=0.8)
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_title(title, loc="left", pad=10)
    ax.set_xlabel(unit)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)


def figure_strong_signal_rankings(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    evidence = evidence[evidence["strong_evidence"]]
    concentration = evidence[evidence["metric"].eq("intensity_fraction")]
    wetness = evidence[evidence["metric"].eq("ssi_7d")]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.5))
    fig.subplots_adjust(left=0.17, right=0.96, bottom=0.12, top=0.81, wspace=0.42)
    _rank_panel(
        axes[0], concentration, "Rainfall concentration", "Percentage points of event rainfall per decade"
    )
    _rank_panel(axes[1], wetness, "Seven-day antecedent wetness", "SSI units per decade")
    _header(
        fig,
        "Magnitude and uncertainty of strong local mechanism signals",
        "Dots are fixed-effect trends; lines are 95% catchment-clustered confidence intervals",
    )
    _footer(fig, "Only signals passing the full strong-evidence definition are shown. Opposing signs are retained rather than averaged into one global direction.")
    _save(fig, config["paths"]["figures"] / "figure_03_strong_signal_rankings", int(config["plotting"]["dpi"]))


def figure_mechanism_trajectories(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    trajectory = pd.read_csv(config["paths"]["tables"] / "hydrobasin_trajectories.csv")
    strong = evidence[evidence["strong_evidence"]]
    selections = []
    concentration = strong[strong["metric"].eq("intensity_fraction")]
    wetness = strong[strong["metric"].eq("ssi_7d")]
    for frame in [concentration, wetness]:
        if not frame.empty:
            selections.extend([frame.loc[frame["slope_per_decade"].idxmin()], frame.loc[frame["slope_per_decade"].idxmax()]])
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.2))
    fig.subplots_adjust(left=0.085, right=0.96, bottom=0.11, top=0.81, wspace=0.18, hspace=0.33)
    for ax, selected in zip(axes.flat, selections):
        series = trajectory[
            trajectory["HYBAS_ID"].eq(selected.HYBAS_ID)
            & trajectory["metric"].eq(selected.metric)
        ].sort_values("year")
        scale = 100.0 if selected.metric == "intensity_fraction" else 1.0
        ax.scatter(series["year"], series["adjusted_mean"] * scale, s=16, color="#90A1AE", alpha=0.72, label="Adjusted annual mean")
        ax.plot(series["year"], series["fitted_mean"] * scale, color=ORANGE if selected.slope_per_decade > 0 else BLUE, linewidth=2.4, label="Continuous-time trend")
        ax.set_title(f"{selected.basin_code} · {selected.dominant_countries}", loc="left")
        ax.text(0.99, 0.94, f"{selected.slope_per_decade:+.2f} per decade", transform=ax.transAxes, ha="right", va="top", fontsize=8, weight="bold")
        ax.set_ylabel("Rainfall concentration (%)" if selected.metric == "intensity_fraction" else "Seven-day SSI")
        ax.set_xlim(1981, 2020)
        ax.grid(color=GRID, linewidth=0.55)
        ax.spines[["top", "right"]].set_visible(False)
    axes.flat[0].legend(frameon=False, fontsize=8, loc="best")
    _header(
        fig,
        "Continuous trajectories in representative hydrological regions",
        "Annual points are adjusted for stable differences between contributing catchments; no arbitrary period split is used",
    )
    _footer(fig, "Selected panels show the strongest negative and positive signals for rainfall concentration and seven-day antecedent wetness.")
    _save(fig, config["paths"]["figures"] / "figure_04_mechanism_trajectories", int(config["plotting"]["dpi"]))


def figure_physical_decomposition(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    strong = evidence[
        evidence["strong_evidence"] & evidence["metric"].eq("intensity_fraction")
    ].copy()
    strong = strong.reindex(strong["slope_per_decade"].abs().sort_values(ascending=False).index).head(12)
    drivers = evidence[
        evidence["HYBAS_ID"].isin(strong["HYBAS_ID"])
        & evidence["metric"].isin(["log_p_max", "log_p_volume", "log_precip_duration"])
    ].pivot(index="HYBAS_ID", columns="metric", values="slope_per_decade")
    plot = strong.set_index("HYBAS_ID").join(drivers).sort_values("slope_per_decade")
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(12.5, 7.1))
    fig.subplots_adjust(left=0.23, right=0.93, bottom=0.13, top=0.80)
    ax.hlines(y, plot["log_p_max"], plot["log_p_volume"], color="#A8B4BE", linewidth=1.2)
    ax.scatter(plot["log_p_max"], y, color=ORANGE, s=42, label="Maximum daily rainfall")
    ax.scatter(plot["log_p_volume"], y, color=BLUE, s=42, label="Total event rainfall")
    ax.scatter(plot["log_precip_duration"], y, color="#6B7D3E", marker="D", s=28, label="Precipitation duration")
    ax.axvline(0, color=INK, linewidth=0.8)
    labels = plot["basin_code"] + " · " + plot["dominant_countries"]
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlabel("Approximate within-catchment change (% per decade)")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.02))
    data_left, data_right = ax.get_xlim()
    annotation_x = data_right + max(2.2, (data_right - data_left) * 0.08)
    ax.set_xlim(data_left, data_right + max(9.0, (data_right - data_left) * 0.30))
    for index, (_, row) in enumerate(plot.iterrows()):
        ax.text(
            annotation_x, index,
            f"concentration {row.slope_per_decade:+.2f} pp / decade",
            ha="left", va="center", fontsize=7.4, color=MUTED,
        )
    _header(
        fig,
        "Rainfall components behind concentration shifts",
        "Strong rainfall-organization regions ranked by the continuous concentration trend",
    )
    _footer(fig, "A concentration decline is physically consistent when total event rainfall grows faster than maximum daily rainfall, or when maximum daily rainfall declines more strongly; duration provides complementary context.")
    _save(fig, config["paths"]["figures"] / "figure_05_physical_decomposition", int(config["plotting"]["dpi"]))


def figure_robustness_matrix(config: dict[str, Any]) -> None:
    evidence = pd.read_csv(config["paths"]["tables"] / "hydrobasin_evidence.csv")
    strong = evidence[evidence["strong_evidence"]].copy()
    intensity = strong[strong["metric"].eq("intensity_fraction")].reindex(
        strong[strong["metric"].eq("intensity_fraction")]["slope_per_decade"].abs().sort_values(ascending=False).index
    ).head(8)
    wet = strong[strong["metric"].eq("ssi_7d")].reindex(
        strong[strong["metric"].eq("ssi_7d")]["slope_per_decade"].abs().sort_values(ascending=False).index
    ).head(8)
    selected = pd.concat([intensity, wet], ignore_index=True)
    columns = [
        ("slope_per_decade", "Q95"),
        ("pot_q90_slope", "Q90"),
        ("annual_maximum_slope", "Annual max"),
        ("pot_q95_gap10_slope", "Q95 · 10d"),
        ("pot_q975_slope", "Q97.5"),
    ]
    matrix = np.column_stack([np.sign(selected[column]).to_numpy(float) for column, _ in columns])
    fig, ax = plt.subplots(figsize=(10.8, 7.4))
    fig.subplots_adjust(left=0.27, right=0.91, bottom=0.13, top=0.80)
    ax.imshow(matrix, cmap=CMAP, vmin=-1, vmax=1, aspect="auto")
    labels = selected["basin_code"] + " · " + selected["metric"].replace(
        {"intensity_fraction": "rainfall", "ssi_7d": "wetness"}
    )
    ax.set_yticks(np.arange(len(selected)), labels, fontsize=8)
    ax.set_xticks(np.arange(len(columns)), [label for _, label in columns], fontsize=8)
    ax.tick_params(length=0)
    for y, row in selected.iterrows():
        for x in range(len(columns)):
            ax.text(x, y, "↑" if matrix[y, x] > 0 else "↓", ha="center", va="center", color="white" if abs(matrix[y, x]) else INK, fontsize=10, weight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)
    _header(
        fig,
        "Strong directions persist across extreme-event definitions",
        "Arrows show the sign of each continuous-time estimate; rows are the largest strong rainfall and seven-day wetness signals",
    )
    _footer(fig, "Strong evidence additionally requires complete-family FDR, at least 20 contributing catchments, leave-one-catchment-out sign stability, and all-window agreement for SSI.")
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
