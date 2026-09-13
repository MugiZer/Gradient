import json
import unittest
from unittest.mock import patch

import httpx

from gradient.schemas import Decoding
from gradient.student.model import QwenStudent


class StudentTest(unittest.IsolatedAsyncioTestCase):
    async def test_base_and_adapter_send_the_same_frozen_decoding(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            action = {"action": "finish"} if len(requests) % 2 == 0 else {
                "action": "write_file", "path": "solution.py", "content": "def solve(): return 1",
            }
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(action)}}]})

        decoding = Decoding.model_validate(Decoding().model_dump())
        for adapter in (None, "adapter"):
            client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
            with patch("gradient.student.model.httpx.AsyncClient", return_value=client):
                student = QwenStudent("http://inference/v1", "", "qwen", adapter)
                code, _ = await student.solve("Implement solve", "def solve(): pass", "solve", decoding)
                self.assertEqual(code, "def solve(): return 1")
        for request in requests:
            self.assertEqual(request["presence_penalty"], 2)
            self.assertEqual(request["temperature"], 0)
            self.assertEqual(request["seed"], 42)
        self.assertEqual({k: v for k, v in requests[0].items() if k != "model"},
                         {k: v for k, v in requests[2].items() if k != "model"})
