# Interaction states and backend contracts

`src/state/gradientMachine.ts` is the sole Gradient stage machine. Presentation fields (peek, disclosure, pending request, error) belong to that model and never create additional stages. Codex transcript and connection status are separate client concerns.

| Stage | Visible Gradient components | Entry |
| --- | --- | --- |
| idle | GradientAnchor | Initial state or persisted dismissal |
| lesson_candidate | Anchor + LessonNudge | correction_candidate |
| lesson_open | Anchor + LessonPopover | Click the nudge or anchor |
| observer_working | Anchor + AgentTray; Observer thinking, Builder idle | lesson_confirmed |
| builder_working | Anchor + AgentTray; Observer done, Builder working | capability_extracted |
| lesson_ready | Anchor + LessonArtifact | curriculum_compiled |
| training | Anchor + TrainingProgress | training_started |
| learned | Anchor + LearnedArtifact | training_completed |
| proof | Anchor + temporary ProofDrawer | proof_started |

Observer and Builder can reveal AgentPeek on hover, focus, or click. View details opens TechnicalDetails. The anchor collapses/reopens a lesson surface; it does not change the underlying stage. Proof close returns to learned. Dismiss moves a candidate/open lesson to idle. Error text and pending actions leave the stage intact; failed training launch remains retryable from lesson_ready.

## Network path

Development: browser → Vite `/api` proxy → FastAPI. Default backend is `http://127.0.0.1:8787`; `GRADIENT_BACKEND_URL` in a local frontend env file overrides it. Host and Origin are preserved so FastAPI's existing same-origin check still applies. An optional `GRADIENT_API_TOKEN` is injected by Vite on the server side, including WebSocket upgrades; it is never a `VITE_` variable and never enters the browser bundle.

Production: `npm run build`; restart FastAPI. It serves `frontend/dist` at `/` and `/assets`, and the built client uses same-origin backend endpoints without `/api`. `/dev/ui` is unavailable in production. If API-token mode is enabled, a trusted same-origin reverse proxy must supply its authorization header for browser HTTP and WebSocket requests.

| User action | Request | Effect |
| --- | --- | --- |
| Send message | POST /interactions `{human_message, original_task, bad_agent_output}` | 202 with run_id; Codex continues and the Observer checks the interaction. The existing synchronous /worker endpoint remains compatible. |
| Teach lesson | POST /runs/{id}/confirm | Persist explicit confirmation and start lesson construction. Duplicate or dismissed confirmations return 409. |
| Dismiss | POST /runs/{id}/dismiss | Persist dismissal; no builder or training call. |
| Post-train agent | POST /runs/{id}/training/launch | Invoke the existing backend training boundary. |
| Run proof | POST /runs/{id}/compare/{task_id} | Run the backend's comparison on a recorded held-out task. |
| View details | GET /runs/{id} | Refresh the list of artifacts that actually exist. Artifact links use the existing file endpoint. |

GET /runs and GET /runs/{id} restore saved events. The client opens `/events` before loading history, buffers incoming events, merges in timestamp order, and deduplicates replay. Socket loss or `resync_required` shows Reconnect; it replays saved history before accepting new input. No timer pretends that backend work happened.

`worker_message`, `worker_event`, `worker_output`, and worker `agent_status` update the conversation. Codex app-server `item/agentMessage/delta`, `item/completed` command outputs, and file changes are forwarded from the existing runtime. These events do not drive Gradient's animation state. Completed message items replace their streamed text, preventing duplicate final responses.

## Compatibility and evidence

Canonical events map exactly as specified above. Existing logs are also understood: `learning_event_detected` maps to a candidate, `environments_compiled` / `ENVIRONMENTS_COMPILED` to lesson_ready, and `training_result` / `TRAINED` to learned. A legacy `TRAINING` state does not claim that launch succeeded; `training_started` does.

Task counts come from compiler events or recorded task specs. Scores summarize backend held-out result records, deduplicated by task ID. A score is absent until those records exist. Progress remains indeterminate without a real numeric progress event. Proof columns show backend-generated code, reward, and verifier reason; they stay pending until results arrive. No compilation, training, model selection, or verifier logic runs in the frontend.

The Observer may have already extracted the capability during ambient detection, so its post-confirmation stage can be brief. No artificial delay is added to make it look busy.

## Operational boundaries

Training launch uses the existing backend workflow. Baseline evaluation, Prime export/publish, adapter collection/deployment, and after-evaluation must be prepared through the backend's existing APIs. The UI reports missing prerequisites instead of constructing experiments or inventing scores. Starting an actual paid training run is not part of frontend verification.

The backend fingerprints its Python source in frozen manifests. Existing frozen experiments may reject evaluation after API/orchestration edits; start a new experiment rather than rewriting their hashes or evidence.

This small local client replays run logs in memory and displays the latest detected lesson as the single ambient object. Add history pagination or a separate run-selection affordance only when real usage requires it.

## Commands

From `frontend/`: `npm ci`, `npm run dev`, `npm run typecheck`, `npm test`, `npm run build`.

From the repository root: `uv run python -m gradient.main`, `uv run python -m unittest tests.test_frontend_contract tests.test_pipeline -q`, and `uv run ruff check gradient tests`.
