# Project Overview

## Repository
- Name: `BypassAIGC`
- Primary work lives under `package/`
- Backend stack: FastAPI + SQLAlchemy + SQLite
- Frontend stack: React + Vite + Tailwind
- Packaged entrypoint: `package/main.py`

## Current Understanding
- Backend development entrypoint is `uvicorn app.main:app --reload --app-dir package/backend --host 0.0.0.0 --port 8000`
- Frontend development entrypoint is `cd package/frontend && npm run dev`
- Frontend dev proxy targets `http://localhost:8000`
- Unified packaged-style app also exists through `package/main.py`

## Working Context
- The team wants durable memory for project facts, plans, collaboration preferences, and session continuity.
- Memory should survive across terminals and, when the files are synced, across machines.

## Non-Goals
- Do not store secrets or private credentials in memory files.
- Do not treat unconfirmed ideas as stable project facts.
