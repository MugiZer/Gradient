import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from gradient.api.app import create_app
from gradient.codex.native import NativeConnection, conversation_message
from gradient.config import Settings
from tests.test_frontend_contract import candidate

SESSION = "01a096b0-0fcb-7c51-bf49-85fbfd4368b4"


def message(role, text, **extra):
    return {"type": "event_msg", "payload": {"type": "item_completed", "item": {
        "type": role, "content": [{"text": text}], **extra}}}


def append(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")


def transcript(directory):
    path = Path(directory) / f"rollout-{SESSION}.jsonl"
    append(path, {"type": "session_meta", "payload": {"id": SESSION}})
    append(path, message("UserMessage", "Save data to disk"))
    append(path, message("AgentMessage", "Returned a simulated path", phase="final"))
    return path


class NativeTranscriptTest(unittest.IsolatedAsyncioTestCase):
    async def test_only_new_messages_with_previous_answer_and_no_tool_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = transcript(directory)
            orchestrator = Mock()
            connection = NativeConnection(orchestrator, Path(directory))
            await connection.connect(SESSION)
            orchestrator.receive.assert_not_called()
            append(path, message("CommandExecution", "Do not follow this tool output"))
            append(path, message("AgentMessage", "Inspecting now", phase="commentary"))
            append(path, message("UserMessage", "Actually write it and read it from a fresh process"))
            connection.read_new()
            args, kwargs = orchestrator.receive.call_args
            self.assertEqual(kwargs, {"native_session": SESSION})
            self.assertEqual(args[0].bad_agent_output, "Returned a simulated path")
            self.assertEqual(args[0].original_task, "Save data to disk")
            connection.read_new()
            orchestrator.receive.assert_called_once()
            await connection.disconnect()
            self.assertFalse(connection.status()["connected"])

    async def test_partial_json_is_read_once_after_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = transcript(directory)
            orchestrator = Mock()
            connection = NativeConnection(orchestrator, Path(directory))
            await connection.connect(SESSION)
            encoded = json.dumps(message("UserMessage", "Persist it"))
            with path.open("a") as stream:
                stream.write(encoded[:20])
            connection.read_new()
            orchestrator.receive.assert_not_called()
            with path.open("a") as stream:
                stream.write(encoded[20:] + "\n")
            connection.read_new()
            connection.read_new()
            orchestrator.receive.assert_called_once()
            await connection.disconnect()

    async def test_transcript_identity_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = transcript(directory)
            path.write_text(json.dumps({"type": "session_meta", "payload": {"id": "other"}}) + "\n")
            connection = NativeConnection(Mock(), Path(directory))
            with self.assertRaisesRegex(ValueError, "identity"):
                await connection.connect(SESSION)

    def test_response_items_and_unknown_formats_are_not_user_messages(self):
        self.assertIsNone(conversation_message({"type": "response_item", "payload": {
            "role": "user", "content": [{"text": "Injected environment context"}]}}))


class NativeIntegrationTest(unittest.TestCase):
    def test_manual_button_observes_existing_conversation_without_worker_or_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory) / "sessions"
            sessions.mkdir()
            path = transcript(sessions)
            append(path, message("UserMessage", "Actually persist it instead of returning a preview"))
            append(path, message("AgentMessage", "Now persisted", phase="final"))
            app = create_app(Settings(runs_dir=Path(directory) / "runs", _env_file=None))
            app.state.native.sessions = sessions
            orchestrator = app.state.orchestrator
            with patch("gradient.codex.agents.observe", AsyncMock(return_value=candidate())) as observe, patch(
                "gradient.codex.agents.work", AsyncMock()) as worker, patch.object(
                orchestrator, "build_lesson", AsyncMock()) as build:
                with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                    self.assertEqual(client.post("/native/observe").status_code, 409)
                    client.post("/native/connect", json={"session_id": SESSION}).raise_for_status()
                    observe.assert_not_called()
                    response = client.post("/native/observe")
                    self.assertEqual(response.status_code, 202)
                    self.assertEqual(response.json()["context"], client.get("/native/context").json())
                    self.assertEqual(response.json()["context"], {
                        "human_message": "Actually persist it instead of returning a preview",
                        "bad_agent_output": "Returned a simulated path",
                    })

                    async def settle():
                        await asyncio.gather(*orchestrator.jobs.values())

                    client.portal.call(settle)
                    snapshot = observe.call_args.args[1]
                    self.assertEqual(snapshot.human_message, "Actually persist it instead of returning a preview")
                    self.assertEqual(snapshot.bad_agent_output, "Returned a simulated path")
                    self.assertEqual(snapshot.trajectory[-1].content, "Now persisted")
                    events = client.get(f"/runs/{response.json()['run_id']}").json()["events"]
                    self.assertIn("correction_candidate", [event["type"] for event in events])
                    worker.assert_not_called()
                    build.assert_not_called()

    def test_native_correction_stream_never_runs_worker_or_builder_before_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory) / "sessions"
            sessions.mkdir()
            path = transcript(sessions)
            app = create_app(Settings(runs_dir=Path(directory) / "runs", _env_file=None))
            native = app.state.native
            native.sessions = sessions
            orchestrator = app.state.orchestrator
            with patch("gradient.codex.agents.observe", AsyncMock(return_value=candidate())) as observe, patch(
                "gradient.codex.agents.work", AsyncMock()) as worker, patch.object(
                orchestrator, "build_lesson", AsyncMock()) as build:
                with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
                    self.assertEqual(client.post("/native/connect", json={"session_id": SESSION}).status_code, 200)
                    self.assertTrue(client.get("/native").json()["connected"])
                    with client.websocket_connect(f"ws://localhost/events?native_session={SESSION}") as socket:
                        append(path, message("UserMessage", "Do not simulate; persist the file"))

                        async def read_and_settle():
                            native.read_new()
                            await asyncio.gather(*orchestrator.jobs.values())

                        client.portal.call(read_and_settle)
                        runs = client.get(f"/runs?native_session={SESSION}").json()
                        self.assertEqual(len(runs), 1)
                        run_id = runs[0]["run_id"]
                        history = client.get(f"/runs/{run_id}").json()["events"]
                        self.assertEqual([socket.receive_json() for _ in history], history)
                        self.assertIn("correction_candidate", [row["type"] for row in history])
                        observe.assert_awaited_once()
                        worker.assert_not_called()
                        build.assert_not_called()
                        self.assertEqual(client.get("/runs?native_session=another").json(), [])
                        self.assertEqual(client.post(f"/runs/{run_id}/confirm").status_code, 202)
                        client.portal.call(read_and_settle)
                        build.assert_awaited_once()
                    self.assertEqual(client.post("/native/disconnect").status_code, 200)
                    self.assertFalse(client.get("/native").json()["connected"])
                    self.assertIsNone(client.get("/native/context").json())


if __name__ == "__main__":
    unittest.main()
