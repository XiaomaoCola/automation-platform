# 这一层只做 HTTP：接收请求、调用服务、返回 schema。
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.script import CreateRunRequest, RunInfo, RunLogs, RunStatus
from app.services.registry import ScriptRegistry, ScriptSpec
from app.services.runner import RunnerService
from app.storage.state_store import InMemoryStateStore

router = APIRouter(tags=["scripts"])


def spec_to_dict(script_spec: ScriptSpec) -> dict:
    return {
        "script_id": script_spec.script_id,
        "entry": script_spec.entry,
        "description": script_spec.description,
        "cwd": script_spec.cwd,
        "timeout_s": script_spec.timeout_s,
        "env": script_spec.env or {},
        "args_schema": script_spec.args_schema or {},
    }


def build_router(*, registry: ScriptRegistry, runner: RunnerService, store: InMemoryStateStore) -> APIRouter:

    @router.get("/scripts")
    # 如果有人用浏览器 / 程序访问/scripts，比如http://127.0.0.1:8000/scripts，FastAPI 会自动帮调用 list_scripts()。
    def list_scripts():
        specs = registry.list()
        return [spec_to_dict(s) for s in specs]

    @router.post("/runs", response_model=RunInfo)
    # GET：要“看东西”
    # POST：要“干一件新事”，即启动一个新进程，也就是改变了系统状态。
    # response_model = “规定这个接口最终返回的数据长什么样”
    def create_run(req: CreateRunRequest):
        try:
            spec = registry.get(req.script_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

        script_path = registry.resolve_script_path(spec.entry)
        if not script_path.exists():
            raise HTTPException(status_code=404, detail=f"Script file not found: {script_path}")

        cwd = registry.resolve_cwd(spec.cwd)
        run_id = runner.start(
            script_id=spec.script_id,
            script_path=script_path,
            params=req.params,
            cwd=cwd,
            env=spec.env,
            timeout_s=spec.timeout_s,
        )

        rec = store.get_run(run_id)
        assert rec is not None

        return RunInfo(
            run_id=rec.run_id,
            script_id=rec.script_id,
            status=rec.status,
            pid=rec.pid,
            returncode=rec.returncode,
            created_at=rec.created_at,
            finished_at=rec.finished_at,
        )

    @router.get("/runs/{run_id}", response_model=RunInfo)
    def get_run(run_id: str):
        rec = store.get_run(run_id)
        if not rec:
            raise HTTPException(status_code=404, detail="run_id not found")

        return RunInfo(
            run_id=rec.run_id,
            script_id=rec.script_id,
            status=rec.status,
            pid=rec.pid,
            returncode=rec.returncode,
            created_at=rec.created_at,
            finished_at=rec.finished_at,
        )

    @router.get("/runs/{run_id}/logs", response_model=RunLogs)
    def get_logs(run_id: str, tail: int = Query(default=200, ge=1, le=5000)):
        rec = store.get_run(run_id)
        if not rec:
            raise HTTPException(status_code=404, detail="run_id not found")

        lines, truncated = store.get_logs(run_id, tail=tail)
        return RunLogs(run_id=run_id, lines=lines, truncated=truncated)

    @router.post("/runs/{run_id}/stop")
    def stop_run(run_id: str):
        ok = runner.stop(run_id)
        if not ok:
            raise HTTPException(status_code=404, detail="run_id not running or not found")
        return {"ok": True, "run_id": run_id}

    return router
