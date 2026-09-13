import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from gradient.api.app import create_app
from gradient.config import Settings
from gradient.curriculum.compiler import compile_curriculum
from gradient.events import EventBus
from gradient.orchestrator import Orchestrator
from gradient.provenance import freeze, read_json, verify_frozen, write_json
from gradient.schemas import Decoding, InteractionSnapshot, LearningEvent, RolloutResult
from gradient.student.evaluate import evaluate
from gradient.training import prime
from tests.test_backend import curriculum


class PipelineTest(unittest.IsolatedAsyncioTestCase):
    async def test_retry_reads_new_run_and_preserves_failed_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "training/run.json", {"run": {"id": "failed-original"}})
            write_json(root / "execution/training_retry.json", {"attempt": 1})
            write_json(root / "training/attempts/1/run.json", {"run": {"id": "retry"}})
            with patch.object(prime, "prime", AsyncMock(return_value={"run": {"id": "retry"}})) as service:
                await prime.status(root)
                self.assertEqual(service.call_args.args, ("train", "get", "retry", "--output", "json"))
            self.assertEqual(read_json(root / "training/run.json")["run"]["id"], "failed-original")

    async def test_orchestrator_owns_training_lifecycle_and_resumes_without_relaunch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image")
            write_json(root / "baseline" / "results.json", {"results": [
                {"split": "train", "reward": i % 2} for i in range(8)]})
            app = Orchestrator(Settings(runs_dir=root, _env_file=None))
            run = {"run": {"id": "remote", "status": "COMPLETED"}}

            async def launch(path):
                write_json(path / "training" / "run.json", run)
                return run

            async def collect(path, adapter):
                write_json(path / "training" / "result.json", {"adapter_id": adapter})

            with patch.object(prime, "publish", AsyncMock()) as publish, patch.object(
                prime, "launch", AsyncMock(side_effect=launch)
            ) as launched, patch.object(prime, "capture", AsyncMock(return_value=run)), patch.object(
                prime, "ready_adapter", AsyncMock(return_value="adapter")
            ), patch.object(app, "collect", AsyncMock(side_effect=collect)) as collected, patch.object(
                prime, "deploy", AsyncMock()
            ), patch.object(app, "run_evaluation", AsyncMock()) as evaluated:
                await app.train(root, "owner", 3)
                await app.train(root)
                self.assertEqual(launched.await_count, 1)
                self.assertEqual(collected.await_count, 1)
                self.assertEqual(publish.await_count, 2)
                evaluated.assert_awaited_with(root, "after")
            self.assertTrue((root / "source" / "gradient" / "orchestrator.py").exists())
            self.assertTrue((root / "training" / "export.json").exists())
            await app.close()

    async def test_observer_runs_before_worker_finishes_and_no_event_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Orchestrator(Settings(runs_dir=root, _env_file=None))
            worker_started, observed = asyncio.Event(), asyncio.Event()

            async def worker(*args):
                worker_started.set()
                await asyncio.wait_for(observed.wait(), 2)
                return "fixed"

            async def observer(*args):
                await asyncio.wait_for(worker_started.wait(), 2)
                observed.set()
                return LearningEvent(is_learning_event=False, confidence=.9,
                                     rejected_behavior="", correction="", capability=None)

            with patch("gradient.codex.agents.work", worker), patch("gradient.codex.agents.observe", observer):
                run_id = app.receive(InteractionSnapshot(original_task="x", human_message="thanks"))
                await app.jobs[run_id]
            self.assertFalse((root / run_id / "manifest.json").exists())
            self.assertIn("NO_LEARNING_EVENT", (root / run_id / "events.jsonl").read_text())
            self.assertEqual(read_json(root / run_id / "worker.json")["output"], "fixed")
            await app.close()

    async def test_same_eval_inputs_and_train_only_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = curriculum()
            hashes = compile_curriculum(batch, root / "envs")
            freeze(root, hashes, "test-qwen", Decoding(), "image-id")
            write_json(root / "curriculum" / "train_specs.json", [s.model_dump() for s in batch.tasks[:8]])
            seen = []

            class Student:
                model, adapter_id = "test-qwen", None

                async def solve(self, *args):
                    seen.append(args)
                    return "code", []

            class Runner:
                image = "image-id"

                async def run(self, spec, code, seed):
                    return RolloutResult(task_id=spec.id, reward=int(spec.mode == "execute"),
                                         verifier_reason="test fixture", duration_ms=1)

            bus = EventBus()
            await evaluate(root, "baseline", Student(), Runner(), bus)
            target = prime.export(root, "test-owner")
            exported = read_json(target / "gradient" / "training" / "train_specs.json")
            self.assertTrue((target / "gradient/codex/skills/environment/SKILL.md").exists())
            self.assertEqual(len(exported), 8)
            self.assertTrue(all(t["split"] == "train" for t in exported))
            self.assertNotIn("heldout", (root / "training" / "config.toml").read_text())
            write_json(root / "training" / "result.json", {"adapter_id": "adapter"})
            trained = Student()
            trained.adapter_id = "adapter"
            await evaluate(root, "after", trained, Runner(), bus)
            self.assertEqual(seen[8:12], seen[12:16])
            with self.assertRaises(ValueError):
                await evaluate(root, "baseline", Student(), Runner(), bus)
            (root / "envs" / "heldout" / "task_8" / "starter.py").write_text("changed")
            with self.assertRaises(ValueError):
                verify_frozen(root)

    async def test_training_rejects_wrong_adapter_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "test-qwen", Decoding(), "image")
            write_json(root / "training" / "run.json", {"run": {"id": "real-run"}})
            responses = [{"run": {"id": "real-run", "status": "COMPLETED", "base_model": "test-qwen"}},
                         {"models": [{"id": "wrong", "base_model": "test-qwen", "rft_run_id": "other", "status": "READY"}]}]
            with patch.object(prime, "prime", AsyncMock(side_effect=responses)):
                with self.assertRaisesRegex(ValueError, "provenance"):
                    await prime.collect(root, "wrong")
            self.assertFalse((root / "training" / "result.json").exists())

    async def test_training_rejects_runtime_failures_at_an_acceptable_pass_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image")
            write_json(root / "baseline" / "results.json", {"results": [
                {"split": "train", "reward": int(i < 3),
                 "verifier_reason": "Contract satisfied" if i < 3 else "Candidate failed"}
                for i in range(8)]})
            with self.assertRaisesRegex(ValueError, "runtime failures"):
                prime.export(root, "owner")
            self.assertFalse((root / "training").exists())

    async def test_publish_launch_and_collect_preserve_real_service_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image")
            write_json(root / "baseline" / "results.json", {"results": [
                {"split": "train", "reward": i % 2} for i in range(8)]})
            prime.export(root, "owner")
            run = {"id": "run", "status": "COMPLETED", "base_model": "qwen",
                   "started_at": "2026-09-12T10:00:00Z", "completed_at": "2026-09-12T11:00:00Z"}
            adapter = {"id": "adapter", "status": "READY", "base_model": "qwen", "rft_run_id": "run"}
            responses = ["Type Personal\nUsername owner\n", "published", "Configuration: test\n" + json.dumps({"run": run}), {"run": run}, {"models": [adapter]},
                         {"metrics": [{"step": 1, "reward": .5}]}]
            with patch.object(prime, "prime", AsyncMock(side_effect=responses)) as service:
                await prime.publish(root)
                self.assertNotIn("--owner", service.call_args_list[1].args)
                await prime.launch(root)
                result = await prime.collect(root, "adapter")
                self.assertEqual(result.run_id, "run")
                with self.assertRaises(FileExistsError):
                    await prime.launch(root)
                self.assertEqual(service.await_count, 6)
            self.assertEqual(read_json(root / "training" / "result.json")["adapter_id"], "adapter")
            self.assertIn('"reward": 0.5', (root / "training" / "logs.jsonl").read_text())

    async def test_failed_sandbox_preserves_candidate_for_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = curriculum()
            hashes = compile_curriculum(batch, root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image")
            student = AsyncMock(model="qwen", adapter_id=None)
            student.solve.return_value = ("saved candidate", [])
            runner = AsyncMock(image="image")
            runner.run.side_effect = RuntimeError("Docker unavailable")
            with self.assertRaisesRegex(RuntimeError, "Docker unavailable"):
                await evaluate(root, "baseline", student, runner, EventBus())
            self.assertEqual(student.solve.await_count, 1)
            with self.assertRaises(RuntimeError):
                await evaluate(root, "baseline", student, runner, EventBus())
            self.assertEqual(student.solve.await_count, 1)

    async def test_shutdown_cancels_worker_when_observer_is_interrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = Orchestrator(Settings(runs_dir=Path(directory), _env_file=None))
            started = asyncio.Event()
            cancelled = asyncio.Event()

            async def work(*args):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

            async def observe(*args):
                await asyncio.Event().wait()

            with patch("gradient.codex.agents.work", work), patch("gradient.codex.agents.observe", observe):
                orchestrator.receive(InteractionSnapshot(original_task="x", human_message="fix it"))
                await started.wait()
                await asyncio.wait_for(orchestrator.close(), 2)
                self.assertTrue(cancelled.is_set())

    async def test_live_comparison_uses_same_seed_and_only_changes_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(runs_dir=root, inference_url="http://model/v1", _env_file=None)
            orchestrator = Orchestrator(settings)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image", settings.inference_url)
            write_json(root / "training" / "result.json", {"adapter_id": "adapter"})
            student = AsyncMock()
            student.solve.return_value = ("source", [])
            runner = AsyncMock()
            runner.run.return_value = RolloutResult(task_id="task_8", reward=1, verifier_reason="fixture", duration_ms=1)
            with patch("gradient.orchestrator.QwenStudent", return_value=student) as model, patch(
                "gradient.orchestrator.DockerRunner", return_value=runner
            ):
                await orchestrator.compare(root, "task_8")
                self.assertEqual(model.call_args_list[0].args[2:], ("qwen", None, None))
                self.assertEqual(model.call_args_list[1].args[2:], ("qwen", "adapter", "qwen:adapter"))
                self.assertEqual(student.solve.call_args_list[0], student.solve.call_args_list[1])
                self.assertEqual(runner.run.call_args_list[0], runner.run.call_args_list[1])
            self.assertEqual(len(list((root / "live").glob("*.json"))), 1)
            await orchestrator.close()



class ApiTest(unittest.TestCase):
    def test_auth_validation_artifact_boundaries_and_websocket(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(runs_dir=Path(directory), _env_file=None)
            app = create_app(settings)
            root = settings.runs_dir / "grad_test"
            root.mkdir()
            app.state.orchestrator.state(root, "WATCHING")
            with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                self.assertEqual(client.get("/health", headers={"origin": "https://evil.test"}).status_code, 401)
                self.assertEqual(client.post("/interactions", json={"human_message": "hi"}).status_code, 422)
                self.assertEqual(client.get("/runs/grad_test/artifacts/%2e%2e%2fsecret.txt").status_code, 404)
                self.assertEqual(client.post("/runs/grad_test/evaluate/wrong").status_code, 422)
                with client.websocket_connect("ws://localhost/events") as websocket:
                    client.portal.call(app.state.orchestrator.state, root, "READY")
                    self.assertEqual(websocket.receive_json()["state"], "READY")
                self.assertEqual(len(app.state.orchestrator.bus.subscribers), 0)
            token_app = create_app(Settings(runs_dir=Path(directory), api_token="secret", _env_file=None))
            with TestClient(token_app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                self.assertEqual(client.get("/health").status_code, 401)
                self.assertEqual(client.get("/health", headers={"authorization": "Bearer secret"}).status_code, 200)
