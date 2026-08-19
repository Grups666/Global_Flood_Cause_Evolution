from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
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

PRIMARY_METRICS = ["intensity_fraction", "ssi_1d", "ssi_3d", "ssi_7d", "ssi_30d"]
FIGURE_STEMS = [
    "figure_01_sample_coverage",
    "figure_02_mechanism_change_maps",
    "figure_03_strong_signal_rankings",
    "figure_04_mechanism_trajectories",
    "figure_05_physical_decomposition",
    "figure_06_robustness_matrix",
]


def record(checks: list[dict[str, object]], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def independent_bh(values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=float)
    positions = np.flatnonzero(np.isfinite(values))
    if not len(positions):
        return result
    valid = values[positions]
    order = np.argsort(valid)
    ranked = valid[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.clip(adjusted, 0.0, 1.0)
    result[positions] = restored
    return result


def expected_primary(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    study = CONFIG["study"]
    settings = CONFIG["event_samples"]
    required = ["q_peak_mm_day", "peak_year", "intensity_fraction", "p_max_daily_mm", "p_volume_daily_mm"]
    events = features.dropna(subset=required).copy()
    events = events[events["peak_year"].between(study["start_year"], study["end_year"])]
    annual_idx = events.groupby(["GCIN", "peak_year"])["q_peak_mm_day"].idxmax()
    annual = events.loc[annual_idx]
    coverage = annual.groupby("GCIN").agg(
        n_event_years=("peak_year", "nunique"),
        first_year=("peak_year", "min"),
        last_year=("peak_year", "max"),
    )
    coverage["record_span_years"] = coverage["last_year"] - coverage["first_year"] + 1
    coverage["coverage_fraction"] = coverage["n_event_years"] / coverage["record_span_years"]
    coverage["eligible"] = (
        (coverage["n_event_years"] >= study["minimum_annual_observations"])
        & (coverage["record_span_years"] >= study["minimum_record_span_years"])
        & (coverage["coverage_fraction"] >= study["minimum_record_coverage"])
    )
    eligible = set(coverage.index[coverage["eligible"]].astype(int))
    pool = events[events["GCIN"].isin(eligible)].copy()
    threshold = pool.groupby("GCIN")["q_peak_mm_day"].transform(lambda values: values.quantile(0.95))
    selected = pool[pool["q_peak_mm_day"] >= threshold].copy()
    summary = selected.groupby("GCIN").agg(
        events=("event_key", "size"), first=("peak_year", "min"), last=("peak_year", "max")
    )
    summary["span"] = summary["last"] - summary["first"] + 1
    keep = set(summary.index[
        (summary["events"] >= settings["minimum_events"])
        & (summary["span"] >= settings["minimum_selected_span_years"])
    ].astype(int))
    return coverage.reset_index(), selected[selected["GCIN"].isin(keep)]


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


def check_daily_spot_sample(features: pd.DataFrame, checks: list[dict[str, object]]) -> None:
    source = Path(CONFIG["paths"]["source_global_data"]) / "daily_data" / "observations"
    failures: list[str] = []
    for row in features.sample(20, random_state=20260818).itertuples(index=False):
        daily = pd.read_csv(source / f"{int(row.GCIN)}.csv", parse_dates=["date"])
        rain = daily[daily["date"].between(row.start_precip_date, row.end_precip_date)]["water_input_mm"]
        flow = daily[daily["date"].between(row.start_stormflow_date, row.end_stormflow_date)]["streamflow_mm"]
        if not np.isclose(rain.sum(), row.p_volume_daily_mm, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: rain volume")
        if not np.isclose(rain.max(), row.p_max_daily_mm, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: daily rain maximum")
        if not np.isclose(flow.max(), row.q_peak_mm_day, atol=1e-9, rtol=0):
            failures.append(f"{row.event_key}: flood peak")
    record(checks, "daily_reconstruction_spot_check", not failures, f"20 events; failures={failures}")


def write_validation_report(result: dict[str, object]) -> None:
    lines = [
        "# Validation report",
        "",
        f"**Status:** {str(result['status']).upper()}",
        f"**Checks:** {result['checks_passed']} / {result['checks_total']} passed",
        "**Execution date:** 2026-08-18",
        "",
        "| Check | Status | Evidence |",
        "|---|---:|---|",
    ]
    for item in result["checks"]:
        detail = str(item["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{item['check']}` | {'PASS' if item['passed'] else 'FAIL'} | {detail} |")
    lines.extend([
        "",
        "The validator independently reconstructs the primary POT/Q95 sample, recomputes the declared FDR family and evidence gates, checks display eligibility, verifies all report assets and the self-contained HTML, and validates the interactive JSON schema.",
        "",
    ])
    (ROOT / "docs" / "quality" / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    checks: list[dict[str, object]] = []
    features = pd.read_parquet(DERIVED / "event_features.parquet")
    primary = pd.read_parquet(DERIVED / "primary_extreme_events.parquet")
    saved_coverage = pd.read_csv(TABLES / "record_eligibility.csv")

    record(checks, "event_key_unique", features["event_key"].is_unique, f"source feature rows={len(features):,}")
    expected_coverage, expected = expected_primary(features)
    coverage_columns = ["GCIN", "n_event_years", "first_year", "last_year", "record_span_years", "eligible"]
    coverage_match = expected_coverage[coverage_columns].sort_values("GCIN").reset_index(drop=True).equals(
        saved_coverage[coverage_columns].sort_values("GCIN").reset_index(drop=True)
    ) and np.allclose(expected_coverage["coverage_fraction"], saved_coverage["coverage_fraction"])
    record(checks, "record_eligibility_exact", coverage_match, f"eligible={int(saved_coverage.eligible.sum()):,}")
    primary_match = set(expected["event_key"]) == set(primary["event_key"])
    record(checks, "primary_pot_q95_exact", primary_match, f"expected={len(expected):,}; saved={len(primary):,}; catchments={primary.GCIN.nunique():,}")

    summary = primary.groupby("GCIN").agg(events=("event_key", "size"), first=("peak_year", "min"), last=("peak_year", "max"))
    display_floor = summary.events.ge(10).all() and (summary["last"] - summary["first"] + 1).ge(20).all()
    record(checks, "primary_event_and_span_floor", display_floor, f"minimum events={summary.events.min()}; minimum span={(summary['last'] - summary['first'] + 1).min()}")

    diagnostics = pd.read_csv(TABLES / "extreme_sample_diagnostics.csv")
    primary_diag = diagnostics[diagnostics["sample"].eq("pot_q95")].iloc[0]
    independence_ok = int(primary_diag.stormflow_window_overlaps) == 0 and int(primary_diag.minimum_peak_gap_days) >= 2
    gap10 = diagnostics[diagnostics["sample"].eq("pot_q95_gap10")].iloc[0]
    independence_ok &= int(gap10.pairs_under_10_days) == 0
    record(checks, "event_independence_diagnostics", independence_ok, f"Q95 overlaps=0; Q95 pairs<10d={int(primary_diag.pairs_under_10_days):,}; declustered pairs<10d={int(gap10.pairs_under_10_days)}")

    evidence = pd.read_csv(TABLES / "hydrobasin_evidence.csv")
    family = evidence[(evidence["sample"].eq("pot_q95")) & (evidence["level"].eq(5)) & evidence["metric"].isin(PRIMARY_METRICS)].copy()
    expected_q = independent_bh(family["p_value"].to_numpy(float))
    q_error = float(np.nanmax(np.abs(expected_q - family["primary_family_q"].to_numpy(float))))
    record(checks, "complete_primary_fdr", len(family) == 490 and q_error < 1e-12, f"tests={len(family)}; FDR-supported={int(family.primary_family_fdr_supported.sum())}; max error={q_error:.3g}")

    recomputed_strong = (
        family["primary_family_fdr_supported"].fillna(False)
        & family["catchments"].ge(CONFIG["local_analysis"]["strong_evidence_minimum_catchments"])
        & family["sample_direction_stable"].fillna(False)
        & family["jackknife_sign_stable"].fillna(False)
        & family["wetness_window_stable"].fillna(False)
    )
    strong_match = recomputed_strong.equals(family["strong_evidence"].fillna(False))
    record(checks, "strong_evidence_gates", strong_match and int(recomputed_strong.sum()) == 63, f"signals={int(recomputed_strong.sum())}; basins={family.loc[recomputed_strong, 'HYBAS_ID'].nunique()}")

    trajectories = pd.read_csv(TABLES / "hydrobasin_trajectories.csv")
    trajectory_ok = trajectories["year"].between(1982, 2019).all() and set(PRIMARY_METRICS).issubset(set(trajectories.metric))
    record(checks, "continuous_time_trajectories", trajectory_ok, f"rows={len(trajectories):,}; years={trajectories.year.min()}–{trajectories.year.max()}")

    catchment = pd.read_csv(TABLES / "catchment_mechanism_trends.csv")
    catchment_primary = catchment[catchment["variable"].isin(PRIMARY_METRICS)]
    catchment_ok = catchment_primary.n_observations.ge(10).all() and catchment_primary.year_span.ge(20).all()
    record(checks, "catchment_trend_eligibility", catchment_ok, f"catchments={catchment_primary.GCIN.nunique():,}; FDR-supported={int(catchment_primary.fdr_significant.sum())}")

    figure_failures: list[str] = []
    expected_asset_names = {f"{stem}.png" for stem in FIGURE_STEMS}
    observed_asset_names = {path.name for path in ASSETS.glob("figure_*.*")}
    if observed_asset_names != expected_asset_names:
        figure_failures.append(f"report assets differ: {sorted(observed_asset_names ^ expected_asset_names)}")
    for stem in FIGURE_STEMS:
        png_source = FIGURES / f"{stem}.png"
        png_asset = ASSETS / png_source.name
        svg_source = FIGURES / f"{stem}.svg"
        if not png_source.exists() or not png_asset.exists() or sha256(png_source) != sha256(png_asset):
            figure_failures.append(f"missing/stale {png_source.name}")
        if not svg_source.exists() or svg_source.stat().st_size < 10_000:
            figure_failures.append(f"missing/undersized {svg_source.name}")
        with Image.open(ASSETS / f"{stem}.png") as image:
            if image.width < 1800 or image.height < 1000:
                figure_failures.append(f"undersized {stem}: {image.size}")
    record(checks, "figure_assets", not figure_failures, "6 report PNGs synchronized; 6 publication SVGs generated" if not figure_failures else "; ".join(figure_failures))

    report_md = (ROOT / "reports" / "global_flood_cause_evolution.md").read_text(encoding="utf-8")
    report_html = (ROOT / "reports" / "global_flood_cause_evolution.html").read_text(encoding="utf-8")
    html_ok = report_html.count("data:image/png;base64,") == 6 and 'id="lightbox"' in report_html and "openFigure(image)" in report_html and "59,048" in report_html and "23" in report_html
    record(checks, "self_contained_html_report", html_ok, f"bytes={len(report_html.encode('utf-8')):,}; embedded PNGs={report_html.count('data:image/png;base64,')}")

    public_report = PUBLIC_REPORTS / "global_flood_cause_evolution.html"
    public_assets = PUBLIC_REPORTS / "assets"
    public_report_ok = public_report.exists() and sha256(public_report) == sha256(ROOT / "reports" / "global_flood_cause_evolution.html")
    public_report_ok &= all(
        (public_assets / f"{stem}.png").exists()
        and sha256(public_assets / f"{stem}.png") == sha256(ASSETS / f"{stem}.png")
        for stem in FIGURE_STEMS
    )
    record(checks, "published_research_materials", public_report_ok, "self-contained report and 6 overview figures synchronized to public/")

    web_path = ROOT / "public" / "modules" / "flood-cause-evolution" / "data" / "flood-cause-explorer.json"
    web_text = web_path.read_text(encoding="utf-8")
    try:
        web = json.loads(web_text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        basins = web["basins"]
        catchments = web["catchments"]
        strong_count = sum(metric.get("strong", False) for basin in basins for key, metric in basin["metrics"].items() if key in PRIMARY_METRICS)
        web_ok = len(basins) == 98 and len(catchments) == 2624 and strong_count == 63
        web_ok &= all(len(item.get("metrics", {})) >= 5 for item in catchments)
        web_ok &= all(metric["observations"] >= 10 and metric["span"] >= 20 for item in catchments for metric in item["metrics"].values())
        web_ok &= all(item["geometry"]["type"] in {"Polygon", "MultiPolygon"} for item in basins)
        web_detail = f"basins={len(basins)}; catchments={len(catchments)}; strong signals={strong_count}; bytes={web_path.stat().st_size:,}"
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        web_ok = False
        web_detail = str(error)
    module = (ROOT / "public" / "modules" / "flood-cause-evolution" / "index.js").read_text(encoding="utf-8")
    required_markers = ["intensity_fraction", "ssi_30d", "Continuous-time trajectory", "Rainfall-process decomposition", "rgba(34, 211, 238", "ctx.shadowBlur", "drawBasinHighlight", "if (hoveredBasin)", "fce-hover-tooltip", "metricMeaning", "fce-signal p", "background:#172235", "fce-overview-nav", "Project materials", "data-scroll=\"resources\""]
    forbidden_markers = ["Early–late", "probability2000", "probability2010", "logistic probability change", "#D946EF", "#ffffff\";\n          ctx.lineWidth", "drawHoverLabel", "overviewLayerId", 'name: "Research overview"']
    web_ok &= all(marker in module for marker in required_markers) and not any(marker in module for marker in forbidden_markers)
    web_ok &= module.count("reports/assets/figure_") == 6
    record(checks, "interactive_web_explorer", web_ok, web_detail)

    current_text = report_md + "\n" + module
    obsolete = [phrase for phrase in ["旧版本", "上一版本", "previous version", "early–late", "probability2000", "probability2010"] if phrase.lower() in current_text.lower()]
    record(checks, "current_only_narrative", not obsolete, f"obsolete phrases={obsolete}")

    check_daily_spot_sample(features, checks)
    check_markdown_links(checks)

    utf8_failures = []
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "reports").glob("*.md"))]:
        if "\ufffd" in path.read_text(encoding="utf-8"):
            utf8_failures.append(str(path.relative_to(ROOT)))
    record(checks, "utf8_documents", not utf8_failures, f"replacement-character files={utf8_failures}")

    hydro_dir = ROOT / CONFIG["paths"]["hydrobasins"]
    manifest = pd.read_csv(LOGS / "hydrobasins_reference_sha256.csv")
    bad_archives = []
    for row in manifest.itertuples(index=False):
        path = hydro_dir / row.file
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
            valid = not bad_member and path.stat().st_size == row.bytes and sha256(path) == row.sha256
        except (FileNotFoundError, zipfile.BadZipFile):
            valid = False
        if not valid:
            bad_archives.append(str(row.file))
    record(checks, "hydrobasins_reference_integrity", len(manifest) == 24 and not bad_archives, f"archives={len(manifest)}; failures={bad_archives}")

    result: dict[str, object] = {
        "status": "pass" if all(bool(item["passed"]) for item in checks) else "fail",
        "checks_passed": sum(bool(item["passed"]) for item in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_validation_report(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
