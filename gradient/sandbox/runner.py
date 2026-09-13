import asyncio
import json
from uuid import uuid4

from gradient.schemas import RolloutResult, TaskSpec


class DockerRunner:
    def __init__(self, image="gradient-sandbox:local"):
        self.image = image

    async def run(self, spec: TaskSpec, code: str, seed: int) -> RolloutResult:
        if len(code.encode()) > 65536:
            raise ValueError("Candidate exceeds 64 KiB")
        name = "gradient-" + uuid4().hex
        process = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "-i", "--name", name, "--network", "none",
            "--read-only", "--memory", "256m", "--cpus", "1", "--pids-limit", "32",
            "--cap-drop", "ALL", "--cap-add", "SETUID", "--cap-add", "SETGID",
            "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE", "--cap-add", "KILL", "--security-opt", "no-new-privileges",
            "--tmpfs", "/work:rw,nosuid,size=8m", "--tmpfs", "/tmp:rw,nosuid,size=2m",
            self.image, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            payload = json.dumps({"spec": spec.model_dump(), "code": code, "seed": seed}).encode()
            stdout, stderr = await asyncio.wait_for(process.communicate(payload), 40)
            if process.returncode:
                raise RuntimeError("Sandbox infrastructure failed: " + stderr.decode(errors="replace")[-2000:])
            return RolloutResult.model_validate_json(stdout)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
            cleanup = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", name, stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await cleanup.wait()
