from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """
    Minimal config object.
    Later you can load from env vars / .env, but keep it simple now.
    """
    project_root: Path
    scripts_dir: Path
    script_specs_dir: Path
    logs_max_lines: int = 2000


def get_settings() -> Settings:
    """
    project_root: automation-platform/
    this file: backend/app/core/config.py
    parents:
      - config.py
      - core
      - app
      - backend
      - automation-platform   <-- we want this
    """
    project_root = Path(__file__).resolve().parents[4]

    return Settings(
        project_root=project_root,
        scripts_dir=project_root / "scripts",
        script_specs_dir=project_root / "script_specs",
        logs_max_lines=2000,
    )
