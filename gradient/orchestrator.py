import asyncio
from uuid import uuid4

from gradient.codex import agents
from gradient.codex.client import CodexClient
from gradient.curriculum.compiler import compile_curriculum
from gradient.events import EventBus
from gradient.provenance import freeze, read_json, verify_frozen, write_json
from gradient.sandbox.runner import DockerRunner
from gradient.schemas import Curriculum, Decoding, InteractionSnapshot, LearningEvent, TaskSpec, now
from gradient.student.evaluate import evaluate, solve
from gradient.student.model import QwenStudent
from gradient.training import prime


class Orchestrator:
    def __init__(self, settings):
        self.settings = settings
        settings.runs_dir.mkdir(parents=True, exist_ok=True)
        self.codex = CodexClient(settings.codex_command, settings.timeout)
        self.bus, self.jobs = EventBus(), {}
        # ponytail: one curriculum pipeline at a time; per-role clients if concurrent runs matter.
        self.pipeline_lock = asyncio.Lock()

    def state(self, root, state, **data):
        self.bus.emit(root, "state", state=state, **data)

    def schedule(self, root, operation):
        if root.name in self.jobs:
            raise ValueError("This run already has an active operation")

        async def execute():
            try:
                await operation()
            except asyncio.CancelledError:
                self.state(root, "INTERRUPTED")
                raise
            except Exception as exc:
                self.state(root, "FAILED", error=str(exc))
            finally:
                self.jobs.pop(root.name, None)
        self.jobs[root.name] = asyncio.create_task(execute())

    def receive(self, snapshot: InteractionSnapshot, *, native_session: str | None = None):
        root = self.settings.runs_dir / ("grad_" + uuid4().hex)
        root.mkdir()
        write_json(root / "interaction.json", snapshot)
        if native_session:
            write_json(root / "native_source.json", {"session_id": native_session})
        self.state(root, "WATCHING")
        self.bus.emit(root, "worker_message", text=snapshot.human_message)
        self.schedule(root, lambda: self.prepare(root, snapshot, run_worker=not native_session))
        return root.name

    async def prepare(self, root, snapshot, *, run_worker=True):
        async def worker():
            self.bus.emit(root, "agent_status", agent="worker", status="WORKING")
            try:
                output = await agents.work(self.codex, self.settings.worker_dir,
                                          snapshot.model_dump_json(),
                                          lambda message: self.bus.emit(root, "worker_event", **message))
                write_json(root / "worker.json", {"output": output})
                self.bus.emit(root, "worker_output", text=output)
                self.bus.emit(root, "agent_status", agent="worker", status="DONE")
            except Exception as exc:
                self.bus.emit(root, "agent_status", agent="worker", status="FAILED", error=str(exc))

        async with self.pipeline_lock:
            worker_task = asyncio.create_task(worker()) if run_worker else None
            try:
                self.bus.emit(root, "agent_status", agent="observer", status="ANALYZING")
                event = await agents.observe(self.codex, snapshot)
                event = event.model_copy(update={"id": root.name})
                write_json(root / "event.json", event)
                self.bus.emit(root, "agent_status", agent="observer",
                              status="DETECTED" if event.is_learning_event else "WATCHING")
                if not event.is_learning_event:
                    self.state(root, "NO_LEARNING_EVENT")
                    return
                self.state(root, "CORRECTION_DETECTED")
                self.bus.emit(root, "correction_candidate", event=event.model_dump(),
                              title="Observable Effect vs Simulation")
            except BaseException:
                if worker_task:
                    worker_task.cancel()
                raise
            finally:
                if worker_task:
                    await asyncio.gather(worker_task, return_exceptions=True)

    def confirm(self, root):
        event = LearningEvent.model_validate(read_json(root / "event.json"))
        if not event.is_learning_event or (root / "dismissed.json").exists():
            raise ValueError("No pending lesson to teach")
        if (root / "confirmed.json").exists():
            raise ValueError("Lesson was already confirmed")
        if root.name in self.jobs:
            raise ValueError("Codex is still finishing this turn; try again when it settles")
        write_json(root / "confirmed.json", {"confirmed": True})
        self.bus.emit(root, "lesson_confirmed")
        self.schedule(root, lambda: self.build_lesson(root, event))

    async def build_lesson(self, root, event):
        async with self.pipeline_lock:
            write_json(root / "capability.json", event.capability)
            self.state(root, "CAPABILITY_EXTRACTED")
            self.bus.emit(root, "capability_extracted", capability=event.capability.model_dump())
            self.state(root, "CURRICULUM_GENERATING")
            self.bus.emit(root, "agent_status", agent="environment", status="BUILDING")
            curriculum = await agents.generate(self.codex, event.capability)
            for split in ("train", "heldout"):
                write_json(root / "curriculum" / f"{split}_specs.json",
                           [s.model_dump() for s in curriculum.tasks if s.split == split])
            for spec in curriculum.tasks:
                self.bus.emit(root, "task_spec_created", task=spec.model_dump(), total=len(curriculum.tasks))
            hashes = compile_curriculum(curriculum, root / "envs")
            process = await asyncio.create_subprocess_exec(
                "docker", "image", "inspect", "--format", "{{.Id}}", self.settings.sandbox_image,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode:
                raise RuntimeError("Build the sandbox image first: " + stderr.decode(errors="replace"))
            freeze(root, hashes, self.settings.model, Decoding(), stdout.decode().strip(),
                   self.settings.inference_url)
            self.state(root, "ENVIRONMENTS_COMPILED")
            self.bus.emit(root, "curriculum_compiled", hashes=hashes,
                          train_count=sum(t.split == "train" for t in curriculum.tasks),
                          unseen_count=sum(t.split == "heldout" for t in curriculum.tasks))
            self.bus.emit(root, "agent_status", agent="environment", status="DONE")

    def dismiss(self, root):
        if (root / "confirmed.json").exists():
            raise ValueError("Lesson is already running")
        if not (root / "dismissed.json").exists():
            write_json(root / "dismissed.json", {"dismissed": True})
            self.bus.emit(root, "lesson_dismissed")

    async def run_evaluation(self, root, phase):
        manifest = verify_frozen(root)
        if manifest["inference_url"] != self.settings.inference_url:
            raise ValueError("Inference endpoint changed since freeze")
        adapter, serving_model = None, manifest["model"]
        if phase == "after":
            adapter = read_json(root / "training" / "result.json")["adapter_id"]
            serving_model = prime.serving_model(manifest["model"], adapter)
        student = QwenStudent(self.settings.inference_url, self.settings.inference_api_key,
                              manifest["model"], adapter, serving_model)
        await evaluate(root, phase, student, DockerRunner(manifest["sandbox_image"]), self.bus)
        self.state(root, "BASELINE_EVALUATED" if phase == "baseline" else "HELDOUT_EVALUATED")

    def iterate(self, parent):
        root = self.settings.runs_dir / ("grad_" + uuid4().hex)
        root.mkdir()
        write_json(root / "iteration.json", {"parent_run": parent.name, "created_at": now(),
                   "reason": "Recompile the same generated TaskSpecs with the current backend; recalibrate before training"})
        for name in ("interaction", "event", "capability", "worker"):
            if (parent / f"{name}.json").exists():
                write_json(root / f"{name}.json", read_json(parent / f"{name}.json"))
        specs = []
        for split in ("train", "heldout"):
            values = read_json(parent / "curriculum" / f"{split}_specs.json")
            write_json(root / "curriculum" / f"{split}_specs.json", values)
            specs.extend(values)
        hashes = compile_curriculum(Curriculum.model_validate({"tasks": specs}), root / "envs")
        image = read_json(parent / "manifest.json")["sandbox_image"]
        freeze(root, hashes, self.settings.model, Decoding(), image, self.settings.inference_url)
        self.state(root, "ENVIRONMENTS_COMPILED", parent_run=parent.name)
        return root.name

    async def train(self, root, owner=None, max_steps=30, *, evaluate_after=True):
        verify_frozen(root)
        if not (root / "baseline" / "results.json").exists():
            await self.run_evaluation(root, "baseline")
        if not (root / "training" / "export.json").exists():
            if not owner:
                raise ValueError("Prime owner is required for the first training launch")
            prime.export(root, owner, max_steps)
            self.state(root, "READY_FOR_TRAINING")
        await prime.publish(root)
        if not (root / "training" / "run.json").exists():
            self.state(root, "TRAINING")
            result = await prime.launch(root)
            self.bus.emit(root, "training_started", run=result["run"])
        while True:
            record = await prime.capture(root)
            status = record["run"]["status"].upper()
            self.bus.emit(root, "training_progress", run=record["run"])
            if status == "COMPLETED":
                break
            if status in {"FAILED", "STOPPED", "CANCELLED", "CANCELED"}:
                raise RuntimeError(f"Prime training ended with status {status}")
            await asyncio.sleep(60)
        adapter = await prime.ready_adapter(root)
        while not adapter:
            self.state(root, "AWAITING_ADAPTER")
            await asyncio.sleep(60)
            adapter = await prime.ready_adapter(root)
        if not (root / "training" / "result.json").exists():
            await self.collect(root, adapter)
        self.state(root, "TRAINED", adapter_id=adapter)
        await prime.deploy(root)
        if evaluate_after and not (root / "after" / "results.json").exists():
            await self.run_evaluation(root, "after")

    async def execute_frozen(self, root):
        from gradient.training.execution import rounds, summarize
        verify_frozen(root)
        await rounds(self, root, "calibration", 8, training=True)
        await rounds(self, root, "pre_repeat", 1)
        if not (root / "execution" / "pre.json").exists():
            write_json(root / "execution" / "pre.json", summarize(root, "pre"))
        await self.train(root, evaluate_after=False)
        await prime.wait_deployment(root)
        await rounds(self, root, "post", 2)
        write_json(root / "execution" / "post.json", summarize(root, "post"))
        self.state(root, "COMPARISON_COMPLETE")

    async def collect(self, root, adapter_id):
        result = await prime.collect(root, adapter_id)
        self.state(root, "TRAINED")
        self.bus.emit(root, "training_result", result=result.model_dump())
        self.bus.emit(root, "training_completed", result=result.model_dump())

    async def close(self):
        for task in list(self.jobs.values()):
            task.cancel()
        await asyncio.gather(*list(self.jobs.values()), return_exceptions=True)
        await self.codex.close()

    async def compare(self, root, task_id):
        manifest = verify_frozen(root)
        if manifest["inference_url"] != self.settings.inference_url:
            raise ValueError("Inference endpoint changed since freeze")
        path = root / "envs" / "heldout" / task_id
        spec = TaskSpec.model_validate(read_json(path / "metadata.json"))
        adapter = read_json(root / "training" / "result.json")["adapter_id"]
        output = {}
        self.bus.emit(root, "proof_started", task_id=task_id)
        for label, identity in (("base", None), ("trained", adapter)):
            student = QwenStudent(self.settings.inference_url, self.settings.inference_api_key,
                                  manifest["model"], identity,
                                  prime.serving_model(manifest["model"], identity) if identity else None)
            code, messages = await solve(path, student, manifest)
            result = await DockerRunner(manifest["sandbox_image"]).run(spec, code, manifest["seeds"][task_id])
            output[label] = {**result.model_dump(), "code": code, "messages": messages,
                             "model": manifest["model"], "adapter_id": identity}
            self.bus.emit(root, "comparison_result", label=label, **output[label])
        verify_frozen(root)
        write_json(root / "live" / (uuid4().hex + ".json"), output)
