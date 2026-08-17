from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "config" / "analysis.yaml").read_text(encoding="utf-8"))


def _record(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _annual_expected(features: pd.DataFrame) -> pd.DataFrame:
    study = CONFIG["study"]
    valid = features.dropna(subset=["q_peak_mm_day", "peak_year", "intensity_fraction"]).copy()
    valid = valid[valid["peak_year"].between(study["start_year"], study["end_year"])]
    selected = valid.loc[
        valid.groupby(["GCIN", "peak_year"])["q_peak_mm_day"].idxmax()
    ].copy()
    coverage = selected.groupby("GCIN")["peak_year"].agg(["nunique", "min", "max"])
    span = coverage["max"] - coverage["min"] + 1
    eligible = coverage.index[
        (coverage["nunique"] >= study["minimum_annual_observations"])
        & (span >= study["minimum_record_span_years"])
        & (coverage["nunique"] / span >= study["minimum_record_coverage"])
    ]
    return selected[selected["GCIN"].isin(eligible)]


def _pot_expected(features: pd.DataFrame) -> pd.DataFrame:
    settings = CONFIG["event_samples"]
    valid = features.dropna(subset=["q_peak_mm_day", "peak_year", "intensity_fraction"]).copy()
    threshold = valid.groupby("GCIN")["q_peak_mm_day"].transform(
        lambda values: values.quantile(settings["pot_quantile"])
    )
    selected = valid[valid["q_peak_mm_day"] >= threshold]
    counts = selected.groupby("GCIN").size()
    eligible = counts.index[counts >= settings["minimum_pot_events"]]
    return selected[selected["GCIN"].isin(eligible)]


def _panel_slope(frame: pd.DataFrame, outcome: str) -> float:
    data = frame[["GCIN", "peak_year", outcome]].dropna().copy()
    x = (data["peak_year"].astype(float) - 2000.0) / 10.0
    y = data[outcome].astype(float)
    xw = x - x.groupby(data["GCIN"]).transform("mean")
    yw = y - y.groupby(data["GCIN"]).transform("mean")
    beta = float(np.dot(xw, yw) / np.dot(xw, xw))
    return beta * (100.0 if outcome.startswith(("intensity_0", "intensity_joint", "wet_")) else 1.0)


def _independent_bh(values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=float)
    valid_positions = np.flatnonzero(np.isfinite(values))
    if not len(valid_positions):
        return result
    valid = values[valid_positions]
    order = np.argsort(valid)
    ranked = valid[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.clip(adjusted, 0.0, 1.0)
    result[valid_positions] = restored
    return result


def _check_markdown_links(checks: list[dict]) -> None:
    missing: list[str] = []
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "reports").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for raw in pattern.findall(text):
            target = raw.strip().split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append(f"{path.relative_to(ROOT)} -> {raw}")
    _record(checks, "markdown_local_links", not missing, "none missing" if not missing else "; ".join(missing))


def _check_daily_spot_sample(features: pd.DataFrame, checks: list[dict]) -> None:
    source_daily = Path(CONFIG["paths"]["source_global_data"]) / "daily_data" / "observations"
    sample = features.sample(24, random_state=20260815)
    failures: list[str] = []
    for row in sample.itertuples(index=False):
        daily = pd.read_csv(source_daily / f"{int(row.GCIN)}.csv", parse_dates=["date"])
        p = daily[daily["date"].between(row.start_precip_date, row.end_precip_date)]["water_input_mm"]
        q = daily[daily["date"].between(row.start_stormflow_date, row.end_stormflow_date)]["streamflow_mm"]
        if not np.isclose(p.sum(), row.p_volume_daily_mm, rtol=0, atol=1e-9):
            failures.append(f"{row.event_key}: precipitation")
        if not np.isclose(p.max(), row.p_max_daily_mm, rtol=0, atol=1e-9):
            failures.append(f"{row.event_key}: Pmax")
        if not np.isclose(q.max(), row.q_peak_mm_day, rtol=0, atol=1e-9):
            failures.append(f"{row.event_key}: Qpeak")
    _record(checks, "daily_reconstruction_spot_check", not failures, f"24 events; failures={failures}")


def main() -> None:
    checks: list[dict] = []
    derived = ROOT / "data" / "derived"
    tables = ROOT / "outputs" / "tables"
    figures = ROOT / "outputs" / "figures"
    report_assets = ROOT / "reports" / "assets"
    features = pd.read_parquet(derived / "event_features.parquet")
    annual = pd.read_parquet(derived / "annual_maximum_events.parquet")
    pot = pd.read_parquet(derived / "pot_q95_events.parquet")

    _record(checks, "event_key_unique", features["event_key"].is_unique, f"rows={len(features):,}")
    _record(
        checks,
        "annual_catchment_year_unique",
        not annual.duplicated(["GCIN", "peak_year"]).any(),
        f"rows={len(annual):,}; catchments={annual['GCIN'].nunique():,}",
    )

    expected_annual = _annual_expected(features)
    annual_match = set(expected_annual["event_key"]) == set(annual["event_key"])
    _record(checks, "annual_sample_exact_reproduction", annual_match, f"expected={len(expected_annual):,}; saved={len(annual):,}")

    expected_pot = _pot_expected(features)
    pot_match = set(expected_pot["event_key"]) == set(pot["event_key"])
    _record(checks, "pot_sample_exact_reproduction", pot_match, f"expected={len(expected_pot):,}; saved={len(pot):,}")

    c = CONFIG["classification"]
    classification_ok = (
        annual["intensity_050"].eq(annual["intensity_fraction"].gt(c["intensity_fraction_threshold"]).astype(int)).all()
        and annual["intensity_075"].eq(annual["intensity_fraction"].gt(c["intensity_fraction_sensitivity_threshold"]).astype(int)).all()
        and annual["intensity_joint_050_cv1"].eq(
            (annual["intensity_fraction"].gt(c["intensity_fraction_threshold"]) & annual["precipitation_cv"].gt(c["intensity_cv_threshold"])).astype(int)
        ).all()
    )
    _record(checks, "rainfall_classification", classification_ok, "three intensity definitions reproduced exactly")

    wetness_ok = True
    for window in c["ssi_windows_days"]:
        expected = annual[f"ssi_{window}d"].gt(c["ssi_thresholds"][1]).astype("Int64")
        wetness_ok &= annual[f"wet_{window}d"].eq(expected).all()
    _record(checks, "wetness_classification", wetness_ok, "1/3/7/30-day wet labels reproduced exactly")

    panel = pd.read_csv(tables / "panel_fixed_effect_trends.csv")
    comparisons = []
    for outcome in ["intensity_050", "wet_1d", "intensity_fraction", "ssi_30d"]:
        saved = panel.query("sample == 'annual_maximum' and region == 'Global' and outcome == @outcome")["slope_per_decade"].iloc[0]
        recomputed = _panel_slope(annual, outcome)
        comparisons.append((outcome, float(saved), recomputed, abs(saved - recomputed)))
    _record(
        checks,
        "fixed_effect_slope_recalculation",
        max(item[3] for item in comparisons) < 1e-12,
        "; ".join(f"{name}: saved={saved:.12g}, recalculated={calc:.12g}" for name, saved, calc, _ in comparisons),
    )

    binary = pd.read_csv(tables / "catchment_binary_trends.csv")
    fdr_errors = []
    for outcome, frame in binary.groupby("outcome"):
        expected = _independent_bh(frame["logistic_p"].to_numpy(float))
        error = float(np.max(np.abs(expected - frame["logistic_q"].to_numpy(float))))
        fdr_errors.append((outcome, error))
    _record(checks, "binary_fdr_recalculation", max(x[1] for x in fdr_errors) < 1e-12, f"max_abs_error={max(x[1] for x in fdr_errors):.3g}")

    composition = pd.read_csv(tables / "cause_composition_by_region.csv")
    share_sums = composition.groupby("continent")["proportion"].sum()
    _record(checks, "cause_composition_sums", np.allclose(share_sums, 1.0, atol=1e-12), f"max_abs_error={float(np.max(np.abs(share_sums - 1))):.3g}")

    membership = pd.read_csv(tables / "hydrobasin_catchment_membership.csv")
    matched = int(membership["hybas_id_l5"].notna().sum())
    unmatched = set(membership.loc[membership["hybas_id_l5"].isna(), "GCIN"].astype(int))
    _record(
        checks,
        "hydrobasin_membership",
        matched == 2835 and unmatched == {2175, 2176, 2177, 3245},
        f"matched={matched:,}; unmatched={sorted(unmatched)}",
    )

    local = pd.read_csv(tables / "local_hydrobasin_trends.csv")
    primary_outcomes = set(CONFIG["local_analysis"]["primary_outcomes"])
    local_primary = local[
        (local["sample"] == "annual_maximum")
        & (local["level"] == CONFIG["local_analysis"]["primary_level"])
        & local["outcome"].isin(primary_outcomes)
    ].copy()
    expected_local_q = _independent_bh(local_primary["cluster_robust_p"].to_numpy(float))
    saved_local_q = local_primary["primary_q"].to_numpy(float)
    finite_local_q = np.isfinite(expected_local_q) & np.isfinite(saved_local_q)
    local_q_error = float(
        np.max(np.abs(expected_local_q[finite_local_q] - saved_local_q[finite_local_q]))
    )
    missingness_matches = bool(
        np.array_equal(np.isnan(expected_local_q), np.isnan(saved_local_q))
    )
    _record(
        checks,
        "local_primary_fdr_recalculation",
        len(local_primary) == 144 and missingness_matches and local_q_error < 1e-12,
        f"tests={len(local_primary)}; valid={int(finite_local_q.sum())}; max_abs_error={local_q_error:.3g}",
    )

    focal = local_primary.loc[
        local_primary["slope_per_decade"].abs().idxmax()
    ]
    focal_ids = set(
        membership.loc[
            membership["hybas_id_l5"].eq(focal["HYBAS_ID"]), "GCIN"
        ].astype(int)
    )
    focal_sample = annual[annual["GCIN"].isin(focal_ids)]
    focal_recalculated = _panel_slope(focal_sample, str(focal["outcome"]))
    _record(
        checks,
        "local_fixed_effect_slope_recalculation",
        abs(float(focal["slope_per_decade"]) - focal_recalculated) < 1e-12,
        f"{focal['basin_code']} {focal['outcome']}: saved={float(focal['slope_per_decade']):.12g}; recalculated={focal_recalculated:.12g}",
    )

    paired = pd.read_csv(tables / "local_hydrobasin_period_comparison.csv")
    paired_focal = paired[
        (paired["HYBAS_ID"] == focal["HYBAS_ID"]) & (paired["outcome"] == focal["outcome"])
    ].iloc[0]
    early_start, early_end = CONFIG["trends"]["early_period"]
    late_start, late_end = CONFIG["trends"]["late_period"]
    paired_values = []
    for _, frame in focal_sample.groupby("GCIN"):
        early = frame.loc[frame["peak_year"].between(early_start, early_end), focal["outcome"]].dropna()
        late = frame.loc[frame["peak_year"].between(late_start, late_end), focal["outcome"]].dropna()
        if len(early) >= 10 and len(late) >= 10:
            paired_values.append((late.mean() - early.mean()) * 100.0)
    paired_recalculated = float(np.mean(paired_values))
    _record(
        checks,
        "local_paired_period_recalculation",
        abs(float(paired_focal["mean_difference_percentage_points"]) - paired_recalculated) < 1e-12,
        f"catchments={len(paired_values)}; saved={float(paired_focal['mean_difference_percentage_points']):.12g}; recalculated={paired_recalculated:.12g}",
    )

    robustness = pd.read_csv(tables / "local_hydrobasin_robustness.csv")
    high_confidence = robustness["high_confidence_local_signal"].fillna(False)
    gates_ok = (
        robustness.loc[high_confidence, "locally_replicated_signal"].all()
        and robustness.loc[high_confidence, "definition_direction_stable"].all()
        and robustness.loc[high_confidence, "jackknife_sign_stable"].all()
    )
    _record(
        checks,
        "local_signal_stability_gates",
        int(high_confidence.sum()) == 17 and gates_ok,
        f"high_confidence_signals={int(high_confidence.sum())}; all gates satisfied={bool(gates_ok)}",
    )

    _check_daily_spot_sample(features, checks)

    image_failures = []
    for number in range(1, 10):
        png_matches = list(figures.glob(f"figure_{number:02d}_*.png"))
        svg_matches = list(figures.glob(f"figure_{number:02d}_*.svg"))
        if len(png_matches) != 1 or len(svg_matches) != 1:
            image_failures.append(f"figure {number:02d}: expected one PNG and SVG")
            continue
        with Image.open(png_matches[0]) as image:
            if image.width < 1600 or image.height < 900:
                image_failures.append(f"{png_matches[0].name}: {image.size}")
        if svg_matches[0].stat().st_size < 10_000:
            image_failures.append(f"{svg_matches[0].name}: undersized")
        report_copy = report_assets / png_matches[0].name
        if not report_copy.exists() or _sha256(report_copy) != _sha256(png_matches[0]):
            image_failures.append(f"{png_matches[0].name}: report-local copy missing or stale")
    _record(checks, "figure_assets", not image_failures, "9 PNG/SVG pairs valid; report-local PNG hashes match" if not image_failures else "; ".join(image_failures))

    _check_markdown_links(checks)
    html_report = ROOT / "reports" / "global_flood_cause_evolution.html"
    html_text = html_report.read_text(encoding="utf-8") if html_report.exists() else ""
    report_markdown = (ROOT / "reports" / "global_flood_cause_evolution.md").read_text(encoding="utf-8")
    expected_report_images = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", report_markdown))
    html_ok = (
        html_text.count("data:image/png;base64,") == expected_report_images
        and "<nav class=\"toc\"" in html_text
        and "降雨型大洪水成因变化的局地水文区格局" in html_text
        and 'id="figure-lightbox"' in html_text
        and "openFigure(image)" in html_text
        and "document.getElementById(a.getAttribute('href').slice(1))" in html_text
        and "document.querySelector(a.getAttribute('href'))" not in html_text
        and "src=\"assets/" not in html_text
    )
    _record(
        checks,
        "self_contained_html_report",
        html_ok,
        f"bytes={html_report.stat().st_size if html_report.exists() else 0:,}; embedded_images={html_text.count('data:image/png;base64,')}; expected={expected_report_images}",
    )

    web_data_path = (
        ROOT
        / "public"
        / "modules"
        / "flood-cause-evolution"
        / "data"
        / "flood-cause-explorer.json"
    )
    web_module_path = ROOT / "public" / "modules" / "flood-cause-evolution" / "index.js"
    web_manifest_path = ROOT / "public" / "module.json"
    web_failures: list[str] = []
    try:
        web_data = json.loads(web_data_path.read_text(encoding="utf-8"))
        web_manifest = json.loads(web_manifest_path.read_text(encoding="utf-8"))
        web_module = web_module_path.read_text(encoding="utf-8")
        web_basins = web_data.get("basins", [])
        web_catchments = web_data.get("catchments", [])
        web_signals = sum(
            bool(metric.get("highConfidence"))
            for basin in web_basins
            for metric in basin.get("metrics", {}).values()
        )
        if len(web_basins) != 72:
            web_failures.append(f"basins={len(web_basins)}")
        if len(web_catchments) != 2839:
            web_failures.append(f"catchments={len(web_catchments)}")
        if web_signals != 17:
            web_failures.append(f"high_confidence={web_signals}")
        expected_meta = {
            "eligibleHydrobasins": 72,
            "limitedSampleHydrobasins": 44,
            "largerSampleHydrobasins": 28,
            "unitedStatesHydrobasins": 17,
            "analysisMinimumCatchments": 5,
            "largerSampleCatchments": 20,
            "minimumObservations": 300,
        }
        observed_meta = {key: web_data.get("meta", {}).get(key) for key in expected_meta}
        if observed_meta != expected_meta:
            web_failures.append(f"map metadata={observed_meta}")
        if any(set(basin.get("metrics", {})) != {"intensity_050", "wet_1d"} for basin in web_basins):
            web_failures.append("one or more basins lack both primary metrics")
        tier_counts = {
            "limited": sum(
                all(not metric.get("largerSample") for metric in basin.get("metrics", {}).values())
                for basin in web_basins
            ),
            "larger": sum(
                all(metric.get("largerSample") for metric in basin.get("metrics", {}).values())
                for basin in web_basins
            ),
        }
        if tier_counts != {"limited": 44, "larger": 28}:
            web_failures.append(f"sample tiers={tier_counts}")
        if any(basin.get("geometry", {}).get("type") not in {"Polygon", "MultiPolygon"} for basin in web_basins):
            web_failures.append("invalid basin geometry")
        if web_manifest.get("className") != "FloodCauseEvolutionModule":
            web_failures.append("manifest className mismatch")
        catchment_metric_counts = {
            outcome: sum(outcome in catchment.get("metrics", {}) for catchment in web_catchments)
            for outcome in ["intensity_050", "wet_1d"]
        }
        if catchment_metric_counts != {"intensity_050": 2516, "wet_1d": 837}:
            web_failures.append(f"catchment metric counts={catchment_metric_counts}")
        catchment_slopes = [
            float(metric["slope"])
            for catchment in web_catchments
            for metric in catchment.get("metrics", {}).values()
            if metric.get("slope") is not None
        ]
        nonzero_share = float(np.mean(np.abs(catchment_slopes) > 1e-12))
        if nonzero_share < 0.95:
            web_failures.append(f"catchment nonzero slope share={nonzero_share:.3f}")
        for marker in [
            "flood-cause-hydrobasins",
            "flood-cause-catchments",
            "renderBasins",
            "renderCatchments",
            "showInspector",
            "drawHoverLabel",
            "if (!metric) continue",
            "colorFor(metric.slope, 20)",
            "metric.largerSample",
            "analysisMinimumCatchments",
            "ctx.setLineDash([])",
            'ctx.shadowColor = "rgba(34,211,238,.98)"',
            'ctx.shadowColor = "rgba(34,211,238,.90)"',
            "ctx.shadowBlur = 19",
            "ctx.shadowBlur = 16",
            "ctx.shadowBlur = 13",
            "ctx.lineWidth = 1.45",
            "ctx.lineWidth = 1.4",
            "ctx.arc(x, y, radius + 3.1",
            'ctx.lineJoin = "round"',
            'ctx.lineCap = "round"',
            "ctx.miterLimit = 2",
            'ctx.strokeStyle = "rgba(34,211,238,.98)"',
            "ctx.lineWidth = 1.5",
            "metric.highConfidence ? 1.2 : 0.7",
            'ctx.font = "600 12px Inter, system-ui, sans-serif"',
            ".legend-card{font-size:12px",
            ".fce-fact span{font-size:11px",
        ]:
            if marker not in web_module:
                web_failures.append(f"module marker missing: {marker}")
        for forbidden in [
            'hovered ? "#ffffff"',
            "fine-dot",
            "border:1px dashed",
            "font-size:9px",
            "font-size:10px",
            "font:600 9px",
            "#D946EF",
            "217,70,239",
            "Hover highlight",
            'ctx.strokeStyle = "rgba(15,23,42,.88)"',
            'active ? "#0f172a"',
            'ctx.strokeStyle = "rgba(14,116,144,.94)"',
            "active ? 2.8",
            "metric.highConfidence ? 1.7",
        ]:
            if forbidden in web_module:
                web_failures.append(f"obsolete boundary/highlight style present: {forbidden}")
    except (OSError, ValueError, TypeError) as error:
        web_failures.append(str(error))
    _record(
        checks,
        "interactive_web_explorer",
        not web_failures,
        (
            f"72 HydroBASINS regions; 2,839 catchments; 17 high-confidence signals; "
            f"data_bytes={web_data_path.stat().st_size:,}"
            if not web_failures
            else "; ".join(web_failures)
        ),
    )
    utf8_failures = []
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), *sorted((ROOT / "reports").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            utf8_failures.append(str(path.relative_to(ROOT)))
    _record(checks, "utf8_documents", not utf8_failures, "all Markdown decodes as UTF-8 without replacement characters")

    hydrobasin_directory = ROOT / CONFIG["paths"]["hydrobasins"]
    checksum_manifest = pd.read_csv(ROOT / "outputs" / "logs" / "hydrobasins_reference_sha256.csv")
    reference_failures = []
    for row in checksum_manifest.itertuples(index=False):
        path = hydrobasin_directory / row.file
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
        except (FileNotFoundError, zipfile.BadZipFile):
            bad_member = "archive unreadable"
        if bad_member or path.stat().st_size != row.bytes or _sha256(path) != row.sha256:
            reference_failures.append(str(row.file))
    _record(
        checks,
        "hydrobasins_reference_integrity",
        len(checksum_manifest) == 24 and not reference_failures,
        f"archives={len(checksum_manifest)}; failures={reference_failures}",
    )

    reference = ROOT / CONFIG["paths"]["world_boundaries"]
    result = {
        "status": "pass" if all(check["passed"] for check in checks) else "fail",
        "checks_passed": sum(check["passed"] for check in checks),
        "checks_total": len(checks),
        "reference_sha256": {str(reference.relative_to(ROOT)): _sha256(reference)},
        "checks": checks,
    }
    destination = ROOT / "outputs" / "logs" / "validation.json"
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
