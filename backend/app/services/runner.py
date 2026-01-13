# import subprocess
# # subprocess 是 Python 标准库中，用来“启动和控制外部程序（子进程）”的模块。
# # Python如果想跑另一个 Python 脚本，调用系统命令（ls / dir / ping）等等，需要来启动控制子进程（child process）。
# import sys
# from pathlib import Path
# import uuid
# import threading
#
# RUNS = {}
# # 这是一个进程注册表（process registry）。
#
# def _stream_logs(run_id: str, proc: subprocess.Popen):
#     try:
#         for line in proc.stdout:
#             print(f"[{run_id}] {line}", end="")
#     finally:
#         proc.wait()
#         RUNS[run_id]["status"] = "done" if proc.returncode == 0 else "failed"
#
# def run_script(script_path: Path, params: dict) -> str:
#     run_id = str(uuid.uuid4())
#     # UUID（Universally Unique Identifier，全局唯一标识符）
#     # UUID 的例子：4a0c693d-0a83-413e-9bbd-9064eddfaef5。
#     # UUID 的特征：128 位（16 字节），十六进制字符串，分5段，用-分隔。
#     # UUID 的设计目标只有一个：在不同机器、不同时刻、不同进程生成，几乎不可能撞号。
#
#     cmd = [sys.executable, "-u", str(script_path)]  # -u: 关闭缓冲，立刻输出
#     proc = subprocess.Popen(
#         cmd,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#         bufsize=1,
#     )
#     # Popen = Process Open，含义就是“打开一个新进程”。
#     # Popen 返回的 proc 是一个 子进程控制对象。
#     # proc.pid 可以查看OS 分配的 PID   ， proc.terminate() 是软杀， proc.kill()  是强杀。
#
#     RUNS[run_id] = {
#         "process": proc,
#         "status": "running",
#     }
#
#     t = threading.Thread(target=_stream_logs, args=(run_id, proc), daemon=True)
#     t.start()
#
#     return run_id

# Runner = “如何启动进程 + 收集日志 + 更新状态 + 停止”。
# 这一层就是之前的代码升级版：不再靠 print 传日志（可保留服务端日志），而是写入 StateStore 的 log buffer，这样你才能通过 API 拉取日志。
from __future__ import annotations

import logging
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

from app.schemas.script import RunStatus
from app.storage.state_store import InMemoryStateStore

logger = logging.getLogger("app.runner")


class RunnerService:
    """
    Starts a script as a subprocess and streams its output into state_store.
    """

    def __init__(self, state_store: InMemoryStateStore) -> None:
        self._store = state_store
        # keep proc handles in-memory (single-process design)
        self._procs: Dict[str, subprocess.Popen] = {}

    def start(self, *, script_id: str, script_path: Path, params: dict) -> str:
        run_id = str(uuid.uuid4())

        # TODO: map params -> CLI args later. For now, ignore params.
        cmd = [sys.executable, "-u", str(script_path)]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self._procs[run_id] = proc
        self._store.create_run(run_id=run_id, script_id=script_id, pid=proc.pid)

        # stream logs in background thread
        t = threading.Thread(target=self._stream_output, args=(run_id, proc), daemon=True)
        t.start()

        logger.info("Started run %s (script_id=%s, pid=%s)", run_id, script_id, proc.pid)
        return run_id

    def _stream_output(self, run_id: str, proc: subprocess.Popen) -> None:
        try:
            if proc.stdout is None:
                self._store.append_log(run_id, "[runner] no stdout pipe\n")
                return

            for line in proc.stdout:
                # store raw line (already includes \n)
                self._store.append_log(run_id, line)

        except Exception as e:
            self._store.append_log(run_id, f"[runner] log stream error: {e}\n")

        finally:
            proc.wait()
            rc = proc.returncode
            status = RunStatus.done if rc == 0 else RunStatus.failed
            self._store.finish_run(run_id, status=status, returncode=rc)

            # cleanup handle
            self._procs.pop(run_id, None)
            logger.info("Finished run %s (returncode=%s, status=%s)", run_id, rc, status)

    def stop(self, run_id: str) -> bool:
        """
        Best-effort stop:
        - terminate
        - mark status stopped if process exits
        """
        proc = self._procs.get(run_id)
        if not proc:
            return False

        try:
            proc.terminate()
            self._store.append_log(run_id, "[runner] terminate requested\n")
            return True
        except Exception as e:
            self._store.append_log(run_id, f"[runner] terminate failed: {e}\n")
            return False

    def get_pid(self, run_id: str) -> Optional[int]:
        proc = self._procs.get(run_id)
        return proc.pid if proc else None
