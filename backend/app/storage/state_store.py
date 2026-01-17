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
    # datetime是表示“具体的时间点”，不是字符串，不是数字，是一个专门表示时间的对象。
    # 可以用字符串表示时间，但是字符串不好算。delta = finished_at - created_at，用这个公式可以直接算运行了多久。
    finished_at: Optional[datetime]
    logs: Deque[str]
    # deque 是一个“为频繁追加而生的容器”，可以把它理解成：“更适合当日志缓冲区的 list”。
    # 如果用普通的list的话，可能会无限长，删前面的很慢。
    # logs = deque(maxlen=2000)的意思是：最多只保留 2000 行，新日志进来的话自动丢掉最旧的。


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
        # 记录“现在时间”，用 UTC（统一标准时间）。以后服务器在哪个时区都不乱。
        with self._lock:
        # 这边表示：“从这里开始，到缩进结束，这一小段代码， 同一时间只能有一个线程执行”。
        # 保护共享数据 self._runs 不被多个线程同时乱改。
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
    # 给某个 run_id，追加一行日志（字符串）。
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.logs.append(line)
            # .append() 不是 list 专属的方法，
            # deque 故意设计成“长得像 list、用起来也像 list”。

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
