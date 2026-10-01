"""`planzilla stats`: the §12 totals line, read-only (FORMAT §9, §12)."""

import pytest

from planzilla import cli
from planzilla.commands import status
from tests.commands.test_status import commit, git, tree
from tests.test_report import NOW, STATS_LINE, write_plan


@pytest.fixture(params=["L", "S"])
def repo(request, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status, "now", lambda: NOW)
    plan = write_plan(tmp_path, request.param)
    git(tmp_path, "init", "-q")
    commit(tmp_path, plan, "add the plan", 500, 0)
    commit(tmp_path, plan, "demo N01: Scaffold", 1000, 1)
    commit(tmp_path, plan, "demo N02: Parser", 3000, 2)
    return tmp_path


def test_stats_prints_the_golden_line(repo, capsys):
    assert cli.main(["stats", "demo"]) == 0
    out = capsys.readouterr()
    assert (out.out, out.err) == (STATS_LINE + "\n", "")


def test_stats_never_writes_a_file(repo, capsys):
    before = tree(repo)
    assert cli.main(["stats", "demo"]) == 0
    capsys.readouterr()
    assert tree(repo) == before


def test_stats_without_git_has_zero_commits_and_unknown_wall(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_plan(tmp_path, "L")
    assert cli.main(["stats", "demo"]) == 0
    assert capsys.readouterr().out == (
        "nodes 5 · done 2 · tries 5 · replans 3 · blocked 1 · commits 0 · wall -\n"
    )


def test_stats_unknown_plan_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["stats", "nope"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")
