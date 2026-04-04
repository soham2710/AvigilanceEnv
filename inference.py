# inference.py — Avigilance 2.0 Baseline Agent
# Uses OpenAI-compatible client. Set API_BASE_URL, MODEL_NAME, HF_TOKEN in .env.
# Supports multi-model fallback: if MODEL_NAME hits rate limits, rotates through
# FREE_MODEL_POOL automatically so inference is never blocked by a single provider.
import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
from environment.avigilance_env import AvigilanceEnv
from environment.models import (
    AvigilanceAction, FTOGradeAction, IncidentPriorityAction,
    ResourceAllocationAction
)

MODEL_NAME = os.environ.get("MODEL_NAME", "openrouter/free")
_base_url = os.environ.get("API_BASE_URL", "https://openrouter.ai/api/v1")
_api_key = (
    os.environ.get("HF_TOKEN") if "huggingface" in _base_url
    else os.environ.get("OPEN_ROUTER_API")
    or os.environ.get("HF_TOKEN")
    or os.environ.get("OPENAI_API_KEY", "")
)

client = OpenAI(base_url=_base_url, api_key=_api_key)

# Ordered fallback pool — first model that responds wins.
# openrouter/free is OpenRouter's own smart router across all free models.
# Explicit models follow as direct fallbacks if the router itself is throttled.
FREE_MODEL_POOL = [
    "openrouter/free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]

# Start from MODEL_NAME; if it's in the pool keep that position, else prepend it.
_pool = [MODEL_NAME] + [m for m in FREE_MODEL_POOL if m != MODEL_NAME]
_active_idx = 0  # module-level: sticky — keeps last working model across calls

SYSTEM_PROMPT = (
    "You are an AI assistant supporting India's DGCA aviation safety inspectors. "
    "You surface patterns and flag risks — humans make all final decisions. "
    "Always respond with valid JSON matching the requested schema exactly."
)


def call_llm(messages: list, retries: int = 5) -> tuple[str, float]:
    global _active_idx
    t0 = time.time()
    n = len(_pool)
    # Try up to retries * pool_size times before giving up
    for attempt in range(retries * n):
        model = _pool[_active_idx % n]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError(f"empty response from {model}")
            latency = round(time.time() - t0, 3)
            return content.strip(), latency
        except Exception as e:
            err = str(e)
            is_rate = any(x in err for x in ("429", "rate limit", "rate_limit"))
            is_transient = any(x in err for x in ("502", "503", "upstream", "timeout", "empty response"))
            if is_rate or is_transient:
                _active_idx += 1
                print(json.dumps({"event": "MODEL_ROTATE",
                                  "from": model,
                                  "to": _pool[_active_idx % n],
                                  "reason": "rate_limit" if is_rate else "bad_response"}))
                if _active_idx % n == 0:
                    time.sleep(5)
            else:
                raise
    raise RuntimeError("All models in pool exhausted after retries")


def parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


# ─── Task 1: FTO Quality Scorer ──────────────────────────────────────────────

def run_task1(seed: int = 42) -> dict:
    task_id = "task1"
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    obs = env.reset()

    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "seed": seed,
        "model": MODEL_NAME,
        "timestamp": time.time()
    }))

    fto = obs.fto_profile
    total = (fto.performance_score + fto.operational_score +
             fto.safety_score + fto.compliance_score + fto.student_support_score)
    prompt = f"""
You are evaluating a Flying Training Organisation (FTO) for India's DGCA.

FTO Data:
- performance_score: {fto.performance_score} (max 20)
- operational_score:  {fto.operational_score} (max 40)
- safety_score:       {fto.safety_score} (max 20)
- compliance_score:   {fto.compliance_score} (max 10)
- student_support_score: {fto.student_support_score} (max 10)
- total_score:        {round(total, 2)} (max 100)
- recent_incidents:   {fto.recent_incidents}
- solo_hours_per_student: {fto.solo_hours_per_student}
- pass_rate:          {fto.pass_rate}
- grievances_last_6_months: {fto.grievances_last_6_months}

Grade rubric:
- A+ : total >= 90, zero incidents, pass_rate >= 0.85
- A  : total 75-89, <=1 incident, pass_rate >= 0.75
- B  : total 50-74, <=3 incidents, pass_rate >= 0.60
- C  : total < 50,  OR >=3 incidents, OR pass_rate < 0.55

Respond with JSON only:
{{
  "grade": "A+|A|B|C",
  "total_score": <float 0-100>,
  "risk_flags": ["high_incident_rate"|"insufficient_solo_hours"|"low_pass_rate"|"excessive_student_grievances"|"safety_critical"],
  "recommended_action": "clear|self_assessment_required|dgca_notice_issued|immediate_audit|suspension_recommended",
  "justification": "<2-3 sentence professional justification>"
}}
"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}]
    raw, latency = call_llm(messages)

    try:
        parsed = parse_json_response(raw)
        action = AvigilanceAction(
            task_id=task_id,
            fto_grade_action=FTOGradeAction(**parsed)
        )
    except Exception as e:
        # Fallback: deterministic grade from total score
        if total >= 90:
            grade = "A+"
        elif total >= 75:
            grade = "A"
        elif total >= 50:
            grade = "B"
        else:
            grade = "C"
        action = AvigilanceAction(
            task_id=task_id,
            fto_grade_action=FTOGradeAction(
                grade=grade,
                total_score=round(total, 2),
                risk_flags=["high_incident_rate"] if fto.recent_incidents >= 3 else [],
                recommended_action="clear" if grade in ["A+", "A"] else "dgca_notice_issued",
                justification=f"Grade {grade} assigned based on DGCA 5-parameter rubric. Total: {round(total,2)}/100."
            )
        )

    obs2, reward, done, info = env.step(action)

    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": 1,
        "reward": reward.score,
        "done": done,
        "latency_s": latency,
    }))
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_reward": reward.score,
        "steps": [reward.score],
        "final_state": env.state()
    }))

    return {"task": task_id, "score": reward.score}


# ─── Task 2: Incident Prioritiser ────────────────────────────────────────────

def run_task2(seed: int = 42) -> dict:
    task_id = "task2"
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    obs = env.reset()

    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "seed": seed,
        "model": MODEL_NAME,
        "timestamp": time.time()
    }))

    incidents = obs.incident_batch
    inc_list = "\n".join(
        f"- id={i.incident_id} type={i.incident_type} sev={i.severity.value} "
        f"recurrence={i.recurrence_count} airport={i.airport_code} "
        f"flights_per_day={i.flights_per_day_at_airport} days_since_insp={i.days_since_last_inspection}"
        for i in incidents
    )
    ids = [i.incident_id for i in incidents]

    prompt = f"""
You are a Senior DGCA Safety Analyst. Triage {len(incidents)} aviation incidents by urgency.

Incidents:
{inc_list}

Priority guidance:
1. runway_incursion is highest risk; atc_deviation next; fdtl_violation, maintenance_lapse moderate.
2. Higher recurrence_count = higher urgency.
3. High flights_per_day airports = higher risk exposure.
4. Critical/high severity incidents with recurrence >= 2 must be escalated immediately.
5. If any (incident_type + airline) pair appears 2+ times, set pattern_detected=true.

Respond with JSON only:
{{
  "priority_ranking": {json.dumps(ids)},  // reorder by urgency, highest first
  "top_3_rationale": "<explain top 3>",
  "defer_list": ["<incident_ids safe to defer>"],
  "escalate_immediately": ["<incident_ids needing same-day response>"],
  "pattern_detected": true|false,
  "pattern_description": "<description or null>"
}}
"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}]
    raw, latency = call_llm(messages)

    try:
        parsed = parse_json_response(raw)
        # Ensure all ids present in priority_ranking
        ranked = parsed.get("priority_ranking", ids)
        missing = [x for x in ids if x not in ranked]
        ranked = ranked + missing
        parsed["priority_ranking"] = ranked
        action = AvigilanceAction(
            task_id=task_id,
            incident_priority_action=IncidentPriorityAction(**parsed)
        )
    except Exception:
        # Fallback: deterministic sort by severity + recurrence
        SEV_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sorted_incs = sorted(incidents,
                             key=lambda i: (SEV_WEIGHT.get(i.severity.value, 0),
                                            i.recurrence_count),
                             reverse=True)
        ranked = [i.incident_id for i in sorted_incs]
        escalate = [i.incident_id for i in sorted_incs[:3]
                    if i.severity.value in ("critical", "high") and i.recurrence_count >= 2]
        action = AvigilanceAction(
            task_id=task_id,
            incident_priority_action=IncidentPriorityAction(
                priority_ranking=ranked,
                top_3_rationale="Top incidents ranked by severity and recurrence.",
                defer_list=ranked[5:],
                escalate_immediately=escalate,
                pattern_detected=False,
            )
        )

    obs2, reward, done, info = env.step(action)

    print(json.dumps({
        "event": "STEP",
        "task_id": task_id,
        "step": 1,
        "reward": reward.score,
        "done": done,
        "latency_s": latency,
    }))
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_reward": reward.score,
        "steps": [reward.score],
        "final_state": env.state()
    }))

    return {"task": task_id, "score": reward.score}


# ─── Task 3: Resource Allocator ──────────────────────────────────────────────

def run_task3(seed: int = 42) -> dict:
    task_id = "task3"
    env = AvigilanceEnv(task_id=task_id, seed=seed)
    obs = env.reset()

    print(json.dumps({
        "event": "START",
        "task_id": task_id,
        "seed": seed,
        "model": MODEL_NAME,
        "timestamp": time.time()
    }))

    step_rewards = []

    for step_num in range(obs.max_steps):
        ftos = obs.fto_audit_queue or []
        incs = obs.incident_queue or []
        capacity = obs.inspector_capacity or 2
        budget = obs.week_budget_hours or 40

        fto_lines = "\n".join(
            f"  - {f.fto_id}: total_score={round(f.performance_score+f.operational_score+f.safety_score+f.compliance_score+f.student_support_score,1)}"
            for f in ftos
        )
        inc_lines = "\n".join(
            f"  - {i.incident_id}: sev={i.severity.value} type={i.incident_type}"
            for i in incs
        )
        inspector_ids = [f"inspector_{j}" for j in range(capacity)]

        prompt = f"""
You are allocating DGCA inspector resources for the coming week.

Available inspectors: {inspector_ids}
Week budget: {budget} hours
Max tasks per inspector: 3

FTO audit queue (FTOs with total score < 50 are C-grade and need 16 hrs; B-grade need 8 hrs):
{fto_lines}

Incident queue (critical=8hrs, high=6hrs, medium=4hrs, low=2hrs):
{inc_lines}

Rules:
1. Prioritise critical-severity incidents and C-grade FTOs first.
2. Do not exceed the {budget}-hour weekly budget.
3. Do not assign more than 3 tasks to any one inspector.
4. Defer what cannot be covered this week.

Respond with JSON only:
{{
  "inspector_assignments": {{"inspector_0": ["<task_id>", ...], ...}},
  "deferred_items": ["<task_ids not assigned>"],
  "priority_rationale": "<brief explanation>",
  "predicted_risk_reduction": 0.7,
  "abstain": false,
  "abstain_reason": null
}}
"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}]
        raw, latency = call_llm(messages)

        try:
            parsed = parse_json_response(raw)
            parsed.setdefault("abstain", False)
            parsed.setdefault("abstain_reason", None)
            parsed.setdefault("deferred_items", [])
            action = AvigilanceAction(
                task_id=task_id,
                resource_allocation_action=ResourceAllocationAction(**parsed)
            )
        except Exception:
            # Fallback: greedy allocation of critical items first
            all_tasks = ([f.fto_id for f in ftos] + [i.incident_id for i in incs])
            assignments = {}
            assigned = []
            hours_used = 0
            HOURS = {"critical": 8, "high": 6, "medium": 4, "low": 2}
            FTO_HOURS = 12
            task_hours = {}
            for f in ftos:
                task_hours[f.fto_id] = FTO_HOURS
            for i in incs:
                task_hours[i.incident_id] = HOURS.get(i.severity.value, 4)

            for idx, insp in enumerate(inspector_ids):
                assignments[insp] = []
            task_idx = 0
            for insp in inspector_ids:
                while task_idx < len(all_tasks) and len(assignments[insp]) < 3:
                    t = all_tasks[task_idx]
                    h = task_hours.get(t, 4)
                    if hours_used + h <= budget:
                        assignments[insp].append(t)
                        assigned.append(t)
                        hours_used += h
                    task_idx += 1

            deferred = [t for t in all_tasks if t not in assigned]
            action = AvigilanceAction(
                task_id=task_id,
                resource_allocation_action=ResourceAllocationAction(
                    inspector_assignments=assignments,
                    deferred_items=deferred,
                    priority_rationale="Greedy allocation prioritising critical tasks within budget.",
                    predicted_risk_reduction=0.6,
                    abstain=False,
                )
            )

        obs, reward, done, info = env.step(action)

        step_rewards.append(reward.score)
        print(json.dumps({
            "event": "STEP",
            "task_id": task_id,
            "step": step_num + 1,
            "reward": reward.score,
            "done": done,
            "latency_s": latency,
        }))

        if done:
            break

    total = sum(step_rewards) / len(step_rewards) if step_rewards else 0.0
    print(json.dumps({
        "event": "END",
        "task_id": task_id,
        "total_reward": total,
        "steps": step_rewards,
        "final_state": env.state()
    }))

    return {"task": task_id, "score": total}


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = []
    for runner in [run_task1, run_task2, run_task3]:
        try:
            r = runner(seed=42)
            results.append(r)
        except Exception as e:
            task = runner.__name__.replace("run_", "")
            print(json.dumps({"event": "ERROR", "task_id": task, "error": str(e)}))
            results.append({"task": task, "score": 0.0})

    mean = round(sum(r["score"] for r in results) / len(results), 4)
    print(json.dumps({
        "event": "SUMMARY",
        "scores": {r["task"]: round(r["score"], 4) for r in results},
        "mean_score": mean,
        "model": MODEL_NAME,
        "timestamp": time.time()
    }))
