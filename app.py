import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction


WEB_DIR = Path(__file__).parent / "web"
INDEX_HTML = WEB_DIR / "index.html"

api_app = FastAPI(
    title="AvigilanceEnv",
    description="India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
    version="1.1.0",
)

api_app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")

_envs: dict[str, AvigilanceEnv] = {}


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _dump_json(value: Any) -> str:
    return json.dumps(_to_jsonable(value), indent=2, ensure_ascii=True)


def _reset_session(task_id: str = "task1", seed: int = 42) -> dict[str, Any]:
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    _envs[task_id] = env
    obs = env.reset()
    return obs.model_dump(mode="json")


def _step_session(action: AvigilanceAction) -> dict[str, Any]:
    env = _envs.get(action.task_id)
    if env is None:
        raise HTTPException(status_code=400, detail=f"No active episode for {action.task_id}. Call /reset first.")

    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(mode="json"),
        "reward": reward.model_dump(mode="json"),
        "done": done,
        "info": info,
    }


def _get_state(task_id: str = "task1") -> dict[str, Any]:
    env = _envs.get(task_id)
    if env is None:
        return {"status": "no_active_episode"}
    return env.state()


@api_app.get("/api/info")
def api_info() -> dict[str, Any]:
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring — OpenEnv Early Warning System",
        "tasks": ["task1", "task2", "task3"],
        "status": "ready",
    }


@api_app.post("/reset")
def reset(task_id: str = "task1", seed: int = 42) -> JSONResponse:
    try:
        return JSONResponse(content=_reset_session(task_id=task_id, seed=seed))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api_app.post("/step")
def step(action: AvigilanceAction) -> JSONResponse:
    try:
        return JSONResponse(content=_step_session(action))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@api_app.get("/state")
def state(task_id: str = "task1") -> JSONResponse:
    return JSONResponse(content=_get_state(task_id=task_id))


@api_app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "env": "AvigilanceEnv"}


@api_app.get("/metadata")
def metadata() -> dict[str, Any]:
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
        "version": "1.1.0",
        "tasks": ["task1", "task2", "task3"],
        "walkthrough": "/#walkthrough",
    }


@api_app.get("/walkthrough")
def walkthrough() -> RedirectResponse:
    return RedirectResponse(url="/#walkthrough", status_code=307)


@api_app.get("/", response_class=HTMLResponse)
def frontend() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@api_app.get("/schema")
def schema() -> dict[str, Any]:
    from environment.models import AvigilanceAction as ActionModel
    from environment.models import AvigilanceObservation, AvigilanceReward

    return {
        "observation": AvigilanceObservation.model_json_schema(),
        "action": ActionModel.model_json_schema(),
        "state": AvigilanceReward.model_json_schema(),
    }


@api_app.post("/mcp")
def mcp(payload: dict | None = None) -> dict[str, Any]:
    body = payload or {}
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {
            "name": "AvigilanceEnv",
            "tools": ["reset", "step", "state"],
        },
    }
app = api_app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
