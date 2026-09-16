# Gradient

Gradient is a headless developer-learning tool that turns a correction from a real coding workflow into a typed capability, executable Python tasks, deterministic rewards, and a frozen base-versus-LoRA evaluation.

The current host integration observes real Codex task transcripts locally. Other IDEs or agent harnesses should integrate through the same adapter boundary rather than through a Gradient-owned editor UI. The Electron app is only the ambient companion/demo surface; Gradient does not ship a mock Codex workspace.

The backend implements the experiment pipeline. Model improvement is **not yet demonstrated**: a configured Qwen inference endpoint and a completed Prime training run are required for that claim.

## Run

Requires Python 3.11+, `uv`, authenticated Codex CLI with `app-server`, and Docker running Linux containers.

```powershell
rtk uv sync --extra dev
rtk docker build -t gradient-sandbox:local -f docker/Dockerfile.sandbox .
rtk uv run gradient
```

The API listens on `127.0.0.1:8787`. Open [API documentation](http://127.0.0.1:8787/docs). Copy `.env.example` to `.env` to configure the inference endpoint and the directory where the Worker may edit code. The default Worker directory is `worker-workspace/`.

For Prime inference, set `GRADIENT_INFERENCE_URL=https://api.pinference.ai/api/v1` and put your inference key in `GRADIENT_INFERENCE_API_KEY`. The student defaults to `Qwen/Qwen3.5-2B`. The same endpoint, model identifier, decoding settings, task files, hidden inputs, verifier image, and backend source hash are checked across evaluations. Only the adapter changes.

Evaluation freezes a presence penalty of `2.0` alongside temperature and seed. A live probe showed the previous zero-penalty setting producing repetitive helper functions until its JSON action was truncated; the same request with this penalty produced a complete action. Both base and adapter evaluations use the frozen value.

The server is intended for one local process. Cross-origin requests are rejected. If `GRADIENT_API_TOKEN` is set, HTTP and WebSocket clients must send `Authorization: Bearer <token>`. No authentication credentials enter candidate containers or experiment artifacts.

## Product integration

The product path is host-first and headless:

```text
real Codex / IDE / agent harness
        ↓
host adapter
        ↓
Gradient backend
        ↓
learning artifacts / training / eval
```

Today, `gradient/codex/native.py` is the concrete Codex adapter. The Electron companion can visualize and control the flow for the demo, but it is not required by the core tool. The `/worker` and `/interactions` APIs below remain useful as an experiment/debug harness; they are not a replacement coding interface.

See `frontend/DESKTOP.md` for the Electron demo/companion.

## Experiment flow

Worker, Observer, and Environment Agent instructions live in `gradient/codex/skills/<role>/SKILL.md`. The backend loads the matching skill text into each Codex agent's developer prompt; the Environment Agent receives only the Capability as input. Skill contents are included in the frozen source hash, source snapshot, and exported package. The observed native Codex task keeps its own instructions, and Qwen keeps its separate student protocol.

1. Send a normal coding task to `POST /worker`, with `{"message":"..."}`. The Worker uses a persistent Codex context.
2. Forward subsequent human-agent interactions to `POST /interactions`. The caller supplies the original requirement, previous response/diff, and latest human message; it does not classify whether the message is a correction. The Worker continues while the Observer analyzes the snapshot. This endpoint returns a run ID immediately.
3. Watch `GET /runs/{run_id}` or subscribe to `ws://127.0.0.1:8787/events`. A detected correction emits `correction_candidate`. Call `POST /runs/{run_id}/confirm` to start the Environment Agent and deterministic compilation, or `/dismiss` to discard the candidate. Ordinary interactions stop at `NO_LEARNING_EVENT`.
4. After `ENVIRONMENTS_COMPILED`, call `POST /runs/{run_id}/training/launch` with `{"owner":"your-prime-owner","max_steps":30}`. **This authorizes a paid hosted LoRA run.** The orchestrator evaluates the baseline if needed, checks calibration, exports the training split, publishes it privately, and launches Prime. Calibration requires 20–70% training success and rejects candidate runtime failures or timeouts.
5. The same orchestrator job polls Prime, saves logs, metrics and available rollout pages, resolves the completed adapter's provenance, requests deployment, and runs the frozen held-out evaluation. Watch WebSocket events or `GET /runs/{run_id}/training/status`. A failed operation records `FAILED` with the reason; resubmitting `/training/launch` resumes a recorded Prime run without launching another one.
6. For inspection before authorizing training, `/evaluate/baseline`, `/training/export`, and `/training/publish` remain available separately. `/training/collect`, `/training/deploy`, and `/evaluate/after` support manual recovery. `/compare/{task_id}` records a fresh base/trained held-out comparison.
7. After changing backend code or calibration settings, `POST /runs/{run_id}/iterate` creates a new run by recompiling the same generated TaskSpecs. It preserves the parent ID and captured interaction, generates a new manifest, and requires a fresh baseline. Earlier evidence is retained.

Example interaction body (illustrative input, not experimental evidence):

Interactions also accept optional `starter_state` files (`path`, `content`), `trajectory` steps (`role`, `content`), `accepted_output`, and `runtime_evidence` entries (`command`, `exit_code`, `stdout`, `stderr`). The complete snapshot is saved and passed to both the Worker and Observer. These are captured evidence, not files to execute or restore on the host.

```json
{
  "original_task": "Implement publish_snapshot(path, data) so another program can read the supplied data after it returns.",
  "bad_agent_output": "def publish_snapshot(path, data): return {'path': path, 'data': data}",
  "bad_diff": "",
  "human_message": "The requirement is about the observable effect. Returning a description does not change what another program reads."
}
```

## Prime setup

```powershell
rtk uv sync --extra dev --extra training
rtk proxy prime --plain login
rtk proxy prime --plain train models --output json
```

Hosted reward execution uses the Prime Sandboxes SDK. Launch reads `PRIME_API_KEY` from the environment or the existing Prime CLI configuration and passes it through Prime's secret channel. It is excluded from config files and saved launch output; the generated candidate receives a clean environment. A fresh isolated VM with an empty outbound allowlist is created per training reward and deleted afterward, with a five-minute maximum lifetime. Training limits concurrent rollouts to eight.

The exported package targets Verifiers v0 (`verifiers==0.1.14`, `prime-sandboxes==0.2.42`). Its dataset includes only the frozen training metadata; it contains no captured correction, baseline rollouts, or held-out task data. The config pins the uploaded environment version. [Prime configuration reference](https://docs.primeintellect.ai/hosted-training/advanced-configs) and [adapter serving format](https://docs.primeintellect.ai/inference/adapter-deployments) describe the external interfaces used here.

## Evidence and recovery

Each run has `interaction.json`, `event.json`, `capability.json`, `curriculum/`, `envs/`, `manifest.json`, and an append-only `events.jsonl`. Evaluations add `baseline/` and `after/`; training adds `training/`; live comparisons add `live/`. `GET /runs/{run_id}/artifacts/{path}` serves individual artifacts.

`source/gradient/` stores the exact backend Python source used at freeze. Each environment retains its prompt, starter, metadata, verifier and content hash. Hosted reward logs include paired `GRADIENT_ROLLOUT` and `GRADIENT_REWARD` JSON records with a correlation ID, task spec, randomized seed, complete candidate, messages, reward, stdout/stderr, and infrastructure errors. `training/snapshots/` keeps timestamped Prime status, metrics and logs; `training/rollouts/` retains all pages of rollout samples exposed by Prime for completed steps. Prime may sample its rollout export; the environment log records are the additional replay trace.

Completed evidence is never overwritten. A failed evaluation can be retried: saved candidates and completed rollouts are reused. If source code or a frozen environment changes, create a new experiment. The manifest records both the current Git commit and whether the checkout was dirty; a source hash identifies uncommitted backend changes.

Training submission has an exclusive `launch.json` marker to prevent duplicate paid jobs. If submission is interrupted, inspect Prime and the recorded artifacts before taking any further action; the backend deliberately refuses automatic resubmission. A failed generation should be submitted as a new interaction. After a server restart, the event journal remains readable, but in-flight tasks are not resumed automatically.

## Verification

```powershell
rtk uv run python -m unittest discover -v
rtk uv run ruff check gradient tests
rtk uv run python -m tests.check_export
rtk proxy .venv/Scripts/python -c "import os,unittest; os.environ['GRADIENT_TEST_DOCKER']='1'; unittest.main(module=None, argv=['unittest','tests.test_sandbox','-v'])"
rtk proxy .venv/Scripts/python -c "import os,unittest; os.environ['GRADIENT_TEST_TRAINING']='1'; unittest.main(module=None, argv=['unittest','tests.test_training','-v'])"
rtk uv run python -m tests.check_codex --curriculum
```

The last check makes small live Codex calls. Local tests cover all six family/mode combinations, forbidden verifier access, forged stdout rewards, time/output limits, schema validation, split isolation, matching evaluation inputs, API/WebSocket access, cancellation, recovery, and adapter provenance. Test doubles are used for inference and paid training; no synthetic scores are presented as a real model improvement.

For a complete live baseline check, start the backend on a separate port with a disposable Worker directory, then run `rtk uv run python -m tests.check_live --url http://127.0.0.1:8788`. This submits a clearly labelled synthetic correction, confirms the lesson, and runs real Codex generation, Prime inference, Docker verification, and WebSocket delivery. It saves the experiment under `runs/` and never publishes or launches training. If inference is interrupted after compilation, resume with `--run <run_id>`; saved candidates and rollouts are reused.

## Scope

The student has a six-turn JSON action loop: read `solution.py`, replace it, check syntax/function presence, and finish. No candidate code executes on the host. Docker uses a read-only root, an unprivileged candidate process, no network, and bounded CPU, memory, processes, files, and runtime. Reward is calculated by a separate privileged supervisor whose source is inaccessible to the candidate.

The compiler covers filesystem replacement, JSON counter updates, and local helper execution, each with execute/simulate modes. Hidden verification checks resulting state and return values. Byte snapshots detect final mutations; the helper marker deters accidental simulation but is not proof against deliberate forgery or execute-and-undo attacks. These are small experiment environments, not an adversarial security benchmark.

No database, broker, agent framework, or optional Ambiguous integration is included. The built frontend bundle is the Electron renderer. Browser rendering is not a product surface; the Gradient core remains usable headlessly through its backend and host adapter.
