"""Policy persistence and lifecycle regression tests; no provider access."""

from pathlib import Path

import pytest

from planzilla import cli
from tests.commands.test_set import brief, graph_text, make_l, row

PIN = "gpt-6.1-sol@high"
MODELS = f"planner={PIN}, exec={PIN}, verify={PIN}"
POLICY = f"harnesses: codex\nproviders: codex\nmodels: {MODELS}\n"


def invoke(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = cli.main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("command", ["next", "set"])
@pytest.mark.parametrize("phase", ["brief", "replan", "verify"])
def test_effective_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: str, phase: str
) -> None:
    status = {"brief": "TODO", "replan": "REPLAN", "verify": "VERIFYING"}[phase]
    plan = make_l(
        tmp_path,
        [row("N01", status, model=f"{PIN}/-")],
        {"N01": brief("N01", "review")} if phase == "verify" else {},
        extra=POLICY,
    )
    if command == "next":
        args = ["next", str(plan)]
        expected = f"N01 {phase} {PIN}\n"
    else:
        target = {"brief": "BRIEFING", "replan": "REPLAN", "verify": "VERIFYING"}[phase]
        args = ["set", str(plan), "N01", target]
        agent = "verifier" if phase == "verify" else "planner"
        expected = f"N01 {target} try 0 rp 0 · dispatch plz-{agent} {PIN}\n"
    assert invoke(capsys, *args) == (0, expected, "")


@pytest.mark.parametrize(
    "args",
    [
        ["set", "N01", "--model", "claude::opus/opus"],
        ["set", "N02", "--add", "--title", "new", "--deps", "-", "--model", "opus/copilot::opus"],
        ["set", "N01", "RETRY"],
        ["next"],
        ["resume"],
    ],
)
def test_restricted_lifecycle_failure_is_atomic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    model = "claude::opus/opus" if len(args) < 3 or args[-1] == "RETRY" else f"{PIN}/{PIN}"
    plan = make_l(
        tmp_path,
        [row("N01", "RUNNING", t=1, model=model)],
        {"N01": brief("N01", "review")},
        extra=POLICY,
    )
    before = {p: p.read_bytes() for p in plan.rglob("*") if p.is_file()}
    code, out, err = invoke(capsys, args[0], str(plan), *args[1:])
    assert (code, out) == (2, "")
    assert "permitted" in err or "allowed" in err or "provider" in err
    assert {p: p.read_bytes() for p in plan.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "option,value",
    [
        ("--providers", ""),
        ("--providers", "codex,codex"),
        ("--providers", "bad"),
        ("--harnesses", ""),
        ("--harnesses", "codex,codex"),
        ("--harnesses", "bad"),
        ("--models", ""),
        ("--models", "planner=opus, planner=opus"),
        ("--models", "planner=-"),
        ("--models", "planner=claude::opus"),
        ("--providers", "claude"),
        ("--harnesses", "copilot"),
    ],
)
def test_invalid_policy_never_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], option: str, value: str
) -> None:
    plan = make_l(tmp_path, [row("N01", model=f"{PIN}/{PIN}")], extra=POLICY)
    before = graph_text(plan)
    code, out, err = invoke(capsys, "policy", str(plan), option, value)
    assert (code, out) == (2, "")
    assert err.startswith("error: ")
    assert graph_text(plan) == before


def test_policy_round_trip_preserves_graph_and_unrelated_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", model="gpt-6.1-sol@medium/gpt-6.1-sol@high")])
    before = graph_text(plan)
    code, out, err = invoke(
        capsys,
        "policy",
        str(plan),
        "--harnesses",
        "codex",
        "--providers",
        "codex",
        "--models",
        MODELS,
    )
    assert (code, out, err) == (0, "policy updated: 2026-09-01-demo\n", "")
    after = graph_text(plan)
    assert POLICY in after
    assert after.split("\n\n", 1)[1] == before.split("\n\n", 1)[1]
    assert invoke(capsys, "next", str(plan)) == (0, f"N01 brief {PIN}\n", "")


def test_policy_rejects_existing_graph_before_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = make_l(tmp_path, [row("N01", model="copilot::opus/opus")])
    before = graph_text(plan)
    assert invoke(capsys, "policy", str(plan), "--providers", "codex")[0] == 2
    assert graph_text(plan) == before


def test_policy_keeps_unspecified_header_bytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    extra = "harnesses: codex, copilot  \nproviders: codex, copilot  \nmodels: planner=opus\n"
    plan = make_l(tmp_path, [row("N01", model="opus/sonnet")], extra=extra)
    assert invoke(capsys, "policy", str(plan), "--models", f"planner={PIN}")[0] == 0
    after = graph_text(plan)
    assert "harnesses: codex, copilot  \nproviders: codex, copilot  \n" in after


@pytest.mark.parametrize(
    "harnesses,providers", [("codex", "codex"), ("codex,copilot", "codex,copilot")]
)
def test_policy_partial_roles_and_multiple_harnesses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], harnesses: str, providers: str
) -> None:
    plan = make_l(tmp_path, [row("N01", model="opus/sonnet")])
    assert (
        invoke(
            capsys,
            "policy",
            str(plan),
            "--harnesses",
            harnesses,
            "--providers",
            providers,
            "--models",
            f"planner={PIN}",
        )[0]
        == 0
    )
    assert invoke(capsys, "next", str(plan)) == (0, f"N01 brief {PIN}\n", "")
    assert "models: planner=" + PIN + "\n" in graph_text(plan)
    assert "opus/sonnet" in graph_text(plan)


def test_policy_requires_update_and_atomic_replace_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from planzilla.commands import _common

    plan = make_l(tmp_path, [row("N01")])
    before = graph_text(plan)
    assert invoke(capsys, "policy", str(plan))[0] == 2

    def fail_replace(*args: object) -> None:
        raise OSError("fixture: replace failed")

    monkeypatch.setattr(_common.os, "replace", fail_replace)
    assert invoke(capsys, "policy", str(plan), "--providers", "codex")[0] == 3
    assert graph_text(plan) == before
    assert not plan.with_name(plan.name + ".lock").exists()


def test_source_upgrade_installed_policy_preserves_plan(tmp_path: Path) -> None:
    import subprocess
    import sys

    plan = make_l(tmp_path, [row("N01", model="gpt-6.1-sol@medium/gpt-6.1-sol@high")])
    (plan / "log").mkdir()
    (plan / "log/N01.md").write_text("# N01 log\nfixture: immutable history\n")

    def snapshot() -> dict[str, bytes]:
        return {
            p.relative_to(tmp_path / ".plan").as_posix(): p.read_bytes()
            for p in (tmp_path / ".plan").rglob("*")
            if p.is_file()
        }

    before = snapshot()
    source = Path(__file__).resolve().parents[2]
    for _ in range(2):
        result = subprocess.run(
            ["uv", "run", "planzilla", "install", "--target", str(tmp_path)],
            cwd=source,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "installed planzilla" in result.stdout
        assert snapshot() == before
        launcher = tmp_path / ".planzilla/plz"
        help_result = subprocess.run(
            [sys.executable, str(launcher), "policy", "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert help_result.returncode == 0 and "--harnesses" in help_result.stdout
    changed = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "policy",
            "demo",
            "--harnesses",
            "codex",
            "--providers",
            "codex",
            "--models",
            MODELS,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert (changed.returncode, changed.stdout, changed.stderr) == (
        0,
        "policy updated: 2026-09-01-demo\n",
        "",
    )
    after = snapshot()
    assert {k: v for k, v in after.items() if k != "2026-09-01-demo/plan.md"} == {
        k: v for k, v in before.items() if k != "2026-09-01-demo/plan.md"
    }
    assert (
        graph_text(plan).split("## Graph", 1)[1]
        == before["2026-09-01-demo/plan.md"].decode().split("## Graph", 1)[1]
    )
    next_result = subprocess.run(
        [sys.executable, str(launcher), "next", "demo"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert next_result.stdout == f"N01 brief {PIN}\n"
