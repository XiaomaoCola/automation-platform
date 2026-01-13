from fastapi import FastAPI
from pathlib import Path
from app.services.runner import run_script

app = FastAPI()

@app.post("/runs")
def create_run():
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "scripts" / "examples" / "hello_sleep.py"

    print("ABOUT TO RUN:", script_path)  # ✅ 加这一行

    run_id = run_script(script_path, {})
    print("RUN_ID:", run_id)            # ✅ 加这一行

    return {"run_id": run_id}
