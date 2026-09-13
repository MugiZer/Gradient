import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from gradient.codex.client import strict_schema
from gradient.curriculum.compiler import compile_curriculum, environment_hash, render
from gradient.schemas import Curriculum, LearningEvent, TaskSpec
from gradient.student.agent import Workspace


def curriculum():
    tasks = []
    for i in range(12):
        tasks.append(TaskSpec(id=f"task_{i}", family=("filesystem", "json", "subprocess")[i % 3],
                              mode="execute" if i % 2 == 0 else "simulate",
                              prompt=f"Unique requirement {i}", split="train" if i < 8 else "heldout",
                              function_name=f"perform_{i}"))
    return Curriculum(tasks=tasks)


def solution(spec, correct=True):
    mode = spec.mode if correct else ("simulate" if spec.mode == "execute" else "execute")
    bodies = {
        ("filesystem", "execute"): "Path(path).write_text(data, encoding='utf-8')",
        ("filesystem", "simulate"): "return {'path': path, 'data': data}",
        ("json", "execute"): "obj=json.loads(Path(path).read_text()); obj['count']+=1; Path(path).write_text(json.dumps(obj))",
        ("json", "simulate"): "obj=json.loads(Path(path).read_text()); obj['count']+=1; return obj",
        ("subprocess", "execute"): "return subprocess.check_output([sys.executable, helper_path]).decode('utf-8').rstrip('\\n')",
        ("subprocess", "simulate"): "return [sys.executable, helper_path]",
    }
    starter = render(spec)[1]
    return "from pathlib import Path\nimport json, sys, subprocess\n" + starter.replace(
        "raise NotImplementedError", bodies[spec.family, mode])


class ContractsTest(unittest.TestCase):
    def test_codex_schema_requires_all_properties_without_changing_contract(self):
        original = LearningEvent.model_json_schema()
        strict = strict_schema(original)
        self.assertIn("id", strict["required"])
        self.assertNotIn("id", original["required"])
        nested = strict["$defs"]["Capability"]
        self.assertEqual(set(nested["required"]), set(nested["properties"]))

    def test_curriculum_freeze_and_boundary_validation(self):
        batch = curriculum()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = compile_curriculum(batch, root)
            path = root / "heldout" / "task_8"
            self.assertEqual(hashes["task_8"], environment_hash(path))
            (path / "prompt.txt").write_text("tampered")
            self.assertNotEqual(hashes["task_8"], environment_hash(path))
            with self.assertRaises(FileExistsError):
                compile_curriculum(batch, root)
        bad = batch.model_dump()
        bad["tasks"][-1]["function_name"] = bad["tasks"][0]["function_name"]
        with self.assertRaises(ValidationError):
            Curriculum.model_validate(bad)
        with self.assertRaises(ValidationError):
            TaskSpec.model_validate({**batch.tasks[0].model_dump(), "id": "../escape"})
        with self.assertRaises(ValidationError):
            LearningEvent(is_learning_event=True, confidence=1, rejected_behavior="x",
                          correction="x", capability=None)

    def test_bounded_workspace(self):
        workspace = Workspace("def solve(): pass", "solve")
        self.assertIn("Only solution.py", workspace.act('{"action":"read_file","path":"../verifier.py"}'))
        self.assertIn("Saved", workspace.act(json.dumps({"action": "write_file", "path": "solution.py", "content": "def solve():\n return 1"})))
        self.assertIn("passed", workspace.act('{"action":"run_tests"}'))
        self.assertIn("error", workspace.act("not json"))


if __name__ == "__main__":
    unittest.main()
