from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction
import uvicorn

app = FastAPI(
    title="AvigilanceEnv",
    description="India Aviation Safety Monitoring OpenEnv — DGCA Early Warning System",
    version="1.0.0"
)

# In-memory session store (one env per session for demo)
_envs: dict = {}

@app.get("/")
def root():
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
    return {"status": "ok", "env": "AvigilanceEnv"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
