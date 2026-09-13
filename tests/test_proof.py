import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from gradient.api.app import create_app
from gradient.api.proof import PostGradientProvider
from gradient.config import Settings
from gradient.curriculum.compiler import compile_curriculum
from gradient.events import EventBus
from gradient.provenance import freeze, read_json, write_json
from gradient.sandbox.runner import DockerRunner
from gradient.schemas import Decoding, RolloutResult
from tests.test_backend import curriculum


class ProofTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.root = self.project / "runs/grad_fixture"
        hashes = compile_curriculum(curriculum(), self.root / "envs")
        freeze(self.root, hashes, "Qwen/Qwen3.5-2B", Decoding(), "image", "http://inference")
        contract = Path(__file__).resolve().parents[1] / "contracts/proof.schema.json"
        write_json(self.project / "contracts/proof.schema.json", read_json(contract))
        self.state = {"objective": "fixed_8_score", "experiment_id": self.root.name,
            "manifest": "runs/grad_fixture/manifest.json", "proof_schema": "contracts/proof.schema.json",
            "proof_schema_sha256": hashlib.sha256((self.project / "contracts/proof.schema.json").read_bytes()).hexdigest(),
            "pre": {"model_id": "Qwen/Qwen3.5-2B", "model_revision": None, "adapter_id": None,
                    "score": {"passed": 5, "total": 8}, "status": "ready"},
            "training": {"status": "running", "run_id": "training-fixture"},
            "post": {"source": "fallback", "status": "waiting", "adapter_id": None,
                     "model_id": "Qwen/Qwen3.5-2B", "score": None},
            "fallback_artifact": "runs/demo/fallback_proof.json"}
        self.feed = self.project / "runs/demo/current.json"
        write_json(self.feed, self.state)
        tasks = [{"task_id": f"task_{i}", "pre_reward": int(i < 5), "post_reward": 1,
                  "pre_artifact": "fixture", "post_artifact": "fixture"} for i in range(8)]
        profile = {"model_id": "Qwen/Qwen3.5-2B", "adapter_id": None, "score": {"passed": 8, "total": 8}}
        self.replay = {"schema_version": 1, "source": "fallback", "claim": "Test fixture replay",
            "pre": self.state["pre"], "post": profile, "tasks": tasks,
            "provenance": {"experiment_id": self.root.name,
                "manifest_sha256": hashlib.sha256((self.root / "manifest.json").read_bytes()).hexdigest()},
            "examples": {task: {"code": "replay", "messages": [], "environment_hash": digest}
                         for task, digest in hashes.items()}}
        write_json(self.project / "runs/demo/fallback_proof.json", self.replay)
        self.settings = Settings(runs_dir=self.project / "runs", inference_url="http://inference", _env_file=None)
        self.provider = PostGradientProvider(self.settings, EventBus())
        self.inference_calls = []

        async def infer(student, prompt, starter, function_name, decoding):
            self.inference_calls.append((student.model, student.adapter_id, student.serving_model,
                                         prompt, starter, function_name, decoding))
            return ("trained" if student.adapter_id else "base"), [{"role": "assistant", "content": "fixture"}]

        async def verify(runner, spec, code, seed):
            return RolloutResult(task_id=spec.id, reward=int(code != "base"), verifier_reason="fixture",
                                 duration_ms=1)

        for name, replacement in (("gradient.api.proof.QwenStudent.solve", infer),
                                  ("gradient.sandbox.runner.DockerRunner.run", verify),
                                  ("gradient.api.proof.frozen_runner", lambda root, image: DockerRunner(image))):
            mock = patch(name, replacement)
            mock.start()
            self.addCleanup(mock.stop)

    def publish_fixture(self):
        # Only this temporary fixture is replaced. Never touch the production feed.
        temporary = self.feed.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state), encoding="utf-8")
        os.replace(temporary, self.feed)

    async def test_fallback_to_real_same_inputs_every_trace_retained(self):
        before = self.feed.read_bytes()
        status = await self.provider.get_proof_status()
        self.assertEqual(status["post"]["source"], "fallback")
        self.assertTrue(status["post"]["ready"])
        self.assertIsNone(status["post"]["score"])
        first = await self.provider.run_proof("task_0")
        self.assertEqual(self.feed.read_bytes(), before)
        self.assertEqual(first.pre.verifier.reward, 0)
        self.assertEqual(first.post.source, "fallback")
        self.assertIsNone(first.post.adapter_id)
        self.assertEqual(len(self.inference_calls), 1)
        self.assertIn("not trained", first.claim)
        self.state["post"].update(source="real", status="ready", adapter_id="adapter-fixture")
        self.publish_fixture()
        before = self.feed.read_bytes()
        self.assertEqual((await self.provider.get_proof_status())["post"]["source"], "real")
        second = await self.provider.run_proof("task_0")
        self.assertEqual(second.post.source, "real")
        self.assertEqual(second.post.adapter_id, "adapter-fixture")
        self.assertEqual(self.inference_calls[0], self.inference_calls[1])
        self.assertEqual(self.inference_calls[1][3:], self.inference_calls[2][3:])
        self.assertEqual(self.inference_calls[2][2], "Qwen/Qwen3.5-2B:adapter-fixture")
        self.assertEqual(self.feed.read_bytes(), before)
        proofs = list((self.project / "runs/demo/proofs").iterdir())
        self.assertEqual(len(proofs), 2)
        for proof in proofs:
            self.assertEqual(read_json(proof / "pre.json")["verifier"]["reward"], 0)
            self.assertTrue((proof / "post.candidate.json").exists())
            self.assertTrue((proof / "result.json").exists())

    async def test_all_three_readiness_conditions_and_retry(self):
        for source, status, adapter in (("real", "validating", "adapter-fixture"),
                                        ("fallback", "ready", "adapter-fixture"),
                                        ("real", "ready", None), ("real", "ready", " ")):
            self.state["post"].update(source=source, status=status, adapter_id=adapter)
            self.publish_fixture()
            self.assertEqual((await self.provider.get_proof_status())["post"]["source"], "fallback")
        with patch("gradient.api.proof.read_json", side_effect=[FileNotFoundError(), self.state]):
            state = await self.provider.read_state()
            self.assertEqual(state.experiment_id, self.root.name)
        with patch("gradient.api.proof.read_json", side_effect=[json.JSONDecodeError("race", "", 0), self.state]):
            self.assertEqual((await self.provider.read_state()).experiment_id, self.root.name)

    async def test_invalid_profile_and_environment_rejected_before_inference(self):
        for change in ({"adapter_id": "bad"}, {"model_id": "other"}, {"model_revision": "unknown"}):
            original = self.state["pre"].copy()
            self.state["pre"].update(change)
            self.publish_fixture()
            with self.assertRaises(ValueError):
                await self.provider.run_proof("task_0")
            self.state["pre"] = original
        self.publish_fixture()
        (self.root / "envs/train/task_0/prompt.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "environment changed"):
            await self.provider.run_proof("task_0")
        self.assertEqual(self.inference_calls, [])

    async def test_incomplete_or_changed_fallback_is_not_reported_ready(self):
        self.replay["provenance"] = {"post_source": "illustration"}
        (self.project / "runs/demo/fallback_proof.json").write_text(json.dumps(self.replay))
        status = await self.provider.get_proof_status()
        self.assertFalse(status["post"]["ready"])
        self.assertIn("another frozen experiment", status["post"]["error"])
        with self.assertRaises(ValueError):
            await self.provider.run_proof("task_0")
        self.assertEqual(self.inference_calls, [])

    async def test_real_failure_does_not_silently_substitute_replay(self):
        self.state["post"].update(source="real", status="ready", adapter_id="adapter-fixture")
        self.publish_fixture()
        with patch("gradient.api.proof.solve", AsyncMock(side_effect=[("base", []), RuntimeError("offline")])):
            with self.assertRaisesRegex(RuntimeError, "offline"):
                await self.provider.run_proof("task_0")
        target = next((self.project / "runs/demo/proofs").iterdir())
        self.assertTrue((target / "pre.json").exists())
        self.assertEqual(read_json(target / "error.json")["error"], "offline")
        self.assertFalse((target / "post.json").exists())

    async def test_existing_compare_route_emits_renderable_events_and_hot_swaps(self):
        app = create_app(self.settings)
        with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
            self.assertEqual(client.get("/proof/status").json()["post"]["source"], "fallback")
            with client.websocket_connect("ws://localhost/events") as socket:
                response = client.post("/runs/grad_fixture/compare/task_8")
                self.assertEqual(response.status_code, 202)
                events = [socket.receive_json() for _ in range(3)]
                self.assertEqual([e["type"] for e in events], ["proof_started", "comparison_result", "comparison_result"])
                self.assertEqual(events[2]["label"], "trained")
                self.assertIn("Fallback/replay", events[2]["verifier_reason"])
            self.state["post"].update(source="real", status="ready", adapter_id="adapter-fixture")
            self.publish_fixture()
            response = client.post("/proof/task_8")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["post"]["source"], "real")
