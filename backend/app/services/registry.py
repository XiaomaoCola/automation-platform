from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import yaml

from app.schemas.script import ScriptInfo

logger = logging.getLogger("app.registry")


class ScriptRegistry:
    """
    Reads script_specs/*.yaml and exposes ScriptInfo list.
    Spec minimal fields:
      id: hello_sleep
      entry: examples/hello_sleep.py
      description: ...
    """

    def __init__(self, *, scripts_dir: Path, specs_dir: Path) -> None:
        self._scripts_dir = scripts_dir
        self._specs_dir = specs_dir
        self._cache: Dict[str, ScriptInfo] = {}

    def reload(self) -> None:
        self._cache.clear()
        if not self._specs_dir.exists():
            logger.warning("script_specs dir not found: %s", self._specs_dir)
            return

        for p in sorted(self._specs_dir.glob("*.yaml")):
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            script_id = str(data.get("id") or "").strip()
            entry = str(data.get("entry") or "").strip()
            desc = str(data.get("description") or "").strip()

            if not script_id or not entry:
                logger.warning("Invalid spec file (missing id/entry): %s", p)
                continue

            info = ScriptInfo(script_id=script_id, entry=entry, description=desc)
            self._cache[script_id] = info

        logger.info("Loaded %d script specs", len(self._cache))

    def list_scripts(self) -> List[ScriptInfo]:
        if not self._cache:
            self.reload()
        return list(self._cache.values())

    def get(self, script_id: str) -> ScriptInfo:
        if not self._cache:
            self.reload()
        if script_id not in self._cache:
            raise KeyError(f"Unknown script_id: {script_id}")
        return self._cache[script_id]

    def resolve_entry_path(self, entry: str) -> Path:
        """
        entry is path relative to scripts_dir.
        """
        return (self._scripts_dir / entry).resolve()
