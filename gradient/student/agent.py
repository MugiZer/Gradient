import ast
import json

SYSTEM = '''Implement solution.py using JSON actions, one per response, no markdown:
{"action":"read_file","path":"solution.py"}
{"action":"write_file","path":"solution.py","content":"complete Python source"}
{"action":"run_tests"}
{"action":"finish"}
Only solution.py is editable. run_tests checks Python syntax and the required function;
the hidden behavioral test is run after finish. Finish after writing your solution.'''


class Workspace:
    def __init__(self, starter: str, function_name: str):
        self.code, self.function_name, self.finished = starter, function_name, False

    def act(self, response: str) -> str:
        try:
            action = json.loads(response)
            name = action["action"]
            if name in ("read_file", "write_file") and action.get("path") != "solution.py":
                raise ValueError("Only solution.py is accessible")
            if name == "read_file":
                return self.code
            if name == "write_file":
                code = action["content"]
                if not isinstance(code, str) or len(code.encode()) > 65536:
                    raise ValueError("Source must be a string of at most 64 KiB")
                self.code = code
                return "Saved solution.py"
            if name == "run_tests":
                tree = ast.parse(self.code)
                if not any(isinstance(n, ast.FunctionDef) and n.name == self.function_name for n in tree.body):
                    raise ValueError("Required function is missing")
                return "Syntax and function check passed. Behavior has not been checked."
            if name == "finish":
                self.finished = True
                return "Submitted"
            raise ValueError("Unknown action")
        except (ValueError, KeyError, TypeError, SyntaxError) as exc:
            return f"Action error: {exc}"

