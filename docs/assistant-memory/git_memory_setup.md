# Private Git Memory Setup

## Purpose
This document defines the recommended cross-platform setup for global assistant memory.

## Canonical Sources
- Project memory: `docs/assistant-memory/`
- Global memory: a private git repository cloned on every machine
- Local bridge path for Codex on Linux: `~/.codex/memories/global_user_preferences.md`
- Local bridge path for Codex on Windows: `%USERPROFILE%\.codex\memories\global_user_preferences.md`

## Recommended Repository Layout
Suggested private repository name:
- `codex-memory-private`

Suggested files:
- `global_user_preferences.md`
- `global_working_rules.md`
- `projects/BypassAIGC-summary.md`

Only `global_user_preferences.md` is required for the current workflow.

## Recommended Backup Topology
Use one private repository with two remotes:
- `github`: primary or equal mirror
- `gitee`: secondary or equal mirror

The file contents should be identical across both remotes.

## Per-Machine Setup
1. Clone the private memory repository on that machine.
2. Choose the file `global_user_preferences.md` inside the clone as the canonical global-memory file.
3. Point the local Codex memory path to that file with a symlink.
4. Pull before starting work on a new machine.
5. Commit and push meaningful memory updates after work.
6. Push to both remotes after each meaningful update.

## Linux Example

```bash
git clone <private-memory-repo-url> ~/codex-memory-private
bash scripts/link_global_memory_to_repo.sh "$HOME/codex-memory-private/global_user_preferences.md"
```

## Windows Example

```powershell
git clone <private-memory-repo-url> $HOME\codex-memory-private
powershell -ExecutionPolicy Bypass -File .\scripts\link_global_memory_to_repo.ps1 "$HOME\codex-memory-private\global_user_preferences.md"
```

## Helper Scripts
Use:

```bash
bash scripts/link_global_memory_to_repo.sh "/path/to/codex-memory-private/global_user_preferences.md"
```

Or on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\link_global_memory_to_repo.ps1 "C:\path\to\codex-memory-private\global_user_preferences.md"
```

To sync both remotes from inside the private memory repository:

```bash
bash /root/Projects/BypassAIGC/scripts/push_memory_mirrors.sh
```

## Verification
After setup:
- the local Codex memory path should resolve to the file in the private git clone
- editing either path should change the same file
- `git status` in the private memory repo should show your edits
- `git remote -v` should show both `github` and `gitee`

## Security Rule
- Never paste personal access tokens into project memory, global memory, repository files, or shell history on shared machines.
- Prefer SSH remotes or a local credential manager.
- If a token was pasted into chat or a terminal transcript, treat it as exposed and rotate it.

## Usage Rule
Keep cross-project preferences in the private git memory repository.
Keep repository-specific facts and plans in `docs/assistant-memory/`.
