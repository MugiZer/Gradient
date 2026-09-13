import asyncio
import hmac
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from gradient.api.proof import PostGradientProvider
from gradient.codex.native import NativeConnection
from gradient.config import Settings
from gradient.orchestrator import Orchestrator
from gradient.provenance import read_json
from gradient.schemas import Contract, Identifier, InteractionSnapshot, Text
from gradient.training import prime


class ExportRequest(Contract):
    owner: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    max_steps: int = Field(default=30, ge=1, le=100)


class AdapterRequest(Contract):
    adapter_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,128}$")


class WorkerRequest(Contract):
    message: Text


class NativeRequest(Contract):
    session_id: str = Field(pattern=r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


def create_app(settings=None):
    settings = settings or Settings()
    orchestrator = Orchestrator(settings)
    native = NativeConnection(orchestrator)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await native.disconnect()
        await orchestrator.close()

    app = FastAPI(title="Gradient backend", version="0.1.0", lifespan=lifespan)
    app.state.orchestrator = orchestrator
    app.state.native = native
    proof = PostGradientProvider(settings, orchestrator.bus)
    app.state.proof = proof
    local = {"127.0.0.1", "::1", "localhost"}

    def authorized(connection):
        origin = connection.headers.get("origin")
        if origin and urlparse(origin).netloc != connection.headers.get("host"):
            return False
        if settings.api_token:
            return hmac.compare_digest(connection.headers.get("authorization", ""),
                                       "Bearer " + settings.api_token)
        return connection.client and connection.client.host in local and connection.url.hostname in local

    @app.middleware("http")
    async def access(request: Request, call_next):
        if not authorized(request):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

    def run_path(run_id):
        root = settings.runs_dir.resolve() / run_id
        if root.parent != settings.runs_dir.resolve() or not root.is_dir() or root.is_symlink():
            raise HTTPException(404, "Unknown run")
        return root

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Required artifact does not exist yet"}, status_code=409)

    @app.get("/health")
    async def health():
        return {"status": "ok", "active_runs": list(orchestrator.jobs),
                "desktop_companion": settings.desktop_companion}

    @app.post("/worker")
    async def worker(body: WorkerRequest):
        from gradient.codex.agents import work
        return {"output": await work(orchestrator.codex, settings.worker_dir, body.message)}

    @app.post("/interactions", status_code=202)
    async def interaction(body: InteractionSnapshot):
        return {"run_id": orchestrator.receive(body)}

    @app.get("/native")
    async def native_status():
        return native.status()

    @app.post("/native/connect")
    async def native_connect(body: NativeRequest):
        return await native.connect(body.session_id)

    @app.post("/native/disconnect")
    async def native_disconnect():
        return await native.disconnect()

    @app.post("/native/observe", status_code=202)
    async def native_observe():
        run_id = native.observe_lesson()
        return {"run_id": run_id, "context": native.latest_snapshot.model_dump(include={"human_message", "bad_agent_output"})}

    @app.get("/native/context")
    async def native_context():
        return native.latest_snapshot.model_dump(include={"human_message", "bad_agent_output"}) if native.status()["connected"] and native.latest_snapshot else None

    @app.post("/native/close")
    async def native_close():
        await native.disconnect()
        await orchestrator.close()
        return {"closed": True}

    def belongs_to_session(root, session_id):
        source = root / "native_source.json"
        return source.is_file() and read_json(source).get("session_id") == session_id

    @app.get("/runs")
    async def runs(native_session: str | None = None):
        return [{"run_id": p.name} for p in sorted(settings.runs_dir.glob("grad_*")) if p.is_dir()
                and (native_session is None or belongs_to_session(p, native_session))]

    @app.get("/runs/{run_id}")
    async def run(run_id: Identifier):
        root = run_path(run_id)
        events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
        return {"run_id": run_id, "active": run_id in orchestrator.jobs, "events": events,
                "artifacts": [p.relative_to(root).as_posix() for p in sorted(root.rglob("*"))
                              if p.is_file() and not p.is_symlink()],
                "manifest": read_json(root / "manifest.json") if (root / "manifest.json").exists() else None}

    @app.get("/runs/{run_id}/artifacts/{path:path}")
    async def artifact(run_id: Identifier, path: str):
        root = run_path(run_id)
        target = (root / path).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise HTTPException(404, "Unknown artifact")
        return FileResponse(target, media_type="text/plain", filename=target.name)

    @app.post("/runs/{run_id}/evaluate/{phase}", status_code=202)
    async def evaluation(run_id: Identifier, phase: str):
        if phase not in ("baseline", "after"):
            raise HTTPException(422, "phase must be baseline or after")
        root = run_path(run_id)
        orchestrator.schedule(root, lambda: orchestrator.run_evaluation(root, phase))
        return {"run_id": run_id, "operation": phase}

    @app.post("/runs/{run_id}/confirm", status_code=202)
    async def confirm(run_id: Identifier):
        root = run_path(run_id)
        if job := orchestrator.jobs.get(run_id):
            await asyncio.shield(job)
        orchestrator.confirm(root)
        return {"run_id": run_id, "operation": "confirm"}

    @app.post("/runs/{run_id}/dismiss")
    async def dismiss(run_id: Identifier):
        orchestrator.dismiss(run_path(run_id))
        return {"run_id": run_id, "operation": "dismiss"}

    @app.post("/runs/{run_id}/training/export")
    async def export(run_id: Identifier, body: ExportRequest):
        root = run_path(run_id)
        if run_id in orchestrator.jobs:
            raise ValueError("Run is busy")
        target = prime.export(root, body.owner, body.max_steps)
        orchestrator.state(root, "READY_FOR_TRAINING")
        return {"package": str(target), "config": str(root / "training" / "config.toml")}

    @app.post("/runs/{run_id}/training/launch", status_code=202)
    async def launch(run_id: Identifier, body: ExportRequest | None = None):
        root = run_path(run_id)
        orchestrator.schedule(root, lambda: orchestrator.train(root, body.owner if body else None,
                                                             body.max_steps if body else 30))
        return {"run_id": run_id, "operation": "training"}

    @app.post("/runs/{run_id}/iterate", status_code=201)
    async def iterate(run_id: Identifier):
        return {"run_id": orchestrator.iterate(run_path(run_id))}

    @app.post("/runs/{run_id}/training/publish")
    async def publish(run_id: Identifier):
        return await prime.publish(run_path(run_id))

    @app.post("/runs/{run_id}/training/collect", status_code=202)
    async def collect(run_id: Identifier, body: AdapterRequest):
        root = run_path(run_id)
        orchestrator.schedule(root, lambda: orchestrator.collect(root, body.adapter_id))
        return {"run_id": run_id, "operation": "collect"}

    @app.websocket("/events")
    async def events(socket: WebSocket, native_session: str | None = None):
        if not authorized(socket):
            await socket.close(code=1008)
            return
        await socket.accept()
        queue = orchestrator.bus.subscribe()
        async def send():
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), 20)
                except asyncio.TimeoutError:
                    event = {"type": "heartbeat"}
                if native_session is not None and event["type"] not in {"heartbeat", "resync_required"}:
                    if not belongs_to_session(settings.runs_dir / event["run_id"], native_session):
                        continue
                await socket.send_json(event)
                if event["type"] == "resync_required":
                    await socket.close(code=1013)
                    return
        sender = asyncio.create_task(send())
        receiver = asyncio.create_task(socket.receive())
        try:
            await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
        except WebSocketDisconnect:
            pass
        finally:
            orchestrator.bus.subscribers.discard(queue)
            sender.cancel()
            receiver.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)

    @app.get("/runs/{run_id}/training/status")
    async def training_status(run_id: Identifier):
        return await prime.status(run_path(run_id))

    @app.post("/runs/{run_id}/training/deploy")
    async def deploy(run_id: Identifier):
        return await prime.deploy(run_path(run_id))

    @app.get("/proof/status")
    async def proof_status():
        return await proof.get_proof_status()

    @app.post("/proof/{task_id}")
    async def run_proof(task_id: Identifier):
        return await proof.run_proof(task_id)

    async def demo_comparison(task_id, run_id):
        try:
            await proof.run_proof(task_id, expected_run_id=run_id)
        except Exception:
            # The proof provider persists errors and emits proof_failed.
            pass

    @app.post("/runs/{run_id}/compare/{task_id}", status_code=202)
    async def compare(run_id: Identifier, task_id: Identifier, background: BackgroundTasks):
        root = run_path(run_id)
        if (settings.runs_dir / "demo/current.json").exists():
            state = await proof.read_state()
            if run_id == state.experiment_id:
                proof.frozen_task(state, task_id)
                background.add_task(demo_comparison, task_id, run_id)
                return {"run_id": run_id, "operation": "compare", "task_id": task_id}
        if not (root / "envs" / "heldout" / task_id).is_dir():
            raise HTTPException(404, "Unknown heldout task")
        orchestrator.schedule(root, lambda: orchestrator.compare(root, task_id))
        return {"run_id": run_id, "operation": "compare", "task_id": task_id}

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend.is_dir():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        @app.get("/desktop", include_in_schema=False)
        async def client():
            return FileResponse(frontend / "index.html")

    return app
