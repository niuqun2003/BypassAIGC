# WPS Backup Setup

## Purpose
This document defines how to use WPS Cloud as an optional backup or mirror for global assistant memory.

## Canonical Files
- Project memory: `docs/assistant-memory/`
- Canonical global memory source: private git repository
- Optional WPS mirror file: `WPS云盘/CodexMemory/global_user_preferences.md`
- Local bridge path for Codex remains the private-git-backed file, not the WPS file

## Recommended Approach
Use WPS only if you want a cloud-synced copy of the git-backed global memory file.
Do not use WPS as the primary source of truth for cross-platform Linux and Windows collaboration.

## Per-Machine Setup
1. Complete the private-git setup in `git_memory_setup.md` first.
2. Make sure WPS Cloud syncs a local folder on the machine where you want a backup copy.
3. Create the directory `CodexMemory` inside the WPS sync root if it does not already exist.
4. Copy or mirror `global_user_preferences.md` from the private git repo into the WPS location when needed.

## Helper Script
No bridge script is recommended for WPS anymore because WPS is no longer the source of truth.

## Confirmed Machine Path
Known Windows WPS local path from the user:

```text
C:\Users\niuqun2003\WPSDrive\425658975_1\WPS云盘\CodexMemory
```

## Verification
If WPS backup is enabled:
- the WPS file should match the current contents of the git-backed `global_user_preferences.md`
- the local Codex path should still resolve to the file in the private git clone, not to the WPS path

## Usage Rule
Keep cross-project preferences in the private git memory repository.
Keep repository-specific facts and plans in `docs/assistant-memory/`.
