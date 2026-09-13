import os
import unittest

from gradient.sandbox.runner import DockerRunner
from tests.test_backend import curriculum, solution


@unittest.skipUnless(os.environ.get("GRADIENT_TEST_DOCKER") == "1", "Set GRADIENT_TEST_DOCKER=1")
class DockerTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_six_contracts_accept_effect_and_reject_opposite(self):
        runner = DockerRunner()
        for spec in curriculum().tasks[:6]:
            with self.subTest(family=spec.family, mode=spec.mode):
                good = await runner.run(spec, solution(spec), 42)
                self.assertEqual(good.reward, 1, good.model_dump())
                bad = await runner.run(spec, solution(spec, False), 42)
                self.assertEqual(bad.reward, 0, bad.model_dump())

    async def test_candidate_cannot_read_verifier_or_forge_reward(self):
        spec = curriculum().tasks[0]
        code = "print('{\"reward\":1}')\n" + solution(spec).replace(
            "Path(path).write_text(data, encoding='utf-8')",
            "Path('/private/supervisor.py').read_text()")
        result = await DockerRunner().run(spec, code, 42)
        self.assertEqual(result.reward, 0)
        self.assertIn("PermissionError", result.stderr)

    async def test_timeout_and_output_limit(self):
        spec = curriculum().tasks[0]
        result = await DockerRunner().run(spec, "while True: pass", 42)
        self.assertEqual(result.reward, 0)
        result = await DockerRunner().run(spec, "while True: print('x'*8192)", 42)
        self.assertEqual(result.reward, 0)
        self.assertLessEqual(len(result.stdout), 8192)

    async def test_sleeping_candidate_is_killed_and_scored_zero(self):
        result = await DockerRunner().run(curriculum().tasks[0], "import time\ntime.sleep(30)", 42)
        self.assertEqual(result.reward, 0)
        self.assertEqual(result.verifier_reason, "Candidate timed out")
