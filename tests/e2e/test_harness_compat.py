"""Installed public boundaries with controlled delivery facts, never live providers.

The full installed lifecycle/pin matrix lives in test_policy_lifecycle; these cases
cover only compatibility across absent, single-harness and multiple-harness policy.
"""

import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from planzilla import cli, resolver
from planzilla.commands import dispatch as host
from tests.e2e.harness import NAME, REF, build_plan, exec_node

SOURCE = Path(__file__).resolve().parents[2]
LINE = "Plan: demo · Node: N01 · Try: 1"
REPLY = "DONE N01 | tests: 1 passed"
EVIDENCE = ("controlled fixture: no live model/auth/quota/browser claim",)


def command(*args: str) -> tuple[int, str, str]:
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(args))
    return code, out.getvalue(), err.getvalue()


def facts(route: str, mode: str = "native") -> resolver.Capability:
    model = (
        resolver.Model("gpt-6.1-sol", "sol", efforts=("medium", "high"))
        if route == "codex"
        else resolver.Model("claude-sonnet-5", "sonnet", ("sonnet",), ("medium", "high"))
    )
    return resolver.Capability(
        route,
        mode,
        f"fixture-{route}-{mode}",
        (model,),
        True,
        True,
        "callable_native" if mode == "native" else "external_reply",
        EVIDENCE,
    )


def _check_installed(root: Path, scenario: str) -> None:
    """Called in an isolated interpreter whose first import path is installed lib."""
    assert Path(host.__file__).resolve().is_relative_to(root / ".planzilla/lib")
    config = "harness: claude-code\nproviders: claude\n"
    build_plan(root, "S", [exec_node("N01", "fixture")], config=config)
    calls: list[dict[str, object]] = []
    records: list[resolver.Selection | resolver.Unavailable] = []

    def native(fields: dict[str, object]) -> str:
        calls.append(fields)
        return "fixture thinking\n" + REPLY

    # Non-Codex fixture schemas deliberately use different host field names.
    schema: dict[str, tuple[object, ...] | None] = {
        "agent": None,
        "prompt": None,
        "model": ("claude-sonnet-5",),
        "reasoningEffort": ("high", "medium"),
    }
    route = "claude" if scenario == "legacy" else "copilot"
    adapter = host.NativeAdapter(
        route,
        schema,
        native,
        role_field="agent",
        input_field="prompt",
        effort_field="reasoningEffort",
        fixed={},
    )
    if scenario == "legacy":
        assert command("next", REF) == (0, "N01 exec sonnet\n", "")
    else:
        harnesses = "codex, copilot" if scenario == "multiple" else route
        provider = "codex" if scenario in ("restricted", "multiple") else "copilot"
        if scenario == "restricted":
            harnesses = "codex"
        result = command("policy", REF, "--harnesses", harnesses, "--providers", provider)
        assert result == (0, f"policy updated: {NAME}\n", ""), result
    token = "copilot::claude-sonnet-5@high" if scenario == "copilot" else "sonnet"
    if scenario == "copilot":
        assert command("set", REF, "N01", "--model", token + "/-")[0] == 0
    code, out, err = command("set", REF, "N01", "RUNNING")
    assert code == 0 and err == "" and f"dispatch plz-executor {token}" in out
    before = {p: p.read_bytes() for p in (root / ".plan").rglob("*") if p.is_file()}

    def dispatch(
        capabilities: tuple[resolver.Capability, ...],
        adapters: tuple[host.NativeAdapter, ...] = (adapter,),
        token: str | None = None,
    ) -> tuple[int, str, str]:
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = host.dispatch(
                REF,
                resolver.Request("executor", token),
                LINE,
                actual_harness="claude-code" if scenario == "legacy" else "copilot",
                capabilities=capabilities,
                adapters=adapters,
                record=records.append,
            )
        return code, out.getvalue(), err.getvalue()

    if scenario == "multiple":
        probes: list[str] = []
        processes: list[list[str]] = []

        def which(name: str) -> str:
            assert name == "codex", "excluded Copilot must not be probed"
            probes.append(name)
            return "/fixture/codex"

        def process(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            processes.append(argv)
            assert kwargs["cwd"] == str(root)
            if argv == ["codex", "login", "status"]:
                return subprocess.CompletedProcess(argv, 0, "", "fixture logged in")
            assert argv[:6] == [
                "codex",
                "exec",
                "-m",
                "gpt-6.1-sol",
                "-c",
                'model_reasoning_effort="medium"',
            ]
            assert LINE in str(kwargs["input"])
            Path(argv[argv.index("-o") + 1]).write_text("fixture thinking\n" + REPLY)
            return subprocess.CompletedProcess(argv, 0, "", "")

        with patch("shutil.which", which), patch("subprocess.run", process):
            assert dispatch((facts("copilot"), facts("codex", "cli"))) == (0, REPLY + "\n", "")
        assert probes == ["codex"] and len(processes) == 2 and calls == []
        selected = records[-1]
        assert isinstance(selected, resolver.Selection)
        assert (selected.route, selected.mode, selected.exact_id, selected.effort) == (
            "codex",
            "cli",
            "gpt-6.1-sol",
            "medium",
        )
    else:
        with (
            patch("subprocess.run", side_effect=AssertionError("unexpected provider invocation")),
            patch("shutil.which", side_effect=AssertionError("unexpected executable probe")),
        ):
            if scenario == "restricted":
                code, out, err = dispatch((facts("copilot"), facts("codex")))
                assert code == 2 and out == ""
                assert "coordinator copilot is not in harnesses" in err
                assert calls == records == []
            else:
                if scenario == "copilot":
                    # Session/profile claims cannot replace an enforceable per-call effort control.
                    incomplete = replace(
                        adapter, schema={k: v for k, v in schema.items() if k != "reasoningEffort"}
                    )
                    code, out, err = dispatch((facts(route),), (incomplete,))
                    assert code == 3 and out == "" and "unsupported_selection" in err
                    assert calls == []
                    records.clear()
                assert dispatch((facts(route),)) == (0, REPLY + "\n", "")
                assert len(calls) == len(records) == 1
                assert calls[0]["agent"] == "plz-executor"
                assert calls[0]["model"] == "claude-sonnet-5"
                assert "AGENTS.md" in str(calls[0]["prompt"])
                assert "Follow .planzilla/roles/executor.md" in str(calls[0]["prompt"])
                assert isinstance(records[0], resolver.Selection)
                assert records[0].route == route and records[0].evidence == EVIDENCE
                if scenario == "copilot":
                    assert calls[0]["reasoningEffort"] == "high"
                    assert records[0].pins == resolver.Pins("claude-sonnet-5", "high", "copilot")
                    copilot_calls: list[list[str]] = []

                    def which(name: str) -> str:
                        assert name == "copilot", "gh must not be probed when copilot is on PATH"
                        return "/fixture/copilot"

                    def process(
                        argv: list[str], **kwargs: object
                    ) -> subprocess.CompletedProcess[str]:
                        copilot_calls.append(argv)
                        assert argv[0] == "copilot" and kwargs["cwd"] == str(root)
                        reply = "fixture thinking\n" + REPLY
                        return subprocess.CompletedProcess(argv, 0, reply, "")

                    calls.clear()
                    with patch("shutil.which", which), patch("subprocess.run", process):
                        run = command("run", "executor", "copilot::claude-sonnet-5@high", LINE)
                        assert run == (0, REPLY + "\n", "")
                        assert len(copilot_calls) == 1
                        assert LINE in copilot_calls[0][copilot_calls[0].index("-p") + 1]
                        argv = copilot_calls[0]
                        assert argv[argv.index("--model") + 1] == "claude-sonnet-5"
                        assert argv[argv.index("--reasoning-effort") + 1] == "high"
                        copilot_calls.clear()
                        assert dispatch((facts("copilot", "cli"),), ()) == (0, REPLY + "\n", "")
                        assert len(copilot_calls) == 1
                        assert "--model" in copilot_calls[0]
                        assert copilot_calls[0][copilot_calls[0].index("--model") + 1] == (
                            "claude-sonnet-5"
                        )
                    assert calls == []
    assert (root / ".plan/config.md").read_text() == config
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("scenario", ["legacy", "restricted", "multiple", "copilot"])
def test_installed_harness_compatibility(tmp_path: Path, scenario: str) -> None:
    installed = subprocess.run(
        [sys.executable, "-m", "planzilla", "install", "--target", str(tmp_path)],
        cwd=SOURCE,
        capture_output=True,
        text=True,
    )
    assert installed.returncode == 0, installed.stderr
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; from pathlib import Path; "
            "sys.path[:0] = [sys.argv[1], sys.argv[2]]; "
            "from tests.e2e.test_harness_compat import _check_installed; "
            "_check_installed(Path(sys.argv[3]), sys.argv[4])",
            str(tmp_path / ".planzilla/lib"),
            str(SOURCE),
            str(tmp_path),
            scenario,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
