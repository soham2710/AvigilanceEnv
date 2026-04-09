import json
from pathlib import Path
from typing import Any

import gradio as gr
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from environment.avigilance_env import AvigilanceEnv
from environment.models import AvigilanceAction


WEB_DIR = Path(__file__).parent / "web"
GRADIO_THEME = gr.themes.Soft(primary_hue="amber", secondary_hue="cyan", neutral_hue="slate")
GRADIO_CSS = """
    .av-shell {max-width: 1220px; margin: 0 auto;}
    .av-hero {background: linear-gradient(135deg, #143642 0%, #255957 55%, #e07a32 100%); color: #fffaf4; border-radius: 24px; padding: 28px;}
    .av-card {border: 1px solid rgba(20, 54, 66, 0.12); border-radius: 22px; background: rgba(255, 250, 244, 0.96);}
    .av-note {font-size: 0.96rem; line-height: 1.6; color: #22333b;}
"""

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


def _default_action(task_id: str, observation: dict[str, Any] | None) -> dict[str, Any]:
    if not observation:
        return {"task_id": task_id}

    if task_id == "task1" and observation.get("fto_profile"):
        fto = observation["fto_profile"]
        total = round(
            fto["performance_score"]
            + fto["operational_score"]
            + fto["safety_score"]
            + fto["compliance_score"]
            + fto["student_support_score"],
            2,
        )
        return {
            "task_id": "task1",
            "fto_grade_action": {
                "grade": "A" if total >= 75 else "B" if total >= 50 else "C",
                "total_score": total,
                "risk_flags": [],
                "recommended_action": "clear" if total >= 75 else "self_assessment_required",
                "justification": "Example action generated from the visible FTO profile in the Gradio console.",
            },
        }

    if task_id == "task2" and observation.get("incident_batch"):
        ids = [item["incident_id"] for item in observation["incident_batch"]]
        return {
            "task_id": "task2",
            "incident_priority_action": {
                "priority_ranking": ids,
                "top_3_rationale": "Example ranking generated in the Gradio console.",
                "defer_list": ids[3:],
                "escalate_immediately": ids[:2],
                "pattern_detected": False,
                "pattern_description": None,
            },
        }

    if task_id == "task3":
        incident_ids = [item["incident_id"] for item in observation.get("incident_queue", [])]
        fto_ids = [item["fto_id"] for item in observation.get("fto_audit_queue", [])]
        all_items = incident_ids + fto_ids
        return {
            "task_id": "task3",
            "resource_allocation_action": {
                "inspector_assignments": {
                    "inspector_0": all_items[:2],
                    "inspector_1": all_items[2:4],
                },
                "deferred_items": all_items[4:],
                "priority_rationale": "Example allocation generated in the Gradio console.",
                "predicted_risk_reduction": 0.55,
                "abstain": False,
                "abstain_reason": None,
            },
        }

    return {"task_id": task_id}


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


def _ui_refresh_status() -> tuple[str, str, str]:
    meta = metadata()
    active_tasks = sorted(_envs)
    session_text = ", ".join(active_tasks) if active_tasks else "No episode yet"
    return health()["status"], f"{meta['name']} v{meta['version']}", session_text


def _ui_reset_episode(task_id: str, seed: float) -> tuple[str, str, str, str, str, str]:
    observation = _reset_session(task_id=task_id, seed=int(seed))
    action = _default_action(task_id, observation)
    health_text, metadata_text, session_text = _ui_refresh_status()
    result = {
        "event": "reset",
        "task_id": task_id,
        "seed": int(seed),
        "status": "ready",
    }
    return _dump_json(observation), _dump_json(action), _dump_json(result), health_text, metadata_text, session_text


def _ui_load_example(task_id: str, observation_text: str) -> str:
    try:
        observation = json.loads(observation_text) if observation_text.strip() else None
    except json.JSONDecodeError:
        observation = None
    return _dump_json(_default_action(task_id, observation))


def _ui_submit_action(action_text: str) -> tuple[str, str, str, str, str, str]:
    try:
        payload = json.loads(action_text)
        action = AvigilanceAction.model_validate(payload)
        result = _step_session(action)
        health_text, metadata_text, active_sessions = _ui_refresh_status()
        session_text = "Episode completed" if result["done"] else "Episode active"
        return (
            _dump_json(result["observation"]),
            _dump_json(result),
            session_text,
            health_text,
            metadata_text,
            active_sessions,
        )
    except Exception as exc:
        health_text, metadata_text, active_sessions = _ui_refresh_status()
        return "", _dump_json({"error": str(exc)}), active_sessions, health_text, metadata_text, active_sessions


def _ui_fetch_state(task_id: str) -> str:
    return _dump_json(_get_state(task_id=task_id))


def _build_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="AvigilanceEnv Space Console") as demo:
        with gr.Column(elem_classes=["av-shell"]):
            gr.HTML(
                """
                <section class="av-hero">
                  <p style="margin:0; text-transform:uppercase; letter-spacing:0.16em; font-size:0.75rem; opacity:0.85;">HF Space Console</p>
                  <h1 style="margin:10px 0 12px; font-size:3.4rem; line-height:0.95;">AvigilanceEnv</h1>
                  <p style="max-width:68ch; margin:0; font-size:1.05rem; line-height:1.65;">
                    Gradio control room for DGCA safety-monitoring tasks. Reset scenarios, inspect typed observations,
                    edit raw action JSON, and submit exact environment steps without leaving the Space.
                  </p>
                </section>
                """
            )

            with gr.Row():
                health_status = gr.Textbox(label="Health", interactive=False, elem_classes=["av-card"])
                metadata_status = gr.Textbox(label="Metadata", interactive=False, elem_classes=["av-card"])
                active_sessions = gr.Textbox(label="Active Sessions", interactive=False, elem_classes=["av-card"])

            with gr.Row():
                with gr.Column(scale=3, elem_classes=["av-card"]):
                    gr.Markdown(
                        """
                        ### Interactive Environment
                        Use the controls below to run the same `/reset`, `/step`, and `/state` flows that validators call.
                        Reward fields remain strictly inside `(0, 1)` across all tasks.
                        """
                    )
                    with gr.Row():
                        task_select = gr.Dropdown(choices=["task1", "task2", "task3"], value="task1", label="Task")
                        seed_input = gr.Number(value=42, precision=0, label="Seed")
                    with gr.Row():
                        refresh_button = gr.Button("Refresh Status", variant="secondary")
                        reset_button = gr.Button("Reset Episode", variant="primary")
                        load_button = gr.Button("Load Example Action")
                        state_button = gr.Button("Fetch State")

                    observation_view = gr.Code(label="Observation", language="json", interactive=False, lines=20)
                    action_input = gr.Code(label="Action JSON", language="json", interactive=True, lines=20)
                    session_status = gr.Textbox(label="Session Status", interactive=False)
                    submit_button = gr.Button("Submit Step", variant="primary")
                    result_view = gr.Code(label="Runtime Output", language="json", interactive=False, lines=20)

                with gr.Column(scale=2, elem_classes=["av-card"]):
                    gr.Markdown(
                        """
                        ### Walkthrough
                        1. Pick a task and click `Reset Episode`.
                        2. Review the returned observation.
                        3. Load or edit a valid action payload.
                        4. Submit a step and inspect reward and state output.

                        ### Review Notes
                        - `task1` and `task2` finish in one step.
                        - `task3` can run for up to two steps.
                        - Missing action objects still serialize reward values inside the open interval.
                        """
                    )
                    gr.Markdown("<div id='walkthrough' class='av-note'>Repository docs remain available under the walkthrough folder for local verification and submission checks.</div>")

        refresh_button.click(_ui_refresh_status, outputs=[health_status, metadata_status, active_sessions])
        reset_button.click(
            _ui_reset_episode,
            inputs=[task_select, seed_input],
            outputs=[observation_view, action_input, result_view, health_status, metadata_status, active_sessions],
        ).then(lambda: "Episode ready", outputs=[session_status])
        load_button.click(_ui_load_example, inputs=[task_select, observation_view], outputs=[action_input])
        submit_button.click(
            _ui_submit_action,
            inputs=[action_input],
            outputs=[observation_view, result_view, session_status, health_status, metadata_status, active_sessions],
        )
        state_button.click(_ui_fetch_state, inputs=[task_select], outputs=[result_view])
        task_select.change(lambda task_id: _dump_json(_default_action(task_id, None)), inputs=[task_select], outputs=[action_input])
        demo.load(_ui_refresh_status, outputs=[health_status, metadata_status, active_sessions])
        demo.load(lambda: _dump_json(_default_action("task1", None)), outputs=[action_input])
        demo.load(lambda: "No episode yet", outputs=[session_status])

    return demo


demo = _build_gradio_app()
app = gr.mount_gradio_app(api_app, demo, path="/", theme=GRADIO_THEME, css=GRADIO_CSS)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
