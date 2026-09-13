import httpx

from gradient.schemas import Decoding
from gradient.student.agent import SYSTEM, Workspace


class QwenStudent:
    def __init__(self, url: str, api_key: str, model: str, adapter_id: str | None = None,
                 serving_model: str | None = None):
        self.url, self.api_key, self.model, self.adapter_id = url.rstrip("/"), api_key, model, adapter_id
        self.serving_model = serving_model or adapter_id or model

    async def solve(self, prompt, starter, function_name, decoding: Decoding):
        workspace = Workspace(starter, function_name)
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        async with httpx.AsyncClient(timeout=180) as client:
            for _ in range(decoding.max_turns):
                response = await client.post(
                    self.url + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                    json={"model": self.serving_model, "messages": messages,
                          **decoding.model_dump(exclude={"max_turns"})},
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise RuntimeError("Inference returned no text")
                messages.append({"role": "assistant", "content": content})
                feedback = workspace.act(content)
                if workspace.finished:
                    break
                messages.append({"role": "user", "content": feedback})
        return workspace.code, messages
