# Workspace Agent Instructions

## Protected File

The file `.env` is user-owned and protected.

Agents must not do any of the following with `.env`:

- read it
- print it
- summarize it
- edit it
- overwrite it
- rename or move it
- delete it
- stage or commit it

If a task would require changing `.env`, stop and ask the user to make that change manually.

`.env.example` is the editable template. `.env` is off-limits.