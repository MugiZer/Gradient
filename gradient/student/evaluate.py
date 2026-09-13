from gradient.provenance import read_json, verify_frozen, write_json
from gradient.schemas import Decoding, TaskSpec, now


async def evaluate(root, phase, student, runner, bus):
    if phase not in ("baseline", "after"):
        raise ValueError("Unknown evaluation phase")
    manifest = verify_frozen(root)
    if student.model != manifest["model"] or runner.image != manifest["sandbox_image"]:
        raise ValueError("Model or sandbox differs from the frozen experiment")
    if phase == "baseline" and student.adapter_id:
        raise ValueError("Baseline must use base weights")
    if phase == "after":
        training = read_json(root / "training" / "result.json")
        if student.adapter_id != training["adapter_id"]:
            raise ValueError("Adapter does not match the recorded training result")
    target = root / phase
    if (target / "results.json").exists():
        raise ValueError("Evaluation already completed; its evidence is immutable")
    target.mkdir(exist_ok=True)
    results = []
    for split in ("train", "heldout") if phase == "baseline" else ("heldout",):
        for path in sorted((root / "envs" / split).iterdir()):
            spec = TaskSpec.model_validate(read_json(path / "metadata.json"))
            previous = target / "rollouts" / f"{spec.id}.json"
            if previous.exists():
                record = read_json(previous)
                results.append({k: v for k, v in record.items() if k not in ("code", "messages")})
                continue
            candidate = target / "rollouts" / f"{spec.id}.candidate.json"
            if not candidate.exists():
                code, messages = await solve(path, student, manifest)
                write_json(candidate, {"code": code, "messages": messages})
            generated = read_json(candidate)
            code, messages = generated["code"], generated["messages"]
            result = await runner.run(spec, code, manifest["seeds"][spec.id])
            record = {**result.model_dump(), "split": split, "mode": spec.mode,
                      "family": spec.family, "timestamp": now()}
            write_json(target / "rollouts" / f"{spec.id}.json", {**record, "code": code, "messages": messages})
            results.append(record)
            bus.emit(root, "baseline_result" if phase == "baseline" else "heldout_result", **record)
    verify_frozen(root)
    summary = {"model": student.model, "adapter_id": student.adapter_id,
               "decoding": manifest["decoding"], "finished_at": now(), "results": results}
    write_json(target / "results.json", summary)
    return summary


async def solve(path, student, manifest):
    spec = TaskSpec.model_validate(read_json(path / "metadata.json"))
    return await student.solve((path / "prompt.txt").read_text(encoding="utf-8"),
                               (path / "starter.py").read_text(encoding="utf-8"), spec.function_name,
                               Decoding.model_validate(manifest["decoding"]))
