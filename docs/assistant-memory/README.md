# Assistant Memory

This directory is the canonical long-term memory for work on this repository.

## Files
- `project_overview.md`: stable facts about the project and its goals
- `collaboration_profile.md`: how the user prefers to work with the assistant
- `current_plan.md`: the active short-horizon plan
- `decision_log.md`: decisions, rationale, and superseded choices
- `session_handoff.md`: concise state for the next session
- `sync_strategy.md`: how to keep memory consistent across machines
- `git_memory_setup.md`: recommended setup for cross-platform global memory
- `wps_setup.md`: optional WPS backup guidance

## Operating Rules
1. Read `project_overview.md`, `collaboration_profile.md`, `current_plan.md`, and `session_handoff.md` before substantial work.
2. Read `/root/.codex/memories/global_user_preferences.md` if present for cross-project user preferences.
3. Write only durable, confirmed information into long-term memory.
4. Put active work and next steps into `current_plan.md` and `session_handoff.md`.
5. Record meaningful architecture or product choices in `decision_log.md`.
6. Never store secrets, tokens, passwords, or one-off debugging noise here.

## Update Threshold
Update these files when one of the following happens:
- a requirement is confirmed
- a technical decision is made
- the working plan changes materially
- session state would otherwise be lost between terminals or machines
