# Decision Log

## 2026-03-20

### Decision
Use repository-tracked files under `docs/assistant-memory/` as the canonical memory for this project.

### Why
- They are reviewable, explicit, and durable.
- They can be synced across machines through the same mechanism already used to sync the repository.
- They do not depend on any hidden model state.

### Implications
- Future sessions should read these files first.
- Significant requirements, plans, and decisions should be written back here.

### Superseded Options
- Relying on implicit assistant memory only: rejected because it is not durable enough across sessions or devices.

### Decision
Use WPS Cloud as the preferred sync source for cross-project global memory.

### Why
- The user already uses WPS Cloud across devices.
- It provides a practical shared file source without changing the project repository structure.
- It allows each machine to expose the same effective global memory through a local bridge path.

### Implications
- Global user preferences should live in a WPS-synced markdown file.
- Each machine should point its local Codex memory path to the WPS-backed file.
- Repository-specific memory remains in `docs/assistant-memory/`.
- The currently known Windows machine path is `C:\Users\niuqun2003\WPSDrive\425658975_1\WPS云盘\CodexMemory`.

### Superseded Options
- Keeping global memory purely local on each machine: rejected because it would fragment continuity across devices.

### Decision
Use a private git repository as the canonical sync source for cross-project global memory.

### Why
- It works cleanly across Linux and Windows.
- It provides version history and conflict visibility.
- It avoids depending on a Windows-specific WPS local path for Linux sessions.

### Implications
- `global_user_preferences.md` should live in a private git repository cloned on every machine.
- Each machine should point its local Codex memory path to the file inside that clone.
- WPS may still be used, but only as a backup or mirror.

### Superseded Options
- Using WPS Cloud as the primary source of truth: superseded because private git is more reliable across Linux and Windows.

### Decision
Mirror the private global-memory repository to both GitHub and Gitee.

### Why
- It reduces dependence on a single hosting provider.
- It provides simple off-site redundancy without changing the local workflow.

### Implications
- The private memory repository should have two remotes, `github` and `gitee`.
- Normal update flow should push to both remotes.
- Credentials must stay outside memory files and outside version-controlled scripts.

### Superseded Options
- Storing tokens inside memory files or setup scripts: rejected for security reasons.

### Decision
Use a GitHub fork plus Pull Request workflow when the upstream repository does not grant direct push access to the current account.

### Why
- The current GitHub account `niuqun2003` can authenticate successfully but cannot push directly to `sut-qi/BypassAIGC`.
- A fork-based workflow still allows branch publication, review, and PR creation without requiring upstream write access.
- It keeps the local merge and verification workflow intact while preserving a standard GitHub review path.

### Implications
- GitHub feature branches may need to be pushed to `niuqun2003/BypassAIGC` instead of the upstream repo.
- PR creation should target `sut-qi/BypassAIGC:main` from the fork branch.
- Direct upstream push attempts should be treated as permission-sensitive and verified before relying on them.

### Superseded Options
- Assuming direct push access to the upstream GitHub repository: rejected because the server returned `403` for `niuqun2003`.
