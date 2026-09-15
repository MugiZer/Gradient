# Gradient desktop companion

The desktop mode follows the user's updated direction: a transparent native window fixed at the bottom-right of the primary display, above ordinary app windows. There is no browser tab, duplicate Codex transcript, or composer. Click the 32px sprite for details; lesson candidates, agents, artifacts, and proof reuse the existing Gradient components and nine-stage reducer. Empty pixels pass mouse input to the app below. Right-click the sprite or use the Windows tray icon to show, hide, or quit.

The initial version is anchored, not draggable. The proof drawer temporarily expands across the display; closing it restores the small companion. Display work-area changes reposition the window above the taskbar.

The companion restores its topmost flag, visibility, and work-area bounds after unintended window changes, with a two-second recovery check. It shows without taking keyboard focus. Hide Gradient and Quit Gradient remain explicit opt-outs; tray Show or relaunching Electron shows it again. An OS-level window close is swallowed and re-shows the sprite instead — only Quit ends the process, so in-app close buttons (proof, details, peeks, dismissals) can never kill the companion or require a redeploy. Renderer crashes and unresponsive states reload the interface. The Windows recovery check confirmed that removing the topmost flag and hiding the deployed window both recover automatically.

Choose **Teach lesson** from the sprite's right-click menu, tray menu, or details panel to run the existing Observer on the connected task's recent conversation. No text entry is required. The Observer receives up to 12 completed conversation messages and the latest user/previous-assistant pair. A detected lesson enters the existing confirmation flow; otherwise the companion reports that no teachable correction was found. `POST /native/observe` implements this action without starting another worker or automatically generating a curriculum.

## Start

From `frontend`, run `npm ci`, `npm run desktop:setup`, `npm run build`, then `npm run desktop`. The explicit setup command downloads Electron's native runtime. The companion starts its own loopback backend on port 8795 with artifacts under `runs/desktop`. It does not reuse or stop existing backend processes. Diagnostic logs are under `%APPDATA%/Gradient`.

The personal Gradient plugin is stored at `C:/Users/moham/plugins/gradient` and installed through the personal Codex marketplace. Its `scripts/gradient.py start --session <task-uuid>` starts the companion and connects one selected task. `status` reads its connection, `disconnect` stops observation, and `connect --session <task-uuid>` changes tasks. Plugin commands are available to newly started Codex tasks after installation; the current task can be connected directly using the same script.

## Demo controls

Right-click the sprite or use its tray menu to switch between **Live** and **Demo**:

- **Live** observes the connected Codex task. **Teach lesson** runs the Observer.
- **Demo** plays the saved lesson walkthrough without FastAPI. Nothing sits fixed on screen: click the sprite to open its details, where **Teach lesson**, **Continue lesson**, **Training evidence**, **← Live**, and **Reset** live. **Continue lesson** keeps details open across stages. While Observer/Builder work runs, the **Builder · RL tasks** list lives inside the Environment Builder agent's own peek (click it in the agent tray), not the main details; afterwards it appears in details alongside the Observer objective. The reference label and proof identify hand-authored solutions separately from trained model results. Scores display pass rates as percentages.

The desktop serves its built interface independently of FastAPI and reads saved demo artifacts through native IPC. A failed backend cannot prevent the offline view from loading. `runs/demo/fallback_proof.json` holds the saved walkthrough; `contracts/proof.schema.json` defines the shared proof format. Only the backend writes `current.json` and real experiment artifacts.

## Conversation connection

There is no on-screen mode selector. Switching happens through the sprite's right-click menu, the tray menu, the **← Live** button in the demo card, or the **Open demo** button in live notices. Switching modes always re-shows the companion window.

Saved artifacts appear at their matching lesson stages. Recorded comparisons reveal code progressively with a stagger between columns and show each verdict after its output. **Show full results** skips playback, and reduced-motion preferences show complete output immediately. Playback animates existing artifacts; it does not start inference or change results.

**Training evidence** opens genuine archived Qwen training samples from `execution/demo_evidence_20260912T195908Z`. It is available when the demo reaches training and inside the proof view. Three selectable examples compare original baseline code with passing training rollouts, with policy versions, independent Docker verification, and source hashes. The scope and differing sampling settings remain visible. These selected samples do not supply an aggregate POST score or a final adapter result; the existing final comparison remains separate.

The evidence view opens the PNG/PDF card, raw sample and verifier JSON, and downloads the full evidence ZIP. Its local `/evidence/` routes serve only named immutable evidence files and continue working without FastAPI. The bridge checks the evidence JSON and displayed comparison files against their SHA256 manifest. The captured status is dated; live status continues to come from backend-owned `runs/demo/current.json`.

Manual observation displays its status inside the Gradient surface, replacing an open peek while the request is pending. Highlighted excerpts show the exact user message and preceding Codex response from the selected transcript. The companion does not draw over Codex message bubbles, whose screen positions it cannot access. `GET /native/context` reads cached context without consuming transcript events; the observation response supplies the context used for that request.

`POST /native/connect` accepts an exact Codex task UUID and resolves its local transcript under the active `CODEX_HOME/sessions`. The adapter verifies the transcript identity, seeds context from existing messages, and observes only newly appended completed user messages. Previous final assistant answers provide the correction context. Tool output, commentary, response-item instruction injections, images, and other tasks are excluded.

Observation uses the existing Observer. It never starts the custom client's Worker. The Observer can flag a candidate; curriculum generation still requires Teach lesson. Post-training updates the separate Qwen model, not Codex's weights.

`GET /native` reports actual connection health. `POST /native/disconnect` stops reading new messages. Existing confirmed work continues; quitting the companion closes its backend jobs. `/runs` and `/events` accept `native_session` to scope history and live events to the selected task.

This uses an opt-in local transcript adapter, not app-shell injection or a lifecycle hook. It supports the installed Codex `event_msg/item_completed` format and legacy user/agent messages. Codex does not guarantee transcript format stability, so a format change may require updating `gradient/codex/native.py`. No hooks are installed or trusted by this plugin.

## Verification

- Frontend build/typecheck and the existing reducer tests pass.
- Native parser/integration tests cover historical context without replay, ignored tool/instruction content, partial records, task identity, session filtering, real WebSocket delivery, no duplicate worker, and confirmation before lesson generation.
- A real Codex Observer classified an isolated correction from an appended transcript record and emitted `correction_candidate` over the actual WebSocket. No lesson was compiled or trained by that check.
- A real Electron window passed transparency (alpha zero outside controls), Windows click-through style toggling, always-on-top, bottom-right placement, no duplicate workspace, sprite details, all lesson stages, and proof expand/Escape/restore checks. The state-transition window checks used explicitly isolated transport fixtures; they did not claim training results.
- Captures are in ignored `output/playwright/desktop-*.png`. Paid training was not exercised.
- The desktop's own HTTP and WebSocket proxy connected to real FastAPI. The native test then traversed the offline walkthrough, terminated only its own backend process, reloaded the window, and verified the offline view still opened. Saved proof files passed the shared schema; current fallback code comes from verified hand-authored reference artifacts, not trained-model output.

The window uses Electron's [documented click-through API](https://www.electronjs.org/docs/latest/tutorial/custom-window-interactions). The local transcript limitation is described in the official [Codex hook input documentation](https://learn.chatgpt.com/docs/hooks#common-input-fields).
