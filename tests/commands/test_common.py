import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from planzilla.cli import COMMANDS
from planzilla.commands import _common
from planzilla.commands._common import (
    GitError,
    LockTimeout,
    ResolveError,
    append_log,
    fail,
    plan_lock,
    resolve_plan,
    uncommitted,
    write_atomic,
    write_plan,
)
from planzilla.plan import load_plan

FIXTURE_REPO = Path(__file__).parent.parent / "fixtures" / "plans" / "repo"
S_NAME = "2026-01-02-demo-s.md"
L_NAME = "2026-01-03-demo-l"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, target)
    return target


# --- append_log --------------------------------------------------------------


def test_append_log_same_key_l_adds_one_heading_two_entries(repo: Path) -> None:
    plan = load_plan(repo / ".plan" / L_NAME)
    plan.node("N01").tries = 2  # key "try 2" differs from the last heading "try 1"
    log = repo / ".plan" / L_NAME / "log" / "N01.md"
    before = log.read_bytes()
    append_log(plan, "N01", "exec", "DONE · 1 passed", ["one"], "2026-10-01")
    append_log(plan, "N01", "note", "again", [], "2026-10-02")
    after = log.read_bytes()
    assert after.startswith(before)
    assert after[len(before) :].decode() == (
        "\n## try 2 · 2026-10-01\nexec: DONE · 1 passed\n- one\nnote: again\n"
    )


def test_append_log_l_creates_file(repo: Path) -> None:
    plan = load_plan(repo / ".plan" / L_NAME)
    append_log(plan, "N04", "plan", "BRIEFED", [], "2026-10-01")
    log = repo / ".plan" / L_NAME / "log" / "N04.md"
    assert log.read_text() == "# N04 log\n\n## try 1 · 2026-10-01\nplan: BRIEFED\n"


def test_append_log_l_key_change_adds_heading(repo: Path) -> None:
    plan = load_plan(repo / ".plan" / L_NAME)
    log = repo / ".plan" / L_NAME / "log" / "N01.md"
    append_log(plan, "N01", "note", "same try", [], "2026-10-05")
    assert log.read_text().count("## ") == 1  # date ignored: still the one try 1 heading
    plan.node("N01").status = "REPLAN"
    append_log(plan, "N01", "plan", "REPLANNED", ["cause"], "2026-10-06")
    assert log.read_text().endswith("\n## replan 0 · 2026-10-06\nplan: REPLANNED\n- cause\n")


def test_append_log_sm_appends_under_log_section(repo: Path) -> None:
    path = repo / ".plan" / S_NAME
    plan = load_plan(path)
    before = path.read_bytes()
    append_log(plan, "N01", "note", "hello", ["b1", "b2"], "2026-10-01")
    after = path.read_bytes()
    assert after.startswith(before)
    # N01 is DONE at try 1: same key as the last heading "### N01 try 1" -> no new heading
    assert after[len(before) :].decode() == "note: hello\n- b1\n- b2\n"
    append_log(plan, "N03", "note", "other node", [], "2026-10-01")
    assert path.read_text().endswith(
        "note: hello\n- b1\n- b2\n\n### N03 try 1 · 2026-10-01\nnote: other node\n"
    )


def test_append_log_sm_creates_log_section(tmp_path: Path) -> None:
    src = (FIXTURE_REPO / ".plan" / S_NAME).read_text()
    head = src[: src.index("## Log")]
    path = tmp_path / ".plan" / S_NAME
    path.parent.mkdir()
    path.write_text(head.rstrip("\n") + "\n")
    plan = load_plan(path)
    append_log(plan, "N02", "note", "first", [], "2026-10-01")
    text = path.read_text()
    assert text.startswith(head.rstrip("\n") + "\n")
    assert text.endswith("\n\n## Log\n\n### N02 try 3 · 2026-10-01\nnote: first\n")
    assert load_plan(path).header == plan.header  # header untouched


# --- write_plan / write_atomic -----------------------------------------------


@pytest.mark.parametrize("name", [S_NAME, L_NAME])
def test_write_plan_changes_only_row_and_header(repo: Path, name: str) -> None:
    path = repo / ".plan" / name
    plan = load_plan(path)
    graph_file = plan.graph_file
    before = graph_file.read_text().split("\n")
    plan.node("N04").status = "BRIEFING"
    written = write_plan(plan, "WAITING", "2026-10-01")
    after = graph_file.read_text().split("\n")
    assert len(before) == len(after)
    changed = [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    assert len(changed) == 3
    assert after[plan.header.lines["status"] - 1] == "status: WAITING"
    assert after[plan.header.lines["created"] - 1].endswith("updated: 2026-10-01")
    row = after[plan.node("N04").line - 1]
    assert "| BRIEFING |" in row
    assert written.header.status == "WAITING"
    assert written.node("N04").status == "BRIEFING"
    assert not list(graph_file.parent.glob("*.tmp"))


def test_write_atomic_replaces_and_leaves_no_temp(tmp_path: Path) -> None:
    path = tmp_path / "f.md"
    path.write_text("old")
    write_atomic(path, "new · ü\n")
    assert path.read_bytes() == "new · ü\n".encode()
    assert [p.name for p in tmp_path.iterdir()] == ["f.md"]


# --- resolve_plan ------------------------------------------------------------


def test_resolve_plan_paths(repo: Path) -> None:
    assert resolve_plan(str(repo / ".plan" / L_NAME), Path("/")) == repo / ".plan" / L_NAME
    assert resolve_plan(str(repo / ".plan" / S_NAME), Path("/")) == repo / ".plan" / S_NAME
    assert resolve_plan(f".plan/{L_NAME}", repo) == repo / ".plan" / L_NAME


def test_resolve_plan_slug_fragment(repo: Path) -> None:
    assert resolve_plan("demo-s", repo) == repo / ".plan" / S_NAME
    assert resolve_plan("demo-l", repo) == repo / ".plan" / L_NAME
    assert resolve_plan("planzilla", repo).name == "2026-10-01-planzilla-v1"


def test_resolve_plan_ambiguous_names_reference(repo: Path) -> None:
    with pytest.raises(ResolveError, match="'demo'"):
        resolve_plan("demo", repo)


def test_resolve_plan_unmatched_names_reference(repo: Path) -> None:
    with pytest.raises(ResolveError, match="'nothing-here'"):
        resolve_plan("nothing-here", repo)


def test_resolve_plan_config_never_matches(repo: Path) -> None:
    for ref in ("config", "config.md", ".plan/config.md", str(repo / ".plan" / "config.md")):
        with pytest.raises(ResolveError):
            resolve_plan(ref, repo)


def test_resolve_plan_without_plan_dir(tmp_path: Path) -> None:
    with pytest.raises(ResolveError, match="'x'"):
        resolve_plan("x", tmp_path)


# --- plan_lock ---------------------------------------------------------------


def test_lock_held_times_out(tmp_path: Path) -> None:
    plan = tmp_path / "2026-01-02-demo-s.md"
    with plan_lock(plan):
        assert (tmp_path / "2026-01-02-demo-s.md.lock").is_dir()
        with pytest.raises(LockTimeout), plan_lock(plan, timeout=0.2, poll=0.01):
            pass
        assert (tmp_path / "2026-01-02-demo-s.md.lock").is_dir()  # holder's lock survives
    assert not (tmp_path / "2026-01-02-demo-s.md.lock").exists()


def test_lock_stale_is_taken_over(tmp_path: Path) -> None:
    plan = tmp_path / "2026-01-03-demo-l"
    lock = tmp_path / "2026-01-03-demo-l.lock"
    lock.mkdir()
    old = time.time() - 120
    os.utime(lock, (old, old))
    with plan_lock(plan, timeout=0.2, stale=60.0, poll=0.01):
        assert lock.is_dir()
        assert lock.stat().st_mtime > old + 100
    assert not lock.exists()


def test_lock_removed_after_exception(tmp_path: Path) -> None:
    plan = tmp_path / "2026-01-02-demo-s.md"
    with pytest.raises(RuntimeError), plan_lock(plan):
        raise RuntimeError("boom")
    assert not (tmp_path / "2026-01-02-demo-s.md.lock").exists()


# --- uncommitted -------------------------------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "g"
    root.mkdir()
    (root / "a.txt").write_text("a\n")
    (root / "b.txt").write_text("b\n")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root


def test_uncommitted_clean(git_repo: Path) -> None:
    assert uncommitted(git_repo, ["a.txt", "b.txt"]) is False


def test_uncommitted_modified_tracked(git_repo: Path) -> None:
    (git_repo / "a.txt").write_text("changed\n")
    assert uncommitted(git_repo, ["a.txt"]) is True
    assert uncommitted(git_repo, ["b.txt"]) is False


def test_uncommitted_untracked(git_repo: Path) -> None:
    (git_repo / "new.txt").write_text("n\n")
    assert uncommitted(git_repo, ["new.txt"]) is True
    assert uncommitted(git_repo, ["a.txt"]) is False


def test_uncommitted_no_paths_is_false(git_repo: Path) -> None:
    (git_repo / "a.txt").write_text("changed\n")
    assert uncommitted(git_repo, []) is False


def test_uncommitted_git_failure_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        uncommitted(tmp_path / "missing", ["a.txt"])


# --- fail / registry ---------------------------------------------------------


def test_fail_prints_error_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert fail("boom", 3) == 3
    captured = capsys.readouterr()
    assert captured.err == "error: boom\n"
    assert captured.out == ""


def test_common_is_not_a_command() -> None:
    assert "_common" not in COMMANDS
    assert _common.__name__ == "planzilla.commands._common"
