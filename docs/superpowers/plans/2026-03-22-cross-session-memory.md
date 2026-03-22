# Cross-Session Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the phase 1 cross-session memory workflow with four shell scripts and updated repository memory documentation so new sessions can restore context, record decisions, validate setup, and write handoff state consistently.

**Architecture:** Add a small `scripts/memory/` shell toolkit that reads and updates the existing file-backed memory under `docs/assistant-memory/`. Keep project memory and global memory separate by responsibility, treat global memory as optional in phase 1, and use explicit CLI flags instead of interactive prompts or implicit summarization.

**Tech Stack:** Bash shell scripts, existing markdown memory files under `docs/assistant-memory/`, git status inspection, repo-local documentation

---

## File Structure

- Create: `scripts/memory/start_session.sh`
  - Print a normalized startup brief from required project memory files and optional global memory.
- Create: `scripts/memory/status_memory.sh`
  - Validate required files, detect empty files, inspect project-memory git status, and report global-memory bridge availability.
- Create: `scripts/memory/capture_decision.sh`
  - Append structured entries to `docs/assistant-memory/decision_log.md`.
- Create: `scripts/memory/end_session.sh`
  - Update the active plan section in `docs/assistant-memory/current_plan.md` and replace handoff sections in `docs/assistant-memory/session_handoff.md`.
- Modify: `docs/assistant-memory/README.md`
  - Document the standard phase 1 workflow and script responsibilities.
- Modify: `docs/assistant-memory/decision_log.md`
  - Add a stable heading/template if needed so validation can treat it as non-empty.
- Modify: `docs/assistant-memory/current_plan.md`
  - Add explicit replaceable markers or normalize sections if the current structure is too ambiguous for safe scripted updates.
- Modify: `docs/assistant-memory/session_handoff.md`
  - Normalize the headings that `end_session.sh` replaces if needed.
- Test: manual shell-script verification in the repository root

## Implementation Notes

- Follow the spec in `docs/superpowers/specs/2026-03-22-cross-session-memory-design.md`.
- Keep scripts POSIX-leaning Bash and ASCII-only.
- Phase 1 is non-interactive. Every script must work from CLI flags and exit codes.
- `GLOBAL_MEMORY_PATH` should override the default `~/.codex/memories/global_user_preferences.md`.
- Required project files for validation:
  - `docs/assistant-memory/project_overview.md`
  - `docs/assistant-memory/collaboration_profile.md`
  - `docs/assistant-memory/current_plan.md`
  - `docs/assistant-memory/session_handoff.md`
  - `docs/assistant-memory/decision_log.md`
  - `docs/assistant-memory/README.md`
- `start_session.sh` should validate readability of all required project files but only print the four summary sections defined in the spec.

### Task 1: Normalize Memory Files For Safe Script Updates

**Files:**
- Modify: `docs/assistant-memory/current_plan.md`
- Modify: `docs/assistant-memory/session_handoff.md`
- Modify: `docs/assistant-memory/decision_log.md`
- Test: manual inspection of the normalized markdown structure

- [ ] **Step 1: Inspect the current markdown structure and confirm which sections are safe to replace**

Run: `sed -n '1,260p' docs/assistant-memory/current_plan.md && sed -n '1,260p' docs/assistant-memory/session_handoff.md && sed -n '1,260p' docs/assistant-memory/decision_log.md`
Expected: Existing headings are visible and any missing stable section markers are identified.

- [ ] **Step 2: Write the failing validation script outline on paper before editing files**

Define the replacement contract:
- `current_plan.md` keeps the document title and uses one explicit replaceable block:
  - `<!-- MEMORY:CURRENT_PLAN:BEGIN -->`
  - `<!-- MEMORY:CURRENT_PLAN:END -->`
- `session_handoff.md` keeps the title and uses three explicit replaceable blocks:
  - `<!-- MEMORY:LAST_CONFIRMED_STATE:BEGIN -->`
  - `<!-- MEMORY:LAST_CONFIRMED_STATE:END -->`
  - `<!-- MEMORY:NEXT_RECOMMENDED_STEP:BEGIN -->`
  - `<!-- MEMORY:NEXT_RECOMMENDED_STEP:END -->`
  - `<!-- MEMORY:OPEN_THREADS:BEGIN -->`
  - `<!-- MEMORY:OPEN_THREADS:END -->`
- `decision_log.md` must remain valid even if it only contains a heading/template
- each marker pair must appear exactly once
Expected: A concrete target structure exists before scripts are written.

- [ ] **Step 3: Update the memory markdown files to use stable replaceable sections**

Edit the files so the scripts can target exact headings or explicit markers without ambiguous parsing.
Expected: The three memory files have deterministic headings/markers and remain readable to humans.

- [ ] **Step 4: Re-read the files to verify the structure is stable**

Run: `sed -n '1,260p' docs/assistant-memory/current_plan.md && sed -n '1,260p' docs/assistant-memory/session_handoff.md && sed -n '1,260p' docs/assistant-memory/decision_log.md`
Expected: The target markers appear exactly once and match the spec.

- [ ] **Step 5: Commit the normalization**

```bash
git add docs/assistant-memory/current_plan.md docs/assistant-memory/session_handoff.md docs/assistant-memory/decision_log.md
git commit -m "chore: normalize memory file structure"
```

### Task 2: Implement `status_memory.sh`

**Files:**
- Create: `scripts/memory/status_memory.sh`
- Test: manual CLI checks against existing and intentionally broken states

- [ ] **Step 1: Write the failing validation cases**

Create a checklist of expected cases:
- success when all required files exist and are non-empty
- failure when a required file is missing
- failure when a required file is whitespace-only
- success with degraded global-memory reporting when the global file is absent
Expected: Clear acceptance cases exist before implementation.

- [ ] **Step 2: Create `scripts/memory/status_memory.sh` with strict mode and shared path resolution**

Implement:
- repository-root resolution from script location
- required file list
- whitespace-only detection
- project-memory git status reporting
- optional global-memory path detection
Expected: The script exists and returns structured stdout with exit codes.

- [ ] **Step 3: Make the script executable**

Run: `chmod +x scripts/memory/status_memory.sh`
Expected: The file is executable.

- [ ] **Step 4: Run the script in the normal repository state**

Run: `bash scripts/memory/status_memory.sh`
Expected: Exit `0` if required files are valid; output reports project-memory git state and global-memory presence.

- [ ] **Step 5: Run one negative check against a temporary whitespace-only copy**

Use a temporary file or temporary renamed file within `/tmp` or a safe repo-local scratch path to confirm the script exits non-zero when a required file becomes invalid, then restore the state.
Expected: The failure mode is observed without damaging tracked files.

- [ ] **Step 6: Commit the script**

```bash
git add scripts/memory/status_memory.sh
git commit -m "feat: add memory status script"
```

### Task 3: Implement `start_session.sh`

**Files:**
- Create: `scripts/memory/start_session.sh`
- Modify: `scripts/memory/status_memory.sh` only if a tiny shared helper needs extraction and the change stays local to memory scripts
- Test: manual startup brief verification

- [ ] **Step 1: Write the failing behavioral checklist**

Define expected output sections:
- `Project Overview`
- `Current Plan`
- `Session Handoff`
- `Global Preferences` or `Global Preferences: not configured`
Expected: The output contract is explicit before implementation.

- [ ] **Step 2: Implement `scripts/memory/start_session.sh`**

Implement:
- required file readability checks
- optional `--no-global`
- optional `GLOBAL_MEMORY_PATH`
- stdout-only normalized section printing
- non-zero exit when required project files are missing or unreadable
Expected: The script prints a compact startup brief with the four required sections.

- [ ] **Step 3: Make the script executable**

Run: `chmod +x scripts/memory/start_session.sh`
Expected: The file is executable.

- [ ] **Step 4: Verify normal startup output**

Run: `bash scripts/memory/start_session.sh`
Expected: The script prints all four sections and exits `0`.

- [ ] **Step 5: Verify degraded mode without global memory**

Run: `GLOBAL_MEMORY_PATH=/tmp/nonexistent-memory.md bash scripts/memory/start_session.sh`
Expected: Exit `0` and output `Global Preferences: not configured`.

- [ ] **Step 6: Verify `--no-global` behavior**

Run: `bash scripts/memory/start_session.sh --no-global`
Expected: Exit `0` and omit file reads from the global path while still printing a global section placeholder.

- [ ] **Step 7: Commit the script**

```bash
git add scripts/memory/start_session.sh scripts/memory/status_memory.sh
git commit -m "feat: add memory session bootstrap"
```

### Task 4: Implement `capture_decision.sh`

**Files:**
- Create: `scripts/memory/capture_decision.sh`
- Modify: `docs/assistant-memory/decision_log.md` only if the final entry template needs a sample heading
- Test: manual append verification

- [ ] **Step 1: Define the exact decision entry template**

Use a concrete markdown shape such as:

```md
## 2026-03-22 - Decision Title
- Status: active
- Rationale: ...
```

Expected: Required fields and ordering are fixed before coding.

- [ ] **Step 2: Implement `scripts/memory/capture_decision.sh`**

Implement:
- required `--title`
- required `--rationale`
- optional `--status` with default `active`
- append-only write to `docs/assistant-memory/decision_log.md`
- stdout confirmation
Expected: The script appends one well-formed decision entry and exits `0`.

- [ ] **Step 3: Make the script executable**

Run: `chmod +x scripts/memory/capture_decision.sh`
Expected: The file is executable.

- [ ] **Step 4: Verify missing-argument failure**

Run: `bash scripts/memory/capture_decision.sh`
Expected: Exit non-zero with a short usage error.

- [ ] **Step 5: Verify append success**

Run: `bash scripts/memory/capture_decision.sh --title "Test decision" --rationale "Verify append behavior"`
Expected: Exit `0`, confirmation on stdout, and one appended entry in `docs/assistant-memory/decision_log.md`.

- [ ] **Step 6: Re-open the decision log and verify formatting**

Run: `sed -n '1,260p' docs/assistant-memory/decision_log.md`
Expected: The new entry matches the exact template and earlier content is preserved.

- [ ] **Step 7: Commit the script**

```bash
git add scripts/memory/capture_decision.sh docs/assistant-memory/decision_log.md
git commit -m "feat: add memory decision capture"
```

### Task 5: Implement `end_session.sh`

**Files:**
- Create: `scripts/memory/end_session.sh`
- Modify: `docs/assistant-memory/current_plan.md`
- Modify: `docs/assistant-memory/session_handoff.md`
- Test: manual write/update verification

- [ ] **Step 1: Write the failing behavioral checklist**

Define expected behavior:
- fail without `--status-summary`
- fail without `--next-step`
- support repeated `--open-thread`
- update only the targeted sections
- never append duplicate blocks
Expected: The update contract is fixed before implementation.

- [ ] **Step 2: Implement `scripts/memory/end_session.sh` with deterministic section replacement**

Implement:
- CLI flag parsing
- safe temp-file writes
- targeted marker-based replacement in `current_plan.md`
- targeted marker-based replacement in `session_handoff.md`
- optional stdout notice for `--propose-global-preference` without writing global memory in phase 1
Expected: The script updates both files deterministically and exits `0`.

- [ ] **Step 2a: Define anchor failure behavior before coding**

If any required marker is missing, duplicated, or malformed:
- print a short error naming the file and marker
- exit non-zero
- do not partially rewrite either target file
Expected: The failure mode is fixed before implementation and does not rely on guesswork.

- [ ] **Step 3: Make the script executable**

Run: `chmod +x scripts/memory/end_session.sh`
Expected: The file is executable.

- [ ] **Step 4: Verify missing-argument failures**

Run: `bash scripts/memory/end_session.sh`
Expected: Exit non-zero with a short usage error.

- [ ] **Step 5: Verify successful update with explicit inputs**

Run: `bash scripts/memory/end_session.sh --status-summary "Phase 1 memory plan written" --next-step "Implement scripts" --open-thread "Decide whether to add sync helper in phase 2"`
Expected: Exit `0`, stdout summarizes the updated sections, and the two markdown files change only in the target sections.

- [ ] **Step 6: Re-open the updated files and verify no duplicate blocks were appended**

Run: `sed -n '1,260p' docs/assistant-memory/current_plan.md && sed -n '1,260p' docs/assistant-memory/session_handoff.md`
Expected: Existing headings remain, targeted sections are replaced, and no duplicate dated blocks appear.

- [ ] **Step 7: Commit the script**

```bash
git add scripts/memory/end_session.sh docs/assistant-memory/current_plan.md docs/assistant-memory/session_handoff.md
git commit -m "feat: add memory session handoff updater"
```

### Task 6: Update Repository Memory Workflow Documentation

**Files:**
- Modify: `docs/assistant-memory/README.md`
- Test: manual documentation review against implemented commands

- [ ] **Step 1: Write the failing docs checklist**

Confirm the README must explain:
- the purpose of each script
- the standard command flow
- required vs optional files
- degraded behavior when global memory is missing
Expected: Documentation scope is explicit before editing.

- [ ] **Step 2: Update `docs/assistant-memory/README.md`**

Add a concise phase 1 operations section covering:
- `bash scripts/memory/status_memory.sh`
- `bash scripts/memory/start_session.sh`
- `bash scripts/memory/capture_decision.sh ...`
- `bash scripts/memory/end_session.sh ...`
Expected: The README describes the standard workflow and matches the implemented behavior.

- [ ] **Step 3: Re-read the README and verify command accuracy**

Run: `sed -n '1,260p' docs/assistant-memory/README.md`
Expected: The documented commands, file roles, and degraded-mode behavior match the scripts.

- [ ] **Step 4: Commit the docs update**

```bash
git add docs/assistant-memory/README.md
git commit -m "docs: document memory workflow scripts"
```

### Task 7: End-to-End Verification

**Files:**
- Test: `scripts/memory/status_memory.sh`
- Test: `scripts/memory/start_session.sh`
- Test: `scripts/memory/capture_decision.sh`
- Test: `scripts/memory/end_session.sh`
- Test: `docs/assistant-memory/README.md`

- [ ] **Step 1: Run the validation script**

Run: `bash scripts/memory/status_memory.sh`
Expected: Exit `0` and report the current project-memory state.

- [ ] **Step 2: Run the startup script**

Run: `bash scripts/memory/start_session.sh`
Expected: Exit `0` and print the normalized startup brief.

- [ ] **Step 3: Run the decision capture flow with a disposable verification entry**

Run: `bash scripts/memory/capture_decision.sh --title "Verification entry" --rationale "Verify end-to-end memory tooling" --status active`
Expected: Exit `0` and append one valid entry.

- [ ] **Step 4: Run the end-session flow with explicit test inputs**

Run: `bash scripts/memory/end_session.sh --status-summary "Memory tooling verified locally" --next-step "Decide whether to implement sync_memory.sh in phase 2" --open-thread "Review whether current_plan markers are sufficient"`
Expected: Exit `0` and update the targeted sections only.

- [ ] **Step 5: Re-run the validation and startup scripts**

Run: `bash scripts/memory/status_memory.sh && bash scripts/memory/start_session.sh`
Expected: Both commands exit `0` and reflect the new memory state.

- [ ] **Step 6: Review the final diff**

Run: `git diff -- scripts/memory docs/assistant-memory docs/superpowers/plans/2026-03-22-cross-session-memory.md`
Expected: Only the planned scripts and memory documentation/files changed.

- [ ] **Step 7: Commit the verification-backed implementation**

```bash
git add scripts/memory docs/assistant-memory
git commit -m "feat: add phase 1 cross-session memory workflow"
```
