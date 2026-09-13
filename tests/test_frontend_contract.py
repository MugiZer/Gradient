import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from gradient.api.app import create_app
from gradient.config import Settings
from gradient.provenance import read_json
from gradient.schemas import Capability, LearningEvent
from tests.test_backend import curriculum


def candidate():
    return LearningEvent(is_learning_event=True, confidence=.95, rejected_behavior="preview",
                         correction="write the file", capability=Capability(
                             name="observable_effect", description="Effect versus simulation",
                             positive_rule="Persist when requested", negative_rule="Do not act on previews"))


class FrontendContractTest(unittest.TestCase):
    def test_live_socket_worker_output_and_explicit_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(runs_dir=Path(directory), _env_file=None))
            orchestrator = app.state.orchestrator

            async def worker(client, cwd, message, on_event):
                on_event({"method": "item/agentMessage/delta", "params": {
                    "itemId": "answer", "delta": "Actual transport fixture"}})
                return "Actual transport fixture"

            async def wait_for_run(run_id):
                if job := orchestrator.jobs.get(run_id):
                    await job

            with patch("gradient.codex.agents.observe", AsyncMock(return_value=candidate())), patch(
                "gradient.codex.agents.work", worker
            ), patch.object(orchestrator, "build_lesson", AsyncMock()) as build:
                with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                    with client.websocket_connect("ws://localhost/events") as socket:
                        response = client.post("/interactions", json={
                            "original_task": "write the file", "human_message": "write the file"})
                        self.assertEqual(response.status_code, 202)
                        run_id = response.json()["run_id"]
                        client.portal.call(wait_for_run, run_id)
                        history = client.get(f"/runs/{run_id}").json()["events"]
                        received = [socket.receive_json() for _ in history]
                        self.assertEqual(received, history)
                        self.assertIn("correction_candidate", [e["type"] for e in received])
                        self.assertIn("worker_event", [e["type"] for e in received])
                        build.assert_not_called()
                        self.assertFalse((Path(directory) / run_id / "capability.json").exists())
                        self.assertEqual(client.post(f"/runs/{run_id}/confirm").status_code, 202)
                        client.portal.call(wait_for_run, run_id)
                        build.assert_awaited_once()
                        self.assertEqual(client.post(f"/runs/{run_id}/confirm").status_code, 409)
                        self.assertEqual(read_json(Path(directory) / run_id / "confirmed.json"), {"confirmed": True})

    def test_dismiss_is_persisted_and_cannot_start_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(runs_dir=Path(directory), _env_file=None))
            with patch("gradient.codex.agents.observe", AsyncMock(return_value=candidate())), patch(
                "gradient.codex.agents.work", AsyncMock(return_value="done")
            ), patch.object(app.state.orchestrator, "build_lesson", AsyncMock()) as build:
                with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                    run_id = client.post("/interactions", json={
                        "original_task": "write the file", "human_message": "write the file"}).json()["run_id"]

                    async def settle():
                        await asyncio.gather(*app.state.orchestrator.jobs.values())

                    client.portal.call(settle)
                    self.assertEqual(client.post(f"/runs/{run_id}/dismiss").status_code, 200)
                    self.assertEqual(client.post(f"/runs/{run_id}/confirm").status_code, 409)
                    build.assert_not_called()
                    events = client.get(f"/runs/{run_id}").json()["events"]
                    self.assertEqual(events[-1]["type"], "lesson_dismissed")


class LessonCompilationContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_builder_emits_canonical_artifact_counts_after_real_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(runs_dir=Path(directory), _env_file=None))
            orchestrator = app.state.orchestrator
            root = Path(directory) / "grad_compile"
            root.mkdir()
            process = AsyncMock(returncode=0)
            process.communicate.return_value = (b"test-image\n", b"")
            with patch("gradient.codex.agents.generate", AsyncMock(return_value=curriculum())), patch(
                "gradient.orchestrator.asyncio.create_subprocess_exec", AsyncMock(return_value=process)
            ):
                await orchestrator.build_lesson(root, candidate())
            events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
            compiled = next(e for e in events if e["type"] == "curriculum_compiled")
            self.assertEqual((compiled["train_count"], compiled["unseen_count"]), (8, 4))
            self.assertEqual(len(list((root / "envs" / "train").iterdir())), 8)
            self.assertTrue((root / "manifest.json").is_file())
            await orchestrator.close()


if __name__ == "__main__":
    unittest.main()
