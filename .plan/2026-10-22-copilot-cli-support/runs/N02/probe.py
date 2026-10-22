"""Bounded N02 research observations; every provider call below is mocked."""

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from planzilla import runner
from planzilla.commands import run as run_command


def mock_run(role: str, effort: str, outcome: str = "success") -> dict[str, object]:
    """Observe dispatch/reply behavior without calling a provider or auth process."""
    calls: list[list[str]] = []
    scratch = Path(__file__).resolve().parent / "mock-reply"
    scratch.mkdir(exist_ok=False)

    def fake_call(
        argv: list[str], cli: str, cwd: str, prompt: str | None = None
    ) -> subprocess.CompletedProcess[str] | None:
        calls.append(argv)
        if argv[1:3] == ["login", "status"]:
            return subprocess.CompletedProcess(argv, 1 if outcome == "auth" else 0, "", "")
        if outcome == "spawn":
            return None
        if outcome == "quota":
            return subprocess.CompletedProcess(
                argv, 1, "", "rate_limit_error: usage limit reached (synthetic fixture)"
            )
        if outcome == "signal":
            return subprocess.CompletedProcess(argv, -15, "", "")
        if outcome != "empty":
            Path(argv[argv.index("-o") + 1]).write_text(
                "intermediate fixture line\nDONE probe | tests: 0 passed\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(argv, 0, "not the final reply", "")

    args = argparse.Namespace(
        role=role,
        model=f"gpt-6.1-sol@{effort}",
        line="Plan: capability-probe · Node: MOCK · Try: 1",
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with (
            patch.object(run_command.shutil, "which", return_value="/mock/codex"),
            patch.object(run_command, "_call", side_effect=fake_call),
            patch.object(run_command.tempfile, "mkdtemp", return_value=str(scratch)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = run_command.run(args)
    finally:
        if scratch.exists():
            scratch.rmdir()
    return {
        "evidence": "mocked",
        "role": role,
        "model": args.model,
        "outcome": outcome,
        "exit": code,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "argv": calls,
    }


def wait_cancel_observation() -> dict[str, object]:
    """Cancel only our benign child; do not infer a provider termination reason."""
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(30)"],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        ready = child.stdout.readline().strip()
        running = child.poll() is None
        child.terminate()
        code = child.wait(timeout=5)
        return {
            "evidence": "demonstrated, benign local process only",
            "ready": ready,
            "pending_before_cancel": running,
            "action": "parent explicitly sent terminate()",
            "returncode": code,
            "provider_or_plz_cancellation": "not exercised",
        }
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        if child.stdout is not None:
            child.stdout.close()


def main() -> None:
    """Print sanitized, reproducible observations."""
    root = str(Path.cwd())
    artifact = str(Path(__file__).resolve().parent)
    results: dict[str, object] = {
        "date": "2026-10-22",
        "model_auth_quota_calls": "none; all runner process calls mocked",
        "dispatch": [
            mock_run(role, effort)
            for role in ("planner", "executor", "verifier")
            for effort in ("medium", "high")
        ],
        "failures": [
            mock_run("executor", "high", outcome)
            for outcome in ("auth", "quota", "signal", "spawn", "empty")
        ],
        "default_opus_under_current_resolver": runner.validate("planner", "opus", "Brief: p N02"),
        "name_collision": {
            name: runner.validate("executor", name, "x")
            for name in ("opus", "claude-opus-5.5", "gpt-6.1-sol")
        },
        "wait_cancel": wait_cancel_observation(),
    }
    rendered = json.dumps(results, indent=2, ensure_ascii=False)
    print(rendered.replace(artifact, "<artifact-dir>").replace(root, "<repo>"))


if __name__ == "__main__":
    main()
