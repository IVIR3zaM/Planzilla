"""`planzilla brief`: executor, cold verifier and ask output (FORMAT §9, §13)."""

from pathlib import Path

import pytest

from planzilla import cli

HEADER = (
    "# Demo\n"
    "status: RUNNING\n"
    "created: 2026-10-01 · updated: 2026-10-01\n"
    "goal: g\n"
    "verify: header-verify\n"
    "commit: none\n"
)
DECISIONS = "\n## Decisions\n\n- D7 Pick a thing | proposed · recommend: a · alt: b\n"
GRAPH = (
    "\n## Graph\n\n"
    "| id | title | type | deps | model | try | rp | status | note |\n"
    "|----|-------|------|------|-------|-----|----|--------|------|\n"
    "{rows}\n"
)
BODY = (
    "Do: Do the thing.\n"
    "Context: facts.\n"
    "Write: `src/x.py`,\n"
    "  `tests/x.py`\n"
    "Test first: -\n"
    "Done when:\n"
    "- C1 [cmd] `true`\n"
    "- C2 [review] the thing is good\n"
    "  and continues here\n"
)
RERUN = "Rerun: this try was interrupted; the tree may hold its partial edits. Continue from them."

Entries = list[tuple[str, list[str]]]


def row(
    node_id: str,
    status: str = "RUNNING",
    t: int = 1,
    rp: int = 0,
    type: str = "exec",
    note: str = "",
) -> str:
    model = {"exec": "sonnet/-", "check": "-/opus", "gate": "-/-"}[type]
    return (
        f"| {node_id} | title {node_id} | {type} | - | {model} | {t} | {rp} | {status} | {note} |"
    )


def make_plan(
    root: Path,
    layout: str,
    rows: list[str],
    briefs: dict[str, str] | None = None,
    entries: Entries | None = None,
    config: str | None = None,
) -> Path:
    """Write a plan with N01 (and noise node N02) in layout `L` or `S`; return its path."""
    briefs = {"N01": BODY, "N02": BODY} if briefs is None else briefs
    entries = entries or []
    noise = [("try 2", ["verify: FAIL C9", "- C9 exit 1: other node", "resume: noise"])]
    text = HEADER + DECISIONS + GRAPH.format(rows="\n".join(rows))
    if layout == "L":
        plan = root / ".plan" / "2026-10-01-demo"
        (plan / "nodes").mkdir(parents=True)
        (plan / "log").mkdir()
        (plan / "plan.md").write_text(text)
        for node_id, body in briefs.items():
            (plan / "nodes" / f"{node_id}.md").write_text(f"# {node_id} title {node_id}\n{body}")
        for node_id, node_entries in (("N01", entries), ("N02", noise)):
            lines = [f"# {node_id} log", ""]
            for key, body_lines in node_entries:
                lines += [f"## {key} · 2026-09-30", *body_lines]
            (plan / "log" / f"{node_id}.md").write_text("\n".join(lines) + "\n")
    else:
        plan = root / ".plan" / "2026-10-01-demo.md"
        plan.parent.mkdir(parents=True)
        for node_id, body in briefs.items():
            text += f"\n## {node_id} title {node_id}\n{body}"
        text += "\n## Log\n"
        for node_id, node_entries in (("N01", entries), ("N02", noise)):
            for key, body_lines in node_entries:
                text += "\n" + "\n".join([f"### {node_id} {key} · 2026-09-30", *body_lines]) + "\n"
        plan.write_text(text)
    if config is not None:
        (root / ".plan" / "config.md").write_text(config)
    return plan


def expected_brief(layout: str, body: str = BODY) -> str:
    return f"{'#' if layout == 'L' else '##'} N01 title N01\n{body}".rstrip("\n")


def brief(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = cli.main(["brief", *args])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture(params=["L", "S"])
def layout(request: pytest.FixtureRequest) -> str:
    return request.param


FINDING_1 = ("try 1", ["exec: DONE · 1 passed", "check: FAIL C1", "- C1 exit 1: older finding"])
FINDING_2 = (
    "try 2",
    ["exec: DONE · 2 passed", "verify: FAIL C2,C3", "- C2 the thing is wrong", "- C3 also wrong"],
)


def test_first_try_prints_the_brief_and_the_verify_line_only(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")])
    code, out, err = brief(capsys, str(plan), "N01")
    assert (code, err) == (0, "")
    assert out == expected_brief(layout) + "\n\nVerify: header-verify\n"


def test_verify_line_comes_from_config_verify_fast(tmp_path, capsys, layout):
    plan = make_plan(
        tmp_path, layout, [row("N01"), row("N02")], config="verify: slow\nverify_fast: quick\n"
    )
    assert brief(capsys, str(plan), "N01")[1].endswith("\n\nVerify: quick\n")


def test_verify_line_without_verify_fast_is_the_plan_verify(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")], config="verify: config-verify\n")
    assert brief(capsys, str(plan), "N01")[1].endswith("\n\nVerify: header-verify\n")


def test_retry_adds_only_the_last_findings(tmp_path, capsys, layout):
    plan = make_plan(
        tmp_path, layout, [row("N01", t=3), row("N02")], entries=[FINDING_1, FINDING_2]
    )
    code, out, _ = brief(capsys, str(plan), "N01")
    assert code == 0
    assert out == (
        expected_brief(layout)
        + "\n\n## Findings (try 2)\n"
        + "verify: FAIL C2,C3\n- C2 the thing is wrong\n- C3 also wrong"
        + "\n\nVerify: header-verify\n"
    )
    assert "older finding" not in out and "C9" not in out


def test_second_try_shows_the_findings_of_try_one(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01", t=2), row("N02")], entries=[FINDING_1])
    out = brief(capsys, str(plan), "N01")[1]
    assert out == (
        expected_brief(layout)
        + "\n\n## Findings (try 1)\ncheck: FAIL C1\n- C1 exit 1: older finding"
        + "\n\nVerify: header-verify\n"
    )


def test_first_try_hides_findings_left_over_from_an_older_brief(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01", t=1), row("N02")], entries=[FINDING_1])
    assert "Findings" not in brief(capsys, str(plan), "N01")[1]


def test_retry_without_any_findings_prints_no_findings_section(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01", t=2), row("N02")], entries=[("try 1", ["x: y"])])
    assert "Findings" not in brief(capsys, str(plan), "N01")[1]


def test_rerun_marker_adds_the_notice_after_the_findings(tmp_path, capsys, layout):
    resume = ["resume: rerun at try 2; partial edits of this try may be in the tree"]
    plan = make_plan(
        tmp_path,
        layout,
        [row("N01", t=2), row("N02")],
        entries=[FINDING_1, ("try 2", ["exec: DONE · x", *resume])],
    )
    out = brief(capsys, str(plan), "N01")[1]
    assert out == (
        expected_brief(layout)
        + "\n\n## Findings (try 1)\ncheck: FAIL C1\n- C1 exit 1: older finding"
        + f"\n\n{RERUN}\n\nVerify: header-verify\n"
    )


def test_resume_line_of_an_earlier_try_is_not_a_rerun_marker(tmp_path, capsys, layout):
    resume = ["resume: rerun at try 1; partial edits of this try may be in the tree"]
    plan = make_plan(
        tmp_path,
        layout,
        [row("N01", t=2), row("N02")],
        entries=[("try 1", resume), ("try 2", ["exec: DONE · x"])],
    )
    assert RERUN not in brief(capsys, str(plan), "N01")[1]


def test_verify_mode_is_cold(tmp_path, capsys, layout):
    resume = ["resume: rerun at try 2; partial edits of this try may be in the tree"]
    plan = make_plan(
        tmp_path,
        layout,
        [row("N01", t=2, status="VERIFYING"), row("N02")],
        entries=[FINDING_1, ("try 2", ["exec: DONE · x", *resume])],
    )
    code, out, err = brief(capsys, str(plan), "N01", "--verify")
    assert (code, err) == (0, "")
    heading = expected_brief(layout).split("\n")[0]
    assert out == (
        f"{heading}\nWrite: `src/x.py`,\n  `tests/x.py`\n"
        "Done when:\n- C1 [cmd] `true`\n- C2 [review] the thing is good\n  and continues here\n"
    )
    for leaked in ("Findings", "older finding", "Rerun", "Verify:", "Do the thing", "facts"):
        assert leaked not in out


def test_verify_mode_adds_the_visual_recipe_only_for_visual_criteria(tmp_path, capsys, layout):
    body = BODY + "- C3 [visual] the page shows the table\n"
    config = "visual_recipe: uv run demo serve, open http://127.0.0.1:8000/\n"
    plan = make_plan(
        tmp_path, layout, [row("N01"), row("N02")], {"N01": body, "N02": BODY}, config=config
    )
    out = brief(capsys, str(plan), "N01", "--verify")[1]
    assert out.endswith(
        "- C3 [visual] the page shows the table\n"
        "Visual recipe: uv run demo serve, open http://127.0.0.1:8000/\n"
    )
    other = brief(capsys, str(plan), "N02", "--verify")[1]
    assert "Visual recipe" not in other


def test_verify_mode_without_a_recipe_has_no_recipe_line(tmp_path, capsys, layout):
    body = BODY + "- C3 [visual] the page shows the table\n"
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")], {"N01": body, "N02": BODY})
    assert "Visual recipe" not in brief(capsys, str(plan), "N01", "--verify")[1]


def test_verify_mode_of_a_check_node_has_no_write_field(tmp_path, capsys, layout):
    body = "Do: check it.\nDone when:\n- C1 [review] fine\n"
    plan = make_plan(
        tmp_path, layout, [row("N01", type="check", status="TODO", t=0), row("N02")], {"N01": body}
    )
    heading = expected_brief(layout, body).split("\n")[0]
    assert brief(capsys, str(plan), "N01", "--verify")[1] == (
        f"{heading}\nDone when:\n- C1 [review] fine\n"
    )


def test_missing_brief_exits_2(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")], briefs={"N02": BODY})
    for mode in ([], ["--verify"]):
        code, out, err = brief(capsys, str(plan), "N01", *mode)
        assert (code, out) == (2, "")
        assert err.startswith("error: ") and err.count("\n") == 1


def test_unknown_node_and_plan_exit_2(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")])
    assert brief(capsys, str(plan), "N99")[0] == 2
    assert brief(capsys, str(tmp_path / ".plan" / "2026-10-01-none"), "N01")[0] == 2


def test_verify_and_ask_are_mutually_exclusive(tmp_path, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")])
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["brief", str(plan), "N01", "--verify", "--ask"])
    assert exit_info.value.code == 2


def test_ask_decision(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01", status="WAITING", note="ask: D7"), row("N02")])
    code, out, _ = brief(capsys, str(plan), "N01", "--ask")
    assert (code, out) == (0, "N01 D7: Pick a thing | proposed · recommend: a · alt: b\n")


def test_ask_criteria(tmp_path, capsys, layout):
    body = BODY + "- C5 [human] the owner likes it\n- C6 [human] and the colors\n"
    plan = make_plan(
        tmp_path,
        layout,
        [row("N01", status="WAITING", note="ask: C5,C6"), row("N02")],
        {"N01": body},
    )
    code, out, _ = brief(capsys, str(plan), "N01", "--ask")
    assert (code, out) == (0, "N01 human C5: the owner likes it · C6: and the colors\n")


def test_ask_blocked(tmp_path, capsys, layout):
    plan = make_plan(
        tmp_path,
        layout,
        [row("N01", status="BLOCKED", note="blocked: C2 keeps failing"), row("N02")],
    )
    assert brief(capsys, str(plan), "N01", "--ask")[1] == "N01 blocked: C2 keeps failing\n"


def test_ask_gate(tmp_path, capsys, layout):
    body = (
        "Do: sign off.\nWrite: -\nDone when:\n"
        "- C1 [human] the owner approves\n- C2 [human] and ships\n"
    )
    plan = make_plan(
        tmp_path, layout, [row("N01", type="gate", status="TODO", t=0), row("N02")], {"N01": body}
    )
    assert brief(capsys, str(plan), "N01", "--ask")[1] == (
        "N01 gate: title N01 · the owner approves · and ships\n"
    )


def test_ask_on_any_other_node_exits_2(tmp_path, capsys, layout):
    plan = make_plan(tmp_path, layout, [row("N01"), row("N02")])
    code, out, err = brief(capsys, str(plan), "N01", "--ask")
    assert (code, out) == (2, "")
    assert err.startswith("error: ")
