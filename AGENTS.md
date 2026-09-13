# Gradient Agent Guide

Applies to the whole repository.

## Source of truth

- For backend, training, sandbox, verifier, or API work, use `backend.md` for the relevant boundaries and contracts.
- For frontend or UI work, use `DESIGN.md` for the relevant visual and interaction rules.
- Use `hackathon_project.md` and `gradient-hackathon-plan.md` for broader product and hackathon context.
- Read only the documents relevant to the requested change; do not map or reread the whole repository by default.

## Boundaries

- Keep agent-to-agent contracts as typed Pydantic models in `gradient/schemas.py`.
- Keep Codex protocol code in `gradient/codex/`, Prime code in `gradient/training/`, deterministic compilation in `gradient/curriculum/`, and untrusted execution/verification in `gradient/sandbox/`.
- Verifiers judge observable consequences, not source-code strings. Keep held-out tasks and verifier details outside the student-writable workspace.
- The frontend displays real backend events; it must not contain experiment or training logic.
- Ambiguous is optional and must never block the core pipeline.

## Verify

- Run the narrowest relevant local tests without waiting for per-step approval; expand to the full suite for cross-cutting changes.
- For Python changes, run `uv run ruff check gradient tests` when lint coverage is relevant.
- For implementation work, continue through verification, fix failures caused by the requested change, and stop when the acceptance criteria are met.

Baseline commands: `uv sync --extra dev --extra training`, `python -m pytest -q`, and `uv run ruff check gradient tests`.

Preserve existing user changes. Do not reset, revert, commit, or push unless explicitly requested.
