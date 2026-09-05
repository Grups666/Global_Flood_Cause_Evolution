from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
import pandas as pd

from .io import assign_continent
from .statistics import (
    binomial_probability_trend,
    fit_continuous_trends,
    poisson_rate_trend,
    theil_sen_per_decade,
)


SAMPLE_FILES = {
    "pot_q95": "primary_extreme_events.parquet",
    "annual_maximum": "sensitivity_annual_maximum_events.parquet",
    "pot_q90": "sensitivity_pot_q90_events.parquet",
    "pot_q975": "sensitivity_pot_q975_events.parquet",
}
MECHANISMS = [
    "Dry-Intensity",
    "Dry-Volume",
    "Moderate-Intensity",
    "Moderate-Volume",
    "Wet-Intensity",
    "Wet-Volume",
]
MARGINAL_GROUPS = ["Dry-All", "Moderate-All", "Wet-All", "All-Intensity", "All-Volume"]
MAGNITUDE_VARIABLES = {
    "flood_peak": ("q_peak_mm_day", "mm/day per decade"),
    "direct_runoff_volume": ("q_direct_volume_mm", "mm per decade"),
    "rainfall_concentration": ("intensity_fraction", "percentage points per decade"),
    "antecedent_wetness": ("source_ssi", "SSI units per decade"),
}


def _group_mask(sample: pd.DataFrame, group: str) -> pd.Series:
    """Select events on two independent axes; All leaves that axis unrestricted."""
    wetness, forcing = group.split("-")
    if wetness not in {"All", "Dry", "Moderate", "Wet"} or forcing not in {"All", "Intensity", "Volume"}:
        raise ValueError(f"Unknown event group: {group}")
    if wetness != "All" and forcing != "All":
        return sample["mechanism"].eq(group)
    mask = pd.Series(True, index=sample.index)
    if wetness != "All":
        mask &= sample["antecedent_state"].eq(wetness)
    if forcing != "All":
        mask &= sample["rainfall_organization"].eq(forcing)
    return mask


def _study_events(features: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    required = [
        "q_peak_mm_day",
        "q_direct_volume_mm",
        "peak_year",
        "intensity_fraction",
        "event_type_source",
    ]
    data = features.dropna(subset=required).copy()
    study = config["study"]
    data = data[data["peak_year"].between(study["start_year"], study["end_year"])]
    states = data["event_type_source"].astype(str).str.split("-").str[-1]
    data["antecedent_state"] = states.replace({"Mod": "Moderate"})
    data = data[data["antecedent_state"].isin(config["classification"]["antecedent_states"])]
    data["continent"] = assign_continent(data["country"])
    return data


def _assign_mechanism(
    frame: pd.DataFrame, threshold: float, cv_threshold: float = 1.0
) -> pd.DataFrame:
    data = frame.copy()
    data["rainfall_organization"] = np.where(
        data["intensity_fraction"].gt(threshold)
        & data["precipitation_cv"].gt(cv_threshold),
        "Intensity",
        "Volume",
    )
    data["mechanism"] = data["antecedent_state"] + "-" + data["rainfall_organization"]
    return data


def _record_eligibility(events: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, set[int]]:
    annual = events.groupby(["GCIN", "peak_year"], as_index=False).agg(events=("event_key", "size"))
    coverage = annual.groupby("GCIN").agg(
        n_event_years=("peak_year", "nunique"),
        first_year=("peak_year", "min"),
        last_year=("peak_year", "max"),
    )
    coverage["record_span_years"] = coverage["last_year"] - coverage["first_year"] + 1
    coverage["coverage_fraction"] = coverage["n_event_years"] / coverage["record_span_years"]
    study = config["study"]
    coverage["eligible"] = (
        coverage["n_event_years"].ge(study["minimum_annual_observations"])
        & coverage["record_span_years"].ge(study["minimum_record_span_years"])
        & coverage["coverage_fraction"].ge(study["minimum_record_coverage"])
    )
    ids = set(coverage.index[coverage["eligible"]].astype(int))
    return coverage.reset_index(), ids


def _screen_selected(sample: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    settings = config["event_samples"]
    summary = sample.groupby("GCIN").agg(
        events=("event_key", "size"), first=("peak_year", "min"), last=("peak_year", "max")
    )
    keep = summary.index[
        summary["events"].ge(settings["minimum_selected_events"])
        & (summary["last"] - summary["first"] + 1).ge(settings["minimum_selected_span_years"])
    ]
    return sample[sample["GCIN"].isin(set(keep))].copy()


def _select_pot(
    events: pd.DataFrame,
    eligible_ids: set[int],
    quantile: float,
    config: dict[str, Any],
) -> pd.DataFrame:
    data = events[events["GCIN"].isin(eligible_ids)].copy()
    ranking_variable = config["event_samples"]["ranking_variable"]
    thresholds = data.groupby("GCIN")[ranking_variable].transform(
        lambda values: values.quantile(quantile)
    )
    data["selection_threshold_mm"] = thresholds
    return _screen_selected(data[data[ranking_variable].ge(thresholds)], config)


def _select_annual_maximum(
    events: pd.DataFrame, eligible_ids: set[int], config: dict[str, Any]
) -> pd.DataFrame:
    data = events[events["GCIN"].isin(eligible_ids)].copy()
    ranking_variable = config["event_samples"]["ranking_variable"]
    index = data.groupby(["GCIN", "peak_year"])[ranking_variable].idxmax()
    selected = data.loc[index].copy()
    selected["selection_threshold_mm"] = np.nan
    return selected


def _select_samples(
    events: pd.DataFrame, eligible_ids: set[int], config: dict[str, Any], threshold: float
) -> dict[str, pd.DataFrame]:
    samples = {
        "pot_q95": _select_pot(events, eligible_ids, 0.95, config),
        "annual_maximum": _select_annual_maximum(events, eligible_ids, config),
        "pot_q90": _select_pot(events, eligible_ids, 0.90, config),
        "pot_q975": _select_pot(events, eligible_ids, 0.975, config),
    }
    cv_threshold = float(config["classification"]["rainfall_temporal_cv_threshold"])
    return {
        name: _assign_mechanism(sample, threshold, cv_threshold)
        for name, sample in samples.items()
    }


def _magnitude_trends(
    sample: pd.DataFrame,
    minimum_years: int,
    minimum_span: int,
    mechanism: str | None = None,
    outcomes: list[str] | None = None,
) -> pd.DataFrame:
    data = sample if mechanism is None else sample[_group_mask(sample, mechanism)]
    selected_outcomes = outcomes or list(MAGNITUDE_VARIABLES)
    trends = fit_continuous_trends(
        data,
        [MAGNITUDE_VARIABLES[outcome][0] for outcome in selected_outcomes],
        minimum_years=minimum_years,
        minimum_span_years=minimum_span,
    )
    if trends.empty:
        return trends
    inverse = {value[0]: key for key, value in MAGNITUDE_VARIABLES.items()}
    units = {key: value[1] for key, value in MAGNITUDE_VARIABLES.items()}
    trends["outcome"] = trends["variable"].map(inverse)
    trends["display_slope_per_decade"] = trends["raw_slope_per_decade"]
    trends["display_ci_low_per_decade"] = trends["raw_ci_low_per_decade"]
    trends["display_ci_high_per_decade"] = trends["raw_ci_high_per_decade"]
    concentration = trends["outcome"].eq("rainfall_concentration")
    for column in [
        "display_slope_per_decade",
        "display_ci_low_per_decade",
        "display_ci_high_per_decade",
        "fitted_first",
        "fitted_last",
        "mean_level",
    ]:
        trends.loc[concentration, column] = 100.0 * trends.loc[concentration, column]
    physical_bounds = {
        "flood_peak": (0.0, np.inf),
        "direct_runoff_volume": (0.0, np.inf),
        "rainfall_concentration": (0.0, 100.0),
        "antecedent_wetness": (0.0, 1.0),
    }
    for outcome, (lower, upper) in physical_bounds.items():
        mask = trends["outcome"].eq(outcome)
        for column in ["fitted_first", "fitted_last"]:
            trends.loc[mask, column] = trends.loc[mask, column].clip(lower=lower, upper=upper)
    trends["display_unit"] = trends["outcome"].map(units)
    trends["relative_slope_percent_per_decade"] = (
        100.0
        * trends["display_slope_per_decade"]
        / trends["mean_level"].replace(0, np.nan)
    )
    trends["mechanism"] = mechanism if mechanism is not None else "All selected floods"
    return trends


def _composition_trends(
    sample: pd.DataFrame, config: dict[str, Any], groups: list[str] | None = None,
) -> pd.DataFrame:
    settings = config["trends"]
    rows: list[dict[str, Any]] = []
    for gcin, catchment in sample.groupby("GCIN", sort=False):
        span = int(catchment["peak_year"].max() - catchment["peak_year"].min() + 1)
        if span < config["event_samples"]["minimum_selected_span_years"]:
            continue
        totals = catchment.groupby("peak_year").size().rename("total")
        for mechanism in MECHANISMS if groups is None else groups:
            positives = _group_mask(catchment, mechanism)
            n_yes = int(positives.sum())
            n_no = int((~positives).sum())
            if n_yes < settings["minimum_mechanism_events"] or n_no < settings["minimum_mechanism_other_events"]:
                continue
            yes = catchment.loc[positives].groupby("peak_year").size().rename("success")
            annual = pd.concat([totals, yes], axis=1).fillna(0).reset_index()
            estimate = binomial_probability_trend(
                annual["peak_year"].to_numpy(float),
                annual["success"].to_numpy(float),
                annual["total"].to_numpy(float),
            )
            if estimate is None:
                continue
            rows.append({
                "GCIN": int(gcin),
                "mechanism": mechanism,
                "outcome": "mechanism_share",
                "variable": "mechanism_share",
                "n_observations": int(len(catchment)),
                "n_mechanism_events": n_yes,
                "n_other_events": n_no,
                "n_years": int(annual["peak_year"].nunique()),
                "first_year": int(annual["peak_year"].min()),
                "last_year": int(annual["peak_year"].max()),
                "year_span": span,
                "mean_level": 100.0 * n_yes / len(catchment),
                "display_unit": "percentage points per decade",
                "relative_slope_percent_per_decade": np.nan,
                **estimate,
            })
    return pd.DataFrame(rows)


def _mechanism_trends(
    sample: pd.DataFrame, record_years: pd.DataFrame, config: dict[str, Any],
    groups: list[str] | None = None,
) -> pd.DataFrame:
    settings = config["trends"]
    frames = [_composition_trends(sample, config, groups=groups)]
    for mechanism in MECHANISMS if groups is None else groups:
        frame = _magnitude_trends(
            sample,
            minimum_years=settings["minimum_mechanism_years"],
            minimum_span=settings["minimum_mechanism_span_years"],
            mechanism=mechanism,
            outcomes=[
                "flood_peak",
                "direct_runoff_volume",
                "rainfall_concentration",
                "antecedent_wetness",
            ],
        )
        if not frame.empty:
            frames.append(frame)
    frequency = _event_rate_trends(sample, record_years, config, by_mechanism=True, groups=groups)
    if not frequency.empty:
        frames.append(frequency)
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _event_rate_trends(
    sample: pd.DataFrame,
    record_years: pd.DataFrame,
    config: dict[str, Any],
    by_mechanism: bool = False,
    groups: list[str] | None = None,
) -> pd.DataFrame:
    settings = config["trends"]
    rows: list[dict[str, Any]] = []
    mechanisms = (MECHANISMS if groups is None else groups) if by_mechanism else ["All selected floods"]
    for mechanism in mechanisms:
        source = sample if not by_mechanism else sample[_group_mask(sample, mechanism)]
        counts = source.groupby(["GCIN", "peak_year"]).size().rename("count")
        for gcin, years in record_years.groupby("GCIN", sort=False):
            annual = years[["peak_year"]].drop_duplicates().sort_values("peak_year").copy()
            annual["count"] = [counts.get((gcin, year), 0) for year in annual["peak_year"]]
            n_events = int(annual["count"].sum())
            if by_mechanism:
                if n_events < settings["minimum_mechanism_events"]:
                    continue
            elif len(annual) < settings["minimum_overall_years"]:
                continue
            estimate = poisson_rate_trend(
                annual["peak_year"].to_numpy(float), annual["count"].to_numpy(float)
            )
            if estimate is None:
                continue
            rows.append({
                "GCIN": int(gcin),
                "mechanism": mechanism,
                "outcome": "mechanism_frequency" if by_mechanism else "exceedance_frequency",
                "variable": "annual_mechanism_count" if by_mechanism else "annual_exceedance_count",
                "n_observations": n_events,
                "n_years": int(len(annual)),
                "first_year": int(annual["peak_year"].min()),
                "last_year": int(annual["peak_year"].max()),
                "year_span": int(annual["peak_year"].max() - annual["peak_year"].min() + 1),
                "mean_level": float(annual["count"].mean()),
                "display_unit": "events per year per decade",
                "relative_slope_percent_per_decade": 100.0 * (estimate["rate_ratio_per_decade"] - 1.0),
                **estimate,
            })
    return pd.DataFrame(rows)


def _overall_trends(
    sample: pd.DataFrame, record_years: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    settings = config["trends"]
    magnitude = _magnitude_trends(
        sample,
        settings["minimum_overall_years"],
        settings["minimum_overall_span_years"],
        outcomes=["flood_peak", "direct_runoff_volume"],
    )
    rate = _event_rate_trends(sample, record_years, config, by_mechanism=False)
    return pd.concat([magnitude, rate], ignore_index=True)


def _sign(values: pd.Series) -> pd.Series:
    return np.sign(pd.to_numeric(values, errors="coerce"))


def _attach_sensitivity(
    primary: pd.DataFrame,
    alternatives: dict[str, pd.DataFrame],
    classification_alternatives: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    keys = ["GCIN", "mechanism", "outcome"]
    result = primary.copy()
    for name, frame in alternatives.items():
        alternate = frame[keys + ["display_slope_per_decade"]].rename(columns={
            "display_slope_per_decade": f"{name}_slope",
        })
        result = result.merge(alternate, on=keys, how="left")
    primary_sign = _sign(result["display_slope_per_decade"])
    sample_checks = []
    for name in alternatives:
        comparison = (
            result[f"{name}_slope"].notna()
            & _sign(result[f"{name}_slope"]).eq(primary_sign)
        )
        # Annual maxima contain exactly one event in every observed year, so
        # they cannot diagnose the frequency of exceedances of a fixed POT
        # threshold. Q90 and Q97.5 remain applicable to that outcome.
        if name == "annual_maximum":
            comparison = comparison | result["outcome"].eq("exceedance_frequency")
        sample_checks.append(comparison)
    result["sample_direction_stable"] = np.logical_and.reduce(sample_checks) if sample_checks else True

    classification_alternatives = classification_alternatives or {}
    class_checks = []
    for name, frame in classification_alternatives.items():
        alternate = frame[keys + ["display_slope_per_decade"]].rename(
            columns={"display_slope_per_decade": f"{name}_slope"}
        )
        result = result.merge(alternate, on=keys, how="left")
        class_checks.append(result[f"{name}_slope"].notna() & _sign(result[f"{name}_slope"]).eq(primary_sign))
    result["classification_direction_stable"] = (
        np.logical_and.reduce(class_checks) if class_checks else True
    )
    return result


def _theil_sen_direction(year: pd.Series, values: pd.Series) -> float:
    """Return the exact Theil--Sen point slope without computing its CI/test."""
    x = pd.to_numeric(year, errors="coerce").to_numpy(float)
    y = pd.to_numeric(values, errors="coerce").to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 2 or np.all(x == x[0]):
        return np.nan
    upper = np.triu_indices(len(x), k=1)
    dx = x[upper[1]] - x[upper[0]]
    dy = y[upper[1]] - y[upper[0]]
    slopes = dy[dx != 0] / dx[dx != 0]
    return float(10.0 * np.median(slopes)) if len(slopes) else np.nan


def _direction_only_trends(
    sample: pd.DataFrame,
    record_years: pd.DataFrame,
    config: dict[str, Any],
    include_overall: bool = True,
    groups: list[str] | None = None,
) -> pd.DataFrame:
    """Fast slopes used only to check direction in sensitivity samples."""
    settings = config["trends"]
    rows: list[dict[str, Any]] = []
    if include_overall:
        for outcome in ["flood_peak", "direct_runoff_volume"]:
            variable = MAGNITUDE_VARIABLES[outcome][0]
            annual = sample.groupby(["GCIN", "peak_year"], as_index=False)[variable].mean()
            for gcin, frame in annual.groupby("GCIN", sort=False):
                span = int(frame.peak_year.max() - frame.peak_year.min() + 1)
                if len(frame) >= settings["minimum_overall_years"] and span >= settings["minimum_overall_span_years"]:
                    rows.append({"GCIN": int(gcin), "mechanism": "All selected floods", "outcome": outcome,
                                 "display_slope_per_decade": _theil_sen_direction(frame.peak_year, frame[variable])})
        sample_counts = sample.groupby(["GCIN", "peak_year"]).size()
        for gcin, years in record_years.groupby("GCIN", sort=False):
            annual = years[["peak_year"]].drop_duplicates().sort_values("peak_year")
            if len(annual) < settings["minimum_overall_years"]:
                continue
            values = annual.peak_year.map(lambda year: sample_counts.get((gcin, year), 0))
            estimate = poisson_rate_trend(annual.peak_year.to_numpy(float), values.to_numpy(float))
            if estimate is not None:
                rows.append({"GCIN": int(gcin), "mechanism": "All selected floods", "outcome": "exceedance_frequency",
                             "display_slope_per_decade": estimate["display_slope_per_decade"]})

    totals = sample.groupby(["GCIN", "peak_year"]).size().rename("total")
    for mechanism in MECHANISMS if groups is None else groups:
        selected = sample[_group_mask(sample, mechanism)]
        event_counts = selected.groupby("GCIN").size()
        other_counts = sample.groupby("GCIN").size().sub(event_counts, fill_value=0)
        for outcome in ["flood_peak", "direct_runoff_volume", "rainfall_concentration", "antecedent_wetness"]:
            variable = MAGNITUDE_VARIABLES[outcome][0]
            annual = selected.groupby(["GCIN", "peak_year"], as_index=False)[variable].mean()
            for gcin, frame in annual.groupby("GCIN", sort=False):
                span = int(frame.peak_year.max() - frame.peak_year.min() + 1)
                if len(frame) >= settings["minimum_mechanism_years"] and span >= settings["minimum_mechanism_span_years"]:
                    slope = _theil_sen_direction(frame.peak_year, frame[variable])
                    if outcome == "rainfall_concentration":
                        slope *= 100.0
                    rows.append({"GCIN": int(gcin), "mechanism": mechanism, "outcome": outcome,
                                 "display_slope_per_decade": slope})
        yes = selected.groupby(["GCIN", "peak_year"]).size().rename("success")
        shares = pd.concat([totals, yes], axis=1).fillna(0).reset_index()
        for gcin, frame in shares.groupby("GCIN", sort=False):
            if event_counts.get(gcin, 0) >= settings["minimum_mechanism_events"] and other_counts.get(gcin, 0) >= settings["minimum_mechanism_other_events"]:
                estimate = binomial_probability_trend(
                    frame["peak_year"].to_numpy(float),
                    frame["success"].to_numpy(float),
                    frame["total"].to_numpy(float),
                )
                if estimate is not None:
                    rows.append({
                        "GCIN": int(gcin),
                        "mechanism": mechanism,
                        "outcome": "mechanism_share",
                        "display_slope_per_decade": estimate["display_slope_per_decade"],
                    })
        process_counts = selected.groupby(["GCIN", "peak_year"]).size()
        for gcin, years in record_years.groupby("GCIN", sort=False):
            if event_counts.get(gcin, 0) < settings["minimum_mechanism_events"]:
                continue
            annual = years[["peak_year"]].drop_duplicates().sort_values("peak_year")
            values = annual.peak_year.map(lambda year: process_counts.get((gcin, year), 0))
            estimate = poisson_rate_trend(annual.peak_year.to_numpy(float), values.to_numpy(float))
            if estimate is not None:
                rows.append({"GCIN": int(gcin), "mechanism": mechanism, "outcome": "mechanism_frequency",
                             "display_slope_per_decade": estimate["display_slope_per_decade"]})
    return pd.DataFrame(rows)


def _refit_without_year(
    catchment: pd.DataFrame,
    row: pd.Series,
    catchment_record_years: pd.DataFrame,
    config: dict[str, Any],
) -> float | None:
    catchment = catchment[catchment["peak_year"].ne(int(row["removed_year"]))]
    mechanism = str(row["mechanism"])
    outcome = str(row["outcome"])
    if outcome == "mechanism_share":
        yes_mask = _group_mask(catchment, mechanism)
        minimum = max(4, int(config["trends"]["minimum_mechanism_events"]) - 1)
        if int(yes_mask.sum()) < minimum or int((~yes_mask).sum()) < minimum:
            return None
        totals = catchment.groupby("peak_year").size().rename("total")
        yes = catchment.loc[yes_mask].groupby("peak_year").size().rename("success")
        annual = pd.concat([totals, yes], axis=1).fillna(0).reset_index()
        estimate = binomial_probability_trend(
            annual["peak_year"].to_numpy(float),
            annual["success"].to_numpy(float),
            annual["total"].to_numpy(float),
        )
        return None if estimate is None else float(estimate["display_slope_per_decade"])
    elif outcome in {"exceedance_frequency", "mechanism_frequency"}:
        years = catchment_record_years[
            catchment_record_years["peak_year"].ne(int(row["removed_year"]))
        ]
        annual = years[["peak_year"]].drop_duplicates().sort_values("peak_year").copy()
        if outcome == "mechanism_frequency":
            catchment = catchment[_group_mask(catchment, mechanism)]
        counts = catchment.groupby("peak_year").size()
        annual["count"] = annual["peak_year"].map(counts).fillna(0)
        estimate = poisson_rate_trend(
            annual["peak_year"].to_numpy(float), annual["count"].to_numpy(float)
        )
        return None if estimate is None else float(estimate["display_slope_per_decade"])
    else:
        settings = config["trends"]
        if mechanism == "All selected floods":
            minimum_years = settings["minimum_overall_years"] - 1
            minimum_span = settings["minimum_overall_span_years"]
            mechanism_arg = None
        else:
            minimum_years = max(4, settings["minimum_mechanism_years"] - 1)
            minimum_span = settings["minimum_mechanism_span_years"]
            mechanism_arg = mechanism
        if mechanism_arg is not None:
            catchment = catchment[_group_mask(catchment, mechanism_arg)]
        variable = MAGNITUDE_VARIABLES[outcome][0]
        annual = (
            catchment[["peak_year", variable]].dropna()
            .groupby("peak_year", as_index=False).agg(value=(variable, "mean"))
        )
        if len(annual) < minimum_years:
            return None
        span = int(annual["peak_year"].max() - annual["peak_year"].min() + 1)
        if span < minimum_span:
            return None
        estimate = theil_sen_per_decade(
            annual["peak_year"].to_numpy(float), annual["value"].to_numpy(float)
        )
        return float(estimate["raw_slope_per_decade"])


def _leave_one_year_stability(
    sample: pd.DataFrame,
    table: pd.DataFrame,
    record_years: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    alpha = float(config["trends"]["alpha"])
    candidates = table[table["p_value"].lt(alpha)].copy()
    sample_groups = {int(gcin): frame for gcin, frame in sample.groupby("GCIN", sort=False)}
    record_groups = {
        int(gcin): frame for gcin, frame in record_years.groupby("GCIN", sort=False)
    }
    rows: list[dict[str, Any]] = []
    for candidate in candidates.itertuples(index=False):
        catchment = sample_groups[int(candidate.GCIN)]
        catchment_record_years = record_groups[int(candidate.GCIN)]
        if candidate.outcome in {"exceedance_frequency", "mechanism_frequency"}:
            observed_years = sorted(
                record_years.loc[record_years["GCIN"].eq(candidate.GCIN), "peak_year"]
                .dropna().astype(int).unique()
            )
        elif candidate.outcome in MAGNITUDE_VARIABLES and candidate.mechanism != "All selected floods":
            observed_years = sorted(
                catchment.loc[_group_mask(catchment, candidate.mechanism), "peak_year"]
                .dropna().astype(int).unique()
            )
        else:
            observed_years = sorted(catchment["peak_year"].dropna().astype(int).unique())
        slopes: list[float] = []
        for year in observed_years:
            row = pd.Series({
                "GCIN": candidate.GCIN,
                "mechanism": candidate.mechanism,
                "outcome": candidate.outcome,
                "removed_year": year,
            })
            slope = _refit_without_year(
                catchment, row, catchment_record_years, config
            )
            if slope is not None and np.isfinite(slope):
                slopes.append(slope)
        sign = np.sign(float(candidate.display_slope_per_decade))
        rows.append({
            "GCIN": int(candidate.GCIN),
            "mechanism": candidate.mechanism,
            "outcome": candidate.outcome,
            "leave_one_year_replicates": len(slopes),
            "leave_one_year_stable": bool(slopes and np.all(np.sign(slopes) == sign)),
            "leave_one_year_min": min(slopes) if slopes else np.nan,
            "leave_one_year_max": max(slopes) if slopes else np.nan,
        })
    return pd.DataFrame(rows, columns=[
        "GCIN", "mechanism", "outcome", "leave_one_year_replicates",
        "leave_one_year_stable", "leave_one_year_min", "leave_one_year_max",
    ])


def _finalize_evidence(
    sample: pd.DataFrame,
    table: pd.DataFrame,
    record_years: pd.DataFrame,
    config: dict[str, Any],
    require_classification_check: bool,
) -> pd.DataFrame:
    stability = _leave_one_year_stability(sample, table, record_years, config)
    keys = ["GCIN", "mechanism", "outcome"]
    result = table.merge(stability, on=keys, how="left")
    result["leave_one_year_stable"] = result["leave_one_year_stable"].fillna(False)
    result["p_pass"] = result["p_value"].lt(config["trends"]["alpha"])
    if not require_classification_check:
        result["classification_direction_stable"] = True
    result["supported_shift"] = (
        result["p_pass"]
        & result["sample_direction_stable"].fillna(False)
        & result["classification_direction_stable"].fillna(False)
        & result["leave_one_year_stable"]
    )
    result["direction"] = np.where(result["display_slope_per_decade"].ge(0), "increase", "decrease")
    return result


def _annual_mechanism_summary(sample: pd.DataFrame) -> pd.DataFrame:
    catchment_year = (
        sample.groupby(["GCIN", "peak_year", "mechanism"]).size().rename("events").reset_index()
    )
    totals = catchment_year.groupby(["GCIN", "peak_year"])["events"].transform("sum")
    catchment_year["share"] = catchment_year["events"] / totals
    rows = []
    for year in sorted(sample["peak_year"].unique()):
        year_frame = catchment_year[catchment_year["peak_year"].eq(year)]
        catchments = int(year_frame["GCIN"].nunique())
        for mechanism in MECHANISMS:
            part = year_frame[year_frame["mechanism"].eq(mechanism)]
            rows.append({
                "year": int(year),
                "mechanism": mechanism,
                "events": int(part["events"].sum()),
                "event_share": float(part["events"].sum() / max(1, year_frame["events"].sum())),
                "catchment_equal_share": float(part["share"].sum() / max(1, catchments)),
                "catchments": catchments,
            })
    return pd.DataFrame(rows)


def _independence(sample: pd.DataFrame) -> dict[str, Any]:
    ordered = sample.sort_values(["GCIN", "q_peak_date"])
    previous = ordered.groupby("GCIN")["q_peak_date"].shift()
    gaps = (ordered["q_peak_date"] - previous).dt.days.dropna()
    previous_end = ordered.groupby("GCIN")["end_stormflow_date"].shift()
    overlaps = (ordered["start_stormflow_date"] <= previous_end).fillna(False)
    return {
        "adjacent_pairs": int(len(gaps)),
        "minimum_peak_gap_days": int(gaps.min()) if len(gaps) else None,
        "pairs_under_10_days": int((gaps < 10).sum()),
        "stormflow_window_overlaps": int(overlaps.sum()),
    }


def run_analysis(config: dict[str, Any], force: bool = False) -> dict[str, Any]:
    summary_file = config["paths"]["logs"] / "analysis_summary.json"
    if summary_file.exists() and not force:
        return json.loads(summary_file.read_text(encoding="utf-8"))
    started = time.time()
    features = pd.read_parquet(config["paths"]["derived_data"] / "event_features.parquet")
    events = _study_events(features, config)
    coverage, eligible_ids = _record_eligibility(events, config)
    record_years = events[events["GCIN"].isin(eligible_ids)][["GCIN", "peak_year"]].drop_duplicates()
    threshold = float(config["classification"]["rainfall_intensity_share_threshold"])
    samples = _select_samples(events, eligible_ids, config, threshold)
    for name, sample in samples.items():
        sample.to_parquet(
            config["paths"]["derived_data"] / SAMPLE_FILES[name], index=False, compression="zstd"
        )

    overall_primary = _overall_trends(samples["pot_q95"], record_years, config)
    mechanism_primary = _mechanism_trends(samples["pot_q95"], record_years, config)
    direction_by_sample = {
        name: _direction_only_trends(sample, record_years, config)
        for name, sample in samples.items()
        if name != "pot_q95"
    }
    cutoff_tables: dict[str, pd.DataFrame] = {}
    for cutoff in config["classification"]["rainfall_intensity_share_sensitivity"]:
        alternate_sample = _assign_mechanism(
            samples["pot_q95"].drop(columns=["rainfall_organization", "mechanism"]),
            float(cutoff),
            float(config["classification"]["rainfall_temporal_cv_threshold"]),
        )
        cutoff_tables[f"cutoff_{str(cutoff).replace('.', '_')}"] = _direction_only_trends(
            alternate_sample, record_years, config, include_overall=False
        )

    overall = _attach_sensitivity(
        overall_primary,
        {name: direction_by_sample[name] for name in config["event_samples"]["sensitivity_samples"]},
    )
    overall = _finalize_evidence(
        samples["pot_q95"], overall, record_years, config, require_classification_check=False
    )
    mechanism = _attach_sensitivity(
        mechanism_primary,
        {name: direction_by_sample[name] for name in config["event_samples"]["sensitivity_samples"]},
        cutoff_tables,
    )
    mechanism = _finalize_evidence(
        samples["pot_q95"], mechanism, record_years, config, require_classification_check=True
    )

    metadata = events[
        ["GCIN", "country", "continent", "longitude", "latitude", "snow_fraction"]
    ].drop_duplicates("GCIN")
    overall = overall.merge(metadata, on="GCIN", how="left", validate="many_to_one")
    mechanism = mechanism.merge(metadata, on="GCIN", how="left", validate="many_to_one")

    tables = config["paths"]["tables"]
    coverage.to_csv(tables / "record_eligibility.csv", index=False)
    overall.to_csv(tables / "catchment_overall_trends.csv", index=False)
    mechanism.to_csv(tables / "catchment_mechanism_trends.csv", index=False)
    pd.concat(
        [mechanism_primary.assign(sample="pot_q95")]
        + [frame.assign(sample=name) for name, frame in direction_by_sample.items()], ignore_index=True
    ).to_csv(tables / "mechanism_sample_sensitivity.csv", index=False)
    pd.concat(
        [frame.assign(classification=name) for name, frame in cutoff_tables.items()], ignore_index=True
    ).to_csv(tables / "mechanism_threshold_sensitivity.csv", index=False)
    annual = _annual_mechanism_summary(samples["pot_q95"])
    annual.to_csv(tables / "global_mechanism_annual.csv", index=False)
    composition = (
        samples["pot_q95"].groupby("mechanism").size().rename("events").reset_index()
    )
    composition["share_percent"] = 100.0 * composition["events"] / composition["events"].sum()
    composition.to_csv(tables / "mechanism_composition.csv", index=False)
    diagnostics = []
    for name, sample in samples.items():
        diagnostics.append({
            "sample": name,
            "events": len(sample),
            "catchments": int(sample["GCIN"].nunique()),
            "first_year": int(sample["peak_year"].min()),
            "last_year": int(sample["peak_year"].max()),
            **_independence(sample),
        })
    pd.DataFrame(diagnostics).to_csv(tables / "extreme_sample_diagnostics.csv", index=False)

    summary = {
        "status": "complete",
        "primary_sample": "pot_q95",
        "ranking_variable": config["event_samples"]["ranking_variable"],
        "classification": {
            "rainfall_temporal_cv_threshold": config["classification"]["rainfall_temporal_cv_threshold"],
            "rainfall_intensity_share_threshold": threshold,
            "antecedent_states": config["classification"]["antecedent_states"],
            "mechanisms": MECHANISMS,
        },
        "eligible_record_catchments": len(eligible_ids),
        "sample_counts": {
            name: {"events": len(sample), "catchments": int(sample["GCIN"].nunique())}
            for name, sample in samples.items()
        },
        "mechanism_counts": composition.set_index("mechanism")["events"].astype(int).to_dict(),
        "overall_trends": len(overall),
        "supported_overall_trends": int(overall["supported_shift"].sum()),
        "mechanism_trends": len(mechanism),
        "supported_mechanism_trends": int(mechanism["supported_shift"].sum()),
        "supported_mechanism_share_trends": int(
            mechanism["supported_shift"].mul(mechanism["outcome"].eq("mechanism_share")).sum()
        ),
        "primary_independence": _independence(samples["pot_q95"]),
        "elapsed_seconds": time.time() - started,
    }
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
