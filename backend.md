# Gradient Backend Directives

Backend directives extracted from hackathon_project.md. The backend is the source of truth for the experiment; the UI is only a view over its real events.

## 1. Product boundary

Gradient learns the distinction between an observable external effect and a representation, preview, or simulation of that effect.

The backend must prove behavior, not reward plausible code or textual claims.

Do not build databases, Redis, Kafka, distributed services, arbitrary repository ingestion, a full SWE-bench harness, or a large autonomous coding-agent platform. The filesystem is the experiment record for the hackathon.

## 2. Canonical lifecycle

    developer correction
      -> capture InteractionSnapshot
      -> Observer extracts LearningEvent and Capability
      -> Environment Agent creates structured TaskSpecs
      -> deterministic compiler creates executable environments
      -> Docker runs the candidate in isolation
      -> hidden verifier returns reward 0 or 1
      -> baseline evaluation
      -> optional Prime RL/LoRA training
      -> exact held-out evaluation
      -> immutable provenance and event stream

Codex agents reason about the lesson. Deterministic code defines truth. Training changes weights. Frozen evaluations prove transfer.

## 3. Agent responsibilities

### Worker

The developer-facing Codex worker continues the coding task normally. It captures the original requirement, starter state, trajectory, bad output or diff, correction, accepted output, and runtime evidence.

### Observer

The Observer receives the captured interaction in an isolated context. It must infer the smallest generalized capability distinction that explains the rejected and accepted behavior. It must not re-solve the original task.

### Environment Agent

The Environment Agent receives only the structured Capability and returns structured train and held-out TaskSpec objects. It must generate positive cases where the effect is required and counterexamples where the effect is forbidden.

It must not generate arbitrary verifier code.

## 4. Task families

Use two or three tiny side-effect surfaces so the model cannot learn a lexical rule such as always write files or never execute commands.

Required families:

1. Filesystem effect required: write randomized data to a supplied path and verify that a fresh reader observes it.
2. Filesystem effect forbidden: return a useful preview while proving the workspace remains byte-for-byte unchanged.
3. Persistent JSON effect required: read, increment, and persist a randomized counter; verify through a fresh reader.
4. Persistent JSON effect forbidden: return the projected next state without modifying the file.
5. Local helper execution required: execute a provided helper and return its randomized output or marker.
6. Local helper execution forbidden: construct the command or plan without executing it.

Positive verifiers must inspect actual resulting state. Negative verifiers must prove that the forbidden side effect did not occur.

## 5. Deterministic compiler and verifier

The Environment Agent emits structured specifications such as:

    {
      "effect_family": "filesystem_write",
      "mode": "execute",
      "surface_form": "publish_snapshot"
    }

The deterministic Python compiler converts each spec into:

    prompt.txt
    starter.py
    verifier.py
    metadata.json

Verifier rules:

- inspect consequences, never source-code strings;
- randomize filenames, values, tokens, and payloads at evaluation time;
- keep the verifier outside the student writable workspace;
- never reward strings such as write_text or subprocess;
- use fresh disposable environments;
- return 1 only when the behavioral contract is satisfied, otherwise 0;
- ensure the candidate cannot control its own reward.

Start with approximately 8 training environments and 4 frozen held-out environments. Held-out tasks must differ in wording, function names, and surface form.

## 6. Student and evaluation

Primary student: Qwen/Qwen3.5-2B.

Use Qwen3.5-0.8B for cheap plumbing or if 2B is too competent. Escalate to Qwen3.5-4B only when 2B fails for basic code incompetence rather than the target semantic distinction.

The base model remains fixed. Training produces a LoRA adapter.

The evaluator must be identical for base and trained models:

- same prompt;
- same starter state;
- same hidden verifier;
- same decoding settings;
- only the adapter or weights differ.

Freeze the held-out set before training. Never expose held-out prompts, solutions, or verifier-specific hints to training.

The meaningful result is improved held-out behavior while counterexamples remain correct. Training reward alone is not proof.

## 7. Go or no-go calibration

Before training, calibrate the base model on a small set.

Good failure means valid Python, a plausible solution, understanding of the contract, and failure specifically at the effect-versus-simulation boundary.

Bad failure means invalid Python, hallucinated imports, inability to understand the contract, or unrelated basic failure.

Do not train until the starting distribution is learnable. If 2B solves everything, make the wording subtler or use 0.8B. If it fails for basic reasons, simplify the task or use 4B.

## 8. Code boundaries

Keep the repository as one small Python monorepo.

    gradient/
      main.py
      config.py
      schemas.py
      orchestrator.py
      events.py
      provenance.py
      codex/
      curriculum/
      sandbox/
      student/
      training/
      api/
    tests/
    docker/
    runs/

schemas.py owns typed contracts including InteractionSnapshot, LearningEvent, Capability, TaskSpec, RolloutResult, and TrainingResult. Agent and subsystem communication must use typed Pydantic objects, not giant prose blobs.

orchestrator.py owns the deterministic lifecycle:

    WATCHING
    -> CORRECTION_DETECTED
    -> CAPABILITY_EXTRACTED
    -> CURRICULUM_GENERATING
    -> ENVIRONMENTS_COMPILED
    -> BASELINE_EVALUATED
    -> READY_FOR_TRAINING
    -> TRAINED
    -> HELDOUT_EVALUATED

Keep Codex protocol logic inside codex/. Keep Prime-specific logic inside training/. Keep compilation deterministic inside curriculum/. Keep untrusted execution and hidden verification inside sandbox/.

Use FastAPI and WebSocket for the thin API/event surface. The frontend must not contain experiment logic.

## 9. Concurrency and event flow

When a correction arrives:

- the Worker continues in one async task;
- the Observer analyzes the same interaction in another async task;
- a detected learning event invokes the Environment Agent;
- compilation starts when structured specs arrive;
- the core pipeline must not wait on optional integrations.

Use a small internal event stream, not Kafka or another external broker:

    HumanMessageReceived
    -> WorkerStatusChanged
    -> ObserverStatusChanged
    -> LearningEventDetected
    -> EnvironmentAgentStarted
    -> TaskSpecsGenerated
    -> EnvironmentsCompiled
    -> BaselineEvaluated
    -> TrainingStarted / TrainingCompleted
    -> HeldoutEvaluated

The event stream feeds the UI subscriber, provenance logger, and optional Ambiguous subscriber.

## 10. Provenance and persistence

Each learning event gets an immutable run directory:

    runs/grad_<timestamp_or_id>/
      interaction.json
      event.json
      capability.json
      curriculum/
        train_specs.json
        heldout_specs.json
      envs/
        train/
        heldout/
      baseline/
        results.json
        rollouts/
      training/
        run.json
        logs.jsonl
      after/
        results.json
        rollouts/
      manifest.json

Preserve the held-out task ID and content hash, frozen-environment Git commit, baseline timestamp, model ID, decoding configuration, raw rollout, verifier result, training timestamps, Prime run ID, reward logs, adapter ID, post-training rollout, and post-training verifier result.

## 11. Prime integration

Use Prime hosted RL/LoRA when it is reliable. Wrap all Prime behavior behind training/prime.py or PrimeTrainer.

Conceptual interface:

    train_envs + base_model -> run_id + adapter_id + logs

Do not spread Prime CLI or API logic through the orchestrator, compiler, sandbox, evaluator, or API.

## 12. Ambiguous integration

Ambiguous is an optional sidecar, never a core dependency. Gradient must work end-to-end if Ambiguous is unavailable, slow, or broken.

Keep one small integration module, conceptually:

    gradient/integrations/ambiguous.py

It may mirror agent identity, task or handoff, curriculum artifacts, status, and audit trail. Call it asynchronously and do not block the core post-training pipeline on it.

Timebox Ambiguous onboarding to 20 minutes. If auth, CLI, API, or permissions are unreliable, cut the integration and prioritize the experiment.

Continue using the existing Codex runtime. Do not introduce another inference provider solely for the sponsor integration.

## 13. Locked build order

1. schemas.py
2. one hardcoded TaskSpec
3. deterministic compiler
4. Docker sandbox
5. reliable 0/1 verifier
6. base Qwen rollout
7. held-out evaluator
8. Observer returning valid LearningEvent JSON
9. Environment Agent returning valid TaskSpec objects
10. correction to Observer to Environment Agent to compiler wiring
11. Prime training wrapper
12. trained-versus-base held-out evaluation
13. provenance artifacts
14. WebSocket event stream
15. presentation UI

First prove:

    TaskSpec -> compiler -> Qwen -> candidate -> Docker -> verifier -> reward

Then prove the correction-to-curriculum path, then prove the trained-versus-base held-out difference. Presentation work comes last.

## 14. Implementation constraints

- Keep the backend roughly 1,000 to 1,500 lines excluding tests and templates.
- Prefer plain Python and asyncio over agent frameworks.
- No database, message broker, distributed deployment, or arbitrary verifier generation.
- No UI logic inside training or compiler code.
- No Prime-specific logic outside training/.
- No Codex protocol logic outside codex/.
- If the codebase reaches several thousand lines before the first successful training run, it is overbuilt.

The target is a reproducible ML experiment with an agentic interface, not a startup-scale platform.

