import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from gradient.config import Settings
from gradient.curriculum.compiler import compile_curriculum
from gradient.orchestrator import Orchestrator
from gradient.provenance import freeze, freeze_continuation, read_json, verify_frozen, write_json
from gradient.schemas import Decoding, RolloutResult
from gradient.training.execution import rounds
from tests.test_backend import curriculum


class ExecutionTest(unittest.IsolatedAsyncioTestCase):
    async def test_same_inputs_all_rounds_preserved_and_original_evidence_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(curriculum(), root / "envs")
            freeze(root, hashes, "qwen", Decoding(), "image", "http://model")
            for name in ("interaction.json", "event.json", "capability.json", "training/export.json"):
                write_json(root / name, {})
            (root / "training/config.toml").write_text('model = "qwen"')
            (root / "execution").mkdir()
            (root / "execution/config.toml").write_text('model = "qwen"\nmax_steps = 60')
            freeze_continuation(root)
            app = Orchestrator(Settings(runs_dir=root, inference_url="http://model", _env_file=None))
            student = AsyncMock()
            student.solve.return_value = ("source", [{"role": "assistant", "content": "action"}])
            runner = AsyncMock()
            runner.run.return_value = RolloutResult(task_id="task", reward=0, verifier_reason="fixture", duration_ms=1)
            with patch("gradient.training.execution.QwenStudent", return_value=student), patch(
                "gradient.training.execution.DockerRunner", return_value=runner
            ):
                await rounds(app, root, "pre_repeat", 1)
                before = student.solve.call_args_list.copy()
                write_json(root / "training/result.json", {"adapter_id": "adapter"})
                await rounds(app, root, "post", 1)
                self.assertEqual(before, student.solve.call_args_list[12:])
                self.assertEqual(runner.run.call_args_list[:12], runner.run.call_args_list[12:])
                await rounds(app, root, "post", 1)
                self.assertEqual(student.solve.await_count, 24)
            record = read_json(root / "execution/post/0/task_0.json")
            self.assertEqual(record["reward"], 0)
            self.assertEqual(record["adapter_id"], "adapter")
            (root / "interaction.json").write_text("changed")
            with self.assertRaisesRegex(ValueError, "Original evidence"):
                verify_frozen(root)
            await app.close()
