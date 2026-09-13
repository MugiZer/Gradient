import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from prime_sandboxes import AsyncSandboxClient, CreateSandboxRequest

from gradient.schemas import RolloutResult


class PrimeRunner:
    async def run(self, spec, code, seed):
        async with AsyncSandboxClient() as client:
            network = ({"network_allowlist": []} if "network_allowlist" in CreateSandboxRequest.model_fields
                       else {"network_access": False})
            sandbox = await client.create(CreateSandboxRequest(
                name="gradient-" + uuid4().hex[:12], docker_image="python:3.11-slim",
                vm=True, **network, timeout_minutes=5, cpu_cores=1, memory_gb=1,
            ))
            try:
                await client.wait_for_creation(sandbox.id)
                setup = await client.execute_command(sandbox.id, "mkdir -p /private /work && chmod 700 /private")
                if setup.exit_code:
                    raise RuntimeError("Prime sandbox setup failed: " + setup.stderr)
                await client.upload_file(sandbox.id, "/private/supervisor.py",
                                         str(Path(__file__).parents[1] / "sandbox" / "supervisor.py"))
                with TemporaryDirectory() as directory:
                    path = Path(directory) / "request.json"
                    path.write_text(json.dumps({"spec": spec.model_dump(), "code": code, "seed": seed}), encoding="utf-8")
                    await client.upload_file(sandbox.id, "/private/request.json", str(path))
                result = await client.execute_command(
                    sandbox.id, "python -I /private/supervisor.py < /private/request.json", timeout=30)
                if result.exit_code:
                    raise RuntimeError("Prime reward infrastructure failed: " + result.stderr)
                return RolloutResult.model_validate_json(result.stdout)
            finally:
                await client.delete(sandbox.id)
