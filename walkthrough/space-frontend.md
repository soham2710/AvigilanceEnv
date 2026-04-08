# Space Frontend Guide

The HF Space now serves a live frontend at the root URL.

What it does:

- Shows API health and metadata.
- Lets a reviewer reset any task directly from the Space.
- Displays the full observation payload returned by `/reset`.
- Generates a valid starter action for each task.
- Submits the action to `/step` and renders the returned reward payload.
- Fetches `/state` for the active task session.

Suggested manual flow:

1. Open the Space root URL.
2. Confirm `Health` reports `healthy`.
3. Select `task1`, keep seed `42`, and click `Reset Episode`.
4. Review the observation payload and click `Load Example Action` if needed.
5. Click `Submit Step` and verify the reward object contains values strictly between 0 and 1.
6. Repeat for `task2` and `task3`.

Reviewer shortcuts:

- `Refresh` re-checks `/health` and `/metadata`.
- `Fetch State` checks the current episode state without stepping.
- The action editor accepts raw JSON, so custom evaluator payloads can be pasted directly.