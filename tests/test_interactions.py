import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from gradient.api.app import create_app
from gradient.config import Settings
from gradient.provenance import read_json
from gradient.schemas import InteractionSnapshot, LearningEvent
from tests.test_backend import curriculum


class InteractionTest(unittest.TestCase):
    def test_correction_compiles_frozen_curriculum_and_streams_events(self):
        event = LearningEvent(
            is_learning_event=True, confidence=1, rejected_behavior="Returned a preview",
            correction="Persist the change", capability={
                "name": "observable_effect", "description": "Distinguish effects from previews",
                "positive_rule": "Apply requested changes", "negative_rule": "Preserve state for previews",
            },
        )
        process = AsyncMock(returncode=0)
        process.communicate.return_value = (b"sha256:frozen-image\n", b"")
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(runs_dir=Path(directory), _env_file=None))
            with patch("gradient.codex.agents.observe", AsyncMock(return_value=event)), patch(
                "gradient.codex.agents.work", AsyncMock(return_value="fixed")
            ), patch("gradient.codex.agents.generate", AsyncMock(return_value=curriculum())) as generate, patch(
                "gradient.orchestrator.asyncio.create_subprocess_exec", AsyncMock(return_value=process)
            ), TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                with client.websocket_connect("ws://localhost/events") as socket:
                    response = client.post("/interactions", json={
                        "original_task": "Persist the counter", "human_message": "Actually update the file",
                    })
                    self.assertEqual(response.status_code, 202)
                    run_id = response.json()["run_id"]
                    self.assertEqual(client.post(f"/runs/{run_id}/confirm").status_code, 202)
                    events = []
                    while not any(e["type"] == "curriculum_compiled" for e in events):
                        streamed = socket.receive_json()
                        self.assertNotEqual(streamed.get("state"), "FAILED", streamed)
                        events.append(streamed)
                    self.assertTrue(all(e["run_id"] == run_id for e in events))
                root = Path(directory) / run_id
                manifest = read_json(root / "manifest.json")
                self.assertEqual(len(manifest["environments"]), 12)
                self.assertEqual(len(read_json(root / "curriculum" / "heldout_specs.json")), 4)
                self.assertEqual(len(list((root / "envs" / "train").glob("*/verifier.py"))), 8)
                self.assertEqual(generate.await_args.args[1], event.capability)
                self.assertIn("CAPABILITY_EXTRACTED", [e.get("state") for e in events])

    def test_api_preserves_captured_evidence_for_observer(self):
        snapshot = InteractionSnapshot(
            original_task="Persist the counter increment.",
            bad_agent_output="return count + 1",
            human_message="The file is still unchanged.",
            starter_state=[{"path": "counter.json", "content": '{"count": 3}'}],
            trajectory=[{"role": "tool", "content": "counter.json still contains 3"}],
            accepted_output="Persist the increment before returning.",
            runtime_evidence=[{"command": "python check_counter.py", "exit_code": 1,
                               "stdout": "Expected 4, got 3"}],
        )
        event = LearningEvent(is_learning_event=False, confidence=1,
                              rejected_behavior="", correction="", capability=None)
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Settings(runs_dir=Path(directory), _env_file=None))
            with patch("gradient.codex.agents.observe", AsyncMock(return_value=event)) as observer, patch(
                "gradient.codex.agents.work", AsyncMock(return_value="fixed")
            ) as worker, TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                response = client.post("/interactions", json=snapshot.model_dump())
                self.assertEqual(response.status_code, 202)
                run_id = response.json()["run_id"]

                async def finish():
                    job = app.state.orchestrator.jobs.get(run_id)
                    if job:
                        await job

                client.portal.call(finish)
                self.assertEqual(observer.await_args.args[1], snapshot)
                self.assertEqual(InteractionSnapshot.model_validate_json(worker.await_args.args[2]), snapshot)
                saved = read_json(Path(directory) / run_id / "interaction.json")
                self.assertEqual(saved, snapshot.model_dump())
                self.assertEqual(client.get(f"/runs/{run_id}").status_code, 200)
                invalid = snapshot.model_dump()
                invalid["runtime_evidence"][0]["exit_code"] = "not an exit code"
                self.assertEqual(client.post("/interactions", json=invalid).status_code, 422)

    def test_existing_minimal_payload_remains_valid(self):
        snapshot = InteractionSnapshot(original_task="Persist state", human_message="Actually write it")
        self.assertEqual(snapshot.starter_state, [])
        self.assertEqual(snapshot.trajectory, [])
        self.assertEqual(snapshot.runtime_evidence, [])
