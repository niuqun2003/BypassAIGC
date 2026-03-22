# Collaboration Profile

## User Preferences
- Keep a durable record of project context, plans, and collaboration preferences.
- Prefer continuity across different terminals and machines.
- Make memory explicit and file-backed instead of relying on implicit model recall.
- In this hyperconverged VM environment, do not start services bound only to `localhost` by default; prefer externally reachable bindings such as `0.0.0.0` unless the user explicitly requests local-only exposure.
- Prefer minimizing token usage when it does not materially reduce solution quality.
- Prefer `gpt-5.4` for brainstorming/design and `gpt-5.3-codex` for implementation/debugging when model routing is available.

## Assistant Working Style For This Repo
- Read the project memory files before substantial work.
- Keep updates concise and pragmatic.
- Distinguish clearly between confirmed facts, active hypotheses, and open questions.
- Update memory as part of normal workflow rather than as a separate cleanup step.

## Conventions
- Stable preferences belong here.
- Session-specific status belongs in `session_handoff.md`.
- Near-term execution steps belong in `current_plan.md`.
