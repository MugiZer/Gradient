import asyncio
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

from gradient.provenance import backend_files, read_json, verify_frozen, write_json
from gradient.schemas import TrainingResult, now


def training_directory(root):
    retries = list((root / "execution").glob("training_retry*.json"))
    if retries:
        numbers = [read_json(path)["attempt"] for path in retries]
        if any(type(number) is not int or number < 1 for number in numbers):
            raise ValueError("Invalid training retry number")
        number = max(numbers)
        return root / "training" / "attempts" / str(number)
    return root / "training"


def serving_model(model, adapter_id):
    return f"{model}:{adapter_id}"


async def prime(*args, raw=False, environment=None, transcript=None):
    environment = {**os.environ, **(environment or {}), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    process = await asyncio.create_subprocess_exec(
        "prime", "--plain", *args, env=environment, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 180)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    stdout, stderr = stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    for name, value in environment.items():
        if value and (name.endswith("API_KEY") or name.endswith("TOKEN")):
            stdout, stderr = stdout.replace(value, "<REDACTED>"), stderr.replace(value, "<REDACTED>")
    if transcript:
        write_json(transcript, {"timestamp": now(), "args": args, "exit_code": process.returncode,
                               "stdout": stdout, "stderr": stderr})
    if process.returncode:
        raise RuntimeError("Prime command failed: " + (stdout + stderr)[-3000:])
    return stdout if raw else json.loads(stdout)


def export(root, owner, max_steps=30):
    manifest = verify_frozen(root)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", owner):
        raise ValueError("Invalid Prime owner")
    baseline = read_json(root / "baseline" / "results.json")
    train = [r for r in baseline["results"] if r["split"] == "train"]
    if any(r.get("verifier_reason") in {"Candidate failed", "Candidate timed out"} for r in train):
        raise ValueError("Calibration required: fix basic candidate runtime failures before training")
    rate = sum(r["reward"] for r in train) / len(train)
    if not 0.2 <= rate <= 0.7:
        raise ValueError(f"Calibration required: training baseline pass rate is {rate:.0%}")
    target = training_directory(root) / "package"
    target.mkdir(parents=True, exist_ok=False)
    version = "0.1." + str(int(hashlib.sha256(root.name.encode()).hexdigest()[:12], 16))
    package = Path(__file__).parents[1]
    for source in backend_files():
        destination = target / "gradient" / source.relative_to(package)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    specs = [read_json(path / "metadata.json") for path in sorted((root / "envs" / "train").iterdir())]
    write_json(target / "gradient" / "training" / "train_specs.json", specs)
    (target / "gradient_effects.py").write_text(
        "from gradient.training.environment import load_environment\n", encoding="utf-8")
    (target / "pyproject.toml").write_text('''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "gradient-effects"
version = "0.1.0"
dependencies = ["verifiers==0.1.14", "prime-sandboxes==0.2.42", "pydantic>=2,<3"]
[tool.setuptools]
py-modules = ["gradient_effects"]
[tool.setuptools.packages.find]
include = ["gradient*"]
[tool.setuptools.package-data]
"gradient.training" = ["train_specs.json"]
"gradient.codex" = ["skills/*/SKILL.md"]
'''.replace('version = "0.1.0"', f'version = "{version}"'), encoding="utf-8")
    (target / "README.md").write_text("# Gradient effects\nGenerated training split only. Requires PRIME_API_KEY for isolated reward execution.\n", encoding="utf-8")
    config = (f'model = {json.dumps(manifest["model"])}\nmax_steps = {max_steps}\n'
              'batch_size = 32\nrollouts_per_example = 4\nmax_inflight_rollouts = 8\n'
              '[sampling]\nmax_tokens = 2048\ntemperature = 1.0\nenable_thinking = false\n'
              'extra_body = { presence_penalty = 2.0, response_format = { type = "json_object" } }\n'
              f'[[env]]\nid = "{owner}/gradient-effects@{version}"\n'
              f'args = {{ max_turns = {manifest["decoding"]["max_turns"]} }}\n')
    (training_directory(root) / "config.toml").write_text(config, encoding="utf-8")
    write_json(training_directory(root) / "export.json", {"owner": owner, "exported_at": now(),
               "files": package_hashes(root), "train_pass_rate": rate})
    return target


def package_hashes(root):
    return {p.relative_to(training_directory(root)).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((training_directory(root)).rglob("*"))
            if p.is_file() and p.suffix in {".py", ".json", ".toml", ".md"}
            and (p.parent == training_directory(root) and p.name == "config.toml"
                 or p.parent == training_directory(root) / "package"
                 or p.is_relative_to(training_directory(root) / "package" / "gradient"))}


async def launch(root):
    verify_frozen(root)
    if package_hashes(root) != read_json(training_directory(root) / "export.json")["files"]:
        raise ValueError("Training export changed")
    read_json(training_directory(root) / "publish.json")
    from prime_sandboxes.core.config import Config
    key = Config().api_key
    if not key:
        raise ValueError("Prime sandbox API key is required for hosted rewards")
    config = training_directory(root) / "config.toml"
    if training_directory(root) == root / "training" and (root / "execution" / "manifest.json").exists():
        config = root / "execution" / "config.toml"
        if hashlib.sha256(config.read_bytes()).hexdigest() != read_json(root / "execution" / "manifest.json")["training_config_hash"]:
            raise ValueError("Sealed training configuration changed")
    write_json(training_directory(root) / "launch.json", {"requested_at": now()})
    output = await prime("train", "run", str(config), "--yes", "--output", "json",
                         "-e", "PRIME_API_KEY", raw=True, environment={**os.environ, "PRIME_API_KEY": key},
                         transcript=training_directory(root) / "launch_transcript.json")
    write_json(training_directory(root) / "launch_output.json", {"output": output.replace(key, "<REDACTED>")})
    # Prime prints a configuration banner before its JSON even with --output json.
    start = list(re.finditer(r"(?m)^\{", output))[-1].start()
    result = json.loads(output[start:])
    write_json(training_directory(root) / "run.json", result)
    return result


async def publish(root):
    verify_frozen(root)
    exported = read_json(training_directory(root) / "export.json")
    if package_hashes(root) != exported["files"]:
        raise ValueError("Training export changed")
    if (training_directory(root) / "publish.json").exists():
        return read_json(training_directory(root) / "publish.json")
    identity = await prime("whoami", raw=True)
    personal_owner = (re.search(r"(?m)^Type\s+Personal\s*$", identity)
                      and re.search(r"(?m)^Username\s+" + re.escape(exported["owner"]) + r"\s*$", identity))
    ownership = () if personal_owner else ("--owner", exported["owner"])
    published = await prime("env", "push", "--path", str(training_directory(root) / "package"),
                            *ownership, "--visibility", "PRIVATE", raw=True,
                            transcript=training_directory(root) / "publish_attempts" / (uuid4().hex + ".json"))
    record = {"output": published, "published_at": now()}
    write_json(training_directory(root) / "publish.json", record)
    return record


async def deploy(root):
    if (training_directory(root) / "deployment.json").exists():
        return read_json(training_directory(root) / "deployment.json")
    result = read_json(training_directory(root) / "result.json")
    output = await prime("deployments", "create", result["adapter_id"], "--yes", raw=True)
    record = {"model": serving_model(result["model"], result["adapter_id"]), "output": output}
    write_json(training_directory(root) / "deployment.json", record)
    return record


async def collect(root, adapter_id):
    verify_frozen(root)
    launched = read_json(training_directory(root) / "run.json")["run"]
    record = (await prime("train", "get", launched["id"], "--output", "json"))["run"]
    if record["status"].upper() != "COMPLETED":
        raise ValueError(f"Training is {record['status']}")
    if record["base_model"] != read_json(root / "manifest.json")["model"]:
        raise ValueError("Training base model changed")
    adapters = (await prime("deployments", "list", "--output", "json", "--num", "100"))["models"]
    adapter = next((a for a in adapters if a["id"] == adapter_id), None)
    if not adapter or adapter.get("base_model") != record["base_model"]:
        raise ValueError("Adapter missing or belongs to another base model")
    if adapter.get("rft_run_id") != record["id"] or adapter.get("status") != "READY":
        raise ValueError("Prime did not confirm adapter provenance for this training run")
    result = TrainingResult(run_id=record["id"], adapter_id=adapter_id, model=record["base_model"],
                            started_at=record["started_at"], finished_at=record["completed_at"])
    metrics = await prime("train", "metrics", record["id"])
    write_json(training_directory(root) / "completed.json", {"run": record, "adapter": adapter})
    with (training_directory(root) / "logs.jsonl").open("x", encoding="utf-8") as stream:
        for metric in metrics["metrics"]:
            stream.write(json.dumps(metric) + "\n")
    write_json(training_directory(root) / "result.json", result)
    return result


async def status(root):
    run_id = read_json(training_directory(root) / "run.json")["run"]["id"]
    return await prime("train", "get", run_id, "--output", "json")


async def capture(root):
    record = await status(root)
    run_id = record["run"]["id"]
    target = training_directory(root) / "snapshots" / uuid4().hex
    write_json(target / "status.json", {"captured_at": now(), **record})
    for name, args, raw in (
        ("metrics", ("metrics", run_id), False),
        ("progress", ("progress", run_id), False),
        ("logs", ("logs", run_id, "--raw", "--tail", "10000"), True),
        ("environment_logs", ("logs", run_id, "--env", "gradient-effects/0", "--raw", "--tail", "10000"), True),
    ):
        try:
            write_json(target / f"{name}.json", await prime("train", *args, raw=raw))
        except Exception as exc:
            write_json(target / f"{name}.error.json", {"error": str(exc)})
    if (target / "progress.json").exists():
        progress = read_json(target / "progress.json")
        for step in progress.get("steps_with_samples", []):
            if step == progress.get("latest_step") and record["run"]["status"].upper() not in {"COMPLETED", "FAILED", "STOPPED"}:
                continue
            page = 1
            while True:
                path = training_directory(root) / "rollouts" / f"step_{step}_page_{page}.json"
                if path.exists():
                    samples = read_json(path)
                else:
                    samples = await prime("train", "rollouts", run_id, "--step", str(step), "--page", str(page))
                    write_json(path, samples)
                if page >= samples.get("total_pages", 1):
                    break
                page += 1
    return record


async def ready_adapter(root):
    run_id = read_json(training_directory(root) / "run.json")["run"]["id"]
    adapters = (await prime("deployments", "list", "--output", "json", "--num", "100"))["models"]
    return next((a["id"] for a in adapters if a.get("rft_run_id") == run_id and a.get("status") == "READY"), None)


async def wait_deployment(root):
    adapter_id = read_json(training_directory(root) / "result.json")["adapter_id"]
    for _ in range(60):
        models = (await prime("deployments", "list", "--output", "json", "--num", "100"))["models"]
        adapter = next((a for a in models if a["id"] == adapter_id), None)
        write_json(training_directory(root) / "deployment_status" / (uuid4().hex + ".json"),
                   {"timestamp": now(), "adapter": adapter})
        if adapter and adapter["deployment_status"] == "DEPLOYED":
            return
        if adapter and adapter["deployment_status"] == "FAILED":
            raise RuntimeError("Prime adapter deployment failed")
        await asyncio.sleep(10)
    raise TimeoutError("Prime adapter has not become available for inference")
