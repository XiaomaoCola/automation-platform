# from fastapi import FastAPI
# from pathlib import Path
# from app.services.runner import run_script
#
# app = FastAPI()
#
# @app.post("/runs")
# # 上面这句代码的意思是，“当有人用 HTTP 的 POST 方法访问 /runs 这个路径时，就执行下面这个函数。”
# # .post的意思是：注册一个 POST /runs 路由。
# def create_run():
#     project_root = Path(__file__).resolve().parents[2]
#     script_path = project_root / "scripts" / "examples" / "hello_sleep.py"
#
#     print("ABOUT TO RUN:", script_path)  # ✅ 加这一行
#
#     run_id = run_script(script_path, {})
#     print("RUN_ID:", run_id)            # ✅ 加这一行
#
#     return {"run_id": run_id}

# 入口：创建 app、初始化 registry/store/runner、挂载 router。
from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.health import router as health_router
from app.api.scripts import build_router
from app.services.registry import ScriptRegistry
from app.services.runner import RunnerService
from app.storage.state_store import InMemoryStateStore


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    store = InMemoryStateStore(logs_max_lines=settings.logs_max_lines)
    registry = ScriptRegistry(scripts_dir=settings.scripts_dir, specs_dir=settings.script_specs_dir)
    runner = RunnerService(store)

    app = FastAPI(title="Automation Platform", version="0.1.0")
    app.include_router(health_router)

    scripts_router = build_router(registry=registry, runner=runner, store=store)
    app.include_router(scripts_router)

    return app


app = create_app()
