import asyncio
import json
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory


def strict_schema(schema):
    schema = json.loads(json.dumps(schema))

    def visit(value):
        if isinstance(value, dict):
            value.pop("default", None)
            if "properties" in value:
                value["required"] = list(value["properties"])
                value["additionalProperties"] = False
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(schema)
    return schema


class CodexClient:
    """One stdio app-server, with separately serialized logical roles."""

    def __init__(self, command="codex", timeout=180):
        self.command, self.timeout = command, timeout
        self.process = self.reader = None
        self.pending, self.queues, self.threads = {}, {}, {}
        self.listeners = {}
        self.locks = defaultdict(asyncio.Lock)
        self.start_lock = asyncio.Lock()
        self.counter = 0
        self.contexts = {}

    def context_dir(self, role):
        if role not in self.contexts:
            self.contexts[role] = TemporaryDirectory(prefix=f"gradient-{role}-", ignore_cleanup_errors=True)
        return Path(self.contexts[role].name)

    async def start(self):
        async with self.start_lock:
            if self.process:
                if self.process.returncode is None and not self.reader.done():
                    return
                await self.close()
            self.process = await asyncio.create_subprocess_exec(
                self.command, "app-server", "--listen", "stdio://",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=2**22,
            )
            self.reader = asyncio.create_task(self._read())
            try:
                await self._rpc("initialize", {"clientInfo": {"name": "gradient", "version": "0.1.0"}})
                self._send({"method": "initialized", "params": {}})
            except BaseException:
                await self.close()
                raise

    def _send(self, message):
        self.process.stdin.write(json.dumps(message).encode() + b"\n")

    async def _rpc(self, method, params):
        self.counter += 1
        key = self.counter
        future = asyncio.get_running_loop().create_future()
        self.pending[key] = future
        try:
            self._send({"id": key, "method": method, "params": params})
            return await asyncio.wait_for(future, self.timeout)
        finally:
            self.pending.pop(key, None)

    async def _read(self):
        try:
            while line := await self.process.stdout.readline():
                message = json.loads(line)
                if "id" in message and "method" in message:
                    self._send({"id": message["id"], "error": {
                        "code": -32601, "message": "Interactive requests are unsupported by Gradient"}})
                elif "id" in message:
                    future = self.pending.get(message["id"])
                    if future and not future.done():
                        if "error" in message:
                            future.set_exception(RuntimeError(str(message["error"])))
                        else:
                            future.set_result(message.get("result"))
                else:
                    params = message.get("params", {})
                    listener = self.listeners.get(params.get("threadId"))
                    if listener:
                        listener(message)
                    queue = self.queues.get(params.get("threadId"))
                    if queue and message.get("method") in ("item/completed", "turn/completed"):
                        queue.put_nowait(message)
        finally:
            error = RuntimeError("Codex app-server disconnected")
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(error)
            for queue in self.queues.values():
                queue.put_nowait(error)

    async def ask(self, role, cwd: Path, instructions, prompt, schema=None, on_event=None):
        await self.start()
        cwd.mkdir(parents=True, exist_ok=True)
        async with self.locks[role]:
            if role not in self.threads:
                result = await self._rpc("thread/start", {
                    "cwd": str(cwd.resolve()), "approvalPolicy": "never",
                    "sandbox": "workspace-write" if role == "worker" else "read-only",
                    "developerInstructions": instructions,
                })
                self.threads[role] = result["thread"]["id"]
            thread = self.threads[role]
            queue = self.queues[thread] = asyncio.Queue()
            if on_event:
                self.listeners[thread] = on_event
            turn_id, output = None, []
            try:
                params = {"threadId": thread, "input": [{"type": "text", "text": prompt}]}
                if schema:
                    params["outputSchema"] = strict_schema(schema)
                result = await self._rpc("turn/start", params)
                turn_id = result["turn"]["id"]
                async with asyncio.timeout(self.timeout):
                    while True:
                        message = await queue.get()
                        if isinstance(message, Exception):
                            raise message
                        params = message["params"]
                        if message["method"] == "item/completed":
                            item = params["item"]
                            if item["type"] == "agentMessage":
                                output.append(item["text"])
                        else:
                            if params["turn"]["status"] != "completed":
                                raise RuntimeError(f"Codex turn failed: {params['turn'].get('error')}")
                            return output[-1] if output else ""
            except BaseException:
                if turn_id:
                    try:
                        await asyncio.wait_for(self._rpc("turn/interrupt", {
                            "threadId": thread, "turnId": turn_id}), 5)
                    except Exception:
                        pass
                self.threads.pop(role, None)
                raise
            finally:
                self.queues.pop(thread, None)
                self.listeners.pop(thread, None)

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
        if self.reader:
            await asyncio.gather(self.reader, return_exceptions=True)
        self.process = self.reader = None
        self.threads.clear()
        for context in self.contexts.values():
            context.cleanup()
        self.contexts.clear()
