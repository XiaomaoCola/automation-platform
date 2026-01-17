from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("app.registry")


@dataclass(frozen=True)
class ScriptSpec:
    script_id: str
    entry: str
    description: str
    cwd: Optional[str] = None
    timeout_s: Optional[float] = None
    env: Dict[str, str] | None = None
    args_schema: Dict[str, Any] | None = None


class ScriptRegistry:
    """
    Reads script_specs/*.yaml into ScriptSpec.
    """

    def __init__(self, *, project_root: Path, scripts_dir: Path, specs_dir: Path) -> None:
        self._project_root = project_root
        self._scripts_dir = scripts_dir
        self._specs_dir = specs_dir
        self._cache: Dict[str, ScriptSpec] = {}

    def reload(self) -> None:
        self._cache.clear()
        # .clear() 是 dict / list / set 的清空。

        logger.info("Loading specs from: %s", self._specs_dir)
        if not self._specs_dir.exists():
            logger.warning("script_specs dir not found: %s", self._specs_dir)
            return

        files = sorted(self._specs_dir.glob("*.yaml"))
        logger.info("Found %d spec files", len(files))

        for p in files:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

            script_id = str(data.get("id") or "").strip()
            entry = str(data.get("entry") or "").strip()
            desc = str(data.get("description") or "").strip()

            if not script_id or not entry:
                logger.warning("Invalid spec (missing id/entry): %s", p)
                continue

            cwd = data.get("cwd")
            timeout_s = data.get("timeout_s")
            env = data.get("env") or None
            args_schema = data.get("args_schema") or None

            spec = ScriptSpec(
                script_id=script_id,
                entry=entry,
                description=desc,
                cwd=str(cwd) if cwd else None,
                timeout_s=float(timeout_s) if timeout_s is not None else None,
                env={str(k): str(v) for k, v in dict(env).items()} if env else None,
                args_schema=dict(args_schema) if args_schema else None,
            )
            self._cache[script_id] = spec

        logger.info("Loaded %d scripts", len(self._cache))

    def list(self) -> List[ScriptSpec]:
        if not self._cache:
        # None, False, 0, "", {}, []等等所有“空容器”都是 False。
            self.reload()
        return list(self._cache.values())
        # .keys(), .values(), .items返回的是：Python 内置的、只属于 dict 的一种特殊对象。

    def get(self, script_id: str) -> ScriptSpec:
        """
        由一个script_id，直接拿到对应的ScriptSpec。

        Args:
            script_id: Unique identifier of the script.

        Returns:
            The corresponding ScriptSpec.

        Raises:
            KeyError: If the script_id is unknown.
        """
        if not self._cache:
            self.reload()
        if script_id not in self._cache:
            raise KeyError(f"Unknown script_id: {script_id}")
        return self._cache[script_id]

    def resolve_script_path(self, entry: str) -> Path:
        return (self._scripts_dir / entry).resolve()

    def resolve_cwd(self, cwd: Optional[str]) -> Optional[Path]:
    # cwd = current working directory
        if not cwd:
            return None
        # allow cwd relative to project root
        return (self._project_root / cwd).resolve()
