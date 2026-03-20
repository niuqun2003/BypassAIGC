# Repository Guidelines

## Project Structure & Module Organization
Primary work lives under `package/`. Use `package/backend/app/` for the FastAPI service: `routes/` holds API endpoints, `services/` contains optimization and streaming logic, `models/` defines SQLAlchemy models, and `utils/` contains helpers such as auth. Use `package/frontend/src/` for the React UI: `pages/` contains route-level screens, `components/` holds shared UI, and `api/` centralizes Axios clients. Packaging assets and entrypoints live in `package/main.py`, `package/app.spec`, `package/build.sh`, and `package/build.ps1`.

## Build, Test, and Development Commands
Run the backend locally with `uvicorn app.main:app --reload --app-dir package/backend --host 0.0.0.0 --port 8000`. Run the frontend with `cd package/frontend && npm install && npm run dev`; Vite serves on port `3000` and proxies `/api` to `http://localhost:8000`. Build the frontend with `cd package/frontend && npm run build`. Build the packaged desktop-style executable with `cd package && ./build.sh` on Linux/macOS or `cd package && .\build.ps1` on Windows.

## Coding Style & Naming Conventions
Follow existing style instead of introducing a new formatter. Python uses 4-space indentation, `snake_case` for functions/modules, and type-aware FastAPI handlers. React files use PascalCase component names such as `AdminDashboard.jsx` and `WorkspacePage.jsx`; hooks and local variables stay `camelCase`. Keep API access in `src/api/index.js`, and prefer small route/service additions over large mixed files. Tailwind utility classes are the current styling standard.

## Testing Guidelines
There is no committed first-party automated test suite yet. For backend changes, at minimum start the API and verify `/health`, `/docs`, login/card-key flows, and the affected endpoint. For frontend changes, run `npm run build` and smoke-test the relevant page in Vite. If you add automated tests, keep them close to the changed area and use clear names like `test_auth.py` or `AdminDashboard.test.jsx`.

## Commit & Pull Request Guidelines
Recent history uses short messages, often with `fix:` or `update:` prefixes and brief Chinese descriptions. Keep commits focused and descriptive, for example `fix: 修复管理员会话分页`. PRs should summarize the user-visible change, list manual verification steps, link any issue, and include screenshots for UI updates. If the change affects packaging or release output, note whether it was validated with `build.sh`, `build.ps1`, or the `v*` GitHub Actions release flow.

## Security & Configuration Tips
Do not commit `.env`, database files, build output, or `node_modules/`. Replace default `ADMIN_PASSWORD` and `SECRET_KEY` before any real deployment, and document new environment variables in `README.md`.
