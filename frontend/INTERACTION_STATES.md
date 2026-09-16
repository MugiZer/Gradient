# Interaction states and integration contracts

`src/state/gradientMachine.ts` is the sole Gradient presentation state machine. The real coding workspace is external to Gradient.

| Stage | Visible Gradient components | Entry |
| --- | --- | --- |
| idle | GradientAnchor | Initial state or dismissal |
| lesson_candidate | Anchor + LessonNudge | correction_candidate |
| lesson_open | Anchor + LessonPopover | User opens candidate |
| observer_working | Anchor + AgentTray | lesson_confirmed |
| builder_working | Anchor + AgentTray | capability_extracted |
| lesson_ready | Anchor + LessonArtifact | curriculum_compiled |
| training | Anchor + TrainingProgress | training_started |
| learned | Anchor + LearnedArtifact | training_completed |
| proof | Anchor + temporary ProofDrawer | proof_started |

Peeks, disclosure, pending requests, connection state, and errors are presentation fields; they do not create extra lifecycle stages.

## Integration boundary

Gradient is headless. A host adapter supplies developer context from the real Codex / IDE / agent harness.

Current concrete path:

```text
real Codex task
    ↓
gradient/codex/native.py
    ↓
Gradient backend + /events
    ↓
Electron companion (optional)
```

Electron never sends coding messages on the developer's behalf and never renders a duplicate transcript, composer, editor, or file tree.

Future IDE/harness integrations should replace the host-adapter layer, not the Gradient renderer.

## Electron modes

**Live** observes the connected host task and displays real backend events. Manual lesson observation uses the native connection; confirmation, training, proof, and artifact inspection use the existing backend boundaries.

**Demo** runs only inside Electron. It replays saved artifacts through native IPC and may operate without FastAPI. Demo playback never invents results or changes the underlying evidence.

There is no `/dev/ui` browser showcase and no browser product UI.

| Gradient action | Boundary |
| --- | --- |
| Observe current lesson | native host adapter / `POST /native/observe` |
| Confirm lesson | `POST /runs/{id}/confirm` |
| Dismiss | `POST /runs/{id}/dismiss` |
| Post-train | `POST /runs/{id}/training/launch` |
| Run proof | recorded held-out comparison boundary |
| Inspect artifacts | saved run/artifact endpoints |

Developer coding actions happen in the host application, not in Gradient.

## Evidence and recovery

Task counts, scores, progress, proof code, rewards, and verifier reasons come only from recorded backend artifacts/events. No compilation, training, model selection, verifier logic, or fabricated timing runs in the renderer.

Socket loss may reconnect and replay saved history. No timer pretends backend work happened. Existing frozen experiments remain immutable; code/calibration changes require a new experiment.

## Commands

From `frontend/`: `npm ci`, `npm run typecheck`, `npm test`, `npm run build`, then `npm run desktop`.

Use Electron Demo mode for UI/state inspection. `npm run dev` is only a Vite development server and is not a demo surface.

From the repository root: `uv run python -m gradient.main`, `uv run python -m unittest tests.test_frontend_contract tests.test_pipeline -q`, and `uv run ruff check gradient tests`.
