# evaluate_agent.py — Avigilance 2.0 LLM Agent Evaluation with Memory
#
# Runs the same LLM agent as inference.py across multiple episodes.
# The agent maintains a memory buffer that accumulates domain knowledge
# across episodes within each task — patterns seen, thresholds that worked,
# escalation decisions — and injects this into subsequent episode prompts.
#
# Multi-model fallback: if MODEL_NAME hits rate limits, call_llm rotates through
# FREE_MODEL_POOL automatically. The active model is sticky — once a working model
# is found it stays until it too is rate-limited. This lets the full evaluation
# run uninterrupted across all available free models simultaneously.
#
# Usage:
#   python evaluate_agent.py               # 10 episodes per task (default)
#   python evaluate_agent.py --full        # 100 / 100 / 10 episodes
#   python evaluate_agent.py --task task1  # single task
#
# Requires: API_BASE_URL and one of OPEN_ROUTER_API / HF_TOKEN / OPENAI_API_KEY in .env.

import json
import os
import sys
import argparse
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from environment.avigilance_env import AvigilanceEnv
from environment.models import (
    AvigilanceAction, FTOGradeAction, IncidentPriorityAction,
    ResourceAllocationAction
)

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")

if "openai.com" in API_BASE_URL:
    API_KEY = (os.environ.get("OPENAI_API_KEY")
               or os.environ.get("HF_TOKEN", ""))
elif "huggingface" in API_BASE_URL:
    API_KEY = os.environ.get("HF_TOKEN", "")
else:
    API_KEY = (os.environ.get("OPEN_ROUTER_API")
               or os.environ.get("HF_TOKEN")
               or os.environ.get("OPENAI_API_KEY", ""))

if not API_KEY:
    print("ERROR: No API key found. Set OPEN_ROUTER_API, HF_TOKEN, or OPENAI_API_KEY in .env.")
    sys.exit(1)

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

# Provider-aware fallback pool — rotation stays within the active endpoint.
_is_hf = "huggingface" in API_BASE_URL
_is_openai = "openai.com" in API_BASE_URL

if _is_hf:
    FREE_MODEL_POOL = [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
    ]
elif _is_openai:
    FREE_MODEL_POOL = [
        "gpt-4o-mini",
        "gpt-3.5-turbo",
    ]
else:
    FREE_MODEL_POOL = [
        "openrouter/auto",
        "google/gemma-3-27b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-3-12b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ]

_pool = [MODEL_NAME] + [m for m in FREE_MODEL_POOL if m != MODEL_NAME]
_active_idx = 0  # sticky: retains last working model across all calls


# ─── Agent Memory ─────────────────────────────────────────────────────────────

class AgentMemory:
    """
    Compact rolling memory that persists across episodes within a task.
    After each episode the agent extracts a lesson (via LLM) and stores it.
    The last MAX_ENTRIES lessons are injected into each subsequent prompt.
    This simulates a real agent that improves with experience.
    """
    MAX_ENTRIES = 8

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.entries: list[str] = []

    def add(self, lesson: str):
        self.entries.append(lesson)
        if len(self.entries) > self.MAX_ENTRIES:
            self.entries = self.entries[-self.MAX_ENTRIES:]

    def as_prompt_block(self) -> str:
        if not self.entries:
            return ""
        joined = "\n".join(f"- {e}" for e in self.entries)
        return (
            f"\n\nPRIOR EXPERIENCE (from previous episodes — use this to improve your decision):\n"
            f"{joined}"
        )


# ─── LLM helpers ─────────────────────────────────────────────────────────────

def call_llm(messages: list, retries: int = 9) -> str:
    """
    Call the LLM with automatic model rotation on rate limits.
    Tries each model in _pool up to `retries` times before rotating.
    The _active_idx is sticky — once a model works it stays until it too fails.
    """
    global _active_idx
    import time
    n = len(_pool)
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
            return content.strip()
        except Exception as e:
            err = str(e)
            is_rate = any(x in err for x in ("429", "rate limit", "rate_limit"))
            is_transient = any(x in err for x in ("502", "503", "upstream", "timeout", "empty response"))
            if is_rate or is_transient:
                next_model = _pool[(_active_idx + 1) % n]
                reason = "rate-limited" if is_rate else "bad response"
                print(f"  [{model}] {reason} — rotating to [{next_model}]")
                _active_idx += 1
                if _active_idx % n == 0:
                    time.sleep(5)
            else:
                raise
    raise RuntimeError("All models in pool exhausted after retries")


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


def extract_lesson(task_id: str, obs_summary: str, score: float) -> str:
    """Ask the LLM to distil one short lesson from this episode for future memory."""
    prompt = (
        f"You just completed one episode of {task_id} in the Avigilance aviation safety environment.\n"
        f"Episode summary: {obs_summary}\n"
        f"Score achieved: {score:.4f}\n\n"
        f"Write ONE short sentence (max 25 words) summarising the most useful lesson "
        f"for future decisions in this task. Be specific, not generic."
    )
    try:
        lesson = call_llm([{"role": "user", "content": prompt}])
        return lesson.strip().strip('"').strip("'")
    except Exception:
        return f"Episode score {score:.2f} — adjust strategy for next episode."


SYSTEM_PROMPT = (
    "You are an AI assistant supporting India's DGCA aviation safety inspectors. "
    "You surface patterns and flag risks — humans make all final decisions. "
    "Always respond with valid JSON matching the requested schema exactly."
)


# ─── Task 1 ──────────────────────────────────────────────────────────────────

def act_task1(obs, memory: AgentMemory) -> AvigilanceAction:
    fto = obs.fto_profile
    total = (fto.performance_score + fto.operational_score +
             fto.safety_score + fto.compliance_score + fto.student_support_score)

    prompt = f"""You are evaluating a Flying Training Organisation (FTO) for India's DGCA.

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
- C  : total < 50, OR >=3 incidents, OR pass_rate < 0.55{memory.as_prompt_block()}

Respond with JSON only:
{{
  "grade": "A+|A|B|C",
  "total_score": <float 0-100>,
  "risk_flags": ["high_incident_rate"|"insufficient_solo_hours"|"low_pass_rate"|"excessive_student_grievances"|"safety_critical"],
  "recommended_action": "clear|self_assessment_required|dgca_notice_issued|immediate_audit|suspension_recommended",
  "justification": "<2-3 sentence professional justification>"
}}"""

    try:
        raw = call_llm([{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}])
        parsed = parse_json(raw)
        return AvigilanceAction(task_id="task1", fto_grade_action=FTOGradeAction(**parsed))
    except Exception:
        grade = "A+" if total >= 90 else "A" if total >= 75 else "B" if total >= 50 else "C"
        action_map = {"A+": "clear", "A": "clear", "B": "self_assessment_required", "C": "dgca_notice_issued"}
        flags = []
        if fto.recent_incidents >= 3: flags.append("high_incident_rate")
        if fto.solo_hours_per_student < 20: flags.append("insufficient_solo_hours")
        if fto.pass_rate < 0.55: flags.append("low_pass_rate")
        return AvigilanceAction(task_id="task1", fto_grade_action=FTOGradeAction(
            grade=grade, total_score=round(total, 2), risk_flags=flags,
            recommended_action=action_map[grade],
            justification=f"Grade {grade} assigned based on DGCA 5-parameter rubric. Total: {round(total,2)}/100."
        ))


def obs_summary_task1(obs) -> str:
    fto = obs.fto_profile
    total = (fto.performance_score + fto.operational_score +
             fto.safety_score + fto.compliance_score + fto.student_support_score)
    return (f"FTO with total={round(total,1)}, incidents={fto.recent_incidents}, "
            f"pass_rate={fto.pass_rate}, solo_hours={fto.solo_hours_per_student}")


# ─── Task 2 ──────────────────────────────────────────────────────────────────

def act_task2(obs, memory: AgentMemory) -> AvigilanceAction:
    incidents = obs.incident_batch
    ids = [i.incident_id for i in incidents]
    inc_list = "\n".join(
        f"- id={i.incident_id} type={i.incident_type} sev={i.severity.value} "
        f"recurrence={i.recurrence_count} airport={i.airport_code} "
        f"flights_per_day={i.flights_per_day_at_airport} days_since_insp={i.days_since_last_inspection}"
        for i in incidents
    )

    prompt = f"""You are a Senior DGCA Safety Analyst. Triage {len(incidents)} aviation incidents by urgency.

Incidents:
{inc_list}

Priority guidance:
1. runway_incursion is highest risk; atc_deviation next; fdtl_violation, maintenance_lapse moderate.
2. Higher recurrence_count = higher urgency.
3. High flights_per_day airports = higher risk exposure.
4. Critical/high severity incidents with recurrence >= 2 must be escalated immediately.
5. If any (incident_type + airline) pair appears 2+ times, set pattern_detected=true.{memory.as_prompt_block()}

Respond with JSON only:
{{
  "priority_ranking": {json.dumps(ids)},
  "top_3_rationale": "<explain top 3>",
  "defer_list": ["<incident_ids safe to defer>"],
  "escalate_immediately": ["<incident_ids needing same-day response>"],
  "pattern_detected": true|false,
  "pattern_description": "<description or null>"
}}"""

    try:
        raw = call_llm([{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}])
        parsed = parse_json(raw)
        ranked = parsed.get("priority_ranking", ids)
        missing = [x for x in ids if x not in ranked]
        parsed["priority_ranking"] = ranked + missing
        return AvigilanceAction(task_id="task2",
                                incident_priority_action=IncidentPriorityAction(**parsed))
    except Exception:
        SEV = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        ranked = [i.incident_id for i in sorted(incidents,
                  key=lambda i: (SEV.get(i.severity.value, 0), i.recurrence_count), reverse=True)]
        return AvigilanceAction(task_id="task2", incident_priority_action=IncidentPriorityAction(
            priority_ranking=ranked,
            top_3_rationale="Ranked by severity and recurrence (fallback).",
            defer_list=ranked[5:],
            escalate_immediately=ranked[:1],
            pattern_detected=False,
        ))


def obs_summary_task2(obs) -> str:
    incidents = obs.incident_batch
    types = [i.incident_type for i in incidents]
    sevs = [i.severity.value for i in incidents]
    return (f"Batch of {len(incidents)} incidents: "
            f"types={list(set(types))}, severities={list(set(sevs))}")


# ─── Task 3 ──────────────────────────────────────────────────────────────────

def act_task3(obs, memory: AgentMemory) -> AvigilanceAction:
    ftos = obs.fto_audit_queue or []
    incs = obs.incident_queue or []
    capacity = obs.inspector_capacity or 2
    budget = obs.week_budget_hours or 40
    inspector_ids = [f"inspector_{j}" for j in range(capacity)]

    fto_lines = "\n".join(
        f"  - {f.fto_id}: total={round(f.performance_score+f.operational_score+f.safety_score+f.compliance_score+f.student_support_score,1)}"
        for f in ftos
    )
    inc_lines = "\n".join(
        f"  - {i.incident_id}: sev={i.severity.value} type={i.incident_type}"
        for i in incs
    )

    prompt = f"""You are allocating DGCA inspector resources for the coming week.

Available inspectors: {inspector_ids}
Week budget: {budget} hours
Max tasks per inspector: 3

FTO audit queue (C-grade FTOs, total score < 50, need 16 hrs; B-grade need 8 hrs):
{fto_lines}

Incident queue (critical=8hrs, high=6hrs, medium=4hrs, low=2hrs):
{inc_lines}

Rules:
1. Prioritise critical-severity incidents and C-grade FTOs first.
2. Do not exceed the {budget}-hour weekly budget.
3. Do not assign more than 3 tasks to any one inspector.
4. Defer what cannot be covered this week.{memory.as_prompt_block()}

Respond with JSON only:
{{
  "inspector_assignments": {{"inspector_0": ["<task_id>", ...], ...}},
  "deferred_items": ["<task_ids not assigned>"],
  "priority_rationale": "<brief explanation>",
  "predicted_risk_reduction": 0.7,
  "abstain": false,
  "abstain_reason": null
}}"""

    try:
        raw = call_llm([{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}])
        parsed = parse_json(raw)
        parsed.setdefault("abstain", False)
        parsed.setdefault("abstain_reason", None)
        parsed.setdefault("deferred_items", [])
        return AvigilanceAction(task_id="task3",
                                resource_allocation_action=ResourceAllocationAction(**parsed))
    except Exception:
        HOURS = {"critical": 8, "high": 6, "medium": 4, "low": 2}
        all_tasks = [(f.fto_id, 12) for f in ftos] + [(i.incident_id, HOURS.get(i.severity.value, 4)) for i in incs]
        assignments = {iid: [] for iid in inspector_ids}
        assigned, hours_used = set(), 0
        ti = 0
        for insp in inspector_ids:
            while ti < len(all_tasks) and len(assignments[insp]) < 3:
                tid, h = all_tasks[ti]; ti += 1
                if hours_used + h <= budget:
                    assignments[insp].append(tid); assigned.add(tid); hours_used += h
        return AvigilanceAction(task_id="task3", resource_allocation_action=ResourceAllocationAction(
            inspector_assignments=assignments,
            deferred_items=[t for t, _ in all_tasks if t not in assigned],
            priority_rationale="Greedy allocation within budget (fallback).",
            predicted_risk_reduction=0.6, abstain=False,
        ))


def obs_summary_task3(obs) -> str:
    ftos = obs.fto_audit_queue or []
    incs = obs.incident_queue or []
    critical = sum(1 for i in incs if i.severity.value == "critical")
    return (f"{len(ftos)} FTOs, {len(incs)} incidents ({critical} critical), "
            f"capacity={obs.inspector_capacity}, budget={obs.week_budget_hours}h")


# ─── Evaluation loop ─────────────────────────────────────────────────────────

def run_task(task_id: str, episodes: int, seed_offset: int,
             act_fn, summary_fn) -> dict:
    memory = AgentMemory(task_id)
    rewards = []
    print(f"\nEvaluating {task_id} ({episodes} episodes, model={MODEL_NAME})...")

    for i in range(episodes):
        seed = i + seed_offset
        env = AvigilanceEnv(task_id=task_id, seed=seed)
        obs = env.reset()
        obs_sum = summary_fn(obs)

        step_rewards = []
        done = False
        while not done:
            action = act_fn(obs, memory)
            obs, reward, done, _ = env.step(action)
            step_rewards.append(reward.score)

        episode_score = sum(step_rewards) / len(step_rewards)
        rewards.append(episode_score)

        lesson = extract_lesson(task_id, obs_sum, episode_score)
        memory.add(lesson)

        if (i + 1) % max(1, episodes // 5) == 0:
            print(f"  Episode {i+1:3d}/{episodes} | score={episode_score:.4f} | "
                  f"mean so far={np.mean(rewards):.4f} | memory={len(memory.entries)} entries")

    return {
        "task": task_id,
        "episodes": episodes,
        "mean_reward": round(float(np.mean(rewards)), 4),
        "std_reward": round(float(np.std(rewards)), 4),
        "min_reward": round(float(np.min(rewards)), 4),
        "max_reward": round(float(np.max(rewards)), 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Avigilance 2.0 LLM Agent Evaluation")
    parser.add_argument("--full", action="store_true",
                        help="Run full evaluation: 100/100/10 episodes. Default: 10/10/5.")
    parser.add_argument("--task", choices=["task1", "task2", "task3"],
                        help="Evaluate a single task only.")
    args = parser.parse_args()

    if args.full:
        episodes = {"task1": 100, "task2": 100, "task3": 10}
    else:
        episodes = {"task1": 10, "task2": 10, "task3": 5}

    task_configs = [
        ("task1", 0,   act_task1, obs_summary_task1),
        ("task2", 100, act_task2, obs_summary_task2),
        ("task3", 200, act_task3, obs_summary_task3),
    ]

    if args.task:
        task_configs = [t for t in task_configs if t[0] == args.task]

    results = []
    for task_id, seed_offset, act_fn, summary_fn in task_configs:
        result = run_task(
            task_id=task_id,
            episodes=episodes[task_id],
            seed_offset=seed_offset,
            act_fn=act_fn,
            summary_fn=summary_fn,
        )
        results.append(result)

    print("\n" + "=" * 70)
    print("Avigilance 2.0 — LLM Agent Evaluation Results")
    print(f"Model: {MODEL_NAME}")
    print("=" * 70)
    print(f"{'Task':<10} {'Episodes':>9} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
    print("-" * 70)
    for r in results:
        print(f"{r['task']:<10} {r['episodes']:>9} {r['mean_reward']:>8.4f} "
              f"{r['std_reward']:>8.4f} {r['min_reward']:>8.4f} {r['max_reward']:>8.4f}")
    if len(results) > 1:
        mean_all = round(float(np.mean([r["mean_reward"] for r in results])), 4)
        print("-" * 70)
        print(f"{'Mean (all)':<10} {'':>9} {mean_all:>8.4f}")
    print("=" * 70)
    print("\nNote: Update openenv.yaml and README.md baseline_scores with --full results.")


if __name__ == "__main__":
    main()
