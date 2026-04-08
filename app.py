from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction
import uvicorn


WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(
    title="AvigilanceEnv",
    description="India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
    version="1.0.0"
)

app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")

# In-memory session store (one env per session for demo)
_envs: dict = {}

@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/info")
def api_info():
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring — OpenEnv Early Warning System",
        "tasks": ["task1", "task2", "task3"],
        "status": "ready"
    }

@app.post("/reset")
def reset(task_id: str = "task1", seed: int = 42):
    try:
        env = AvigilanceEnv(task_id=task_id, seed=seed)
        _envs[task_id] = env
        obs = env.reset()
        return JSONResponse(content=obs.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
def step(action: AvigilanceAction):
    env = _envs.get(action.task_id)
    if env is None:
        raise HTTPException(status_code=400,
                           detail=f"No active episode for {action.task_id}. Call /reset first.")
    try:
        obs, reward, done, info = env.step(action)
        return JSONResponse(content={
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
def state(task_id: str = "task1"):
    env = _envs.get(task_id)
    if env is None:
        return JSONResponse(content={"status": "no_active_episode"})
    return JSONResponse(content=env.state())

@app.get("/health")
def health():
    return {"status": "healthy", "env": "AvigilanceEnv"}


@app.get("/metadata")
def metadata():
    return {
        "name": "AvigilanceEnv",
        "description": "India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
        "version": "1.0.0",
        "tasks": ["task1", "task2", "task3"],
        "walkthrough": "/#walkthrough",
    }


@app.get("/schema")
def schema():
    from environment.models import AvigilanceObservation, AvigilanceAction, AvigilanceReward
    return {
        "observation": AvigilanceObservation.model_json_schema(),
        "action": AvigilanceAction.model_json_schema(),
        "state": AvigilanceReward.model_json_schema(),
    }


@app.post("/mcp")
def mcp(payload: dict = {}):
    return {
        "jsonrpc": "2.0",
        "id": payload.get("id"),
        "result": {
            "name": "AvigilanceEnv",
            "tools": ["reset", "step", "state"],
        },
    }


@app.get("/{frontend_path:path}")
def frontend_fallback(frontend_path: str):
    if frontend_path.startswith(("api/", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")
    if frontend_path in {"reset", "step", "state", "health", "metadata", "schema", "mcp"}:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(WEB_DIR / "index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
