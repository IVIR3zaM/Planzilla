"""`planzilla.report`: the pure per-node view (FORMAT §12)."""

import ast
from pathlib import Path

import pytest

from planzilla import report
from planzilla.plan import load_plan

HEADER = (
    "# Demo plan\n"
    "status: RUNNING\n"
    "created: 2026-10-01 · updated: 2026-10-01\n"
    "goal: g\n"
    "verify: true\n"
    "commit: per-node\n"
)
GRAPH = (
    "\n## Graph\n\n"
    "| id | title | type | deps | model | try | rp | status | note |\n"
    "|----|-------|------|------|-------|-----|----|--------|------|\n"
)
ROWS = [
    "| N01 | Scaffold | exec | - | sonnet/- | 1 | 0 | DONE | |",
    "| N02 | Parser | exec | N01 | sonnet/opus | 2 | 1 | DONE | |",
    "| N03 | Reports | exec | N01 | sonnet/- | 1 | 0 | RUNNING | |",
    "| N04 | Docs | exec | N01 | sonnet/- | 1 | 2 | BLOCKED | blocked: no spec |",
    "| N05 | Final | check | N02,N03 | -/opus | 0 | 0 | TODO | |",
]
LOGS = {
    "N01": [("try 1", ["exec: DONE · 3 passed", "check: PASS 2/2"])],
    "N02": [
        ("try 1", ["exec: DONE · 1 passed", "check: FAIL C1", "- C1 exit 1: boom"]),
        ("try 2", ["exec: DONE · 2 passed", "", "verify: PASS", ""]),
    ],
    "N03": [("try 1", ["exec: DONE · 1 passed"])],
    "N04": [("try 1", ["exec: BLOCKED · no spec"])],
}
# git log, newest first: (time, subject). The plan's own commit is the oldest.
COMMITS = [(3000, "demo N02: Parser"), (1000, "demo N01: Scaffold"), (500, "add the plan")]
NOW = 10000

STATUS_TEXT = """\
Demo plan · RUNNING · 2/5 done · 2h38m
wave 1
  N01 done · Scaffold · try 1 rp 0 · 8m · - · check: PASS 2/2
wave 2
  N02 done · Parser · try 2 rp 1 · 33m · - · verify: PASS
  N03 executing · Reports · try 1 rp 0 · 2h30m · - · exec: DONE · 1 passed
  N04 blocked · Docs · try 1 rp 2 · 2h30m · blocked: no spec · exec: BLOCKED · no spec
wave 3
  N05 todo · Final · try 0 rp 0 · - · - · -"""
STATS_LINE = "nodes 5 · done 2 · tries 5 · replans 3 · blocked 1 · commits 2 · wall 2h38m"


def write_plan(root: Path, layout: str, rows: list[str] = ROWS, logs=LOGS) -> Path:
    """Write the demo plan as `.plan/2026-10-01-demo` (layout L) or `.md` (S); return its path."""
    plan_dir = root / ".plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    text = HEADER + GRAPH + "\n".join(rows) + "\n"
    if layout == "L":
        path = plan_dir / "2026-10-01-demo"
        (path / "log").mkdir(parents=True)
        (path / "plan.md").write_text(text)
        for node_id, entries in logs.items():
            body = [f"# {node_id} log", ""]
            for key, lines in entries:
                body += [f"## {key} · 2026-10-01", *lines]
            (path / "log" / f"{node_id}.md").write_text("\n".join(body) + "\n")
        return path
    path = plan_dir / "2026-10-01-demo.md"
    text += "\n## Log\n"
    for node_id, entries in logs.items():
        for key, lines in entries:
            text += "\n" + "\n".join([f"### {node_id} {key} · 2026-10-01", *lines]) + "\n"
    path.write_text(text)
    return path


def log_texts(plan) -> dict[str, str]:
    """What `status` passes in: the node's log file (L) or the whole plan file (S/M)."""
    if plan.is_dir:
        return {
            node.id: (plan.path / "log" / f"{node.id}.md").read_text()
            for node in plan.nodes
            if (plan.path / "log" / f"{node.id}.md").is_file()
        }
    return {node.id: plan.text for node in plan.nodes}


@pytest.fixture(params=["L", "S"])
def plan(request, tmp_path):
    return load_plan(write_plan(tmp_path, request.param))


def build(plan, commits=COMMITS, now=NOW):
    return report.build_report(plan, log_texts(plan), commits, now)


def test_rows_are_grouped_by_wave_with_live_view_names(plan):
    result = build(plan)
    assert [(wave, [v.id for v in views]) for wave, views in result.waves] == [
        (1, ["N01"]),
        (2, ["N02", "N03", "N04"]),
        (3, ["N05"]),
    ]
    views = {v.id: v for _, group in result.waves for v in group}
    assert {i: v.view for i, v in views.items()} == {
        "N01": "done",
        "N02": "done",
        "N03": "executing",
        "N04": "blocked",
        "N05": "todo",
    }
    assert (views["N02"].tries, views["N02"].rp, views["N04"].note) == (2, 1, "blocked: no spec")


def test_last_log_line_and_elapsed_per_node(plan):
    views = {v.id: v for _, group in build(plan).waves for v in group}
    assert {i: v.last for i, v in views.items()} == {
        "N01": "check: PASS 2/2",
        "N02": "verify: PASS",
        "N03": "exec: DONE · 1 passed",
        "N04": "exec: BLOCKED · no spec",
        "N05": "-",
    }
    assert {i: v.elapsed for i, v in views.items()} == {
        "N01": 500,
        "N02": 2000,
        "N03": 9000,
        "N04": 9000,
        "N05": None,
    }


def test_totals(plan):
    result = build(plan)
    assert (result.done, result.total, result.tries, result.replans) == (2, 5, 5, 3)
    assert (result.blocked, result.commits, result.elapsed) == (1, 2, 9500)
    assert (result.slug, result.tier) == ("demo", "L" if plan.is_dir else "M")


def test_status_and_stats_text_are_the_golden_strings(plan):
    result = build(plan)
    assert report.format_status(result) == STATUS_TEXT
    assert report.format_stats(result) == STATS_LINE


def test_without_commits_every_elapsed_is_unknown(plan):
    result = build(plan, commits=[])
    assert all(v.elapsed is None for _, group in result.waves for v in group)
    assert result.elapsed is None
    assert report.format_status(result).splitlines()[0] == "Demo plan · RUNNING · 2/5 done · -"
    assert report.format_stats(result).endswith("commits 0 · wall -")


def test_done_node_without_commit_is_unknown_and_start_comes_from_dep_commits(tmp_path):
    plan = load_plan(write_plan(tmp_path, "S"))
    result = build(plan, commits=[(900, "demo N01: Scaffold"), (100, "add the plan")])
    views = {v.id: v for _, group in result.waves for v in group}
    assert views["N02"].elapsed is None
    assert views["N03"].elapsed == NOW - 900


def test_node_commit_is_the_newest_with_the_slug_and_id_prefix(tmp_path):
    plan = load_plan(write_plan(tmp_path, "S"))
    commits = [
        (4000, "demo N01: Scaffold again"),
        (3500, "other N01: Scaffold"),
        (3200, "demo N011: Not it"),
        (1000, "demo N01: Scaffold"),
        (500, "add the plan"),
    ]
    views = {v.id: v for _, group in build(plan, commits).waves for v in group}
    assert views["N01"].elapsed == 3500
    assert views["N03"].elapsed == NOW - 4000


def test_finished_plan_ends_at_its_newest_node_commit(tmp_path):
    rows = [row.replace("RUNNING", "DONE").replace("BLOCKED", "DONE") for row in ROWS]
    rows[-1] = rows[-1].replace("TODO", "DONE")
    plan = load_plan(write_plan(tmp_path, "S", rows))
    result = build(plan)
    assert (result.done, result.elapsed) == (5, 3000 - 500)


def test_last_line_is_cut_to_80_characters_with_an_ellipsis():
    long = "note: " + "x" * 100
    cut = report.last_line(["a", long, "", "  "])
    assert len(cut) == 80 and cut.endswith("…") and cut.startswith("note: xxx")
    assert report.last_line(["exact " + "y" * 74]) == "exact " + "y" * 74
    assert report.last_line(["", " "]) == "-"


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (None, "-"),
        (0, "0s"),
        (59, "59s"),
        (60, "1m"),
        (3599, "59m"),
        (3600, "1h00m"),
        (5400, "1h30m"),
        (9500, "2h38m"),
        (90000, "25h00m"),
    ],
)
def test_format_elapsed(seconds, text):
    assert report.format_elapsed(seconds) == text


def test_parse_git_log_keeps_time_and_subject():
    text = "300 demo N02: Parser\n100 add the plan\nnot a time\n\n"
    assert report.parse_git_log(text) == [(300, "demo N02: Parser"), (100, "add the plan")]


def test_s_m_log_entries_of_other_nodes_do_not_count(tmp_path):
    plan = load_plan(write_plan(tmp_path, "S"))
    result = report.build_report(plan, {"N01": plan.text}, [], NOW)
    views = {v.id: v for _, group in result.waves for v in group}
    assert views["N01"].last == "check: PASS 2/2"
    assert views["N02"].last == "-"
    assert result.tries == 1


def test_report_module_imports_no_io():
    source = Path(report.__file__).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    io_modules = {"os", "sys", "subprocess", "shutil", "socket", "tempfile", "time", "io", "urllib"}
    assert not imported & io_modules
    assert not any(
        isinstance(n, ast.ImportFrom) and (n.module or "").startswith("planzilla.commands")
        for n in ast.walk(ast.parse(source))
    )
    assert "open(" not in source and "read_text" not in source and "write_" not in source
