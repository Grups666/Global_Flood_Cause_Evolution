from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "analysis.yaml").read_text(encoding="utf-8"))
DERIVED = ROOT / "data" / "derived"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
ASSETS = ROOT / "reports" / "assets"
PUBLIC_REPORTS = ROOT / "public" / "reports"
LOGS = ROOT / "outputs" / "logs"

SAMPLES = {
    "pot_q95": "primary_extreme_events.parquet",
    "annual_maximum": "sensitivity_annual_maximum_events.parquet",
    "pot_q90": "sensitivity_pot_q90_events.parquet",
    "pot_q975": "sensitivity_pot_q975_events.parquet",
}
MECHANISMS = {
    "Dry-Intensity", "Dry-Volume", "Moderate-Intensity",
    "Moderate-Volume", "Wet-Intensity", "Wet-Volume",
}
FIGURE_STEMS = [
    "figure_01_sample_and_process_coverage",
    "figure_02_overall_flood_changes",
    "figure_03_process_frequency_changes",
    "figure_04_process_share_changes",
    "figure_05_process_response_rankings",
    "figure_06_example_process_trajectories",
]


def record(checks: list[dict[str, object]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def study_events(features: pd.DataFrame) -> pd.DataFrame:
    required = [
        "q_peak_mm_day", "q_direct_volume_mm", "peak_year",
        "intensity_fraction", "event_type_source",
    ]
    data = features.dropna(subset=required).copy()
    data = data[data["peak_year"].between(CONFIG["study"]["start_year"], CONFIG["study"]["end_year"])]
    data["antecedent_state"] = (
        data["event_type_source"].astype(str).str.split("-").str[-1].replace({"Mod": "Moderate"})
    )
    return data[data["antecedent_state"].isin(CONFIG["classification"]["antecedent_states"])]


def expected_eligibility(events: pd.DataFrame) -> pd.DataFrame:
    annual = events[["GCIN", "peak_year"]].drop_duplicates()
    coverage = annual.groupby("GCIN").agg(
        n_event_years=("peak_year", "nunique"),
        first_year=("peak_year", "min"),
        last_year=("peak_year", "max"),
    )
    coverage["record_span_years"] = coverage["last_year"] - coverage["first_year"] + 1
    coverage["coverage_fraction"] = coverage["n_event_years"] / coverage["record_span_years"]
    study = CONFIG["study"]
    coverage["eligible"] = (
        coverage["n_event_years"].ge(study["minimum_annual_observations"])
        & coverage["record_span_years"].ge(study["minimum_record_span_years"])
        & coverage["coverage_fraction"].ge(study["minimum_record_coverage"])
    )
    return coverage.reset_index()


def expected_pot(events: pd.DataFrame, eligible: set[int], quantile: float) -> pd.DataFrame:
    ranking = CONFIG["event_samples"]["ranking_variable"]
    pool = events[events["GCIN"].isin(eligible)].copy()
    threshold = pool.groupby("GCIN")[ranking].transform(lambda values: values.quantile(quantile))
    selected = pool[pool[ranking].ge(threshold)].copy()
    summary = selected.groupby("GCIN").agg(
        events=("event_key", "size"), first=("peak_year", "min"), last=("peak_year", "max")
    )
    settings = CONFIG["event_samples"]
    keep = set(summary.index[
        summary["events"].ge(settings["minimum_selected_events"])
        & (summary["last"] - summary["first"] + 1).ge(settings["minimum_selected_span_years"])
    ].astype(int))
    return selected[selected["GCIN"].isin(keep)]


def expected_annual_maximum(events: pd.DataFrame, eligible: set[int]) -> pd.DataFrame:
    pool = events[events["GCIN"].isin(eligible)].copy()
    ranking = CONFIG["event_samples"]["ranking_variable"]
    indices = pool.groupby(["GCIN", "peak_year"])[ranking].idxmax()
    return pool.loc[indices]


def check_daily_spot_sample(features: pd.DataFrame, checks: list[dict[str, object]]) -> None:
    source = Path(CONFIG["paths"]["source_global_data"]) / "daily_data" / "observations"
    failures: list[str] = []
    for row in features.sample(20, random_state=20260904).itertuples(index=False):
        daily = pd.read_csv(source / f"{int(row.GCIN)}.csv", parse_dates=["date"])
        rain = daily[daily["date"].between(row.start_precip_date, row.end_precip_date)]["water_input_mm"]
        flow = daily[daily["date"].between(row.start_stormflow_date, row.end_stormflow_date)]["streamflow_mm"]
        if not np.isclose(rain.sum(), row.p_volume_daily_mm, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: rainfall volume")
        if not np.isclose(rain.max(), row.p_max_daily_mm, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: maximum daily rainfall")
        if not np.isclose(flow.max(), row.q_peak_mm_day, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: daily flood peak")
    record(checks, "daily_reconstruction_spot_check", not failures, f"20 events; failures={failures}")


def check_markdown_links(checks: list[dict[str, object]]) -> None:
    missing: list[str] = []
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "reports").glob("*.md"))]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for raw in pattern.findall(text):
            target = raw.strip().split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append(f"{path.relative_to(ROOT)} -> {raw}")
    record(checks, "markdown_local_links", not missing, "none missing" if not missing else "; ".join(missing))


def write_report(result: dict[str, object]) -> None:
    lines = [
        "# Validation report", "",
        f"**Status:** {str(result['status']).upper()}",
        f"**Checks:** {result['checks_passed']} / {result['checks_total']} passed",
        f"**Execution date:** {date.today().isoformat()}", "",
        "| Check | Status | Evidence |", "|---|---:|---|",
    ]
    for item in result["checks"]:
        detail = str(item["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{item['check']}` | {'PASS' if item['passed'] else 'FAIL'} | {detail} |")
    lines.extend([
        "", "The validator independently reconstructs record eligibility and the event-volume Q95 sample, "
        "checks the six process labels and evidence gates, verifies report assets and the self-contained HTML, "
        "and confirms that the interactive payload contains observed catchment points only.", "",
    ])
    (ROOT / "docs" / "quality" / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    checks: list[dict[str, object]] = []
    features = pd.read_parquet(DERIVED / "event_features.parquet")
    events = study_events(features)
    coverage = expected_eligibility(events)
    saved_coverage = pd.read_csv(TABLES / "record_eligibility.csv")
    eligible = set(coverage.loc[coverage["eligible"], "GCIN"].astype(int))

    record(checks, "event_key_unique", features["event_key"].is_unique, f"feature rows={len(features):,}")
    columns = ["GCIN", "n_event_years", "first_year", "last_year", "record_span_years", "eligible"]
    expected_coverage_sorted = coverage.sort_values("GCIN").reset_index(drop=True)
    saved_coverage_sorted = saved_coverage.sort_values("GCIN").reset_index(drop=True)
    coverage_match = expected_coverage_sorted[columns].equals(saved_coverage_sorted[columns])
    coverage_match &= np.allclose(
        expected_coverage_sorted["coverage_fraction"], saved_coverage_sorted["coverage_fraction"]
    )
    record(checks, "record_eligibility_exact", coverage_match, f"eligible catchments={len(eligible):,}")

    expected_samples = {
        "pot_q95": expected_pot(events, eligible, 0.95),
        "pot_q90": expected_pot(events, eligible, 0.90),
        "pot_q975": expected_pot(events, eligible, 0.975),
        "annual_maximum": expected_annual_maximum(events, eligible),
    }
    saved_samples = {name: pd.read_parquet(DERIVED / filename) for name, filename in SAMPLES.items()}
    for name in SAMPLES:
        exact = set(expected_samples[name]["event_key"]) == set(saved_samples[name]["event_key"])
        record(checks, f"{name}_sample_exact", exact,
               f"events={len(saved_samples[name]):,}; catchments={saved_samples[name].GCIN.nunique():,}")

    primary = saved_samples["pot_q95"]
    expected_org = np.where(
        primary["intensity_fraction"].gt(CONFIG["classification"]["rainfall_intensity_share_threshold"])
        & primary["precipitation_cv"].gt(CONFIG["classification"]["rainfall_temporal_cv_threshold"]),
        "Intensity", "Volume",
    )
    labels_ok = np.array_equal(primary["rainfall_organization"].to_numpy(), expected_org)
    labels_ok &= set(primary["mechanism"].dropna().unique()) == MECHANISMS
    labels_ok &= np.array_equal(
        primary["mechanism"].to_numpy(),
        (primary["antecedent_state"].astype(str) + "-" + pd.Series(expected_org, index=primary.index)).to_numpy(),
    )
    record(checks, "six_process_classification_exact", labels_ok,
           ", ".join(f"{key}={value:,}" for key, value in primary.mechanism.value_counts().sort_index().items()))

    summary_by_catchment = primary.groupby("GCIN").agg(
        events=("event_key", "size"), first=("peak_year", "min"), last=("peak_year", "max")
    )
    floor_ok = summary_by_catchment["events"].ge(CONFIG["event_samples"]["minimum_selected_events"]).all()
    floor_ok &= (summary_by_catchment["last"] - summary_by_catchment["first"] + 1).ge(
        CONFIG["event_samples"]["minimum_selected_span_years"]
    ).all()
    record(checks, "primary_event_and_span_floor", floor_ok,
           f"minimum events={summary_by_catchment.events.min()}; minimum selected span="
           f"{(summary_by_catchment['last'] - summary_by_catchment['first'] + 1).min()}")

    diagnostics = pd.read_csv(TABLES / "extreme_sample_diagnostics.csv")
    primary_diag = diagnostics[diagnostics["sample"].eq("pot_q95")].iloc[0]
    independence_ok = int(primary_diag.stormflow_window_overlaps) == 0
    independence_ok &= set(diagnostics["sample"]) == set(SAMPLES)
    record(checks, "event_independence_diagnostics", independence_ok,
           f"overlapping stormflow windows={int(primary_diag.stormflow_window_overlaps)}; "
           f"adjacent peaks under 10 days={int(primary_diag.pairs_under_10_days):,}")

    overall = pd.read_csv(TABLES / "catchment_overall_trends.csv")
    process = pd.read_csv(TABLES / "catchment_mechanism_trends.csv", low_memory=False)
    expected_overall = (
        overall["p_value"].lt(CONFIG["trends"]["alpha"])
        & overall["sample_direction_stable"].fillna(False)
        & overall["leave_one_year_stable"].fillna(False)
    )
    expected_process = (
        process["p_value"].lt(CONFIG["trends"]["alpha"])
        & process["sample_direction_stable"].fillna(False)
        & process["classification_direction_stable"].fillna(False)
        & process["leave_one_year_stable"].fillna(False)
    )
    evidence_ok = expected_overall.equals(overall["supported_shift"].fillna(False))
    evidence_ok &= expected_process.equals(process["supported_shift"].fillna(False))
    record(checks, "catchment_evidence_gates_exact", evidence_ok,
           f"overall supported={int(expected_overall.sum()):,}; process supported={int(expected_process.sum()):,}")

    minimum = CONFIG["trends"]["minimum_mechanism_events"]
    shares = process[process["outcome"].eq("mechanism_share")]
    nonshares = process[~process["outcome"].eq("mechanism_share")]
    five_event_ok = shares["n_mechanism_events"].ge(minimum).all()
    five_event_ok &= shares["n_other_events"].ge(CONFIG["trends"]["minimum_mechanism_other_events"]).all()
    five_event_ok &= nonshares["n_observations"].ge(minimum).all()
    record(checks, "single_process_event_threshold", five_event_ok,
           f"threshold={minimum}; no sample-size tiers")

    no_infinite = np.isfinite(overall["display_slope_per_decade"].dropna()).all()
    no_infinite &= np.isfinite(process["display_slope_per_decade"].dropna()).all()
    record(checks, "finite_reported_effects", no_infinite,
           f"overall estimates={len(overall):,}; process estimates={len(process):,}")

    check_daily_spot_sample(features, checks)

    figure_ok = True
    figure_details = []
    for stem in FIGURE_STEMS:
        png, svg, asset = FIGURES / f"{stem}.png", FIGURES / f"{stem}.svg", ASSETS / f"{stem}.png"
        present = png.exists() and svg.exists() and asset.exists()
        if present:
            with Image.open(png) as image:
                present &= image.width >= 1800 and image.height >= 900
                figure_details.append(f"{stem}:{image.width}x{image.height}")
            present &= sha256(png) == sha256(asset)
        figure_ok &= present
    record(checks, "six_current_figures", figure_ok, "; ".join(figure_details))

    reports = [
        ROOT / "reports" / "global_flood_cause_evolution.md",
        ROOT / "reports" / "global_flood_cause_evolution_en.md",
    ]
    terminology = "\n".join(path.read_text(encoding="utf-8") for path in reports)
    forbidden = ["HydroBASINS", "BH-FDR", "unadjusted p", "10-day declustering", "previous version", "old version"]
    record(checks, "current_report_scope", not any(term.lower() in terminology.lower() for term in forbidden),
           f"forbidden terms absent: {', '.join(forbidden)}")
    check_markdown_links(checks)

    html = ROOT / "reports" / "global_flood_cause_evolution.html"
    html_text = html.read_text(encoding="utf-8") if html.exists() else ""
    html_ok = html.exists() and html_text.count("data:image/png;base64,") == 6
    html_ok &= "report-nav" in html_text and "figure-lightbox" in html_text
    record(checks, "self_contained_html", html_ok,
           f"embedded figures={html_text.count('data:image/png;base64,')}; bytes={html.stat().st_size if html.exists() else 0:,}")

    web_path = ROOT / "public" / "modules" / "flood-cause-evolution" / "data" / "flood-cause-explorer.json"
    web = json.loads(web_path.read_text(encoding="utf-8"))
    web_ok = len(web.get("catchments", [])) > 0
    web_ok &= all("geometry" not in item and {"lon", "lat", "overall", "processes"}.issubset(item) for item in web["catchments"])
    web_ok &= len(web["meta"].get("mechanisms", [])) == 6
    record(checks, "catchment_point_web_schema", web_ok,
           f"catchment points={len(web.get('catchments', [])):,}; process classes={len(web['meta'].get('mechanisms', []))}")

    js_text = (ROOT / "public" / "modules" / "flood-cause-evolution" / "index.js").read_text(encoding="utf-8")
    ui_forbidden = ["HydroBASINS", "BH-FDR", "unadjusted", "candidate"]
    ui_ok = not any(term.lower() in js_text.lower() for term in ui_forbidden)
    ui_ok &= all(token in js_text for token in ["All estimates", "Supported focus", "pointer.x", "#22d3ee"])
    record(checks, "interactive_ui_semantics", ui_ok,
           "catchment points, pale all-estimate directions, supported z-order, pointer-anchored opaque tooltip")

    public_sync = True
    for stem in FIGURE_STEMS:
        public_asset = PUBLIC_REPORTS / "assets" / f"{stem}.png"
        public_sync &= public_asset.exists() and sha256(public_asset) == sha256(ASSETS / f"{stem}.png")
    public_html = PUBLIC_REPORTS / "global_flood_cause_evolution.html"
    public_sync &= public_html.exists() and sha256(public_html) == sha256(html)
    record(checks, "public_report_sync", public_sync, "HTML and six PNG assets match reports/")

    result = {
        "status": "pass" if all(item["passed"] for item in checks) else "fail",
        "checks_total": len(checks),
        "checks_passed": sum(bool(item["passed"]) for item in checks),
        "checks": checks,
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "validation_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(result)
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
