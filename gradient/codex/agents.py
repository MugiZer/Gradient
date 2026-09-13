from pathlib import Path

from gradient.schemas import Capability, Curriculum, InteractionSnapshot, LearningEvent


def role_skill(role: str) -> str:
    return (Path(__file__).with_name("skills") / role / "SKILL.md").read_text(encoding="utf-8")


async def observe(client, snapshot: InteractionSnapshot) -> LearningEvent:
    client.threads.pop("observer", None)
    output = await client.ask(
        "observer", client.context_dir("observer"),
        role_skill("observer"),
        snapshot.model_dump_json(), LearningEvent.model_json_schema(),
    )
    return LearningEvent.model_validate_json(output)


async def generate(client, capability: Capability) -> Curriculum:
    client.threads.pop("environment", None)
    output = await client.ask(
        "environment", client.context_dir("environment"),
        role_skill("environment"),
        capability.model_dump_json(), Curriculum.model_json_schema(),
    )
    return Curriculum.model_validate_json(output)


async def work(client, directory: Path, message: str, on_event=None) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    return await client.ask("worker", directory, role_skill("worker"),
                            message, on_event=on_event)
