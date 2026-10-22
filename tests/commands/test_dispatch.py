"""Drive the callable host boundary with controlled observations, never live tools."""

from dataclasses import replace
from pathlib import Path

import pytest

from planzilla import resolver
from planzilla.commands import dispatch as host
from planzilla.commands import run as run_cmd
from planzilla.config import Policy
from tests.commands.test_policy import PIN, POLICY
from tests.commands.test_set import make_l, row

SCHEMA = {
    "task_name": None,
    "message": None,
    "model": ("gpt-6.1-sol",),
    "reasoning_effort": ("high", "medium", "low"),
    "fork_turns": ("none",),
}
LINE = "Plan: demo · Node: N01 · Try: 1"


def capability(route: str = "codex", mode: str = "native", **kwargs: object) -> resolver.Capability:
    model = (
        resolver.Model("gpt-6.1-sol", "sol", efforts=("high", "medium", "low"))
        if route == "codex"
        else resolver.Model("claude-opus-5", "opus", ("opus",), ("high",))
    )
    return replace(
        resolver.Capability(
            route,
            mode,
            f"{route}-{mode}",
            (model,),
            True,
            True,
            "callable_native" if mode == "native" else "external_reply",
            ("fixture:observed",),
        ),
        **kwargs,
    )


def adapter(
    calls: list[dict[str, str]], schema: dict = SCHEMA, route: str = "codex", **kwargs: object
) -> host.NativeAdapter:
    def invoke(fields: dict[str, str]) -> str:
        calls.append(fields)
        return "thinking\nDONE N01 | tests: 1 passed\n"

    return host.NativeAdapter(route, schema, invoke, **kwargs)


@pytest.mark.parametrize(
    "token,effort",
    [
        (None, "high"),
        ("opus", "high"),
        ("sonnet", "medium"),
        ("codex::gpt-6.1-sol@high", "high"),
        ("gpt-6.1-sol@medium", "medium"),
    ],
)
def test_actual_codex_over_configured_claude(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    token: str | None,
    effort: str,
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{token or PIN}/{PIN}")], extra=POLICY)
    monkeypatch.chdir(tmp_path)
    calls: list[dict[str, str]] = []
    records: list = []
    result = host.dispatch(
        str(plan),
        resolver.Request("executor", token),
        LINE,
        actual_harness="codex",
        capabilities=(capability(),),
        adapters=(adapter(calls),),
        record=records.append,
    )
    assert result == 0
    assert calls[0]["model"] == "gpt-6.1-sol"
    assert calls[0]["reasoning_effort"] == effort
    assert calls[0]["fork_turns"] == "none"
    assert calls[0]["task_name"] == "plz-executor"
    assert "Follow .planzilla/roles/executor.md" in calls[0]["message"]
    assert "AGENTS.md" in calls[0]["message"]
    assert capsys.readouterr().out == "DONE N01 | tests: 1 passed\n"
    selected = records[0]
    assert selected.mismatch and selected.original == (token or PIN)
    assert selected.delivery_id == "codex-native" and selected.evidence == ("fixture:observed",)


@pytest.mark.parametrize(
    "missing", ["model", "reasoning_effort", "fork_turns", "task_name", "message"]
)
def test_missing_actual_native_controls_falls_back_through_run_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"codex::{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    launched: list = []
    monkeypatch.setattr(run_cmd, "run_selection", lambda *args: launched.append(args) or 0)
    schema = {k: v for k, v in SCHEMA.items() if k != missing}
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", "codex::gpt-6.1-sol@high"),
            LINE,
            actual_harness="codex",
            capabilities=(capability(), capability(mode="cli")),
            adapters=(adapter(calls, schema),),
        )
        == 0
    )
    assert not calls
    selection = launched[0][1]
    assert selection.mode == "cli"
    assert selection.pins == resolver.Pins("gpt-6.1-sol", "high", "codex")
    assert selection.failures[0].reason == "unsupported_selection"


def test_no_native_controls_or_cli_gives_focused_handoff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", PIN),
            LINE,
            actual_harness="codex",
            capabilities=(capability(),),
        )
        == 3
    )
    out = capsys.readouterr()
    assert out.out == ""
    for text in ("executor", "unsupported_selection", "fixture:observed", "evidence", "authorize"):
        assert text in out.err


def test_disallowed_coordinator_precedes_default_and_tools(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("planner"),
            "Replan: demo",
            actual_harness="copilot",
            capabilities=(capability(),),
            adapters=(adapter(calls),),
        )
        == 2
    )
    assert not calls
    assert "coordinator copilot is not in harnesses" in capsys.readouterr().err


def test_native_only_copilot_uses_supplied_schema_and_separate_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(
        tmp_path,
        [row("N01", "RUNNING", model="copilot::opus@high/copilot::opus@high")],
        extra=(
            "harnesses: copilot\nproviders: copilot\n"
            "models: planner=opus@high, exec=opus@high, verify=opus@high\n"
        ),
    )
    calls: list[dict[str, str]] = []
    schema = {
        "agent": None,
        "prompt": None,
        "model": ("claude-opus-5",),
        "reasoningEffort": ("high",),
    }
    native = adapter(
        calls,
        schema,
        "copilot",
        role_field="agent",
        input_field="prompt",
        effort_field="reasoningEffort",
        fixed={},
    )
    records: list = []
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", "copilot::opus@high"),
            LINE,
            actual_harness="copilot",
            capabilities=(capability("copilot"),),
            adapters=(native,),
            reviewer=resolver.Request("verifier", "copilot::opus@high"),
            review_line=LINE,
            record=records.append,
        )
        == 0
    )
    assert [c["agent"] for c in calls] == ["plz-executor"]
    assert len(records) == 2
    (plan / "plan.md").write_text(
        (plan / "plan.md").read_text().replace("| RUNNING |", "| VERIFYING |")
    )
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", "copilot::opus@high"),
            LINE,
            actual_harness="copilot",
            capabilities=(capability("copilot"),),
            adapters=(native,),
            reviewer=resolver.Request("verifier", "copilot::opus@high"),
            review_line=LINE,
            review=True,
        )
        == 0
    )
    assert [c["agent"] for c in calls] == ["plz-executor", "plz-verifier"]
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("verifier", "copilot::opus@high", visual=True),
            LINE,
            actual_harness="copilot",
            capabilities=(capability("copilot"),),
            adapters=(native,),
        )
        == 3
    )
    assert len(calls) == 2
    assert "visual" in capsys.readouterr().err


@pytest.mark.parametrize("quota,expected", [("independent", 0), ("shared", 3), ("unknown", 3)])
def test_pair_fallback_retains_deliberate_independence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, quota: str, expected: int
) -> None:
    plan = make_l(
        tmp_path,
        [row("N01", "RUNNING", model="claude-opus-5@high/copilot::claude-opus-5@high")],
        extra=(
            "harnesses: claude-code,copilot\nproviders: claude,copilot\n"
            "models: planner=opus@high, exec=opus@high, verify=opus@high\n"
        ),
    )
    calls: list[dict[str, str]] = []
    schema = {
        "agent": None,
        "prompt": None,
        "model": ("claude-opus-5",),
        "reasoningEffort": ("high",),
    }
    native = adapter(
        calls,
        schema,
        "copilot",
        role_field="agent",
        input_field="prompt",
        effort_field="reasoningEffort",
        fixed={},
    )
    launched: list = []
    monkeypatch.setattr(run_cmd, "run_selection", lambda *args: launched.append(args) or 0)
    failed = capability(
        "claude",
        "cli",
        delivery_id="failed",
        failure=resolver.Failure("quota_exhausted", ("fixture:failure",)),
    )
    good = capability("claude", "cli", quota_id="A", quota_evidence=("fixture:quota-A",))
    review = capability(
        "copilot",
        quota_id={"independent": "B", "shared": "A", "unknown": None}[quota],
        quota_evidence=("fixture:quota-B",),
    )
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", "claude-opus-5@high"),
            LINE,
            actual_harness="copilot",
            capabilities=(failed, good, review),
            adapters=(native,),
            reviewer=resolver.Request("verifier", "copilot::claude-opus-5@high"),
            review_line=LINE,
            independence=resolver.Independence(delivery=True, quota=True),
        )
        == expected
    )
    assert not calls
    assert len(launched) == (1 if expected == 0 else 0)
    if expected == 0:
        (plan / "plan.md").write_text(
            (plan / "plan.md").read_text().replace("| RUNNING |", "| VERIFYING |")
        )
        assert (
            host.dispatch(
                str(plan),
                resolver.Request("executor", "claude-opus-5@high"),
                LINE,
                actual_harness="copilot",
                capabilities=(failed, good, review),
                adapters=(native,),
                reviewer=resolver.Request("verifier", "copilot::claude-opus-5@high"),
                review_line=LINE,
                independence=resolver.Independence(delivery=True, quota=True),
                review=True,
            )
            == 0
        )
        assert len(calls) == 1
    if launched:
        assert launched[0][1].pins.exact_id == "claude-opus-5"
        assert launched[0][1].failures[0].evidence == ("fixture:failure",)


def test_initial_planning_without_plan_uses_supplied_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[dict[str, str]] = []
    assert (
        host.dispatch(
            None,
            resolver.Request("planner"),
            "Outline: demo",
            actual_harness="codex",
            capabilities=(capability(),),
            adapters=(adapter(calls),),
            initial_policy=Policy(("codex",), {"planner": PIN}, ("codex",)),
        )
        == 0
    )
    assert calls[0]["task_name"] == "plz-planner"
    assert calls[0]["reasoning_effort"] == "high"


def test_graph_pin_and_state_checked_at_callable_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", model="gpt-6.1-sol@medium/gpt-6.1-sol@high")], extra=POLICY)
    calls: list[dict[str, str]] = []
    common = dict(
        actual_harness="codex",
        capabilities=(capability(),),
        adapters=(adapter(calls),),
        node_id="N01",
    )
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, **common) == 2
    assert not calls
    assert "before dispatch" in capsys.readouterr().err
    text = (plan / "plan.md").read_text().replace("| TODO |", "| RUNNING |")
    (plan / "plan.md").write_text(text)
    assert host.dispatch(str(plan), resolver.Request("executor", PIN), LINE, **common) == 2
    assert not calls
    assert "cannot be overridden" in capsys.readouterr().err
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, **common) == 0
    assert calls[0]["reasoning_effort"] == "medium"


def test_cli_dispatch_loads_facts_and_uses_resolved_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json
    from dataclasses import asdict

    from planzilla import cli

    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps([asdict(capability(mode="cli"))]))
    launched: list = []
    monkeypatch.setattr(run_cmd, "run_selection", lambda *args: launched.append(args) or 0)
    record = tmp_path / "record.json"
    assert (
        cli.main(
            [
                "dispatch",
                str(plan),
                "executor",
                LINE,
                "--node",
                "N01",
                "--actual-harness",
                "codex",
                "--facts",
                str(facts),
                "--record",
                str(record),
            ]
        )
        == 0
    )
    assert launched[0][1].exact_id == "gpt-6.1-sol"
    assert launched[0][1].effort == "high"
    saved = json.loads(record.read_text())[0]
    assert saved["pins"]["exact_id"] == "gpt-6.1-sol"
    assert saved["mismatch"] is True
    assert saved["evidence"] == ["fixture:observed"]
    assert capsys.readouterr().err == ""


def test_pair_selection_does_not_launch_review_before_state_transition(tmp_path: Path) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", t=1, model=f"{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    common = dict(
        actual_harness="codex",
        capabilities=(capability(),),
        adapters=(adapter(calls),),
        node_id="N01",
        reviewer=resolver.Request("verifier"),
        review_line=LINE,
    )
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, **common) == 0
    assert [c["task_name"] for c in calls] == ["plz-executor"]
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, review=True, **common) == 2
    assert len(calls) == 1
    (plan / "plan.md").write_text(
        (plan / "plan.md").read_text().replace("| RUNNING |", "| VERIFYING |")
    )
    assert host.dispatch(str(plan), resolver.Request("executor"), LINE, review=True, **common) == 0
    assert [c["task_name"] for c in calls] == ["plz-executor", "plz-verifier"]


def test_node_input_cannot_bypass_graph_pins(tmp_path: Path) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor", "sonnet"),
            LINE,
            actual_harness="codex",
            capabilities=(capability(),),
            adapters=(adapter(calls),),
        )
        == 2
    )
    assert not calls


@pytest.mark.parametrize(
    "changes",
    [
        {"model_field": "task_name"},
        {"effort_field": "model"},
        {"fixed": {"fork_turns": "none", "reasoning_effort": "low"}},
    ],
)
def test_conflicting_native_field_bindings_never_launch(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor"),
            LINE,
            actual_harness="codex",
            capabilities=(capability(),),
            adapters=(adapter(calls, **changes),),
        )
        == 3
    )
    assert not calls


def test_mismatch_is_visible_without_record_sink(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", "RUNNING", model=f"{PIN}/{PIN}")], extra=POLICY)
    calls: list[dict[str, str]] = []
    assert (
        host.dispatch(
            str(plan),
            resolver.Request("executor"),
            LINE,
            actual_harness="codex",
            capabilities=(capability(),),
            adapters=(adapter(calls),),
        )
        == 0
    )
    assert "configured claude-code; actual codex" in capsys.readouterr().err


@pytest.mark.parametrize("outcome", ["success", "exit", "signal", "missing", "unreadable", "empty"])
def test_dispatch_cli_uses_plan_repository_and_exact_tuple(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    import shutil
    import subprocess

    from tests.commands.test_run import Fake

    root = tmp_path / "repo"
    plan = make_l(root, [row("N01", "RUNNING", model=f"codex::{PIN}/{PIN}")], extra=POLICY)
    monkeypatch.chdir(tmp_path)
    fake = Fake()
    if outcome in ("exit", "signal"):
        fake.main = (7 if outcome == "exit" else -9, "fallback", "observed detail")
    if outcome in ("missing", "empty"):
        fake.reply = None if outcome == "missing" else " \n"
    read_text = Path.read_text

    def read(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "reply.txt" and outcome == "unreadable":
            raise PermissionError("read denied")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(subprocess, "run", fake)
    lookups: list[str] = []
    selections: list[resolver.Selection | resolver.Unavailable] = []
    monkeypatch.setattr(shutil, "which", lambda name: lookups.append(name) or f"/bin/{name}")
    assert host.dispatch(
        str(plan),
        resolver.Request("executor"),
        LINE,
        actual_harness="codex",
        capabilities=(capability("claude", "cli"), capability(mode="cli")),
        record=selections.append,
    ) == (0 if outcome == "success" else 3)
    assert len(selections) == 1 and isinstance(selections[0], resolver.Selection)
    assert selections[0].mismatch
    assert lookups == ["codex"]
    login, main = fake.calls
    assert login[0] == ["codex", "login", "status"]
    argv, kwargs = main
    assert argv[:6] == ["codex", "exec", "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"']
    assert argv[argv.index("-C") + 1] == str(root)
    assert kwargs["cwd"] == str(root)
    assert f"Input: {LINE}" in kwargs["input"]
    captured = capsys.readouterr()
    assert fake.out_dir is not None and not fake.out_dir.exists()
    if outcome == "success":
        assert (captured.out, captured.err) == ("PASS N01\n", "")
    else:
        assert captured.out == "" and captured.err.count("\n") == 1
        expected = {
            "exit": "codex exited 7: observed detail",
            "signal": "codex terminated by signal 9: observed detail",
            "missing": "codex reply read failed: ",
            "unreadable": "codex reply read failed: read denied",
            "empty": "codex gave an empty reply",
        }[outcome]
        assert captured.err.startswith(f"error: {expected}")
