# Sync Strategy

## Goal
Make different terminals and machines feel like the same assistant by giving every session the same durable memory source.

## Recommended Model
Use two layers of memory:

1. Project memory
- Canonical source: this directory, `docs/assistant-memory/`
- Sync method: the same git workflow used to sync this repository
- Scope: project facts, plans, decisions, session handoff

2. Global user memory
- Canonical source: a separate private synced location
- Suggested file: `global_user_preferences.md`
- Scope: user habits, communication preferences, recurring engineering expectations across projects

## Chosen Setup For This Workflow
The current chosen setup is:
- project memory stays in `docs/assistant-memory/`
- global user memory uses a private git repository as the canonical source
- each machine exposes that file locally as `/root/.codex/memories/global_user_preferences.md` or the equivalent home-directory path
- WPS is optional and may be used only as a backup or secondary mirror

## Best Practical Setup
For this project, the easiest way to get "the same assistant" across machines is:
- keep `docs/assistant-memory/` tracked in git
- `git pull` before starting work on another machine
- update these files during work
- `git commit` and `git push` when the memory changes matter

For this user workflow, a private git repository is the preferred sync mechanism for user-wide memory.

Alternative options remain possible:
- a synced folder such as Syncthing, iCloud Drive, Dropbox, or OneDrive
- WPS Cloud as a backup or secondary mirror
- a dotfiles repository if that is already how you manage shell/editor config
- dual-remote mirroring of the private memory repository to GitHub and Gitee

## Machine Integration
Each machine can keep a local path such as `/root/.codex/memories/global_user_preferences.md` or the equivalent user home path.

The recommended integration is a symlink:
- file in the private git clone is the real file
- local Codex memory path points to it

The important rule is not the exact path. The important rule is that every machine points to the same canonical file contents.

## Recommended Directory Layout
- Global memory repository: `codex-memory-private/`
- Canonical global file: `codex-memory-private/global_user_preferences.md`
- Repository project memory: `docs/assistant-memory/`
- Local bridge path: `/root/.codex/memories/global_user_preferences.md`
- Optional remotes: `github` and `gitee`

If a machine uses a different home directory, adapt only the local bridge path.

## Workflow
1. Open the repository on any machine.
2. Pull the latest repository changes.
3. Pull the latest changes in the private global-memory repository.
4. Ensure the local Codex path points to `global_user_preferences.md` inside that clone.
5. Start the assistant session.
6. The assistant reads project memory from `docs/assistant-memory/` and global memory if present.
7. At the end of meaningful work, update memory and push the private memory repository to both remotes.

## Conflict Rule
If project memory and global memory conflict:
- project-specific memory wins inside this repository
- global memory only fills in collaboration preferences and cross-project habits

## Operational Notes
- Avoid editing the same global memory file on multiple machines at the same time without pulling first.
- Do not store secrets in the global memory repository.
- If WPS is used as a mirror, treat git as the source of truth and WPS as secondary.
- Do not store GitHub or Gitee tokens in memory files, repo config files under version control, or setup scripts.
