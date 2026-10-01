"""`planzilla status`: the §12 text, read-only (FORMAT §9, §12)."""

import os
import subprocess
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import status
from tests.test_report import NOW, STATUS_TEXT, write_plan

NO_GIT_TEXT = "\n".join(
    [
        "Demo plan · RUNNING · 2/5 done · -",
        "wave 1",
        "  N01 done · Scaffold · try 1 rp 0 · - · - · check: PASS 2/2",
        "wave 2",
        "  N02 done · Parser · try 2 rp 1 · - · - · verify: PASS",
        "  N03 executing · Reports · try 1 rp 0 · - · - · exec: DONE · 1 passed",
        "  N04 blocked · Docs · try 1 rp 2 · - · blocked: no spec · exec: BLOCKED · no spec",
        "wave 3",
        "  N05 todo · Final · try 0 rp 0 · - · - · -",
    ]
)


def git(root: Path, *args: str, when: int | None = None) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    if when is not None:
        env |= {"GIT_AUTHOR_DATE": f"@{when} +0000", "GIT_COMMITTER_DATE": f"@{when} +0000"}
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
    )


def commit(root: Path, plan: Path, subject: str, when: int, version: int) -> None:
    """Commit a change under the plan path (L: intent.md; S/M: trailing blank lines)."""
    if plan.is_dir():
        (plan / "intent.md").write_text(f"# Intent {version}\n")
    else:
        plan.write_text(plan.read_text().rstrip("\n") + "\n" + "\n" * version)
    git(root, "add", "-A")
    git(root, "commit", "-m", subject, when=when)


def tree(root: Path) -> dict[str, bytes | None]:
    """Every path below `root` (not `.git`) with its bytes; directories map to None."""
    found: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[0] == ".git":
            continue
        found[rel.as_posix()] = path.read_bytes() if path.is_file() else None
    return found


@pytest.fixture(params=["L", "S"])
def repo(request, tmp_path, monkeypatch):
    """A git repo holding the demo plan with the three commits of the report tests."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status, "now", lambda: NOW)
    plan = write_plan(tmp_path, request.param)
    git(tmp_path, "init", "-q")
    commit(tmp_path, plan, "add the plan", 500, 0)
    commit(tmp_path, plan, "demo N01: Scaffold", 1000, 1)
    commit(tmp_path, plan, "demo N02: Parser", 3000, 2)
    return tmp_path


def test_status_prints_the_golden_text(repo, capsys):
    assert cli.main(["status", "demo"]) == 0
    out = capsys.readouterr()
    assert (out.out, out.err) == (STATUS_TEXT + "\n", "")


def test_status_takes_a_path_as_well(repo, capsys):
    plan = next((repo / ".plan").glob("2026-10-01-demo*"))
    assert cli.main(["status", str(plan)]) == 0
    assert capsys.readouterr().out == STATUS_TEXT + "\n"


def test_status_never_writes_a_file(repo, capsys):
    before = tree(repo)
    assert cli.main(["status", "demo"]) == 0
    capsys.readouterr()
    assert tree(repo) == before


def test_without_git_the_text_has_unknown_elapsed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_plan(tmp_path, "S")
    assert cli.main(["status", "demo"]) == 0
    assert capsys.readouterr().out == NO_GIT_TEXT + "\n"


def test_unknown_plan_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["status", "nope"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_parse_error_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    plan = write_plan(tmp_path, "S")
    plan.write_text(plan.read_text().replace("| DONE |", "| FINISHED |", 1))
    assert cli.main(["status", "demo"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ") and "FINISHED" in out.err


def test_cycle_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    plan = write_plan(tmp_path, "S")
    plan.write_text(
        plan.read_text().replace("| N01 | Scaffold | exec | - |", "| N01 | Scaffold | exec | N02 |")
    )
    assert cli.main(["status", "demo"]) == 2
    assert "cycle" in capsys.readouterr().err
