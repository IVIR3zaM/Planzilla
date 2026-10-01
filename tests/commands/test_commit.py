"""`planzilla commit` (FORMAT §10): staging, message, push and retention in tmp git repos."""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import commit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "commit"
FORMATS = ["l", "sm"]
SLUG = "demo"
L_PLAN = ".plan/2026-10-01-demo"
SM_PLAN = ".plan/2026-10-01-demo.md"


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch):
    """Keep user and system git config out of the tmp repos."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=os.environ
    )
    return result.stdout


def make_repo(tmp_path: Path, fmt: str) -> Path:
    """A tmp git repo holding the fixture of that format, committed as the base."""
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / fmt, repo)
    git(repo, "init", "-q")
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def plan_path(fmt: str) -> str:
    return L_PLAN if fmt == "l" else SM_PLAN


def plan_marker(fmt: str) -> str:
    """A path of the plan that is in the tree whenever the plan is."""
    return L_PLAN + "/plan.md" if fmt == "l" else SM_PLAN


def graph_file(repo: Path, fmt: str) -> Path:
    return repo / (L_PLAN + "/plan.md" if fmt == "l" else SM_PLAN)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def work_on_n01(repo: Path, fmt: str) -> None:
    """Dirty everything N01 owns (Write paths, plan state, log, evidence) in every way."""
    append(repo / "src/one.txt", "more\n")
    append(repo / "docs/a.md", "more\n")
    append(repo / "data/y/z.txt", "more\n")
    (repo / "data/x.txt").unlink()
    (repo / "data/y/new.txt").write_text("new\n", encoding="utf-8")
    if fmt == "l":
        append(repo / L_PLAN / "plan.md", "\nprose\n")
        append(repo / L_PLAN / "log/N01.md", "note: more\n")
        append(repo / L_PLAN / "runs/N01/check-try1.txt", "more\n")
    else:
        append(repo / SM_PLAN, "note: more\n")


def dirty_elsewhere(repo: Path, fmt: str) -> list[str]:
    """Dirty files N01 does not own; return their expected porcelain lines."""
    append(repo / "src/two.txt", "more\n")
    append(repo / "docs/sub/b.md", "more\n")
    append(repo / "other.txt", "more\n")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    lines = [
        " M src/two.txt",
        " M docs/sub/b.md",
        " M other.txt",
        "?? untracked.txt",
    ]
    if fmt == "l":
        append(repo / L_PLAN / "log/N02.md", "note: more\n")
        append(repo / L_PLAN / "runs/N02/check-try1.txt", "more\n")
        lines += [f" M {L_PLAN}/log/N02.md", f" M {L_PLAN}/runs/N02/check-try1.txt"]
    return lines


def finish_plan(repo: Path, fmt: str) -> None:
    """N02 is the last node: DONE, plan DONE, and its work and records are dirty."""
    path = graph_file(repo, fmt)
    edit(path, "| 0 | 0 | TODO | |", "| 1 | 0 | DONE | |")
    edit(path, "status: RUNNING", "status: DONE")
    append(repo / "src/two.txt", "more\n")
    if fmt == "l":
        append(repo / L_PLAN / "log/N02.md", "note: more\n")
    else:
        append(path, "note: more\n")


def configure(repo: Path, text: str) -> None:
    (repo / ".plan" / "config.md").write_text(text, encoding="utf-8")


def run_commit(monkeypatch, repo: Path, capsys, plan: str = SLUG, node: str = "N01"):
    monkeypatch.chdir(repo)
    code = cli.main(["commit", plan, node])
    out = capsys.readouterr()
    return code, out.out, out.err


def committed_files(repo: Path, rev: str = "HEAD") -> list[str]:
    return sorted(git(repo, "show", "--name-only", "--format=", rev).split())


def tree(repo: Path, rev: str = "HEAD") -> list[str]:
    return git(repo, "ls-tree", "-r", "--name-only", rev).split()


def porcelain(repo: Path) -> list[str]:
    return git(repo, "status", "--porcelain", "-uall").splitlines()


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").strip()


def add_remote(tmp_path: Path, repo: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=os.environ)
    git(repo, "remote", "add", "origin", str(remote))
    return remote


# --- pure helpers -----------------------------------------------------------


def test_commit_message_subject_and_trailer():
    assert commit.commit_message("demo", "N01", "parse input", "") == "demo N01: parse input\n"
    assert (
        commit.commit_message("demo", "N01", "parse input", "A: 1\nB: 2")
        == "demo N01: parse input\n\nA: 1\nB: 2\n"
    )


def test_write_specs_are_glob_pathspecs_and_trailing_slash_means_recursive():
    assert commit.write_specs(["src/a.py", "docs/*.md", "data/"]) == [
        ":(glob)src/a.py",
        ":(glob)docs/*.md",
        ":(glob)data/**",
    ]
    assert commit.write_specs([]) == []


def test_plan_files_l_keeps_plan_files_this_log_and_this_runs():
    files = [
        ".plan/p/plan.md",
        ".plan/p/nodes/N01.md",
        ".plan/p/log/N01.md",
        ".plan/p/log/N02.md",
        ".plan/p/runs/N01/check-try1.txt",
        ".plan/p/runs/N02/check-try1.txt",
        ".plan/p/runs/N011/x.txt",
    ]
    assert commit.plan_files(files, ".plan/p", "N01", is_dir=True) == [
        ".plan/p/plan.md",
        ".plan/p/nodes/N01.md",
        ".plan/p/log/N01.md",
        ".plan/p/runs/N01/check-try1.txt",
    ]


def test_plan_files_single_file_is_the_file():
    assert commit.plan_files([".plan/p.md"], ".plan/p.md", "N01", is_dir=False) == [".plan/p.md"]


def test_strip_log_section_removes_log_to_the_end():
    text = "# T\n\n## Graph\n\nrow\n\n## N01 a\nDo: x\n\n## Log\n\n### N01 try 1\nexec: DONE\n"
    assert commit.strip_log_section(text) == "# T\n\n## Graph\n\nrow\n\n## N01 a\nDo: x\n"
    assert commit.strip_log_section("# T\n\n## Graph\n") == "# T\n\n## Graph\n"


# --- staging and message ----------------------------------------------------


def test_l_commit_has_exactly_write_paths_plan_log_and_runs(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "l")
    base = head(repo)
    work_on_n01(repo, "l")
    expected_dirty = dirty_elsewhere(repo, "l")

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, err) == (0, "")
    assert out == f"N01 committed {head(repo)[:7]}\n"
    assert git(repo, "rev-parse", "HEAD~1").strip() == base
    assert committed_files(repo) == sorted(
        [
            f"{L_PLAN}/plan.md",
            f"{L_PLAN}/log/N01.md",
            f"{L_PLAN}/runs/N01/check-try1.txt",
            "src/one.txt",
            "docs/a.md",
            "data/x.txt",
            "data/y/z.txt",
            "data/y/new.txt",
        ]
    )
    assert git(repo, "log", "-1", "--format=%B").strip() == "demo N01: parse input"
    # C3: everything else stays dirty, unstaged and uncommitted
    assert sorted(porcelain(repo)) == sorted(expected_dirty)


def test_sm_commit_has_exactly_write_paths_and_the_plan_file(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    base = head(repo)
    work_on_n01(repo, "sm")
    expected_dirty = dirty_elsewhere(repo, "sm")

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, err) == (0, "")
    assert out == f"N01 committed {head(repo)[:7]}\n"
    assert git(repo, "rev-parse", "HEAD~1").strip() == base
    assert committed_files(repo) == sorted(
        [
            SM_PLAN,
            "src/one.txt",
            "docs/a.md",
            "data/x.txt",
            "data/y/z.txt",
            "data/y/new.txt",
        ]
    )
    assert git(repo, "log", "-1", "--format=%B").strip() == "demo N01: parse input"
    assert sorted(porcelain(repo)) == sorted(expected_dirty)


def test_l_commit_stages_the_whole_plan_directory_except_other_logs_and_runs(
    tmp_path, monkeypatch, capsys
):
    repo = make_repo(tmp_path, "l")
    append(repo / L_PLAN / "intent.md", "more\n")
    append(repo / L_PLAN / "nodes/N02.md", "more\n")
    (repo / L_PLAN / "nodes/N03.md").write_text("# N03 x\n", encoding="utf-8")
    append(repo / L_PLAN / "log/N02.md", "more\n")
    append(repo / L_PLAN / "runs/N02/check-try1.txt", "more\n")

    code, _, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0
    assert committed_files(repo) == [
        f"{L_PLAN}/intent.md",
        f"{L_PLAN}/nodes/N02.md",
        f"{L_PLAN}/nodes/N03.md",
    ]
    assert sorted(porcelain(repo)) == [
        f" M {L_PLAN}/log/N02.md",
        f" M {L_PLAN}/runs/N02/check-try1.txt",
    ]


def test_write_paths_that_match_nothing_are_skipped(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "l")
    append(repo / L_PLAN / "log/N01.md", "more\n")
    # src/one.txt, docs/*.md and data/ are all clean: nothing matches, only the log is staged

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, err) == (0, "")
    assert committed_files(repo) == [f"{L_PLAN}/log/N01.md"]


@pytest.mark.parametrize("fmt", FORMATS)
def test_trailer_follows_a_blank_line(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    work_on_n01(repo, fmt)
    configure(repo, "commit_trailer: Co-Authored-By: Bot <b@example.com>\\nSigned-off-by: Demo\n")

    code, _, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0
    assert git(repo, "log", "-1", "--format=%B").strip() == (
        "demo N01: parse input\n\nCo-Authored-By: Bot <b@example.com>\nSigned-off-by: Demo"
    )


@pytest.mark.parametrize("fmt", FORMATS)
def test_plan_by_path_and_by_fragment(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    work_on_n01(repo, fmt)
    code, _, _ = run_commit(monkeypatch, repo, capsys, plan=plan_path(fmt))
    assert code == 0
    assert git(repo, "rev-list", "--count", "HEAD").strip() == "2"


def test_ambiguous_and_unknown_plan_exit_2(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    shutil.copy(repo / SM_PLAN, repo / ".plan/2026-10-02-demo-other.md")
    before = head(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys, plan="demo")
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "demo" in err
    code, out, err = run_commit(monkeypatch, repo, capsys, plan="nothing")
    assert (code, out) == (2, "")
    assert err.startswith("error: ")
    assert head(repo) == before


@pytest.mark.parametrize("fmt", FORMATS)
def test_unknown_node_exits_2(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    code, out, err = run_commit(monkeypatch, repo, capsys, node="N99")
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "N99" in err


# --- not DONE and commit none (C4) -------------------------------------------


@pytest.mark.parametrize("fmt", FORMATS)
def test_node_not_done_exits_2_and_stages_nothing(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    append(repo / "src/two.txt", "more\n")
    before = head(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys, node="N02")

    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "N02" in err and "TODO" in err
    assert head(repo) == before
    assert git(repo, "diff", "--cached", "--name-only") == ""
    assert porcelain(repo) == [" M src/two.txt"]


@pytest.mark.parametrize("fmt", FORMATS)
def test_commit_none_skips_with_the_line(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    work_on_n01(repo, fmt)
    edit(graph_file(repo, fmt), "commit: per-node", "commit: none")
    before = head(repo)
    dirty = porcelain(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, out, err) == (0, "N01 commit skipped: commit none\n", "")
    assert head(repo) == before
    assert porcelain(repo) == dirty
    assert git(repo, "diff", "--cached", "--name-only") == ""


# --- push (C5) ----------------------------------------------------------------


@pytest.mark.parametrize("value", ["yes", "per-node"])
@pytest.mark.parametrize("fmt", FORMATS)
def test_push_per_node_pushes_to_the_bare_remote(tmp_path, monkeypatch, capsys, fmt, value):
    repo = make_repo(tmp_path, fmt)
    remote = add_remote(tmp_path, repo)
    work_on_n01(repo, fmt)
    edit(graph_file(repo, fmt), "commit: per-node", f"commit: per-node\npush: {value}")

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, err) == (0, "")
    assert out == f"N01 committed {head(repo)[:7]} · pushed\n"
    assert git(remote, "rev-parse", "refs/heads/main").strip() == head(repo)
    assert git(repo, "rev-parse", "@{u}").strip() == head(repo)


def test_push_from_config_when_the_header_lacks_it(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    remote = add_remote(tmp_path, repo)
    work_on_n01(repo, "sm")
    configure(repo, "push: yes\n")

    code, out, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0 and out.endswith(" · pushed\n")
    assert git(remote, "rev-parse", "refs/heads/main").strip() == head(repo)


def test_header_push_none_wins_over_config(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    remote = add_remote(tmp_path, repo)
    work_on_n01(repo, "sm")
    edit(graph_file(repo, "sm"), "commit: per-node", "commit: per-node\npush: none")
    configure(repo, "push: yes\n")

    code, out, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0 and "push" not in out
    assert git(remote, "branch", "--list").strip() == ""


@pytest.mark.parametrize("fmt", FORMATS)
def test_push_failure_keeps_the_commit_and_exits_3(tmp_path, monkeypatch, capsys, fmt):
    repo = make_repo(tmp_path, fmt)
    git(repo, "remote", "add", "origin", str(tmp_path / "missing.git"))
    work_on_n01(repo, fmt)
    edit(graph_file(repo, fmt), "commit: per-node", "commit: per-node\npush: yes")
    base = head(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert code == 3 and err == ""
    assert head(repo) != base
    assert git(repo, "rev-parse", "HEAD~1").strip() == base
    prefix = f"N01 committed {head(repo)[:7]} · push failed: "
    assert out.startswith(prefix) and out.count("\n") == 1 and out.strip() != prefix.strip()


# --- retention (C6) ------------------------------------------------------------


def finishing(tmp_path, monkeypatch, capsys, fmt, retention=None, remote=False):
    repo = make_repo(tmp_path, fmt)
    base = head(repo)
    bare = add_remote(tmp_path, repo) if remote else None
    if remote:
        edit(graph_file(repo, fmt), "commit: per-node", "commit: per-node\npush: yes")
    finish_plan(repo, fmt)
    if retention is not None:
        configure(repo, f"retention: {retention}\n")
    code, out, err = run_commit(monkeypatch, repo, capsys, node="N02")
    return repo, base, bare, code, out, err


@pytest.mark.parametrize("fmt", FORMATS)
def test_retention_is_keep_by_default(tmp_path, monkeypatch, capsys, fmt):
    repo, base, _, code, out, err = finishing(tmp_path, monkeypatch, capsys, fmt)

    assert (code, err) == (0, "")
    assert out == f"N02 committed {head(repo)[:7]} · plan DONE · retention keep\n"
    assert git(repo, "rev-parse", "HEAD~1").strip() == base
    assert tree(repo) == tree(repo, base)
    if fmt == "l":
        assert f"{L_PLAN}/log/N02.md" in tree(repo)
        assert f"{L_PLAN}/runs/N01/check-try1.txt" in tree(repo)
    else:
        assert "## Log" in git(repo, "show", f"HEAD:{SM_PLAN}")


@pytest.mark.parametrize("fmt", FORMATS)
def test_retention_keep_explicit_removes_nothing(tmp_path, monkeypatch, capsys, fmt):
    repo, base, _, code, out, _ = finishing(tmp_path, monkeypatch, capsys, fmt, "keep")

    assert code == 0 and out.endswith(" · plan DONE · retention keep\n")
    assert tree(repo) == tree(repo, base)


def test_retention_prune_logs_l_removes_log_and_runs(tmp_path, monkeypatch, capsys):
    repo, base, _, code, out, _ = finishing(tmp_path, monkeypatch, capsys, "l", "prune-logs")

    assert code == 0
    assert out == f"N02 committed {head(repo)[:7]} · plan DONE · retention prune-logs\n"
    assert git(repo, "rev-list", "--count", f"{base}..HEAD").strip() == "1"
    assert sorted(tree(repo)) == sorted(
        path for path in tree(repo, base) if "/log/" not in path and "/runs/" not in path
    )
    assert f"{L_PLAN}/plan.md" in tree(repo) and f"{L_PLAN}/nodes/N02.md" in tree(repo)
    assert "src/two.txt" in committed_files(repo)
    assert not (repo / L_PLAN / "log").exists() and not (repo / L_PLAN / "runs").exists()


def test_retention_prune_logs_sm_removes_the_log_section(tmp_path, monkeypatch, capsys):
    repo, base, _, code, out, _ = finishing(tmp_path, monkeypatch, capsys, "sm", "prune-logs")

    assert code == 0 and out.endswith(" · plan DONE · retention prune-logs\n")
    assert git(repo, "rev-list", "--count", f"{base}..HEAD").strip() == "1"
    text = git(repo, "show", f"HEAD:{SM_PLAN}")
    assert "## Log" not in text and "### N0" not in text
    assert "## N02 render output" in text and "status: DONE" in text
    assert text.endswith("- C1 [cmd] `true`\n")
    assert (repo / SM_PLAN).read_text(encoding="utf-8") == text
    assert porcelain(repo) == ["?? .plan/config.md"]


@pytest.mark.parametrize("fmt", FORMATS)
def test_retention_delete_removes_the_whole_plan(tmp_path, monkeypatch, capsys, fmt):
    repo, base, _, code, out, _ = finishing(tmp_path, monkeypatch, capsys, fmt, "delete")

    assert code == 0
    assert out == f"N02 committed {head(repo)[:7]} · plan DONE · retention delete\n"
    assert git(repo, "rev-list", "--count", f"{base}..HEAD").strip() == "1"
    assert [path for path in tree(repo) if path.startswith(".plan/2026-10-01-demo")] == []
    assert "src/two.txt" in committed_files(repo)
    assert not (repo / plan_path(fmt)).exists()
    assert (repo / "src/two.txt").read_text(encoding="utf-8") == "two\nmore\n"
    # no other commit anywhere: history keeps the plan
    assert plan_path(fmt) in git(repo, "show", "--name-only", "--format=", base)


@pytest.mark.parametrize("fmt", FORMATS)
def test_retention_branch_only_keeps_records_on_a_side_branch(tmp_path, monkeypatch, capsys, fmt):
    repo, base, _, code, out, _ = finishing(tmp_path, monkeypatch, capsys, fmt, "branch-only")

    assert code == 0
    assert out == f"N02 committed {head(repo)[:7]} · plan DONE · retention branch-only\n"
    # the current branch gets exactly one commit, with the plan removed
    assert git(repo, "rev-list", "--count", f"{base}..HEAD").strip() == "1"
    assert [path for path in tree(repo) if path.startswith(".plan/2026-10-01-demo")] == []
    assert not (repo / plan_path(fmt)).exists()
    # the side branch holds the node commit with the records kept, parent = the old HEAD
    side = f"plan/{SLUG}"
    assert git(repo, "rev-parse", f"{side}~1").strip() == base
    assert tree(repo, side) == tree(repo, base)
    assert git(repo, "log", "-1", "--format=%B", side) == git(repo, "log", "-1", "--format=%B")
    assert git(repo, "log", "-1", "--format=%B").strip() == "demo N02: render output"
    assert "src/two.txt" in committed_files(repo, side)
    assert plan_marker(fmt) in tree(repo, side)
    if fmt == "l":
        assert f"{L_PLAN}/log/N02.md" in tree(repo, side)
    else:
        assert "note: more" in git(repo, "show", f"{side}:{SM_PLAN}")
    assert git(repo, "branch", "--show-current").strip() == "main"


def test_retention_branch_only_pushes_both_branches(tmp_path, monkeypatch, capsys):
    repo, _, remote, code, out, _ = finishing(
        tmp_path, monkeypatch, capsys, "l", "branch-only", remote=True
    )

    assert code == 0
    assert out == (f"N02 committed {head(repo)[:7]} · plan DONE · retention branch-only · pushed\n")
    assert git(remote, "rev-parse", "refs/heads/main").strip() == head(repo)
    assert (
        git(remote, "rev-parse", f"refs/heads/plan/{SLUG}").strip()
        == git(repo, "rev-parse", f"plan/{SLUG}").strip()
    )


def test_finishing_commit_pushes_after_retention(tmp_path, monkeypatch, capsys):
    repo, _, remote, code, out, _ = finishing(
        tmp_path, monkeypatch, capsys, "sm", "delete", remote=True
    )

    assert code == 0
    assert out == f"N02 committed {head(repo)[:7]} · plan DONE · retention delete · pushed\n"
    assert git(remote, "rev-parse", "refs/heads/main").strip() == head(repo)


@pytest.mark.parametrize("retention", ["prune-logs", "delete", "branch-only"])
@pytest.mark.parametrize("fmt", FORMATS)
def test_retention_waits_for_the_plan_to_be_done(tmp_path, monkeypatch, capsys, fmt, retention):
    repo = make_repo(tmp_path, fmt)
    work_on_n01(repo, fmt)
    configure(repo, f"retention: {retention}\n")

    code, out, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0
    assert out == f"N01 committed {head(repo)[:7]}\n"
    assert plan_marker(fmt) in tree(repo)
    assert git(repo, "branch", "--list", f"plan/{SLUG}").strip() == ""
    if fmt == "l":
        assert f"{L_PLAN}/log/N02.md" in tree(repo)
    else:
        assert "## Log" in git(repo, "show", f"HEAD:{SM_PLAN}")


# --- git failure and locking ------------------------------------------------------


def test_nothing_to_commit_exits_3(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    before = head(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, out) == (3, "")
    assert err.startswith("error: ")
    assert head(repo) == before


def test_not_a_git_repo_exits_3(tmp_path, monkeypatch, capsys):
    shutil.copytree(FIXTURES / "sm", tmp_path / "plain")

    code, out, err = run_commit(monkeypatch, tmp_path / "plain", capsys)

    assert (code, out) == (3, "")
    assert err.startswith("error: ")


def test_lock_is_released_after_the_commit(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "l")
    work_on_n01(repo, "l")

    assert run_commit(monkeypatch, repo, capsys)[0] == 0

    assert not (repo / ".plan/2026-10-01-demo.lock").exists()


def test_a_held_lock_times_out_with_exit_3(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    work_on_n01(repo, "sm")
    (repo / ".plan/2026-10-01-demo.md.lock").mkdir()
    monkeypatch.setattr(commit, "LOCK_TIMEOUT", 0.2)
    before = head(repo)

    code, out, err = run_commit(monkeypatch, repo, capsys)

    assert (code, out) == (3, "")
    assert err.startswith("error: ") and "lock" in err
    assert head(repo) == before
    assert (repo / ".plan/2026-10-01-demo.md.lock").exists()


def test_a_stale_lock_is_removed(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "sm")
    work_on_n01(repo, "sm")
    lock = repo / ".plan/2026-10-01-demo.md.lock"
    lock.mkdir()
    old = time.time() - 120
    os.utime(lock, (old, old))

    code, _, _ = run_commit(monkeypatch, repo, capsys)

    assert code == 0
    assert not lock.exists()
