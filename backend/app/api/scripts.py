# 这一层只做 HTTP：接收请求、调用服务、返回 schema。
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.script import CreateRunRequest, RunInfo, RunLogs, ScriptInfo
from app.services.registry import ScriptRegistry
from app.services.runner import RunnerService
from app.storage.state_store import InMemoryStateStore
from app.schemas.script import RunStatus

router = APIRouter(tags=["scripts"])


def build_router(*, registry: ScriptRegistry, runner: RunnerService, store: InMemoryStateStore) -> APIRouter:
    """
    Simple factory to close over dependencies without overusing Depends right now.
    """

    @router.get("/scripts", response_model=list[ScriptInfo])
    def list_scripts():
        return registry.list_scripts()

    @router.post("/runs", response_model=RunInfo)
    def create_run(req: CreateRunRequest):
        try:
            info = registry.get(req.script_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

        script_path = registry.resolve_entry_path(info.entry)
        if not script_path.exists():
            raise HTTPException(status_code=404, detail=f"Script file not found: {script_path}")

        run_id = runner.start(script_id=info.script_id, script_path=script_path, params=req.params)

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

        # We do not immediately mark stopped here because proc may still be exiting.
        # But you can choose to set status early:
        store.set_status(run_id, RunStatus.stopped)

        return {"ok": True, "run_id": run_id}

    return router
