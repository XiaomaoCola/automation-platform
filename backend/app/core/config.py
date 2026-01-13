from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def find_project_root(start: Path) -> Path:
    """
    Walk upwards until we find a marker file.
    This avoids fragile `.parents[n]` assumptions.
    """
    start = start.resolve()
    markers = {"pyproject.toml", "README.md"}

    for p in [start, *start.parents]:
        for m in markers:
            if (p / m).exists():
                return p

    # fallback: repo root guess
    return start.parents[0]


@dataclass(frozen=True)
class Settings:
    project_root: Path
    scripts_dir: Path
    script_specs_dir: Path
    logs_max_lines: int = 2000
    default_tail_lines: int = 200


def get_settings() -> Settings:
    # this file: backend/app/core/config.py
    here = Path(__file__)
    project_root = find_project_root(here)

    return Settings(
        project_root=project_root,
        scripts_dir=project_root / "scripts",
        script_specs_dir=project_root / "script_specs",
        logs_max_lines=2000,
        default_tail_lines=200,
    )
