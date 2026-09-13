"""Recorded rollout rounds for the existing frozen experiment."""
from gradient.provenance import read_json, verify_frozen, write_json
from gradient.sandbox.runner import DockerRunner
from gradient.schemas import Decoding, TaskSpec, now
from gradient.student.model import QwenStudent
from gradient.training.prime import serving_model


async def rounds(orchestrator, root, phase, count, *, training=False):
    manifest = verify_frozen(root)
    adapter = read_json(root / "training" / "result.json")["adapter_id"] if phase == "post" else None
    settings = orchestrator.settings
    if settings.inference_url != manifest["inference_url"]:
        raise ValueError("Inference endpoint differs from frozen PRE")
    student = QwenStudent(settings.inference_url, settings.inference_api_key, manifest["model"], adapter,
                          serving_model(manifest["model"], adapter) if adapter else None)
    runner = DockerRunner(manifest["sandbox_image"])
    for repetition in range(count):
        for split in ("train",) if training else ("train", "heldout"):
            for path in sorted((root / "envs" / split).iterdir()):
                target = root / "execution" / phase / str(repetition) / (path.name + ".json")
                if target.exists():
                    continue
                spec = TaskSpec.model_validate(read_json(path / "metadata.json"))
                decoding = Decoding.model_validate(manifest["decoding"])
                if training:
                    decoding = decoding.model_copy(update={"temperature": 1.0, "seed": 42 + repetition})
                candidate = target.with_suffix(".candidate.json")
                if not candidate.exists():
                    code, messages = await student.solve((path / "prompt.txt").read_text(encoding="utf-8"),
                        (path / "starter.py").read_text(encoding="utf-8"), spec.function_name, decoding)
                    write_json(candidate, {"code": code, "messages": messages, "decoding": decoding.model_dump()})
                generated = read_json(candidate)
                seed = manifest["seeds"][spec.id]
                result = await runner.run(spec, generated["code"], seed)
                record = {**generated, **result.model_dump(), "split": split, "mode": spec.mode,
                          "family": spec.family, "seed": seed, "model": manifest["model"],
                          "adapter_id": adapter, "timestamp": now(), "round": repetition}
                write_json(target, record)
                orchestrator.bus.emit(root, "rollout_recorded", phase=phase, task_id=spec.id,
                                      round=repetition, reward=result.reward, reason=result.verifier_reason)
    verify_frozen(root)


def summarize(root, phase):
    rows = read_json(root / "baseline" / "results.json")["results"] if phase == "pre" else []
    directory = root / "execution" / ("pre_repeat" if phase == "pre" else "post")
    rows += [read_json(p) for p in sorted(directory.glob("*/*.json")) if not p.name.endswith(".candidate.json")]
    scores = {}
    for split in ("train", "heldout"):
        for mode in ("all", "execute", "simulate"):
            selected = [r for r in rows if r["split"] == split and (mode == "all" or r["mode"] == mode)]
            scores[f"{split}/{mode}"] = {"passed": sum(r["reward"] for r in selected), "total": len(selected)}
    return {"phase": phase, "scores": scores, "results": rows, "timestamp": now()}
