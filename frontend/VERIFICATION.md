# Frontend verification

September 12, 2026. Work continued in the existing `Gradient` repository, as confirmed by the user. Existing backend files and run evidence were preserved; no commit or push was made.

## Automated checks

| Check | Result |
| --- | --- |
| `npm run build` | PASS: strict TypeScript check and Vite production build. 375.57 kB JavaScript, 119.80 kB gzip. |
| `npm test` | PASS: 3 tests covering all canonical transitions, consent boundaries, dismissal, proof return, run scoping, result deduplication, missing scores/progress, and the HTTP/event failure race. |
| `uv run python -m unittest tests.test_frontend_contract tests.test_pipeline -q` | PASS: 12 tests, including existing backend pipeline checks. |
| `uv run ruff check gradient tests` | PASS. |
| Dependency installation | PASS: npm reported zero vulnerabilities. |

The new backend checks prove that the real FastAPI WebSocket receives worker events, confirmation is required before building, repeated confirmation cannot start duplicate work, dismissal persists, and the real deterministic compiler emits 8 train / 4 unseen artifacts. Codex/Prime/Docker boundaries are mocked only inside those automated checks.

## Browser checks

Used Chromium through Playwright CLI. All nine stages were manually traversed at 1366×768 and 390×844. No horizontal overflow occurred. Measured desktop widths: idle 32 px; candidate 148 px; agent tray plus anchor 132 px; opened lesson surfaces 320 px. Proof uses 42% viewport height on desktop. Mobile retains the 32 px artwork inside 44 px controls, with a 320 px lesson surface and stacked proof columns.

Recorded control outcomes:

- Lesson found opens the popover and focuses Teach lesson.
- Dismiss returns to idle.
- Teach lesson deploys Observer and Builder in the explicitly labeled showcase.
- Observer hover opens its peek; View details opens technical details; Close returns to the anchor.
- Builder click shows “Creating executable lessons” and “6 / 12 complete”; Close works.
- The anchor collapses and restores an artifact without changing its lifecycle stage.
- Post-train agent enters the training showcase.
- Run proof opens the drawer; Tab stays on its close control; Escape returns to learned. The initial focus issue was corrected and the check rerun successfully.
- Tool action and Changes reveal their content.
- Reduced-motion mode renders every control and state without sprite movement. Motion's development-only reduced-motion notice is expected; there were no application console errors.
- Reconnect restored saved conversation events without duplicating a completed answer.
- The real Codex runtime returned `GRADIENT_CONNECTION_OK` in the browser while Gradient remained idle. The final `/interactions` transport check returned HTTP 202, streamed `GRADIENT_EVENT_PATH_OK`, and again left Gradient idle.

Screenshots are in the ignored `output/playwright/` directory: `1366-{stage}.png`, `390-{stage}.png`, `reduced-motion-agents.png`, and `live-codex.png`. Final desktop captures include the avatar refinements from the user's references.

## Design gate

- Hard gate PASS: no invented production scores or work; nine states only; responsive bounds checked; keyboard controls exercised; error and empty states exist; only existing artifacts become links.
- Purpose gate PASS: color, character silhouettes, typography, shallow surfaces, and motion each have a specific purpose recorded in DESIGN_SYSTEM.md.
- Liveliness PASS: ENERGY 1 / RHYTHM 1 / MOTION 2; the transcript stays primary; role-specific paired-eye sprites provide the identity and peripheral state cues.
- Craftsmanship PASS: production build and interaction checks completed; proof is the only large Gradient surface; the supplied Codex workspace direction is preserved.

## Limits and local services

No paid training run was started. Live post-training completion and learned proof require the existing backend's configured Prime, model-serving, Docker, and evaluation prerequisites. The frontend reports backend failures and leaves absent evidence empty.

The existing services on ports 8787/8788 were left running. Verification used a separate backend on 8793 with `runs/frontend_check` and its own worker directory. The ignored `frontend/.env.local` points the Vite preview at that backend. Change `GRADIENT_BACKEND_URL` there or remove the file to use the default port 8787. Restart an existing backend process to load the updated consent/event endpoints and production build.
