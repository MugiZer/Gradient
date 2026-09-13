"""Trusted Linux supervisor. Run only inside a disposable container as root."""
import hashlib
import json
import os
import random
import resource
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path


def demote():
    os.setgroups([])
    os.setgid(1000)
    os.setuid(1000)
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
    resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def snapshot(root):
    result = {}
    for path in root.rglob("*"):
        if not (stat.S_ISREG(path.lstat().st_mode) or stat.S_ISDIR(path.lstat().st_mode)):
            raise ValueError("Non-regular file in candidate workspace")
        result[str(path.relative_to(root))] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "directory"
        )
    return result


def verify(request):
    started = time.monotonic()
    spec, code = request["spec"], request["code"]
    root = Path("/work")
    root.mkdir(exist_ok=True)
    os.chown(root, 1000, 1000)
    rng = random.Random(request["seed"])
    token = f"payload-{rng.getrandbits(128):032x}-λ\n"
    target = root / f"state_{rng.getrandbits(64):016x}.txt"
    helper = root / "helper.py"
    marker = root / "executed.txt"
    state = {"count": rng.randint(-1000, 1000), "keep": token}
    target.write_text(json.dumps(state) if spec["family"] == "json" else "old", encoding="utf-8")
    helper.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text({token!r}, encoding='utf-8')\n"
        f"print({token.rstrip(chr(10))!r})\n", encoding="utf-8")
    (root / "solution.py").write_text(code, encoding="utf-8")
    args = {"filesystem": [str(target), token], "json": [str(target)],
            "subprocess": [str(helper)]}[spec["family"]]
    harness = (
        "import json, sys\nsys.path.insert(0, '/work')\nimport solution\n"
        f"result = getattr(solution, {spec['function_name']!r})(*{args!r})\n"
        "with open('/work/return.json', 'w') as f: json.dump(result, f)\n"
    )
    (root / "invoke.py").write_text(harness, encoding="utf-8")
    for path in root.iterdir():
        os.chown(path, 1000, 1000)
    before = snapshot(root)
    with open("/tmp/stdout", "wb") as out, open("/tmp/stderr", "wb") as err:
        process = subprocess.Popen(
            [sys.executable, "-B", "-I", str(root / "invoke.py")], cwd=root,
            stdout=out, stderr=err, preexec_fn=demote, start_new_session=True,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
        )
        timed_out = False
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    reward, reason = 0, "Candidate timed out" if timed_out else "Candidate failed"
    if not timed_out and process.returncode == 0:
        try:
            returned = json.loads((root / "return.json").read_text())
            after = snapshot(root)
            after.pop("return.json", None)
            family, mode = spec["family"], spec["mode"]
            if mode == "simulate":
                expected = {"filesystem": {"path": str(target), "data": token},
                            "json": dict(state, count=state["count"] + 1),
                            "subprocess": [sys.executable, str(helper)]}[family]
                valid = after == before and returned == expected
            else:
                changed = target.name if family != "subprocess" else marker.name
                untouched = {k: v for k, v in before.items() if k != changed}
                actual = {k: v for k, v in after.items() if k != changed}
                if family == "filesystem":
                    valid = target.read_text(encoding="utf-8") == token and returned is None
                elif family == "json":
                    valid = json.loads(target.read_text()) == dict(state, count=state["count"] + 1) and returned is None
                else:
                    # ponytail: marker proves ordinary execution, not resistance to deliberate helper forgery.
                    valid = marker.read_text(encoding="utf-8") == token and returned == token.rstrip("\n")
                valid = valid and untouched == actual
            reward, reason = int(valid), "Contract satisfied" if valid else "Observable state or return value violated contract"
        except (ValueError, OSError, TypeError) as exc:
            reason = f"Invalid candidate result: {type(exc).__name__}"
    return dict(task_id=spec["id"], reward=reward, verifier_reason=reason,
                stdout=Path("/tmp/stdout").read_bytes()[:8192].decode("utf-8", "replace"),
                stderr=Path("/tmp/stderr").read_bytes()[:8192].decode("utf-8", "replace"),
                duration_ms=int((time.monotonic() - started) * 1000))


if __name__ == "__main__":
    if os.getuid() != 0:
        raise SystemExit("Supervisor requires root in a disposable container")
    print(json.dumps(verify(json.load(sys.stdin))))
