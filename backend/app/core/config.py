from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def find_project_root(start: Path) -> Path:
    """
    Walk upwards until we find a marker file.
    This avoids fragile `.parents[n]` assumptions.
    """
    start = start.resolve()
    # .resolve()把路径变成绝对路径，比如/Users/xxx/project/backend/app/core/config.py。
    markers = {"pyproject.toml", "README.md"}
    # 这里的意思是：“只要某个目录下有这些文件之一，就认为它是项目根目录”。

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
    # __file__ 永远等于“当前这个 .py 文件的路径”。
    project_root = find_project_root(here)

    return Settings(
        project_root=project_root,
        scripts_dir=project_root / "scripts",
        script_specs_dir=project_root / "script_specs",
        logs_max_lines=2000,
        default_tail_lines=200,
    )
