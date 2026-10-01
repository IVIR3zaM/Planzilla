import shutil
from pathlib import Path

import pytest

from planzilla.plan import Node, append_entry, attempt_key, load_plan, render_graph, render_plan

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "plans" / "repo"


def _node(status: str, tries: int, rp: int) -> Node:
    return Node("N01", "t", "exec", [], "sonnet", "-", tries, rp, status, "")


@pytest.mark.parametrize(
    ("status", "tries", "rp", "key"),
    [
        ("BRIEFING", 0, 0, "brief"),
        ("REPLAN", 3, 1, "replan 1"),
        ("TODO", 0, 0, "try 1"),
        ("RETRY", 1, 0, "try 2"),
        ("RUNNING", 1, 0, "try 1"),
        ("VERIFYING", 2, 0, "try 2"),
        ("DONE", 2, 0, "try 2"),
    ],
)
def test_attempt_key(status: str, tries: int, rp: int, key: str) -> None:
    assert attempt_key(_node(status, tries, rp)) == key


@pytest.mark.parametrize("name", ["2026-01-02-demo-s.md", "2026-01-03-demo-l"])
def test_render_plan_replaces_only_status_and_updated(tmp_path: Path, name: str) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, repo)
    plan = load_plan(repo / ".plan" / name)
    out = render_plan(plan, "BLOCKED", "2026-10-01")
    old, new = plan.text.split("\n"), out.split("\n")
    assert len(old) == len(new)
    diff = [i + 1 for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    assert diff == [plan.header.lines["status"], plan.header.lines["created"]]
    assert new[1] == "status: BLOCKED"
    assert new[2] == f"created: {plan.header.created} · updated: 2026-10-01"


def test_render_plan_includes_graph_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, repo)
    plan = load_plan(repo / ".plan" / "2026-01-03-demo-l")
    plan.node("N04").status = "RUNNING"
    out = render_plan(plan, plan.header.status, plan.header.updated)
    assert out == render_graph(plan)


def test_append_entry_new_heading_when_key_differs() -> None:
    log = "# N01 log\n\n## try 1 · 2026-01-03\nexec: DONE · ok\n"
    out = append_entry(log, "## try 2 · 2026-10-01", "check", "FAIL C2", ["C2 exit 1: x"])
    assert out == log + "\n## try 2 · 2026-10-01\ncheck: FAIL C2\n- C2 exit 1: x\n"


def test_append_entry_same_key_ignores_date_and_time() -> None:
    log = "# N01 log\n\n## try 1 · 2026-01-03 14:03\nexec: DONE · ok\n"
    out = append_entry(log, "## try 1 · 2026-10-01", "note", "more", [])
    assert out == log + "note: more\n"


def test_append_entry_sm_heading_includes_id() -> None:
    log = "## Log\n\n### N01 try 1 · 2026-01-02\nexec: DONE · ok\n"
    same = append_entry(log, "### N01 try 1 · 2026-10-01", "note", "a", [])
    assert same == log + "note: a\n"
    other = append_entry(log, "### N02 try 1 · 2026-10-01", "note", "a", [])
    assert other == log + "\n### N02 try 1 · 2026-10-01\nnote: a\n"


def test_append_entry_adds_missing_final_newline() -> None:
    out = append_entry(
        "# N01 log\n\n## brief · 2026-01-03", "## brief · 2026-01-04", "note", "x", []
    )
    assert out == "# N01 log\n\n## brief · 2026-01-03\nnote: x\n"


def test_append_entry_empty_log_gets_heading() -> None:
    out = append_entry("# N01 log\n", "## try 1 · 2026-10-01", "note", "x", ["b"])
    assert out == "# N01 log\n\n## try 1 · 2026-10-01\nnote: x\n- b\n"
