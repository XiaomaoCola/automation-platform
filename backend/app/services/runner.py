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
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.schemas.script import RunStatus
from app.storage.state_store import InMemoryStateStore

logger = logging.getLogger("app.runner")


def params_to_cli_args(params: dict) -> list[str]:
    """
    Simple rule:
      {"x": 1, "name": "abc"} -> ["--x", "1", "--name", "abc"]
    Later you can support booleans / lists / json.
    """
    args: list[str] = []
    for k, v in (params or {}).items():
        key = str(k).strip()
        if not key:
            continue
        args.append(f"--{key}")
        args.append(str(v))
    return args


class RunnerService:
    def __init__(self, store: InMemoryStateStore) -> None:
        self._store = store
        self._procs: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def start(
        self,
        *,
        script_id: str,
        script_path: Path,
        params: dict,
        cwd: Optional[Path] = None,
        env: Optional[dict[str, str]] = None,
        timeout_s: Optional[float] = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        # 这边是生成一个全局唯一的 ID。
        # UUID（Universally Unique Identifier，全局唯一标识符）
        # UUID 的例子：4a0c693d-0a83-413e-9bbd-9064eddfaef5。
        # UUID 的特征：128 位（16 字节），十六进制字符串，分5段，用-分隔。
        # UUID 的设计目标只有一个：在不同机器、不同时刻、不同进程生成，几乎不可能撞号。

        cli_args = params_to_cli_args(params)
        cmd = [sys.executable, "-u", str(script_path), *cli_args]
        # 拼出启动命令 cmd。

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(cwd) if cwd else None,
            env={**(env or {})} if env else None,  # minimal; later merge with os.environ
        )

        with self._lock:
            self._procs[run_id] = proc
            # 把进程保存到字典里。

        self._store.create_run(run_id=run_id, script_id=script_id, pid=proc.pid)

        t = threading.Thread(
            target=self._stream_and_watch,
            args=(run_id, proc, timeout_s),
            daemon=True,
        )
        # 开一个后台线程去读输出，看超时。
        # target=self._stream_and_watch：这个线程要执行哪个函数。
        # args=(...)：给 target 函数传参数。
        # daemon=True：守护线程，主进程退出时，不会因为它还在跑而卡住退出（它会被直接干掉）。
        t.start()

        logger.info(
            "Started run %s (script_id=%s pid=%s cwd=%s timeout=%s)",
            run_id, script_id, proc.pid, cwd, timeout_s
        )
        return run_id

    def _stream_and_watch(self, run_id: str, proc: subprocess.Popen, timeout_s: Optional[float]) -> None:
        start_ts = time.time()
        try:
            if proc.stdout is None:
                self._store.append_log(run_id, "[runner] no stdout pipe\n")
            else:
                for line in proc.stdout:
                    self._store.append_log(run_id, line)

                    # timeout check while streaming
                    if timeout_s is not None and (time.time() - start_ts) > float(timeout_s):
                        self._store.append_log(run_id, "[runner] timeout reached, killing process\n")
                        self._kill_process(run_id, proc)
                        self._store.finish_run(run_id, status=RunStatus.failed, returncode=-9)
                        return

        except Exception as e:
            self._store.append_log(run_id, f"[runner] stream error: {e}\n")

        finally:
            # if already finished by timeout path, return
            if self._store.get_run(run_id) and self._store.get_run(run_id).finished_at is not None:
                self._cleanup(run_id)
                return

            proc.wait()
            rc = proc.returncode
            status = RunStatus.done if rc == 0 else RunStatus.failed
            self._store.finish_run(run_id, status=status, returncode=rc)
            self._cleanup(run_id)
            logger.info("Finished run %s (rc=%s status=%s)", run_id, rc, status)

    def stop(self, run_id: str, *, kill_after_s: float = 2.0) -> bool:
        proc = self._get_proc(run_id)
        if not proc:
            return False

        self._store.append_log(run_id, "[runner] stop requested\n")
        try:
            proc.terminate()
        except Exception as e:
            self._store.append_log(run_id, f"[runner] terminate failed: {e}\n")
            return False

        # wait a bit, then kill if still alive
        t0 = time.time()
        while time.time() - t0 < kill_after_s:
            if proc.poll() is not None:
                break
            time.sleep(0.05)

        if proc.poll() is None:
            self._store.append_log(run_id, "[runner] terminate timeout -> kill\n")
            self._kill_process(run_id, proc)
            self._store.finish_run(run_id, status=RunStatus.stopped, returncode=-9)
        else:
            self._store.finish_run(run_id, status=RunStatus.stopped, returncode=proc.returncode)

        self._cleanup(run_id)
        return True

    def _kill_process(self, run_id: str, proc: subprocess.Popen) -> None:
        try:
            proc.kill()
        except Exception as e:
            self._store.append_log(run_id, f"[runner] kill failed: {e}\n")

    def _get_proc(self, run_id: str) -> Optional[subprocess.Popen]:
        with self._lock:
            return self._procs.get(run_id)

    def _cleanup(self, run_id: str) -> None:
        with self._lock:
            self._procs.pop(run_id, None)
