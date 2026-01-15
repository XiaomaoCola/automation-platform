from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScriptInfo(BaseModel):
    script_id: str
    entry: str  # scripts/ 下相对路径，比如 "examples/hello_sleep.py"
    description: str = ""


class CreateRunRequest(BaseModel):
    script_id: str
    params: Dict[str, Any] = Field(default_factory=dict)


class RunStatus(str, Enum):
    running = "running"
    done = "done"
    failed = "failed"
    stopped = "stopped"


class RunInfo(BaseModel):
    run_id: str
    script_id: str
    status: RunStatus
    pid: Optional[int] = None
    returncode: Optional[int] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class RunLogs(BaseModel):
    run_id: str
    lines: List[str]
    truncated: bool = False


class ScriptDetail(BaseModel):
    script_id: str
    entry: str
    description: str = ""
    cwd: Optional[str] = None
    timeout_s: Optional[float] = None
    env: Dict[str, str] = {}
    args_schema: Dict[str, Any] = {}
