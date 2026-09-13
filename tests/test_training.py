import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, patch

from gradient.schemas import RolloutResult
from tests.test_backend import curriculum, solution


@unittest.skipUnless(os.environ.get("GRADIENT_TEST_TRAINING") == "1", "Install the training extra and set GRADIENT_TEST_TRAINING=1")
class TrainingBridgeTest(unittest.IsolatedAsyncioTestCase):
    async def test_real_verifiers_loader_and_typed_action_messages(self):
        from verifiers.types import AssistantMessage

        from gradient.training.environment import load_environment, replay

        specs = curriculum().tasks[:8]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "specs.json"
            path.write_text(json.dumps([s.model_dump() for s in specs]), encoding="utf-8")
            env = load_environment(path, backend="docker")
            self.assertEqual(len(env.dataset), 8)
            spec = specs[0]
            messages = [AssistantMessage(content=json.dumps({"action": "write_file", "path": "solution.py",
                                                             "content": solution(spec)})),
                        AssistantMessage(content='{"action":"finish"}')]
            workspace, _ = replay(spec, messages)
            self.assertEqual(workspace.code, solution(spec))
            state = {"info": {"spec": spec.model_dump()}}
            await env.env_response(messages, state)
            self.assertIn("final_env_response", state)
            reward = next(f for f in env.rubric._get_reward_funcs() if f.__name__ == "reward")
            result = RolloutResult(task_id=spec.id, reward=1, verifier_reason="fixture", duration_ms=1)
            trace = io.StringIO()
            with redirect_stdout(trace), patch("gradient.sandbox.runner.DockerRunner.run", AsyncMock(return_value=result)) as run:
                self.assertEqual(await reward(messages, {"spec": spec.model_dump()}), 1)
                self.assertEqual(run.call_args.args[:2], (spec, solution(spec)))
            start, finish = [json.loads(line.split(" ", 1)[1]) for line in trace.getvalue().splitlines()]
            self.assertEqual(start["seed"], run.call_args.args[2])
            self.assertEqual(start["spec"], spec.model_dump())
            self.assertEqual(start["code"], solution(spec))
            self.assertEqual(start["messages"][0]["role"], "assistant")
            self.assertEqual(start["id"], finish["id"])
            self.assertEqual(finish["reward"], 1)
            path.write_text(json.dumps([curriculum().tasks[-1].model_dump()]))
            with self.assertRaisesRegex(ValueError, "training tasks only"):
                load_environment(path, backend="docker")
