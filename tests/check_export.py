"""Build and inspect a training wheel from an explicitly synthetic fixture."""
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

from gradient.codex.agents import role_skill
from gradient.curriculum.compiler import compile_curriculum
from gradient.provenance import freeze, read_json, write_json
from gradient.schemas import Decoding
from gradient.training.prime import export, package_hashes
from tests.test_backend import curriculum


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        batch = curriculum()
        hashes = compile_curriculum(batch, root / "envs")
        freeze(root, hashes, "fixture-model", Decoding(), "fixture-image")
        write_json(root / "baseline" / "results.json", {"results": [
            {"split": "train", "reward": i % 2} for i in range(8)]})
        target = export(root, "fixture-owner")
        subprocess.run(["uv", "build", "--wheel", str(target), "--out-dir", str(root / "dist")], check=True)
        assert package_hashes(root) == read_json(root / "training" / "export.json")["files"]
        wheel = next((root / "dist").glob("*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert "gradient_effects.py" in names
            assert "gradient/sandbox/supervisor.py" in names
            for role in ("worker", "observer", "environment"):
                assert archive.read(f"gradient/codex/skills/{role}/SKILL.md").decode() == role_skill(role)
            specs = json.loads(archive.read("gradient/training/train_specs.json"))
            assert len(specs) == 8 and all(spec["split"] == "train" for spec in specs)
            assert not any("heldout" in name for name in names)
        print("Training wheel built: entrypoint, trusted supervisor, and training-only dataset verified")


if __name__ == "__main__":
    main()
