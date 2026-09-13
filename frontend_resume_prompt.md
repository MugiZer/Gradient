# Frontend Worker Resume Prompt

Copy and paste the prompt below into the frontend worker.

```text
You are the Gradient frontend worker resuming an interrupted one-shot implementation.

Read AGENTS.md first, then read DESIGN.md. DESIGN.md is the canonical frontend directive for this task. Do not use hackathon_project.md as the frontend implementation source; if anything conflicts, DESIGN.md wins.

Inspect the current working tree and existing frontend/backend contracts before editing. Preserve existing work and continue from the current state; do not rebuild or overwrite completed work. If frontend/ is missing, create the small purpose-built frontend specified by DESIGN.md.

Implement the design faithfully: React + Vite + Motion, the locked component tree and file structure, centralized CSS/motion tokens, one explicit GradientStage state machine, the /dev/ui state showcase, and real FastAPI/WebSocket event wiring. Use DESIGN.md’s exact copy, component contracts, event mapping, motion rules, and visual acceptance criteria. The UI must feel like a minimal Codex workspace with an ambient Gradient control—not a dashboard—and must not contain experiment, training, or verifier logic. Do not use fake setTimeout-based agent work or invent extra top-level states.

Run the narrowest relevant frontend checks available (typecheck/lint/build/tests), fix failures caused by your changes, and verify the live event path where possible. Do not commit or push unless explicitly requested. Finish only when the requested frontend work is implemented and verified; if genuinely blocked, report the exact blocker and the smallest next action.
```
