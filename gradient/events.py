import asyncio
import json

from gradient.schemas import now


class EventBus:
    def __init__(self):
        self.subscribers = set()

    def emit(self, root, event_type, **data):
        event = {"type": event_type, "timestamp": now(), "run_id": root.name, **data}
        with (root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        for queue in tuple(self.subscribers):
            if queue.full():
                self.subscribers.discard(queue)
                queue.get_nowait()
                queue.put_nowait({"type": "resync_required", "run_id": root.name})
            else:
                queue.put_nowait(event)
        return event

    def subscribe(self):
        queue = asyncio.Queue(maxsize=256)
        self.subscribers.add(queue)
        return queue

