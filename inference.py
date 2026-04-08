import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from environment.avigilance_env import AvigilanceEnv
from environment.models import (
    AvigilanceAction,
    FTOGradeAction,
    IncidentPriorityAction,
    ResourceAllocationAction,
)
from environment.scoring import format_open_score, normalize_open_score

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_ROUTER_API")
BENCHMARK = "avigilance-env"


def build_client() -> OpenAI:
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "missing-token")


CLIENT = build_client()


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def log_start(task: str) -> None:
    print(f"[START] task={task} env={BENCHMARK} model={MODEL_NAME}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_text = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={format_open_score(reward, decimals=2)} done={str(done).lower()} error={error_text}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_text = ",".join(format_open_score(reward, decimals=2) for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={format_open_score(score, decimals=3)} rewards={rewards_text}",
        flush=True,
    )


def maybe_generate_rationale(prompt: str) -> Optional[str]:
    if not HF_TOKEN or HF_TOKEN == "your_api_key_here":
        return None

    try:
        completion = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Respond with one concise operational sentence."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        content = (completion.choices[0].message.content or "").strip()
        return content or None
    except Exception:
        return None


def build_task1_action(obs) -> AvigilanceAction:
    fto = obs.fto_profile
    total = round(
        fto.performance_score
        + fto.operational_score
        + fto.safety_score
        + fto.compliance_score
        + fto.student_support_score,
        2,
    )

    if total >= 90 and fto.recent_incidents == 0 and fto.pass_rate >= 0.85:
        grade = "A+"
        recommended_action = "clear"
    elif total >= 75 and fto.recent_incidents <= 1 and fto.pass_rate >= 0.75:
        grade = "A"
        recommended_action = "clear"
    elif total >= 50 and fto.recent_incidents <= 3 and fto.pass_rate >= 0.60:
        grade = "B"
        recommended_action = "self_assessment_required"
    else:
        grade = "C"
        recommended_action = "immediate_audit" if fto.recent_incidents >= 3 else "dgca_notice_issued"

    risk_flags: List[str] = []
    if fto.recent_incidents >= 3:
        risk_flags.append("high_incident_rate")
    if fto.solo_hours_per_student < 15:
        risk_flags.append("insufficient_solo_hours")
    if fto.pass_rate < 0.55:
        risk_flags.append("low_pass_rate")
    if fto.grievances_last_6_months >= 5:
        risk_flags.append("excessive_student_grievances")
    if fto.safety_score < 10:
        risk_flags.append("safety_critical")

    rationale = maybe_generate_rationale(
        f"Explain a DGCA action for grade {grade}, total score {total}, incidents {fto.recent_incidents}, and pass rate {fto.pass_rate}."
    ) or f"Assigned grade {grade} from the DGCA rubric using a total score of {total} with risk flags derived from incidents, safety, pass rate, and grievances."

    return AvigilanceAction(
        task_id="task1",
        fto_grade_action=FTOGradeAction(
            grade=grade,
            total_score=total,
            risk_flags=risk_flags,
            recommended_action=recommended_action,
            justification=rationale,
        ),
    )


def compute_incident_priority(incident) -> float:
    type_base = {
        "runway_incursion": 0.95,
        "atc_deviation": 0.80,
        "fdtl_violation": 0.70,
        "technical_snag": 0.60,
        "maintenance_lapse": 0.65,
        "bird_strike": 0.50,
        "fuel_irregularity": 0.55,
        "unauthorized_access": 0.45,
    }
    severity_multiplier = {"low": 1.0, "medium": 1.15, "high": 1.30, "critical": 1.50}
    base = type_base.get(incident.incident_type, 0.5)
    recurrence_boost = min(incident.recurrence_count * 0.08, 0.25)
    traffic_boost = min(incident.flights_per_day_at_airport / 500 * 0.10, 0.10)
    inspection_penalty = min(incident.days_since_last_inspection / 180 * 0.10, 0.10)
    raw = (base + recurrence_boost + traffic_boost + inspection_penalty) * severity_multiplier[incident.severity.value]
    return round(min(raw, 1.0), 4)


def build_task2_action(obs) -> AvigilanceAction:
    incidents = list(obs.incident_batch)
    ranked_incidents = sorted(incidents, key=compute_incident_priority, reverse=True)
    ranking = [incident.incident_id for incident in ranked_incidents]
    escalate = [incident.incident_id for incident in ranked_incidents if compute_incident_priority(incident) >= 0.85]
    defer = [incident.incident_id for incident in ranked_incidents if compute_incident_priority(incident) < 0.60]

    pattern_counts: Dict[str, int] = {}
    for incident in incidents:
        key = f"{incident.incident_type}:{incident.airline}"
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
    repeated = [key for key, count in pattern_counts.items() if count >= 2]

    rationale = maybe_generate_rationale(
        f"Summarize why these incident ids are highest priority: {ranking[:3]}."
    ) or "Top incidents rank highest because their severity, recurrence, and delayed inspection windows imply the greatest operational urgency."

    return AvigilanceAction(
        task_id="task2",
        incident_priority_action=IncidentPriorityAction(
            priority_ranking=ranking,
            top_3_rationale=rationale,
            defer_list=defer,
            escalate_immediately=escalate,
            pattern_detected=bool(repeated),
            pattern_description=("Repeated operator-pattern pairs detected: " + ", ".join(repeated)) if repeated else None,
        ),
    )


def task_hours_for_fto(fto) -> int:
    total = (
        fto.performance_score
        + fto.operational_score
        + fto.safety_score
        + fto.compliance_score
        + fto.student_support_score
    )
    if total < 50:
        return 16
    if total < 70:
        return 8
    return 4


def task_hours_for_incident(incident) -> int:
    return {"critical": 8, "high": 6, "medium": 4, "low": 2}[incident.severity.value]


def build_task3_action(obs) -> AvigilanceAction:
    ftos = list(obs.fto_audit_queue or [])
    incidents = list(obs.incident_queue or [])
    inspectors = [f"inspector_{index + 1}" for index in range(obs.inspector_capacity or 2)]
    remaining_budget = obs.week_budget_hours or 40
    assignments: Dict[str, List[str]] = {inspector: [] for inspector in inspectors}

    prioritized: List[Dict[str, Any]] = []
    for incident in sorted(incidents, key=compute_incident_priority, reverse=True):
        prioritized.append({"id": incident.incident_id, "hours": task_hours_for_incident(incident)})
    for fto in sorted(ftos, key=task_hours_for_fto):
        prioritized.append({"id": fto.fto_id, "hours": task_hours_for_fto(fto)})

    deferred: List[str] = []
    inspector_index = 0
    for item in prioritized:
        assigned = False
        for _ in inspectors:
            inspector = inspectors[inspector_index % len(inspectors)]
            inspector_index += 1
            if len(assignments[inspector]) >= 3:
                continue
            if item["hours"] <= remaining_budget:
                assignments[inspector].append(item["id"])
                remaining_budget -= item["hours"]
                assigned = True
                break
        if not assigned:
            deferred.append(item["id"])

    rationale = maybe_generate_rationale(
        f"Summarize an allocation strategy for {len(ftos)} FTOs and {len(incidents)} incidents under a budget of {obs.week_budget_hours} hours."
    ) or "Allocated inspectors to the highest-risk incidents first, then used remaining hours for audit coverage without breaching per-inspector task caps."

    covered = sum(len(tasks) for tasks in assignments.values())
    total_items = len(prioritized) if prioritized else 1
    predicted_reduction = normalize_open_score(covered / total_items)

    return AvigilanceAction(
        task_id="task3",
        resource_allocation_action=ResourceAllocationAction(
            inspector_assignments=assignments,
            deferred_items=deferred,
            priority_rationale=rationale,
            predicted_risk_reduction=predicted_reduction,
            abstain=False,
            abstain_reason=None,
        ),
    )


def run_episode(task_id: str, seed: int = 42) -> float:
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    rewards: List[float] = []
    steps_taken = 0
    success = False
    score = normalize_open_score(0)

    log_start(task_id)

    try:
        obs = env.reset()
        done = False
        while not done:
            if task_id == "task1":
                action = build_task1_action(obs)
            elif task_id == "task2":
                action = build_task2_action(obs)
            else:
                action = build_task3_action(obs)

            action_text = compact_json(action.model_dump(exclude_none=True))
            error = None
            try:
                obs, reward, done, _info = env.step(action)
                rewards.append(reward.score)
                steps_taken += 1
                log_step(steps_taken, action_text, reward.score, done, error)
            except Exception as exc:
                done = True
                error = str(exc)
                rewards.append(normalize_open_score(0.0))
                steps_taken += 1
                log_step(steps_taken, action_text, normalize_open_score(0.0), done, error)

        if rewards:
            score = normalize_open_score(sum(rewards) / len(rewards))
        success = score >= 0.1
    finally:
        log_end(success, steps_taken, score, rewards)

    return score


def main() -> None:
    for task_id in ("task1", "task2", "task3"):
        run_episode(task_id, seed=42)


if __name__ == "__main__":
    main()
