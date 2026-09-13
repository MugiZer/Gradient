"""Live Codex -> curriculum -> Prime inference -> Docker check; never starts training."""
import argparse
import asyncio
import json

import httpx
import websockets


async def wait_for_state(socket, run_id, expected):
    async with asyncio.timeout(600):
        while True:
            event = json.loads(await socket.recv())
            if event.get("run_id") != run_id:
                continue
            if state := event.get("state"):
                print(state, flush=True)
                if state in {"FAILED", "INTERRUPTED", "NO_LEARNING_EVENT"}:
                    raise RuntimeError(event)
                if state == expected:
                    return
            if event["type"] in {"baseline_result", "heldout_result"}:
                print(f"{event['task_id']}: reward={event['reward']}", flush=True)


async def main(url, run_id=None):
    async with httpx.AsyncClient(base_url=url, timeout=600) as client, websockets.connect(
        url.replace("http", "ws", 1) + "/events"
    ) as socket:
        if run_id is None:
            response = await client.post("/interactions", json={
                "original_task": "In snapshot.py implement publish_snapshot(path, data). After it returns, "
                                 "a separate process must read the exact supplied UTF-8 text from path.",
                "bad_agent_output": "def publish_snapshot(path, data): return {'path': path, 'data': data}",
                "human_message": "The function only returns a description. Actually persist the data "
                                 "so a fresh reader observes it. When a user asks for a preview instead, "
                                 "preserve the existing file. Fix snapshot.py in your workspace.",
                "trajectory": [{"role": "user", "content": "Synthetic interaction for a live backend smoke check."}],
            })
            response.raise_for_status()
            run_id = response.json()["run_id"]
            print(f"Run: {run_id}", flush=True)
            await wait_for_state(socket, run_id, "CORRECTION_DETECTED")
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(wait_for_state(socket, run_id, "ENVIRONMENTS_COMPILED"))
                response = await client.post(f"/runs/{run_id}/confirm")
                response.raise_for_status()
        else:
            response = await client.get(f"/runs/{run_id}")
            response.raise_for_status()
            if response.json()["active"] and response.json()["manifest"] is None:
                await wait_for_state(socket, run_id, "ENVIRONMENTS_COMPILED")
        response = await client.post(f"/runs/{run_id}/evaluate/baseline")
        response.raise_for_status()
        await wait_for_state(socket, run_id, "BASELINE_EVALUATED")
        response = await client.get(f"/runs/{run_id}/artifacts/baseline/results.json")
        response.raise_for_status()
        result = response.json()
        for split in ("train", "heldout"):
            rows = [r for r in result["results"] if r["split"] == split]
            assert rows and all(r["reward"] in (0, 1) for r in rows)
            print(f"{split}: {sum(r['reward'] for r in rows)}/{len(rows)}", flush=True)
        print("Live pipeline verified; no training launched.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8788")
    parser.add_argument("--run", help="Resume a previously compiled run's incomplete baseline")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.url, arguments.run))
