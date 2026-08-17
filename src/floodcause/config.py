from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load analysis configuration and resolve project-local paths."""
    config_path = Path(path) if path else PROJECT_ROOT / "config" / "analysis.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    paths = config["paths"]
    for key, value in list(paths.items()):
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        paths[key] = candidate.resolve()
    config["project_root"] = PROJECT_ROOT
    config["config_path"] = config_path.resolve()
    return config


def ensure_output_directories(config: dict[str, Any]) -> None:
    """Create only project-owned output directories."""
    for key in ("derived_data", "tables", "figures", "report_assets", "logs"):
        config["paths"][key].mkdir(parents=True, exist_ok=True)
    config["paths"]["report"].parent.mkdir(parents=True, exist_ok=True)
