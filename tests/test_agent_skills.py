import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from gradient.codex import agents
from gradient.provenance import engine_hash, freeze, read_json
from gradient.schemas import Capability, Decoding, InteractionSnapshot, LearningEvent
from tests.test_backend import curriculum


class AgentSkillsTest(unittest.IsolatedAsyncioTestCase):
    async def test_each_role_receives_its_skill_and_only_its_input(self):
        capability = Capability(name="observable_effect_vs_simulation", description="effect boundary",
                                positive_rule="make required state observable", negative_rule="preserve state for proposals")
        snapshot = InteractionSnapshot(original_task="private seed requirement", human_message="correction")
        event = LearningEvent(is_learning_event=True, confidence=1, rejected_behavior="simulated",
                              correction="perform the effect", capability=capability)
        with tempfile.TemporaryDirectory() as directory:
            client = Mock(threads={"observer": "old", "environment": "old"})
            client.context_dir.return_value = Path(directory)
            client.ask = AsyncMock(side_effect=["worker output", event.model_dump_json(),
                                                curriculum().model_dump_json()])
            await agents.work(client, Path(directory), snapshot.model_dump_json())
            await agents.observe(client, snapshot)
            await agents.generate(client, capability)
            for call, role in zip(client.ask.call_args_list, ("worker", "observer", "environment")):
                self.assertEqual(call.args[0], role)
                self.assertEqual(call.args[2], agents.role_skill(role))
                self.assertIn("Completion:", call.args[2])
            self.assertEqual(client.ask.call_args_list[1].args[3], snapshot.model_dump_json())
            self.assertEqual(client.ask.call_args_list[2].args[3], capability.model_dump_json())
            self.assertNotIn("private seed requirement", client.ask.call_args_list[2].args[2])
            self.assertFalse(client.threads)

    async def test_skill_content_is_frozen_and_changes_the_engine_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            freeze(root, {}, "fixture", Decoding(), "image")
            for role in ("worker", "observer", "environment"):
                saved = root / "source/gradient/codex/skills" / role / "SKILL.md"
                self.assertEqual(saved.read_text(encoding="utf-8"), agents.role_skill(role))
            before = read_json(root / "manifest.json")["engine_hash"]
            original = Path.read_bytes

            def changed(path):
                value = original(path)
                return value + b"changed skill" if path.name == "SKILL.md" else value

            with patch.object(Path, "read_bytes", changed):
                self.assertNotEqual(engine_hash(), before)
