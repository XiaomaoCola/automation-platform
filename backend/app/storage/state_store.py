# 这就是“后端平台的内存状态层”。先用内存，后面换 Redis 不改变上层 API 结构。
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections import deque
from threading import Lock
from typing import Deque, Dict, Optional, List

from app.schemas.script import RunStatus


@dataclass
class RunRecord:
    run_id: str
    script_id: str
    status: RunStatus
    pid: Optional[int]
    returncode: Optional[int]
    created_at: datetime
    finished_at: Optional[datetime]
    logs: Deque[str]


class InMemoryStateStore:
    """
    Single-process in-memory store.
    - Thread-safe enough for your current "subprocess + thread streaming logs" design.
    - Later: replace with RedisStateStore implementing same methods.
    """

    def __init__(self, logs_max_lines: int = 2000) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = Lock()
        self._logs_max_lines = int(logs_max_lines)

    def create_run(self, *, run_id: str, script_id: str, pid: Optional[int]) -> None:
        now = datetime.utcnow()
        with self._lock:
            self._runs[run_id] = RunRecord(
                run_id=run_id,
                script_id=script_id,
                status=RunStatus.running,
                pid=pid,
                returncode=None,
                created_at=now,
                finished_at=None,
                logs=deque(maxlen=self._logs_max_lines),
            )

    def append_log(self, run_id: str, line: str) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.logs.append(line)

    def finish_run(self, run_id: str, *, status: RunStatus, returncode: Optional[int]) -> None:
        now = datetime.utcnow()
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.status = status
            rec.returncode = returncode
            rec.finished_at = now

    def set_status(self, run_id: str, status: RunStatus) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.status = status

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> List[RunRecord]:
        with self._lock:
            return list(self._runs.values())

    def get_logs(self, run_id: str, tail: int = 200) -> tuple[list[str], bool]:
        """
        Return last N lines, with truncated indicator.
        """
        tail = max(1, int(tail))
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return [], False
            logs = list(rec.logs)
            if len(logs) <= tail:
                return logs, False
            return logs[-tail:], True
