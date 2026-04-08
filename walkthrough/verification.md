# Verification Guide

This repository is designed to be verified in four layers.

## 1. Python tests

Run:

```bash
python -m pytest
```

Coverage focus:

- reward bounds stay strictly inside `(0, 1)`
- API contract and typed models remain valid
- inference log format stays validator-compatible

## 2. Space and API smoke test

Run locally:

```bash
python app.py
```

Then verify:

```bash
curl http://127.0.0.1:7860/health
curl -X POST "http://127.0.0.1:7860/reset?task_id=task1&seed=42"
curl "http://127.0.0.1:7860/state?task_id=task1"
```

## 3. Inference contract

Required environment variables:

```bash
API_BASE_URL
MODEL_NAME
HF_TOKEN
```

Run:

```bash
python inference.py
```

Expected behavior:

- emits only `[START]`, `[STEP]`, and `[END]` log lines
- runs tasks `task1`, `task2`, and `task3`
- prints step rewards with two decimal places
- prints final score with three decimal places

The script is resilient: if the configured model cannot be reached, it falls back to deterministic task heuristics and still completes.

## 4. Container and submission validation

Docker:

```bash
docker build -t avigilance-env .
```

Pre-submission validator:

```bash
bash scripts/validate-submission.sh https://your-space-url.hf.space .
```

The validator script checks:

- Space reachability via `/reset`
- Docker build success
- `openenv validate` success when `openenv-core` is installed