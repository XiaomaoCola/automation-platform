import subprocess
import sys
from pathlib import Path
import uuid
import threading

RUNS = {}

def _stream_logs(run_id: str, proc: subprocess.Popen):
    try:
        for line in proc.stdout:
            print(f"[{run_id}] {line}", end="")
    finally:
        proc.wait()
        RUNS[run_id]["status"] = "done" if proc.returncode == 0 else "failed"

def run_script(script_path: Path, params: dict) -> str:
    run_id = str(uuid.uuid4())

    cmd = [sys.executable, "-u", str(script_path)]  # -u: 关闭缓冲，立刻输出
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    RUNS[run_id] = {
        "process": proc,
        "status": "running",
    }

    t = threading.Thread(target=_stream_logs, args=(run_id, proc), daemon=True)
    t.start()

    return run_id
