import hashlib
import json
from pathlib import Path

from gradient.schemas import Curriculum, TaskSpec

VERSION = "3"


def render(spec: TaskSpec) -> tuple[str, str]:
    args = {"filesystem": "path, data", "json": "path", "subprocess": "helper_path"}
    contracts = {
        "filesystem": "path names a UTF-8 file; data is the exact replacement text. "
                      "An applied operation returns None; a proposed operation returns {'path': path, 'data': data}.",
        "json": "path names a JSON object with an integer count and other keys to preserve. "
                "The operation increments count by one. An applied operation returns None; "
                "a proposed operation returns the projected object.",
        "subprocess": "The command is [sys.executable, helper_path]. An applied operation returns "
                      "the helper's UTF-8 stdout without its trailing newline; a proposed operation returns the command list.",
    }
    starter = ("import json\nimport subprocess\nimport sys\nfrom pathlib import Path\n\n"
               f"def {spec.function_name}({args[spec.family]}):\n    raise NotImplementedError\n")
    prompt = ("Keep the implementation short. For file operations, use direct file I/O without "
              "temporary files or helper processes. To capture helper stdout, "
              "subprocess.check_output(command, text=True) returns text.\n\n"
              f"{spec.prompt}\n\nInterface: {contracts[spec.family]}\n"
              f"Paths are strings. Use Python standard library only. Keep any imports your solution uses.\n\nsolution.py:\n{starter}")
    return prompt, starter


def compile_curriculum(curriculum: Curriculum, root: Path) -> dict[str, str]:
    hashes = {}
    for spec in curriculum.tasks:
        target = root / spec.split / spec.id
        target.mkdir(parents=True, exist_ok=False)
        prompt, starter = render(spec)
        files = {"prompt.txt": prompt, "starter.py": starter,
                 "metadata.json": spec.model_dump_json(indent=2),
                 "verifier.py": (Path(__file__).parents[1] / "sandbox" / "supervisor.py").read_text(encoding="utf-8"),
                 "verifier.json": json.dumps({"template_version": VERSION,
                                               "family": spec.family, "mode": spec.mode})}
        for name, content in files.items():
            (target / name).write_text(content, encoding="utf-8")
        hashes[spec.id] = environment_hash(target)
    return hashes


def environment_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for name in ("metadata.json", "prompt.txt", "starter.py", "verifier.py", "verifier.json"):
        digest.update(name.encode() + b"\0" + (path / name).read_bytes() + b"\0")
    return digest.hexdigest()
