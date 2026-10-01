"""`planzilla set`: transitions, redirects, structure options and output lines (FORMAT §5, §9)."""

import io
import sys
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import set as set_cmd

HEADER = (
    "# Demo\n"
    "status: {status}\n"
    "created: 2026-09-01 · updated: 2026-09-01\n"
    "goal: g\n"
    "verify: true\n"
    "commit: none\n"
    "{extra}"
)
GRAPH = (
    "\nProse is kept.\n\n## Graph\n\n"
    "| id | title | type | deps | model | try | rp | status | note |\n"
    "|----|-------|------|------|-------|-----|----|--------|------|\n"
    "{rows}\n"
)


def row(
    node_id: str,
    status: str = "TODO",
    t: int = 0,
    rp: int = 0,
    type: str = "exec",
    deps: str = "-",
    model: str = "sonnet/opus",
    note: str = "",
) -> str:
    cells = [node_id, f"t {node_id}", type, deps, model, str(t), str(rp), status, note]
    return "|" + "".join(f" {cell} |" if cell else " |" for cell in cells)


def brief(node_id: str, *tags: str, type: str = "exec", heading: str = "# ") -> str:
    lines = [f"{heading}{node_id} t {node_id}", "Do: x."]
    if type == "exec":
        lines.append("Write: `src/x.py`")
    lines.append("Done when:")
    for number, tag in enumerate(tags, 1):
        lines.append(f"- C{number} [{tag}] " + ("`true`" if tag == "cmd" else "thing"))
    return "\n".join(lines) + "\n"


def make_l(
    root: Path,
    rows: list[str],
    briefs: dict[str, str] | None = None,
    status: str = "RUNNING",
    extra: str = "",
) -> Path:
    plan = root / ".plan" / "2026-09-01-demo"
    (plan / "nodes").mkdir(parents=True)
    (plan / "plan.md").write_text(
        HEADER.format(status=status, extra=extra) + GRAPH.format(rows="\n".join(rows))
    )
    for node_id, text in (briefs or {}).items():
        (plan / "nodes" / f"{node_id}.md").write_text(text)
    return plan


def make_s(root: Path, rows: list[str], briefs: list[str]) -> Path:
    plan = root / ".plan" / "2026-09-01-demo.md"
    plan.parent.mkdir(parents=True)
    text = HEADER.format(status="RUNNING", extra="") + GRAPH.format(rows="\n".join(rows))
    plan.write_text(text + "".join("\n" + text for text in briefs))
    return plan


def graph_text(plan: Path) -> str:
    return (plan / "plan.md" if plan.is_dir() else plan).read_text()


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(set_cmd, "today", lambda: "2026-10-01")


def plz_set(capsys: pytest.CaptureFixture[str], plan: Path, *args: str) -> tuple[int, str, str]:
    code = cli.main(["set", str(plan), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_running_increments_try_writes_row_and_header(tmp_path, capsys):
    plan = make_l(
        tmp_path, [row("N01"), row("N02", deps="N01")], {"N01": brief("N01", "cmd", "review")}
    )
    code, out, err = plz_set(capsys, plan, "N01", "RUNNING")
    assert (code, out, err) == (0, "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet\n", "")
    text = graph_text(plan)
    assert "| N01 | t N01 | exec | - | sonnet/opus | 1 | 0 | RUNNING | |\n" in text
    assert "status: RUNNING\ncreated: 2026-09-01 · updated: 2026-10-01\n" in text
    assert "\nProse is kept.\n" in text


def test_illegal_transition_exits_2_and_keeps_bytes(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01")], {"N01": brief("N01", "cmd")})
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_set(capsys, plan, "N01", "DONE")
    assert (code, out) == (2, "")
    assert err == "error: illegal transition N01 TODO -> DONE\n"
    assert (plan / "plan.md").read_bytes() == before
    assert sorted(p.name for p in plan.parent.iterdir()) == ["2026-09-01-demo"]


@pytest.mark.parametrize(
    "rows, args, message",
    [
        ([row("N01")], ["N01", "RUNNING"], "no brief"),
        ([row("N01", type="check", model="-/opus")], ["N01", "VERIFYING"], "no brief"),
        ([row("N01", type="check", model="-/opus")], ["N01", "RETRY", "--note", "x"], "no brief"),
        ([row("N01", "RUNNING", t=1), row("N02", deps="N01")], ["N02", "BRIEFING"], "deps"),
        ([row("N01")], ["N09", "RUNNING"], "unknown node N09"),
        ([row("N01", "DONE", t=1)], ["N01", "DONE"], "illegal transition"),
        ([row("N01")], ["N01"], "STATUS"),
    ],
)
def test_failed_preconditions_exit_2_and_keep_bytes(tmp_path, capsys, rows, args, message):
    plan = make_l(tmp_path, rows)
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_set(capsys, plan, *args)
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and message in err
    assert (plan / "plan.md").read_bytes() == before


def test_unbriefed_check_node_goes_to_briefing_only(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01", type="check", model="-/opus")])
    code, out, err = plz_set(capsys, plan, "N01", "BRIEFING")
    assert (code, err) == (0, "")
    assert out == "N01 BRIEFING try 0 rp 0 · dispatch plz-planner opus\n"


def test_draft_plan_exits_2(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01")], {"N01": brief("N01", "cmd")}, status="DRAFT")
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_set(capsys, plan, "N01", "RUNNING")
    assert (code, out) == (2, "") and "DRAFT" in err
    assert (plan / "plan.md").read_bytes() == before


def test_file_is_written_before_the_line_prints(tmp_path, monkeypatch):
    plan = make_l(tmp_path, [row("N01")], {"N01": brief("N01", "cmd")})
    seen: list[str] = []

    class Spy(io.StringIO):
        def write(self, text: str) -> int:
            seen.append((plan / "plan.md").read_text())
            return super().write(text)

    monkeypatch.setattr(sys, "stdout", Spy())
    assert cli.main(["set", str(plan), "N01", "RUNNING"]) == 0
    assert seen and "| 1 | 0 | RUNNING |" in seen[0]


def test_redirect_prints_the_status_written(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01", "RUNNING", t=1)], {"N01": brief("N01", "cmd")})
    code, out, _ = plz_set(capsys, plan, "N01", "VERIFYING")
    assert (code, out) == (0, "N01 DONE try 1 rp 0\n")
    assert "status: DONE\n" in graph_text(plan)


def test_budget_redirect_to_blocked_with_note(tmp_path, capsys):
    plan = make_l(
        tmp_path,
        [row("N01", "VERIFYING", t=3, rp=1)],
        {"N01": brief("N01", "review")},
        extra="budgets: 3 tries per brief · 1 replans per node\n",
    )
    code, out, _ = plz_set(capsys, plan, "N01", "RETRY", "--note", "fail C1")
    assert (code, out) == (0, "N01 BLOCKED try 3 rp 1\n")
    text = graph_text(plan)
    assert "| 3 | 1 | BLOCKED | blocked: fail C1 |\n" in text
    assert "status: BLOCKED\n" in text


@pytest.mark.parametrize(
    "start, tags, status, line",
    [
        (row("N01"), (), "BRIEFING", "N01 BRIEFING try 0 rp 0 · dispatch plz-planner opus"),
        (
            row("N01", "RETRY", t=1),
            ("cmd",),
            "RUNNING",
            "N01 RUNNING try 2 rp 0 · dispatch plz-executor sonnet",
        ),
        (
            row("N01", "RUNNING", t=1),
            ("review",),
            "VERIFYING",
            "N01 VERIFYING try 1 rp 0 · dispatch plz-verifier opus",
        ),
        (
            row("N01", "RUNNING", t=1),
            ("visual",),
            "VERIFYING",
            "N01 VERIFYING try 1 rp 0 · dispatch plz-visual opus",
        ),
        (
            row("N01", "RUNNING", t=1, model="sonnet/-"),
            ("review",),
            "VERIFYING",
            "N01 VERIFYING try 1 rp 0 · dispatch plz-verifier sonnet",
        ),
        (
            row("N01", "RUNNING", t=2),
            ("cmd",),
            "REPLAN",
            "N01 REPLAN try 2 rp 1 · dispatch plz-planner opus",
        ),
        (row("N01", "REPLAN", t=2, rp=1), ("cmd",), "TODO", "N01 TODO try 0 rp 1"),
        (row("N01", "VERIFYING", t=1), ("review", "human"), "DONE", "N01 WAITING try 1 rp 0"),
    ],
)
def test_dispatch_suffix_per_status(tmp_path, capsys, start, tags, status, line):
    briefs = {"N01": brief("N01", *tags)} if tags else {}
    plan = make_l(tmp_path, [start], briefs)
    code, out, err = plz_set(capsys, plan, "N01", status)
    assert (code, out, err) == (0, line + "\n", "")


def test_note_option_replaces_the_note(tmp_path, capsys):
    plan = make_l(
        tmp_path,
        [row("N01", "BLOCKED", t=2, rp=2, note="blocked: x")],
        {"N01": brief("N01", "cmd")},
    )
    code, out, _ = plz_set(capsys, plan, "N01", "DONE", "--note", "skipped: later")
    assert (code, out) == (0, "N01 DONE try 2 rp 2\n")
    assert "| DONE | skipped: later |\n" in graph_text(plan)


def test_add_appends_a_row_after_the_last(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01", "DONE", t=1), row("N02", "REPLAN", t=2, rp=1, deps="N01")])
    code, out, _ = plz_set(
        capsys,
        plan,
        "N03",
        "--add",
        "--title",
        "split part",
        "--deps",
        "N01, N02",
        "--model",
        "haiku/-",
    )
    assert (code, out) == (0, "N03 TODO try 0 rp 0\n")
    text = graph_text(plan)
    assert (
        "| N02 | t N02 | exec | N01 | sonnet/opus | 2 | 1 | REPLAN | |\n"
        "| N03 | split part | exec | N01,N02 | haiku/- | 0 | 0 | TODO | |\n"
    ) in text


def test_add_check_type(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01")])
    code, out, _ = plz_set(
        capsys,
        plan,
        "N02",
        "--add",
        "--type",
        "check",
        "--title",
        "c",
        "--deps",
        "-",
        "--model=-/opus",
    )
    assert (code, out) == (0, "N02 TODO try 0 rp 0\n")
    assert "| N02 | c | check | - | -/opus | 0 | 0 | TODO | |\n" in graph_text(plan)


def test_deps_edit_and_refused_cycle(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N01"), row("N02", deps="N01"), row("N03")])
    code, out, _ = plz_set(capsys, plan, "N03", "--deps", "N02", "--title", "renamed")
    assert (code, out) == (0, "N03 TODO try 0 rp 0\n")
    assert "| N03 | renamed | exec | N02 | sonnet/opus | 0 | 0 | TODO | |\n" in graph_text(plan)
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_set(capsys, plan, "N01", "--deps", "N03")
    assert (code, out, err) == (2, "", "error: cycle N01 -> N03 -> N02 -> N01\n")
    assert (plan / "plan.md").read_bytes() == before


@pytest.mark.parametrize(
    "args, message",
    [
        (["N01", "--deps", "N09"], "unknown dep N09"),
        (["N02", "--title", "x"], "DONE"),
        (["N01", "--add", "--title", "x", "--deps", "-", "--model", "a/b"], "exists"),
        (["N03", "--add", "--title", "x", "--deps", "-"], "--model"),
        (["N01", "--type", "check"], "--type"),
    ],
)
def test_bad_structure_edits_exit_2(tmp_path, capsys, args, message):
    plan = make_l(tmp_path, [row("N01"), row("N02", "DONE", t=1)])
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_set(capsys, plan, *args)
    assert (code, out) == (2, "") and message in err
    assert (plan / "plan.md").read_bytes() == before


def test_single_file_plan(tmp_path, capsys, monkeypatch):
    plan = make_s(
        tmp_path, [row("N01"), row("N02", deps="N01")], [brief("N01", "cmd", heading="## ")]
    )
    monkeypatch.chdir(tmp_path)
    code = cli.main(["set", "demo", "N01", "RUNNING"])
    assert (code, capsys.readouterr().out) == (
        0,
        "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet\n",
    )
    assert "| N01 | t N01 | exec | - | sonnet/opus | 1 | 0 | RUNNING | |\n" in plan.read_text()
    assert not plan.with_name(plan.name + ".lock").exists()


def test_unknown_plan_exits_2(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["set", "nope", "N01", "RUNNING"]) == 2
    assert capsys.readouterr().err.startswith("error: ")
