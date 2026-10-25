#!/usr/bin/env python3
"""Replay the current signature audit against an immutable baseline and runtime."""

import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

BASELINE = "d1457dbf45de25f22505a683acdb1bbed5a1726a"
AUDIT = Path("tests/test_runtime_contract.py")
EXPECTED = {
    "src/planzilla/commands/install.py:46: __init__: missing return annotation",
    "src/planzilla/commands/install.py:80: _source_files: missing return annotation",
    "src/planzilla/commands/serve.py:91: log_message: missing annotation for parameter 'args'",
}


def git_bytes(root: Path, *arguments: str) -> bytes:
    return subprocess.run(["git", *arguments], cwd=root, check=True, stdout=subprocess.PIPE).stdout


def run_audit(root: Path, config: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "--color=no",
        "--noconftest",
        "-p",
        "no:cacheprovider",
        "-c",
        str(config),
        AUDIT.as_posix(),
    ]
    environment = os.environ.copy()
    for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONPATH"):
        environment.pop(name, None)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"cwd: {root}\ncommand: {shlex.join(command)}\nexit: {result.returncode}")
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    audit_bytes = (root / AUDIT).read_bytes()
    with tempfile.TemporaryDirectory(prefix="planzilla-signature-replay-") as directory:
        temporary = Path(directory)
        baseline = temporary / "baseline"
        config = temporary / "pytest.ini"
        config.write_text("[pytest]\n", encoding="utf-8")
        paths = git_bytes(root, "ls-tree", "-r", "--name-only", "-z", BASELINE, "src/planzilla")
        sources = [os.fsdecode(path) for path in paths.split(b"\0") if path.endswith(b".py")]
        assert sources, "Baseline has no runtime Python sources"
        for source in sources:
            target = baseline / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git_bytes(root, "show", f"{BASELINE}:{source}"))
        (baseline / AUDIT).parent.mkdir(parents=True, exist_ok=True)
        (baseline / AUDIT).write_bytes(audit_bytes)

        print(f"Baseline replay: {BASELINE}", flush=True)
        before = run_audit(baseline, config)
        assert before.returncode == 1, "Baseline must fail the audit with pytest exit 1"
        diagnostics = re.findall(r"^E\s+(src/planzilla/[^\n]+)$", before.stdout, re.MULTILINE)
        assert len(diagnostics) == 3 and set(diagnostics) == EXPECTED, diagnostics
        assert re.search(r"^1 failed in ", before.stdout, re.MULTILINE), before.stdout

        print("Current runtime: same audit", flush=True)
        assert (root / AUDIT).read_bytes() == audit_bytes, "Audit changed during replay"
        after = run_audit(root, config)
        assert after.returncode == 0, "Current runtime must pass the same audit"
        assert re.search(r"^1 passed in ", after.stdout, re.MULTILINE), after.stdout
    print("Replay passed: exactly three baseline gaps; current runtime has none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
