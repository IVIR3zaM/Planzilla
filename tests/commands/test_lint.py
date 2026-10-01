"""`planzilla lint`: one test per D12 rule, each fixture breaks only its rule (FORMAT §9)."""

import shutil
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands.lint import items_overlap
from tests.commands.test_status import tree

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "lint"
SM = ".plan/2026-10-01-demo.md"
L = ".plan/2026-10-01-demo"


def lint(capsys, name: str, monkeypatch, tmp_path: Path, ref: str = SM) -> tuple[int, str, str]:
    """Lint a copy of fixture `name` from its repo root (the copy lives under `tmp_path`)."""
    root = tmp_path / name
    shutil.copytree(FIXTURES / name, root)
    monkeypatch.chdir(root)
    code = cli.main(["lint", ref])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture
def run(capsys, monkeypatch, tmp_path):
    def call(name: str, ref: str = SM):
        return lint(capsys, name, monkeypatch, tmp_path, ref)

    return call


def test_clean_single_file_plan_exits_0(run):
    assert run("clean") == (0, "lint ok: 3 nodes, 2 waves\n", "")


def test_clean_directory_plan_exits_0(run):
    assert run("l-clean", L) == (0, "lint ok: 2 nodes, 2 waves\n", "")


def test_rule_parse_reports_the_parse_error_line(run):
    assert run("parse") == (1, f"{SM}:16: parse: bad status 'FINISHED'\n", "")


def test_rule_parse_covers_a_broken_brief(run):
    assert run("brief-parse") == (1, f"{SM}:18: parse: brief N01 has no 'Do:' field\n", "")


def test_rule_tag_names_the_untagged_criterion(run):
    assert run("tag") == (1, f"{SM}:23: tag: criterion C2 has no tag\n", "")


def test_rule_tag_in_a_directory_plan_names_the_brief_file(run):
    code, out, err = run("l-tag", L)
    assert (code, err) == (1, "")
    assert out == f"{L}/nodes/N01.md:6: tag: criterion C2 has unknown tag [maybe]\n"


def test_rule_cmd_needs_a_backticked_command(run):
    code, out, _ = run("cmd")
    assert (code, out) == (
        1,
        f"{SM}:22: cmd: criterion C1 [cmd] must start with a backticked command\n",
    )


def test_rule_length_flags_a_brief_over_40_lines(run):
    assert run("length") == (1, f"{SM}:18: length: brief N01 has 41 lines (max 40)\n", "")


def test_rule_deps_flags_a_dep_that_is_not_a_node(run):
    assert run("deps") == (1, f"{SM}:17: deps: N02 depends on N09, which is not a node\n", "")


def test_rule_cycle_is_reported_on_the_first_row_of_the_cycle(run):
    code, out, _ = run("cycle")
    assert (code, out) == (1, f"{SM}:16: cycle: Graph has a cycle: N01 -> N02 -> N01\n")


def test_rule_overlap_names_both_items_on_the_second_nodes_write_line(run):
    code, out, _ = run("overlap")
    assert code == 1
    assert out == (
        f"{SM}:27: overlap: N02 Write `src/a.py` overlaps N01 Write `src/**` (same wave 1)\n"
    )


def test_a_missing_brief_is_not_a_problem(tmp_path, monkeypatch):
    root = tmp_path / "nobrief"
    shutil.copytree(FIXTURES / "l-clean", root)
    (root / L / "nodes" / "N02.md").unlink()
    monkeypatch.chdir(root)
    assert cli.main(["lint", L]) == 0


def test_overlap_is_only_checked_within_a_wave(tmp_path, monkeypatch, capsys):
    root = tmp_path / "waves"
    shutil.copytree(FIXTURES / "overlap", root)
    plan = root / SM
    plan.write_text(
        plan.read_text().replace("| N02 | Node 2 | exec | - |", "| N02 | Node 2 | exec | N01 |")
    )
    monkeypatch.chdir(root)
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 2 nodes, 2 waves\n"


def test_lint_never_writes_a_file(tmp_path, monkeypatch):
    for name, ref in (("clean", SM), ("overlap", SM), ("l-tag", L)):
        root = tmp_path / name
        shutil.copytree(FIXTURES / name, root)
        monkeypatch.chdir(root)
        before = tree(root)
        cli.main(["lint", ref])
        assert tree(root) == before


def test_unknown_plan_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["lint", "nope"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_missing_plan_file_exits_2(tmp_path, monkeypatch, capsys):
    (tmp_path / ".plan" / "2026-10-01-demo").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["lint", ".plan/2026-10-01-demo"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_a_plan_is_found_by_slug_fragment(run):
    assert run("clean", "demo")[0] == 0


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("src/planzilla/kit/**", "src/planzilla/kit/roles/x.md", True),
        (".claude/skills/plz-*/**", ".claude/agents/plz-a.md", False),
        ("src/a.py", "src/a.py", True),
        ("src/a.py", "src/b.py", False),
        ("src/", "src/a/b.py", True),
        ("**", "src/a.py", True),
        ("src/**/x.py", "src/a/b/x.py", True),
        ("src/**/x.py", "src/a/b/y.py", False),
        ("src/*.py", "src/a.py", True),
        ("src/*.py", "src/a.md", False),
        ("src/*.py", "src/a*", True),
        ("src/**", "src", True),
        ("src/a", "src/a/b", False),
        ("plz-*/x", "plz-a/*", True),
    ],
)
def test_items_overlap(a, b, expected):
    assert items_overlap(a, b) is expected
    assert items_overlap(b, a) is expected
