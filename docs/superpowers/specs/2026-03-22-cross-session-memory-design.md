# Cross-Session Memory Design

## Context

This repository already contains a file-backed memory structure under `docs/assistant-memory/` and a global memory bridge at `~/.codex/memories/global_user_preferences.md`.

The user's goal is to make assistant memory reliable across:

1. new sessions in the same repository
2. long-term personal collaboration preferences
3. different terminals and machines

The user explicitly prefers a strong-automation model rather than a lightweight manual workflow.

## Goals

- Restore project context automatically at the start of a session
- Preserve durable user preferences across repositories
- Keep project memory and global memory separated by responsibility
- Make cross-machine continuity practical through synced file-backed memory
- Reduce reliance on implicit model recall

## Non-Goals

- Do not build user-facing product memory features
- Do not store secrets, tokens, or passwords in memory files
- Do not fully automate summarization without a review boundary
- Do not mix temporary debugging noise into long-term memory

## Recommended Approach

Use a dual-layer memory model with an automation layer on top.

### Layer 1: Project Memory

Canonical location: `docs/assistant-memory/`

Scope:

- repository facts
- current execution plan
- decisions and rationale
- handoff state for the next session

This layer is synced through the repository's normal git workflow.

### Layer 2: Global User Memory

Canonical location: a private git-backed memory repository exposed locally through `~/.codex/memories/global_user_preferences.md`

Scope:

- durable communication preferences
- recurring engineering expectations
- cross-project working conventions

This layer is synced independently from the project repository and mirrored across machines.

### Layer 3: Automation Orchestration

Canonical location: repository scripts under `scripts/memory/`

Scope:

- start-of-session bootstrap
- end-of-session capture
- decision recording
- consistency and sync checks

This layer makes the other two layers operational instead of optional.

## Why This Approach

This design matches the user's three stated needs without collapsing all memory into one place.

- Project-specific facts should move with the repository
- User-wide preferences should remain independent of any single repository
- Automation should connect both layers without making either layer ambiguous

This is preferable to a project-only approach because project-only memory cannot cleanly carry cross-project preferences. It is preferable to a global-only approach because repository execution state should remain close to the codebase it describes.

## Workflow Design

### Session Start

Command: `scripts/memory/start_session.sh`

Responsibilities:

- verify required project memory files exist
- verify global memory file is available if configured
- summarize `project_overview.md`, `current_plan.md`, `session_handoff.md`, and global preferences
- print a compact startup brief to stdout for the current terminal session
- delegate full drift inspection to `status_memory.sh`

Desired outcome:

- a new session begins with a compact, durable summary rather than relying on the assistant to rediscover state ad hoc

Interface:

- inputs:
  - repository root inferred from script location
  - optional `GLOBAL_MEMORY_PATH` environment variable
  - optional `--no-global` flag to skip reading global memory
- outputs:
  - stdout only
  - no file writes in phase 1
- exit behavior:
  - `0` when the startup brief was produced
  - non-zero only when required project memory files are missing or unreadable

Compact startup brief means a terminal-readable summary with fixed sections:

- `Project Overview`
- `Current Plan`
- `Session Handoff`
- `Global Preferences` or `Global Preferences: not configured`

Phase 1 does not generate a new summary file. It reads existing memory files and prints a normalized summary to stdout.

CLI contract:

- phase 1 supports non-interactive invocation with no required arguments
- `--no-global` is optional and suppresses reading the global memory file

### Decision Capture

Command: `scripts/memory/capture_decision.sh`

Responsibilities:

- append a new decision entry to `decision_log.md`
- enforce a consistent entry structure
- optionally link the decision to the current plan when relevant

Desired outcome:

- confirmed technical and workflow decisions are captured when they happen instead of being reconstructed later

Interface:

- inputs:
  - required `--title`
  - required `--rationale`
  - optional `--status` such as `active` or `superseded`
- outputs:
  - append-only write to `docs/assistant-memory/decision_log.md`
  - short stdout confirmation with the appended title
- exit behavior:
  - `0` on successful append
  - non-zero on invalid arguments or write failure

### Session End

Command: `scripts/memory/end_session.sh`

Responsibilities:

- update `current_plan.md`
- update `session_handoff.md`
- optionally propose new durable global preferences for review
- show a summary of memory changes before sync or commit

Desired outcome:

- the next session has accurate next-step context

Interface:

- inputs:
  - required `--status-summary`
  - required `--next-step`
  - optional repeated `--open-thread`
  - optional `--propose-global-preference` text input
- outputs:
  - write updates to `current_plan.md`
  - write updates to `session_handoff.md`
  - stdout summary of changed sections
- exit behavior:
  - `0` on successful write
  - non-zero on invalid arguments, missing files, or write failure

Phase 1 should use explicit user-provided text through CLI flags. It should not infer session status automatically from chat logs or git history.

Update strategy:

- `current_plan.md` should preserve existing headings and replace only the active short-horizon execution section intended for current work
- `session_handoff.md` should preserve the document heading and replace the `Last Confirmed State`, `Next Recommended Step`, and `Open Threads` sections
- phase 1 should not append duplicate dated blocks on every run
- interactive prompts are out of scope for phase 1

### Memory Status

Command: `scripts/memory/status_memory.sh`

Responsibilities:

- check presence of required files
- check whether files are empty
- report uncommitted changes in project memory
- report whether the global memory bridge exists

Desired outcome:

- memory drift and missing setup are visible early

Interface:

- inputs:
  - repository root inferred from script location
  - optional `GLOBAL_MEMORY_PATH` environment variable
- outputs:
  - stdout status report only
- exit behavior:
  - `0` when setup is valid
  - non-zero when required files are missing, empty, or unreadable

Responsibility split with `start_session.sh`:

- `start_session.sh` prints a readable startup brief for humans
- `status_memory.sh` performs explicit validation and drift checks
- uncommitted memory changes, empty files, and global bridge validation belong to `status_memory.sh`
- `start_session.sh` may mention missing global memory in the brief, but does not perform the full validation role

## File Responsibilities

### Project Memory Files

`docs/assistant-memory/project_overview.md`

- stable repository facts
- architecture basics
- durable goals and non-goals

`docs/assistant-memory/collaboration_profile.md`

- repository-specific collaboration constraints
- local working conventions for this codebase

`docs/assistant-memory/current_plan.md`

- near-term execution plan
- current step status
- next actions

`docs/assistant-memory/session_handoff.md`

- concise restart state for the next session
- what is done, what remains, and what should happen next

`docs/assistant-memory/decision_log.md`

- confirmed decisions
- rationale
- superseded choices when applicable

### Global Memory File

`~/.codex/memories/global_user_preferences.md`

- durable personal preferences
- cross-project collaboration habits
- stable engineering expectations

## Required Files For Phase 1

The following repository files are required for phase 1 and are validated by the memory scripts:

- `docs/assistant-memory/project_overview.md`
- `docs/assistant-memory/collaboration_profile.md`
- `docs/assistant-memory/current_plan.md`
- `docs/assistant-memory/session_handoff.md`
- `docs/assistant-memory/decision_log.md`
- `docs/assistant-memory/README.md`

Validation rules:

- required files must exist and be readable
- for phase 1, "empty" means zero bytes or whitespace-only content
- `status_memory.sh` should treat any required empty file as invalid
- `decision_log.md` may contain a heading-only placeholder and still count as valid

The following file is optional in phase 1:

- `~/.codex/memories/global_user_preferences.md`

Missing optional global memory should produce a degraded-mode message, not a hard failure.

## Phase 1 Assumptions

- `scripts/memory/` does not exist yet and will be created as part of phase 1
- new shell scripts added in phase 1 should be executable
- `docs/assistant-memory/README.md` already exists and will be updated, not replaced
- the global memory bridge may or may not exist on a given machine
- phase 1 assumes global-memory git synchronization is handled manually outside these scripts

If the global memory file is not configured, phase 1 scripts should continue to work in degraded mode:

- `start_session.sh` prints `Global Preferences: not configured`
- `status_memory.sh` reports the bridge as missing
- `end_session.sh` does not attempt to write global memory
- no phase 1 script performs `git pull`, `git push`, or remote mirror management for the private memory repository

## Automation Principles

- Prefer command-triggered automation over silent background mutation
- Keep generated content structured and reviewable
- Distinguish confirmed facts from proposals
- Treat project memory as the source of truth for repository context
- Treat global memory as the source of truth for cross-project preferences
- Avoid writing directly into long-term memory from speculative analysis

## Minimum Viable Implementation

Phase 1 should implement only the smallest useful workflow:

1. `start_session.sh`
2. `end_session.sh`
3. `capture_decision.sh`
4. `status_memory.sh`
5. memory workflow documentation in `docs/assistant-memory/README.md`

Phase 1 should not attempt:

- full automatic sync to private remotes
- git hooks
- background daemons
- autonomous decision extraction from arbitrary chat logs

## Phase 1 Acceptance Checklist

- `scripts/memory/` exists in the repository with executable shell scripts
- `start_session.sh` prints the four required summary sections to stdout
- `start_session.sh` succeeds without global memory configured and clearly reports degraded mode
- `status_memory.sh` fails with a non-zero exit code if required project memory files are missing or empty
- `status_memory.sh` reports whether the global memory bridge exists
- `capture_decision.sh` appends a structured entry to `decision_log.md`
- `end_session.sh` updates `current_plan.md` and `session_handoff.md` through explicit inputs
- `docs/assistant-memory/README.md` documents the standard phase 1 workflow and the role of each script

## Future Extensions

Once the minimum workflow is stable, future work may add:

- a `sync_memory.sh` helper for the private global-memory repository
- structured templates for handoff and plan updates
- optional commit-message or recent-diff based summary assistance
- stronger machine-setup verification for the global-memory symlink

These should be added only after the base workflow proves reliable.

## Risks And Controls

### Risk: Memory Pollution

Long-term memory becomes noisy if every transient thought is recorded.

Control:

- only write durable, confirmed information
- keep active work in `current_plan.md` and `session_handoff.md`
- avoid storing debugging noise in stable files

### Risk: Responsibility Drift

The same fact may end up duplicated across project and global memory.

Control:

- project-specific context stays in repository memory
- user-wide preferences stay in global memory
- if there is a conflict, project memory wins inside this repository

### Risk: Automation Hides Errors

Heavy automation can make bad summaries look authoritative.

Control:

- prefer structured command-driven updates
- show proposed changes before they are finalized
- avoid uncontrolled background summarization in phase 1

## Success Criteria

The design is successful when:

- a fresh session can recover relevant repository state in one command
- durable user preferences remain available across repositories and machines
- end-of-session state is captured consistently enough that work does not need to be re-derived
- the workflow remains simple enough to use routinely

## Recommended Next Step

Create an implementation plan for phase 1 that adds the four memory scripts and updates the repository memory README to define the standard operating flow.
