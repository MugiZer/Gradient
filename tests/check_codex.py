"""Small live structured-output check using the authenticated Codex runtime."""
import asyncio
import sys

from gradient.codex.agents import generate, observe
from gradient.codex.client import CodexClient
from gradient.schemas import Capability, InteractionSnapshot


async def main():
    client = CodexClient(timeout=180)
    try:
        event = await observe(client, InteractionSnapshot(
            original_task="Write a function that adds two integers.",
            bad_agent_output="def add(a, b): return a + b",
            human_message="Thanks, that is exactly what I needed.",
        ))
        assert not event.is_learning_event, event
        print("Live Codex structured output: non-correction correctly rejected")
        if "--curriculum" in sys.argv:
            batch = await generate(client, Capability(
                name="observable_effect_vs_simulation", description="Decide when an observable effect is required.",
                positive_rule="Required effects must occur in the external state.",
                negative_rule="An approval proposal must preserve the current state.",
            ))
            assert len(batch.tasks) == 12
            print("Live Codex environment agent: 8 train + 4 heldout tasks validated")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
