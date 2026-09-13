"""Verifiers v0 bridge; shares the student's action protocol and trusted reward code."""
import json
import secrets
from pathlib import Path
from uuid import uuid4

import verifiers as vf
from datasets import Dataset

from gradient.curriculum.compiler import render
from gradient.schemas import TaskSpec, now
from gradient.student.agent import SYSTEM, Workspace


def replay(spec, messages):
    workspace = Workspace(render(spec)[1], spec.function_name)
    feedback = ""
    for message in messages:
        if message["role"] == "assistant":
            feedback = workspace.act(message["content"])
            if workspace.finished:
                break
    return workspace, feedback


class GradientEnv(vf.MultiTurnEnv):
    async def env_response(self, messages, state, **kwargs):
        spec = TaskSpec.model_validate(state["info"]["spec"])
        workspace, feedback = replay(spec, messages)
        response = [{"role": "user", "content": feedback}]
        if workspace.finished:
            state["final_env_response"] = response
        return response


def load_environment(specs_path=None, backend="prime", max_turns=6):
    specs = [TaskSpec.model_validate(item) for item in json.loads(
        Path(specs_path or Path(__file__).with_name("train_specs.json")).read_text(encoding="utf-8"))]
    if not specs or any(spec.split != "train" for spec in specs):
        raise ValueError("Training loader accepts training tasks only")
    if backend == "prime":
        from gradient.training.sandbox import PrimeRunner
        runner = PrimeRunner()
    elif backend == "docker":
        from gradient.sandbox.runner import DockerRunner
        runner = DockerRunner()
    else:
        raise ValueError("backend must be prime or docker")

    async def reward(completion, info, **kwargs):
        spec = TaskSpec.model_validate(info["spec"])
        workspace, _ = replay(spec, completion)
        trace = {"id": uuid4().hex, "timestamp": now(), "spec": spec.model_dump(),
                 "seed": secrets.randbits(32), "code": workspace.code,
                 "messages": [m.model_dump(mode="json") if hasattr(m, "model_dump") else m for m in completion]}
        print("GRADIENT_ROLLOUT " + json.dumps(trace), flush=True)
        try:
            result = await runner.run(spec, workspace.code, trace["seed"])
        except Exception as exc:
            print("GRADIENT_REWARD " + json.dumps({"id": trace["id"], "error": str(exc)}), flush=True)
            raise
        print("GRADIENT_REWARD " + json.dumps({"id": trace["id"], **result.model_dump()}), flush=True)
        return float(result.reward)

    dataset = Dataset.from_list([
        {"prompt": [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": render(spec)[0]}],
         "answer": "", "info": {"spec": spec.model_dump()}} for spec in specs
    ])
    return GradientEnv(dataset=dataset, rubric=vf.Rubric(funcs=[reward]), max_turns=max_turns)
