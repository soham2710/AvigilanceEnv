# Submission Checklist

Before submitting, confirm all of the following.

## Environment configuration

- `API_BASE_URL` is defined.
- `MODEL_NAME` is defined.
- `HF_TOKEN` is defined.

## Required repository assets

- Root-level `inference.py` exists.
- `openenv.yaml` reflects the environment metadata.
- `Dockerfile` builds from the repository root.
- `walkthrough/` contains operator and validation guidance.
- `scripts/validate-submission.sh` is present.

## Runtime behavior

- HF Space root URL loads the frontend successfully.
- `POST /reset` returns HTTP 200.
- `POST /step` accepts valid task actions.
- `GET /state` returns the current episode state.
- all task reward values remain strictly inside `(0, 1)`

## Baseline reproducibility

- `python inference.py` completes without error.
- output lines follow the exact `[START]`, `[STEP]`, `[END]` format.
- all three tasks execute.

## Validator run

- `docker build -t avigilance-env .` succeeds.
- `openenv validate` succeeds once `openenv-core` is installed.
- `scripts/validate-submission.sh <space_url> .` completes successfully.