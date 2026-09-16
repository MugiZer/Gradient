# Frontend verification contract

The current frontend architecture is Electron-only. Gradient does not have a browser showcase or a mock Codex workspace.

The September 12 browser-workspace verification is historical and superseded. Do **not** restore `CodexWorkspace`, `CodexTranscript`, `Composer`, `ToolAction`, `DiffPreview`, `codex.css`, or `/dev/ui` to satisfy old screenshots or checks.

## Required checks

For frontend changes:

- `npm run typecheck`
- `npm test`
- `npm run build`
- launch with `npm run desktop`
- inspect both Electron Live and Demo modes
- verify the transparent/click-through companion remains usable over a real host workspace
- verify expanded lesson / environment / proof surfaces collapse back to the ambient sprite

Demo verification must use saved evidence and native IPC. It must not require a fake coding transcript or fabricate model/training results.

Live verification should connect to a real supported host adapter. Codex is the current implementation in `gradient/codex/native.py`.

No paid training run is required for frontend verification.
