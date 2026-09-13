import asyncio
import json
import os
from pathlib import Path

from gradient.schemas import InteractionSnapshot, TrajectoryStep, now


def conversation_message(row):
    """Read completed conversation items, never tool output or injected instructions."""
    if row.get("type") != "event_msg":
        return None
    event = row.get("payload", {})
    if event.get("type") == "item_completed":
        item = event.get("item", {})
        if item.get("type") not in {"UserMessage", "AgentMessage"}:
            return None
        if item["type"] == "AgentMessage" and item.get("phase") == "commentary":
            return None
        text = "\n".join(c["text"] for c in item.get("content", [])
                         if isinstance(c.get("text"), str))
        return ("user" if item["type"] == "UserMessage" else "assistant", text)
    if event.get("type") in {"user_message", "agent_message"}:
        return ("user" if event["type"] == "user_message" else "assistant",
                event.get("message", ""))
    return None


class NativeConnection:
    def __init__(self, orchestrator, sessions=None):
        self.orchestrator = orchestrator
        self.sessions = sessions or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
        self.task = None
        self.session_id = self.path = self.error = self.last_message_at = None
        self.offset = 0
        self.original = self.answer = ""
        self.latest_snapshot = None
        self.recent = []
        self.observation_run = None

    def status(self):
        return {"session_id": self.session_id, "connected": bool(self.task and not self.task.done()),
                "error": self.error, "last_message_at": self.last_message_at}

    async def connect(self, session_id):
        matches = list(self.sessions.rglob(f"*{session_id}.jsonl"))
        if len(matches) != 1:
            raise ValueError("The selected Codex task has no unique local transcript")
        path = matches[0].resolve()
        if not path.is_relative_to(self.sessions.resolve()):
            raise ValueError("Transcript must be inside Codex sessions")
        with path.open(encoding="utf-8") as stream:
            metadata = json.loads(stream.readline())
        if metadata.get("type") != "session_meta" or metadata["payload"].get("id") != session_id:
            raise ValueError("Transcript identity does not match the selected task")
        if self.session_id == session_id and self.task and not self.task.done():
            return self.status()
        await self.disconnect()
        self.session_id, self.path = session_id, path
        self.offset = 0
        self.original = self.answer = ""
        self.latest_snapshot = None
        self.recent = []
        self.observation_run = None
        self.error = self.last_message_at = None
        # Seed context without analyzing old turns. Only newly appended corrections trigger work.
        self.read_new(observe=False)
        self.task = asyncio.create_task(self.watch())
        return self.status()

    def read_new(self, *, observe=True):
        if self.path.stat().st_size < self.offset:
            raise ValueError("Codex transcript was replaced; reconnect Gradient to this task")
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            while line := stream.readline():
                if not line.endswith(b"\n"):
                    break  # Keep the offset before a partially written JSON record.
                row = json.loads(line)
                self.offset = stream.tell()
                message = conversation_message(row)
                if not message:
                    continue
                role, text = message
                if not text.strip():
                    continue
                self.last_message_at = row.get("timestamp", now())
                self.recent = (self.recent + [TrajectoryStep(role=role, content=text[-8000:])])[-12:]
                if role == "assistant":
                    self.answer = text[-32000:]
                else:
                    self.original = self.original or text[:16000]
                    self.latest_snapshot = InteractionSnapshot(
                        original_task=self.original, human_message=text[:16000],
                        bad_agent_output=self.answer)
                    if observe:
                        self.orchestrator.receive(self.latest_snapshot, native_session=self.session_id)

    def observe_lesson(self):
        if not self.status()["connected"]:
            raise ValueError("Connect a Codex task before looking for a lesson")
        if self.observation_run in self.orchestrator.jobs:
            return self.observation_run
        self.read_new(observe=False)
        if self.latest_snapshot is None:
            raise ValueError("This task has no conversation to observe yet")
        snapshot = self.latest_snapshot.model_copy(update={"trajectory": list(self.recent)})
        self.observation_run = self.orchestrator.receive(snapshot, native_session=self.session_id)
        return self.observation_run

    async def watch(self):
        try:
            while True:
                self.read_new()
                await asyncio.sleep(1)
        except (OSError, ValueError, TypeError) as exc:
            self.error = str(exc)

    async def disconnect(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.task = None
        self.session_id = None
        return self.status()
