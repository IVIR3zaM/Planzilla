"""Codex-only lifecycle across planner phases, execution, retries and cold review."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from planzilla import cli, resolver
from planzilla.commands import dispatch as host
from planzilla.config import Policy
from tests.commands.test_dispatch import LINE, SCHEMA, adapter, capability
from tests.commands.test_policy import MODELS, PIN, POLICY
from tests.commands.test_set import brief, make_l, row


def _assert_exact_dispatch(plan_ref: str, node_id: str, role: str) -> resolver.Selection:
    """Exercise the loaded package's host boundary using fixture callbacks only."""
    calls: list[dict[str, object]] = []
    records: list[resolver.Selection | resolver.Unavailable] = []
    line = f"Plan: demo · Node: {node_id} · Try: 1"
    reply = f"DONE {node_id} | tests: 1 passed" if role == "executor" else f"PASS {node_id}"

    def invoke(fields: dict[str, object]) -> str:
        calls.append(fields)
        return reply

    common = dict(
        actual_harness="codex",
        capabilities=(capability(),),
        adapters=(host.NativeAdapter("codex", SCHEMA, invoke),),
        record=records.append,
    )
    out, err = StringIO(), StringIO()
    # A native-only fixture must never discover, authenticate or launch any provider.
    with (
        patch("subprocess.run", side_effect=AssertionError("unexpected provider call")),
        patch("shutil.which", side_effect=AssertionError("unexpected executable probe")),
        redirect_stdout(out),
        redirect_stderr(err),
    ):
        assert host.dispatch(plan_ref, resolver.Request(role, "codex"), line, **common) == 2
        assert "cannot be overridden" in err.getvalue()
        assert not calls and not records
        assert host.dispatch(plan_ref, resolver.Request(role, PIN), line, **common) == 0
    assert out.getvalue() == reply + "\n"
    assert len(calls) == len(records) == 1
    assert calls[0]["task_name"] == f"plz-{role}"
    assert calls[0]["model"] == "gpt-6.1-sol"
    assert calls[0]["reasoning_effort"] == "high"
    assert calls[0]["fork_turns"] == "none"
    selected = records[0]
    assert isinstance(selected, resolver.Selection)
    assert selected.original == PIN
    assert selected.exact_id == selected.pins.exact_id == "gpt-6.1-sol"
    assert selected.effort == selected.pins.effort == "high"
    assert (selected.route, selected.mode, selected.delivery_id) == (
        "codex",
        "native",
        "codex-native",
    )
    assert selected.mismatch
    assert selected.evidence == ("fixture:observed",)
    return selected


def _check_installed_graph_lifecycle(root: Path) -> None:
    """Run in an isolated interpreter importing the freshly installed package."""
    assert Path(host.__file__).resolve().is_relative_to(root / ".planzilla/lib")
    medium_pair = f"gpt-6.1-sol@medium/{PIN}"
    plan = make_l(
        root,
        [
            row("N05", "DONE", t=1, model=medium_pair),
            row("N07", "DONE", t=1, model=medium_pair),
            row("N08", model=f"{PIN}/{PIN}"),
            row("N09", deps="N08", model=f"{PIN}/{PIN}"),
            row("N10", deps="N09", model=f"{PIN}/{PIN}"),
            row("N11", type="check", deps="N10", model=f"-/{PIN}"),
        ],
        {
            node: brief(node, "review", type="check" if node == "N11" else "exec")
            for node in ("N08", "N09", "N10", "N11")
        },
    )
    config = root / ".plan/config.md"
    config.write_text("harness: claude-code\nproviders: claude\nmodels: planner=opus\n")
    original_config = config.read_bytes()
    (plan / "log").mkdir()
    for node in ("N05", "N07"):
        (plan / f"log/{node}.md").write_text(f"# {node}\nexec medium; separate verify high\n")
    original_graph = (plan / "plan.md").read_text()
    history = {p: p.read_bytes() for p in (plan / "log").iterdir()}

    def snapshot() -> dict[Path, bytes]:
        return {p: p.read_bytes() for p in plan.rglob("*") if p.is_file()}

    with redirect_stdout(StringIO()):
        assert (
            cli.main(
                [
                    "policy",
                    str(plan),
                    "--harnesses",
                    "codex",
                    "--providers",
                    "codex",
                    "--models",
                    MODELS,
                ]
            )
            == 0
        )
        assert POLICY in (plan / "plan.md").read_text()
        assert (plan / "plan.md").read_text().split("## Graph", 1)[1] == original_graph.split(
            "## Graph", 1
        )[1]
        for node in ("N08", "N09", "N10", "N11"):
            if node != "N11":
                assert cli.main(["set", str(plan), node, "RUNNING"]) == 0
                before = snapshot()
                _assert_exact_dispatch(str(plan), node, "executor")
                assert snapshot() == before
            assert cli.main(["set", str(plan), node, "VERIFYING"]) == 0
            before = snapshot()
            _assert_exact_dispatch(str(plan), node, "verifier")
            assert snapshot() == before
            assert cli.main(["set", str(plan), node, "DONE"]) == 0
    assert config.read_bytes() == original_config
    assert {p: p.read_bytes() for p in history} == history
    graph = (plan / "plan.md").read_text()
    for node in ("N05", "N07"):
        assert next(line for line in original_graph.splitlines() if f"| {node} |" in line) in graph


def test_installed_exact_codex_graph_lifecycle(tmp_path: Path) -> None:
    import subprocess
    import sys

    source = Path(__file__).resolve().parents[2]
    installed = subprocess.run(
        ["uv", "run", "planzilla", "install", "--target", str(tmp_path)],
        cwd=source,
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
            "from tests.commands.test_policy_lifecycle import _check_installed_graph_lifecycle; "
            "_check_installed_graph_lifecycle(Path(sys.argv[3]))",
            str(tmp_path / ".planzilla/lib"),
            str(source),
            str(tmp_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_codex_policy_survives_every_lifecycle_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".plan").mkdir()
    config = tmp_path / ".plan/config.md"
    config.write_text(
        "harness: claude-code\nproviders: claude\n"
        "models: planner=opus, exec=sonnet, verify=sonnet\n"
    )
    original = config.read_bytes()
    calls: list[dict[str, str]] = []
    records: list = []
    common = dict(
        actual_harness="codex",
        capabilities=(capability(),),
        adapters=(adapter(calls),),
        record=records.append,
    )
    initial = Policy(("codex",), dict(item.split("=") for item in MODELS.split(", ")), ("codex",))
    assert (
        host.dispatch(
            None, resolver.Request("planner"), "Outline: demo", initial_policy=initial, **common
        )
        == 0
    )
    plan = make_l(
        tmp_path, [row("N01", model=f"gpt-6.1-sol@medium/{PIN}")], status="DRAFT", extra=POLICY
    )
    assert host.dispatch(str(plan), resolver.Request("planner"), "Revise: demo", **common) == 0
    graph = plan / "plan.md"
    # Simulate planner-owned confirmation and JIT brief writes in this controlled fixture.
    graph.write_text(graph.read_text().replace("status: DRAFT", "status: READY"))
    assert cli.main(["next", str(plan)]) == 0
    assert f"N01 brief {PIN}" in capsys.readouterr().out
    assert cli.main(["set", str(plan), "N01", "BRIEFING"]) == 0
    assert (
        host.dispatch(str(plan), resolver.Request("planner"), "Brief: demo · Node: N01", **common)
        == 0
    )
    (plan / "nodes/N01.md").write_text(brief("N01", "review"))
    assert cli.main(["set", str(plan), "N01", "TODO"]) == 0
    assert cli.main(["set", str(plan), "N01", "RUNNING"]) == 0
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, **common) == 0
    assert calls[-1]["reasoning_effort"] == "medium"
    assert cli.main(["set", str(plan), "N01", "VERIFYING"]) == 0
    assert host.dispatch(str(plan), resolver.Request("verifier"), LINE, **common) == 0
    assert calls[-1]["task_name"] == "plz-verifier" and calls[-1]["reasoning_effort"] == "high"
    assert cli.main(["set", str(plan), "N01", "RETRY", "--note", "fail C1"]) == 0
    assert cli.main(["set", str(plan), "N01", "RUNNING"]) == 0
    assert cli.main(["resume", str(plan)]) == 0
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, **common) == 0
    assert calls[-1]["reasoning_effort"] == "medium"
    assert cli.main(["set", str(plan), "N01", "REPLAN"]) == 0
    assert (
        host.dispatch(str(plan), resolver.Request("planner"), "Replan: demo · Node: N01", **common)
        == 0
    )
    assert calls[-1]["reasoning_effort"] == "high"
    assert host.dispatch(str(plan), resolver.Request("planner"), "Revise: demo", **common) == 0
    assert (
        cli.main(
            [
                "set",
                str(plan),
                "N02",
                "--add",
                "--title",
                "next",
                "--deps",
                "-",
                "--model",
                f"{PIN}/{PIN}",
            ]
        )
        == 0
    )
    assert cli.main(["set", str(plan), "N02", "BRIEFING"]) == 0
    assert (
        host.dispatch(str(plan), resolver.Request("planner"), "Brief: demo · Node: N02", **common)
        == 0
    )
    (plan / "nodes/N02.md").write_text(brief("N02", "review"))
    assert cli.main(["set", str(plan), "N02", "TODO"]) == 0
    assert cli.main(["set", str(plan), "N02", "RUNNING"]) == 0
    assert (
        host.dispatch(str(plan), resolver.Request("executor"), LINE.replace("N01", "N02"), **common)
        == 0
    )
    assert calls[-1]["reasoning_effort"] == "high"
    assert (
        host.dispatch(str(plan), resolver.Request("verifier"), "Final review: demo", **common) == 0
    )
    assert calls[-1]["task_name"] == "plz-verifier"
    assert config.read_bytes() == original
    assert all(record.route == "codex" and record.exact_id == "gpt-6.1-sol" for record in records)
    assert [call["task_name"] for call in calls].count("plz-verifier") == 2
