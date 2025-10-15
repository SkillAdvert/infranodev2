# Agent Guidelines

## Scope
- These instructions apply to the entire `infranodev2` repository unless a subdirectory introduces a more specific `AGENTS.md` file.
- Add directory-level guides when a new area (e.g., data ingestion, infrastructure scripts) needs tailored conventions.

## Repository Overview
- **FastAPI backend**: `main.py` exposes persona-scoring endpoints that use helpers under `backend/`.
- **Shared backend modules**: `backend/` contains services, schemas, and utilities consumed by the API and scripts.
- **Data ingestion & analytics**: Top-level scripts such as `fetch_network_data.py`, `fetch_tnuos_data.py`, `fetch_fiber_data/`, and `import_projects.py` handle data acquisition and ETL preparation.
- **Operational tooling**: `start_backend.py` and related helpers wire up local execution; `requirements.txt`/`runtime.txt` pin Python dependencies.
- **Docs & references**: Keep project-wide explanations in `README.md` and add deep dives under `docs/` if new components warrant them.

## Collaboration Workflow
1. **Gather context first**
   - Inspect every file you intend to modify before proposing edits; reference paths relative to the repository root.
   - Ask for additional snippets when the structure or API surface is unclear instead of guessing.
2. **Plan deliberately**
   - Describe changes with explicit insert/replace instructions anchored to surrounding code.
   - Avoid speculative refactors or interface design—only add constructs you can verify in this repo.
3. **Keep diffs focused**
   - Scope each commit/PR to the requested work. Defer opportunistic cleanup unless the task requires it or the change is trivial and nearby.
4. **Document assumptions**
   - Call out open questions, trade-offs, or skipped steps in commit messages, summaries, or PR bodies.

## Development Workflow & Tooling
- Use the pinned dependency managers:
  - **Python**: rely on `requirements.txt`/`runtime.txt`; avoid adding or upgrading packages unless explicitly requested.
  - **Node**: if a task introduces frontend tooling, use **npm** (not pnpm or yarn) because the repo standardizes on `package-lock.json`.
- Run applicable checks before completion:
  - **Backend & shared modules**: `pytest backend/tests` plus linting (`flake8` or project-specific tools) when the task touches these areas.
  - **Data/ETL scripts**: prefer idempotent smoke tests or dry runs; document sample commands or why full execution was skipped.
  - **Frontend additions (if any)**: `npm run lint` and `npm run build` when UI code is introduced or modified.
- When a command cannot run (e.g., missing credentials, long runtime), note the reason in your summary and PR description.

## Coding Standards
- Match the surrounding style of any file you edit; avoid wholesale reformatting.
- Favor small, testable functions with descriptive names. Extract helpers when logic grows beyond ~40 lines.
- Never wrap imports or large sections in blanket `try/except` blocks—catch the narrowest exception required.

### Python (FastAPI & utilities)
- Target Python 3.9+ syntax with explicit type hints and Pydantic models for request/response payloads.
- Use FastAPI dependency injection patterns already present in `main.py` and shared modules.
- Prefer the shared module-level logger (via `logging.getLogger`) over ad-hoc `print` statements.
- Keep side effects (I/O, network calls) isolated to well-defined functions to ease testing.

### Data & ETL Scripts
- Make scripts idempotent where possible and guard entry points with `if __name__ == "__main__":` for CLI execution.
- Surface configuration via arguments, environment variables, or clearly documented constants.
- Record any external data requirements, rate limits, or credentials in code comments or accompanying docs.

### Frontend (React + TypeScript)
- Use functional components with explicit `Props` interfaces or types and avoid `any` unless justified inline.
- Compose dynamic class names with the `cn` helper from `@/lib/utils` if a frontend is added.
- Keep component-specific logic and styles colocated; extract shared utilities only when reused across modules.

## Documentation Expectations
- Update `README.md` and/or `docs/` when behavior, configuration, or setup instructions change.
- Mention new API endpoints, background jobs, or data ingestion flows in accompanying documentation or summaries.

## Git & PR Process
- Use descriptive commit messages summarizing the functional change.
- Keep branches rebased and ensure the working tree is clean before hand-off.
- PR summaries must highlight functional changes and list the tests/checks that were run (or explicitly state when none were executed).
- If follow-up work is required, document it clearly in the PR description or project notes.
