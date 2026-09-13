# Backend Worker Resume Prompt

Copy and paste the prompt below into the backend worker.

```text
You are the Gradient backend worker resuming an interrupted one-shot implementation.

Read AGENTS.md first, then read backend.md. backend.md is the canonical backend directive for this task. Do not use hackathon_project.md as the backend implementation source; if anything conflicts, backend.md wins.

Inspect the current working tree, existing implementation, git diff, tests, and any relevant run/process state. Preserve existing work and continue from the current state; do not rebuild or overwrite completed work. Do not stop at a plan or explanation: make the implementation changes needed for a working end-to-end backend.

Stay within backend.md: keep typed Pydantic contracts, the Worker → Observer → Environment Agent → deterministic compiler → sandbox/verifier → evaluation lifecycle, real FastAPI/WebSocket events, immutable run artifacts, and Prime/Ambiguous integrations behind their existing boundaries. Ambiguous must remain optional and never block the core pipeline. Do not add a database, broker, distributed architecture, or UI/training logic to the wrong layer.

Run the narrowest relevant local tests and lint checks, fix failures caused by your changes, and expand verification when the change crosses boundaries. Do not launch paid hosted training, commit, or push unless explicitly requested. Finish only when the requested backend work is implemented and verified; if genuinely blocked, report the exact blocker and the smallest next action.
```
