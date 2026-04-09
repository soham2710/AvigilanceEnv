---
title: AvigilanceEnv
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
tags:
  - openenv
  - aviation
  - safety
  - india
  - dgca
---

# AvigilanceEnv — India Aviation Safety Monitoring OpenEnv

First aviation safety monitoring OpenEnv in India. An AI agent surfaces safety patterns to human DGCA inspectors. The agent flags — humans decide.

---

## Real-World Problem

India's civil aviation safety infrastructure is under severe strain:

- **50.3% vacancy rate**: Only 843 of 1,630 sanctioned DGCA safety posts are filled.
- **3,540 safety cases** logged in 2024 alone — more than 9 per day.
- **Zero A/A+ rated FTOs**: As of September 30, 2025, not a single Flying Training Organisation in India holds a top-tier rating.
- **Air India Flight 171** (June 2025): A high-profile incident exposing systemic oversight gaps.

No existing AI system supports DGCA inspectors at scale. AvigilanceEnv is the first open benchmark for this problem.

---

## Why This Matters

India trains more pilots per year than it can safely oversee. The global standard for aviation safety AI requires:

1. Transparent reasoning — inspectors must be able to audit every flag.
2. Regulatory alignment — actions must comply with DGCA operational constraints.
3. Systemic awareness — isolated incidents mask recurring patterns across airlines and airports.

AvigilanceEnv operationalises all three requirements as measurable reward components.

---

## Theoretical Foundation

This environment is grounded in the MGURM framework (Minimal Theory of Bounded Reasoning Systems):

> Sharma, S. (2026). *A Minimal Theory of Bounded Reasoning Systems*. NARTC Technical Report, Botmartz IT Solutions, Indore.

Three safety principles map directly to MGURM axioms:

| Principle | Name | MGURM Axiom |
|-----------|------|-------------|
| P1 | Semantic State Transparency — agent state is always explicit and loggable | A1: Explicit Semantic State |
| P2 | Policy Compliance Enforcement — decisions align with DGCA regulatory rubrics | A2: Constraint-Governed Transitions |
| P3 | Temporal Consistency Tracking — systemic risks detected across patterns | A3: Local-to-Global Consistency |

---

## Tasks

| ID | Name | Difficulty | Description | Max Steps |
|----|------|-----------|-------------|-----------|
| task1 | FTO Quality Scorer | Easy | Score a Flying Training Organisation against DGCA's 5-parameter rubric and recommend an action | 1 |
| task2 | Incident Prioritiser | Medium | Rank a batch of 8-10 DGCA safety incidents by urgency and detect systemic recurrence patterns | 1 |
| task3 | Resource Allocator | Hard | Optimally dispatch 2-3 inspectors across FTO audits and incidents within a weekly hour budget | 2 |

---

## Observation Space

All observations are `AvigilanceObservation` (Pydantic v2 model):

| Field | Type | Present in | Description |
|-------|------|-----------|-------------|
| task_id | str | all | "task1", "task2", or "task3" |
| episode_step | int | all | Current step number |
| max_steps | int | all | Maximum steps for this task |
| fto_profile | FTOProfile or null | task1 | Full 5-parameter FTO profile |
| incident_batch | List[IncidentReport] or null | task2 | 8-10 incidents to triage |
| available_inspectors | int or null | task2 | Number of inspectors available |
| fto_audit_queue | List[FTOProfile] or null | task3 | FTOs queued for audit |
| incident_queue | List[IncidentReport] or null | task3 | Incidents queued for investigation |
| inspector_capacity | int or null | task3 | Number of inspectors available |
| week_budget_hours | int or null | task3 | Total available inspector-hours for the week |
| dgca_current_vacancy_pct | float | all | Real vacancy rate (0.503) |
| india_aviation_risk_level | str | all | Overall risk level ("HIGH") |
| context_note | str | all | Task-specific instructions |

---

## Action Space

All actions are submitted as `AvigilanceAction` (Pydantic v2 model).

**Task 1 — FTOGradeAction:**

| Field | Type | Description |
|-------|------|-------------|
| grade | "A+" or "A" or "B" or "C" | DGCA grade |
| total_score | float (0-100) | Computed 5-parameter total |
| risk_flags | List[str] | Identified issues (e.g. "high_incident_rate") |
| recommended_action | str | One of: clear, self_assessment_required, dgca_notice_issued, immediate_audit, suspension_recommended |
| justification | str | Professional written rationale |

**Task 2 — IncidentPriorityAction:**

| Field | Type | Description |
|-------|------|-------------|
| priority_ranking | List[str] | All incident IDs ordered by urgency (highest first) |
| top_3_rationale | str | Explanation for top-3 selection |
| defer_list | List[str] | Incident IDs safe to defer |
| escalate_immediately | List[str] | Incident IDs needing same-day response |
| pattern_detected | bool | Whether a systemic recurrence pattern exists |
| pattern_description | str or null | Description of the detected pattern |

**Task 3 — ResourceAllocationAction:**

| Field | Type | Description |
|-------|------|-------------|
| inspector_assignments | Dict[str, List[str]] | Inspector ID mapped to list of task IDs (FTO or incident) |
| deferred_items | List[str] | Task IDs not assigned this week |
| priority_rationale | str | Explanation of allocation strategy |
| predicted_risk_reduction | float (0-1) | Agent's estimate (informational only; not scored) |
| abstain | bool | Agent may abstain if scenario is genuinely unsolvable (P1) |
| abstain_reason | str or null | Required if abstain is true |

---

## Reward Function

All task rewards are normalized into the strict open interval (0, 1). In practice this repo emits scores in [0.0001, 0.9999] to satisfy validator requirements.

**Task 1:**

| Component | Weight | Criterion |
|-----------|--------|-----------|
| Grade accuracy | 40% | Exact match = 0.40; adjacent grade = 0.20 |
| Score accuracy | 20% | max(0, 1 - error/20) |
| Risk flags | 20% | Overlap against expected flags |
| Recommended action | 20% | Exact = 0.20; acceptable = 0.10 |

**Task 2:**

| Component | Weight | Criterion |
|-----------|--------|-----------|
| Top-3 accuracy | 50% | Set overlap of predicted vs true top-3 |
| Top-5 overlap | 15% | Set overlap of predicted vs true top-5 |
| Escalation F1 | 20% | F1 of escalate_immediately vs incidents scoring >= 0.85 |
| Pattern detection | 15% | Boolean match; false alarm earns 0.05 partial credit |

**Task 3:**

| Component | Weight | Criterion |
|-----------|--------|-----------|
| Budget constraint | 30% | Smooth penalty for exceeding weekly hour budget |
| Critical coverage | 50% | Fraction of critical incidents and C-grade FTOs assigned |
| Risk reduction | 20% | Computed from actual assignments (critical + high items covered) |

---

## Baseline Scores

Measured by running `evaluate_agent.py --full` with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference API (210 episodes total):

| Task | Mean Reward | Std | Episodes |
|------|------------|-----|---------|
| Task 1: FTO Quality Scorer | 0.8000 | 0.1050 | 100 |
| Task 2: Incident Prioritiser | 0.7100 | 0.1420 | 100 |
| Task 3: Resource Allocator | 0.8530 | 0.0920 | 10 |
| Mean | 0.7877 | | |

These scores match `openenv.yaml`. The agent uses a rolling memory buffer (8 entries) that accumulates domain lessons across episodes.

---

## Setup

## Space Frontend

The Hugging Face Space root URL now serves a Gradio control room for manual evaluation.

- Reset any task directly in the browser.
- Inspect the exact observation payload returned by the environment.
- Load a valid starter action for each task and submit it to `/step`.
- Check `/state`, `/health`, and metadata without leaving the Space.
- Use the same server for both the Gradio UI and the OpenEnv API endpoints.

Repository walkthrough docs live in `walkthrough/` and the validator helper script lives in `scripts/validate-submission.sh`.

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```
API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
HF_TOKEN=your_token_here
```

Any OpenAI-compatible endpoint works (HuggingFace Inference, Together, Fireworks, etc.).

### Local Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 generate_data.py
python3 app.py
```

Server starts on http://localhost:7860.

### Run Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="sk-..."
python3 inference.py
```

Produces strict `[START]`, `[STEP]`, and `[END]` stdout logs in the submission validator format.

### Run LLM Evaluation (requires API key in .env)

```bash
python3 evaluate_agent.py          # 10 episodes per task
python3 evaluate_agent.py --full   # 100 / 100 / 10 episodes
```

### Docker

```bash
docker build -t avigilance-env .
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e MODEL_NAME="gpt-4o-mini" \
  -e HF_TOKEN="your_token" \
  avigilance-env
```

Verify:
```bash
curl http://localhost:7860/health
curl -X POST "http://localhost:7860/reset?task_id=task1"
```

### Submission Validator

```bash
bash scripts/validate-submission.sh https://your-space-url.hf.space .
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Environment info |
| GET | /health | Health check |
| POST | /reset?task_id=task1&seed=42 | Start new episode |
| POST | /step | Submit action, receive reward |
| GET | /state?task_id=task1 | Current episode state |

---

## HuggingFace Space

https://huggingface.co/spaces/soham27/AvigilanceEnv

## GitHub Repository

https://github.com/soham27/AvigilanceEnv

---

## Citations

- Sharma, S. (2026). *A Minimal Theory of Bounded Reasoning Systems*. NARTC Technical Report, Botmartz IT Solutions, Indore.
- DGCA Public Notice DGCA-16017/10/2025-DFT (Sept 30, 2025) — FTO Performance Rankings.
- Parliamentary Committee: *Review of Safety in Civil Aviation Sector* (Aug 20, 2025).
- DGCA Annual Safety Report 2024 — 3,540 safety cases.

---

Built for the OpenEnv Hackathon by Scaler x Meta x HuggingFace.
Author: Soham Sharma, NARTC / Botmartz IT Solutions, Indore.
