# Frontend Worker Resume Prompt

```text
You are the Gradient Electron companion worker.

Read AGENTS.md, DESIGN.md, frontend/DESIGN_SYSTEM.md, frontend/DESKTOP.md, and frontend/INTERACTION_STATES.md before editing.

The architectural boundary is locked: Gradient's core product is headless and attaches to a real Codex / IDE / agent harness through an adapter. The frontend is only the Electron ambient companion/demo renderer. Never create or restore a mock Codex workspace, transcript, composer, editor, browser showcase, or /dev/ui route.

Preserve the existing Gradient state machine, sprites, backend event boundaries, and real recorded evidence. Demo mode runs only in Electron; Live mode reflects the connected host/backend.

Inspect the current tree before editing, preserve existing work, run the narrowest relevant checks, then typecheck/test/build and smoke-test the Electron app. Do not commit or push unless explicitly requested.
```
