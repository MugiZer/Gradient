import hashlib
import json
import secrets
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from gradient.curriculum.compiler import environment_hash
from gradient.schemas import now


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def backend_files():
    package = Path(__file__).parent
    return sorted([*package.rglob("*.py"), *package.glob("codex/skills/*/SKILL.md")])


def engine_hash():
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in backend_files():
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def freeze(root, hashes, model, decoding, image, inference_url=None):
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    package = Path(__file__).parent
    for source in backend_files():
        target = root / "source" / "gradient" / source.relative_to(package)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output, source.open("rb") as original:
            shutil.copyfileobj(original, output)
    write_json(root / "manifest.json", {
        "frozen_at": now(), "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "engine_hash": engine_hash(), "environments": hashes, "model": model,
        "git_dirty": bool(status.stdout.strip()), "inference_url": inference_url,
        "decoding": decoding.model_dump(), "sandbox_image": image,
        "seeds": {task_id: secrets.randbits(32) for task_id in hashes},
    })


def verify_frozen(root):
    manifest = read_json(root / "manifest.json")
    continuation_path = root / "execution" / "manifest.json"
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        if continuation["engine_hash"] != engine_hash():
            raise ValueError("Execution source changed since continuation was sealed")
        for name, digest in continuation["original_files"].items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Original evidence changed: {name}")
    elif manifest["engine_hash"] != engine_hash():
        raise ValueError("Backend changed since freeze; start a new experiment")
    found = {p.name: environment_hash(p) for split in ("train", "heldout")
             for p in (root / "envs" / split).iterdir()}
    if found != manifest["environments"]:
        raise ValueError("Frozen curriculum has changed")
    return manifest


def freeze_continuation(root):
    protected = ("schemas.py", "student/agent.py", "student/model.py", "student/evaluate.py",
                 "sandbox/runner.py", "sandbox/supervisor.py", "curriculum/compiler.py")
    package = Path(__file__).parent
    for name in protected:
        if (package / name).read_bytes() != (root / "source" / "gradient" / name).read_bytes():
            raise ValueError(f"Frozen evaluation code differs: {name}")
    original = [root / name for name in ("manifest.json", "interaction.json", "event.json", "capability.json",
                                         "training/config.toml", "training/export.json")]
    for directory in ("envs", "curriculum", "baseline", "source"):
        original.extend(p for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for source in backend_files():
        target = root / "execution" / "source" / "gradient" / source.relative_to(package)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(source.read_bytes())
    write_json(root / "execution" / "manifest.json", {
        "sealed_at": now(), "engine_hash": engine_hash(), "evaluation_files_unchanged": list(protected),
        "original_files": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in original},
        "plan": {"calibration_per_train_task": 8, "pre_rounds": 2, "post_rounds": 2,
                 "max_steps": 60, "batch_size": 32, "rollouts_per_example": 8},
        "training_config_hash": hashlib.sha256((root / "execution" / "config.toml").read_bytes()).hexdigest(),
    })
