import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import jsonschema

from gradient.curriculum.compiler import environment_hash
from gradient.provenance import read_json, write_json
from gradient.schemas import ProofComparison, ProofOutput, ProofState, TaskSpec, now
from gradient.student.evaluate import solve
from gradient.student.model import QwenStudent
from gradient.training import prime

REPLAY_CLAIM = "Fallback/replay: verified reference code; not trained model output or evidence of different weights."
REAL_CLAIM = "Same model · Same task · Same verifier · Different weights"


def frozen_runner(root, image):
    path = root / "source/gradient/sandbox/runner.py"
    spec = importlib.util.spec_from_file_location("gradient_proof_frozen_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DockerRunner(image)


class PostGradientProvider:
    def __init__(self, settings, bus):
        self.settings, self.bus = settings, bus
        self.runs = settings.runs_dir.resolve()
        self.project = self.runs.parent

    def artifact(self, name):
        path = (self.project / name).resolve()
        if not path.is_relative_to(self.project):
            raise ValueError("Proof artifact escapes the repository")
        return path

    async def read_state(self):
        for attempt in range(2):
            try:
                return ProofState.model_validate(read_json(self.runs / "demo/current.json"))
            except (OSError, json.JSONDecodeError):
                if attempt:
                    raise
                await asyncio.sleep(.05)

    @staticmethod
    def adapter(state):
        post = state.post
        return post.adapter_id if (post.source == "real" and post.status == "ready"
                                   and post.adapter_id and post.adapter_id.strip()) else None

    def fallback(self, state):
        path = self.artifact(state.fallback_artifact)
        if path != self.runs / "demo/fallback_proof.json":
            raise ValueError("Unexpected fallback artifact")
        contract = self.artifact(state.proof_schema)
        if contract != self.project / "contracts/proof.schema.json":
            raise ValueError("Unexpected proof contract")
        if hashlib.sha256(contract.read_bytes()).hexdigest() != state.proof_schema_sha256:
            raise ValueError("Shared proof contract changed")
        proof = read_json(path)
        try:
            jsonschema.validate(proof, read_json(contract))
        except jsonschema.ValidationError as exc:
            raise ValueError("Fallback does not conform to the shared proof contract") from exc
        if proof["source"] != "fallback" or proof["post"]["adapter_id"] is not None:
            raise ValueError("Replay must not claim a trained adapter")
        if proof["pre"]["model_id"] != state.pre.model_id:
            raise ValueError("Fallback belongs to another base model")
        if (proof["provenance"].get("experiment_id") != state.experiment_id
                or proof["provenance"].get("manifest_sha256") != hashlib.sha256(
                    self.artifact(state.manifest).read_bytes()).hexdigest()):
            raise ValueError("Fallback belongs to another frozen experiment")
        return proof

    async def get_proof_status(self):
        state = await self.read_state()
        adapter = self.adapter(state)
        fallback, error = None, None
        if not adapter:
            try:
                fallback = self.fallback(state)
            except (OSError, ValueError) as exc:
                error = str(exc)
        return {"experiment_id": state.experiment_id, "pre": state.pre.model_dump(),
                "training": state.training.model_dump(),
                "post": {**state.post.model_dump(), "source": "real" if adapter else "fallback",
                         "adapter_id": adapter, "ready": bool(adapter or fallback),
                         "score": state.post.score.model_dump() if adapter and state.post.score else None,
                         "replay_score": fallback["post"]["score"] if fallback else None,
                         "error": error}, "claim": REAL_CLAIM if adapter else REPLAY_CLAIM}

    def frozen_task(self, state, task_id):
        root = self.runs / state.experiment_id
        if self.artifact(state.manifest) != root / "manifest.json":
            raise ValueError("Manifest does not belong to the indexed experiment")
        manifest = read_json(root / "manifest.json")
        if state.pre.adapter_id is not None or state.pre.status != "ready":
            raise ValueError("PRE must be the ready frozen base without an adapter")
        if state.pre.model_id != manifest["model"]:
            raise ValueError("PRE model differs from the frozen experiment")
        if state.pre.model_revision != manifest.get("model_revision"):
            raise ValueError("PRE revision differs from the frozen experiment")
        if manifest["inference_url"] != self.settings.inference_url:
            raise ValueError("Inference endpoint differs from frozen PRE")
        if task_id not in manifest["environments"]:
            raise ValueError("Unknown frozen proof task")
        paths = [root / "envs" / split / task_id for split in ("train", "heldout")]
        path = next((p for p in paths if p.is_dir()), None)
        if path is None or environment_hash(path) != manifest["environments"][task_id]:
            raise ValueError("Frozen proof environment changed")
        # Proof/API additions must not invalidate training's sealed engine hash.
        # Check the actual evaluator/runtime files used here against original PRE instead.
        package = Path(__file__).resolve().parents[1]
        for name in ("student/agent.py", "student/model.py", "student/evaluate.py"):
            if (package / name).read_bytes() != (root / "source/gradient" / name).read_bytes():
                raise ValueError(f"Frozen proof runtime changed: {name}")
        return root, manifest, path, TaskSpec.model_validate(read_json(path / "metadata.json"))

    async def run_proof(self, task_id, expected_run_id=None):
        state = await self.read_state()
        if expected_run_id is not None and expected_run_id != state.experiment_id:
            raise ValueError("Proof requested for a different experiment")
        root, manifest, path, spec = self.frozen_task(state, task_id)
        runner = frozen_runner(root, manifest["sandbox_image"])
        adapter = self.adapter(state)
        replay = None
        if not adapter:
            proof = self.fallback(state)
            if task_id not in proof.get("examples", {}):
                raise ValueError("No replay exists for this task")
            replay = proof["examples"][task_id]
            if replay["environment_hash"] != manifest["environments"][task_id]:
                raise ValueError("Replay environment differs from frozen PRE")
        proof_id = uuid4().hex
        target = self.runs / "demo/proofs" / proof_id
        target.mkdir(parents=True)
        write_json(target / "request.json", {"state": state.model_dump(), "task": spec.model_dump(),
                   "manifest": manifest, "prompt": (path / "prompt.txt").read_text(encoding="utf-8"),
                   "starter": (path / "starter.py").read_text(encoding="utf-8"), "timestamp": now()})
        claim = REAL_CLAIM if adapter else REPLAY_CLAIM
        output = {}
        self.bus.emit(root, "proof_started", task_id=task_id, proof_id=proof_id,
                      post_source="real" if adapter else "fallback", claim=claim)
        try:
            for label, identity in (("pre", None), ("post", adapter)):
                source = "fallback" if label == "post" and not adapter else "real"
                if source == "fallback":
                    code, messages = replay["code"], replay.get("messages", [])
                else:
                    student = QwenStudent(manifest["inference_url"], self.settings.inference_api_key,
                                          manifest["model"], identity,
                                          prime.serving_model(manifest["model"], identity) if identity else None)
                    code, messages = await solve(path, student, manifest)
                write_json(target / f"{label}.candidate.json", {"source": source, "code": code,
                           "messages": messages, "model_id": manifest["model"], "adapter_id": identity})
                result = await runner.run(spec, code, manifest["seeds"][task_id])
                output[label] = ProofOutput(source=source, model_id=manifest["model"],
                    model_revision=state.pre.model_revision, adapter_id=identity, output=code,
                    messages=messages, verifier=result)
                write_json(target / f"{label}.json", output[label])
                self.bus.emit(root, "comparison_result", label="base" if label == "pre" else "trained",
                    **{**result.model_dump(), "verifier_reason": result.verifier_reason + (
                        " · " + REPLAY_CLAIM if source == "fallback" else " · Live " + (
                            "trained adapter" if identity else "base inference"))},
                    code=code, messages=messages, model=manifest["model"], adapter_id=identity,
                    source=source, proof_id=proof_id, claim=claim)
            self.frozen_task(state, task_id)
            response = ProofComparison(proof_id=proof_id, task=spec,
                prompt=(path / "prompt.txt").read_text(encoding="utf-8"), claim=claim, **output)
            write_json(target / "result.json", response)
            return response
        except Exception as exc:
            write_json(target / "error.json", {"error": str(exc), "timestamp": now()})
            self.bus.emit(root, "proof_failed", task_id=task_id, proof_id=proof_id, error=str(exc))
            self.bus.emit(root, "state", state="FAILED", operation="proof", proof_id=proof_id,
                          error="Proof failed: " + str(exc))
            raise
