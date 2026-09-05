from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from floodcause.analysis import run_analysis
from floodcause.audit import run_source_audit
from floodcause.config import ensure_output_directories, load_config
from floodcause.features import build_event_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Global Flood Cause Evolution pipeline.")
    parser.add_argument(
        "--stage",
        choices=["audit", "features", "analysis", "conditions", "filters", "wetness-sensitivity", "figures", "reports", "html", "web", "all"],
        default="all",
    )
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "analysis.yaml"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    ensure_output_directories(config)
    receipt: dict[str, object] = {}
    if args.stage in {"audit", "all"}:
        receipt["audit"] = run_source_audit(config)
    if args.stage in {"features", "all"}:
        receipt["features"] = build_event_features(config, force=args.force)
    if args.stage in {"analysis", "all"}:
        receipt["analysis"] = run_analysis(config, force=args.force)
    if args.stage in {"conditions", "all"}:
        from floodcause.conditions import run_conditions_analysis

        receipt["conditions"] = run_conditions_analysis(config)
    if args.stage in {"filters", "all"}:
        from floodcause.filter_groups import run_filter_groups

        receipt["filters"] = run_filter_groups(config)
    if args.stage in {"wetness-sensitivity", "all"}:
        from floodcause.wetness_sensitivity import run_wetness_sensitivity

        receipt["wetness_sensitivity"] = run_wetness_sensitivity(config)
    if args.stage in {"figures", "all"}:
        from floodcause.plots import build_all_figures

        build_all_figures(config)
        receipt["figures"] = {"status": "complete", "directory": str(config["paths"]["figures"])}
    if args.stage in {"reports", "all"}:
        from build_reports import build_reports

        receipt["reports"] = build_reports()
    if args.stage in {"html", "all"}:
        from build_html_report import build_html_report

        receipt["html"] = build_html_report(
            config["paths"]["report"], config["paths"]["html_report"]
        )
    if args.stage in {"web", "all"}:
        from build_web_data import build_web_data

        receipt["web"] = build_web_data()
    print(json.dumps(receipt, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
