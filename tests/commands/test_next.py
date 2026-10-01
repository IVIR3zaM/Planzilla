"""`planzilla next`: one `<id> <action> <model>` line per ready action (FORMAT §5, §9)."""

from pathlib import Path

import pytest

from planzilla import cli

HEADER = (
    "# Demo\n"
    "status: {status}\n"
    "created: 2026-09-01 · updated: 2026-09-01\n"
    "goal: g\n"
    "verify: true\n"
    "commit: none\n"
)
GRAPH = (
    "\n## Graph\n\n"
    "| id | title | type | deps | model | try | rp | status | note |\n"
    "|----|-------|------|------|-------|-----|----|--------|------|\n"
    "{rows}\n"
)
DIAMOND = {
    "N01": ("-", "exec"),
    "N02": ("N01", "exec"),
    "N03": ("N01", "check"),
    "N04": ("N02,N03", "exec"),
}


def row(node_id: str, status: str, deps: str = "-", type: str = "exec", note: str = "") -> str:
    model = {"exec": "haiku/opus", "check": "-/sonnet", "gate": "-/-"}[type]
    t = 1 if status in ("RUNNING", "VERIFYING", "RETRY", "DONE") else 0
    cells = [node_id, f"t {node_id}", type, deps, model, str(t), "0", status, note]
    return "|" + "".join(f" {cell} |" if cell else " |" for cell in cells)


def make_plan(root: Path, rows: list[str], status: str = "RUNNING", config: str = "") -> Path:
    plan = root / ".plan" / "2026-09-01-demo"
    (plan / "nodes").mkdir(parents=True)
    (plan / "plan.md").write_text(HEADER.format(status=status) + GRAPH.format(rows="\n".join(rows)))
    if config:
        (root / ".plan" / "config.md").write_text(config)
    return plan


def write_brief(plan: Path, node_id: str, tag: str) -> None:
    write = "Write: `src/x.py`\n" if node_id != "N03" else ""
    text = f"# {node_id} t {node_id}\nDo: x.\n{write}Done when:\n- C1 [{tag}] `true`\n"
    (plan / "nodes" / f"{node_id}.md").write_text(text)


def plz_next(capsys: pytest.CaptureFixture[str], plan: Path) -> tuple[int, str, str]:
    code = cli.main(["next", str(plan)])
    out = capsys.readouterr()
    return code, out.out, out.err


def diamond(statuses: dict[str, str]) -> list[str]:
    return [row(i, statuses.get(i, "TODO"), deps, type) for i, (deps, type) in DIAMOND.items()]


def test_diamond_yields_its_waves_in_order(tmp_path, capsys):
    plan = make_plan(tmp_path, diamond({}))
    for node_id in DIAMOND:
        write_brief(plan, node_id, "cmd")
    graph = plan / "plan.md"
    seen = []
    for done in ([], ["N01"], ["N01", "N02", "N03"]):
        graph.write_text(
            HEADER.format(status="RUNNING")
            + GRAPH.format(rows="\n".join(diamond(dict.fromkeys(done, "DONE"))))
        )
        code, out, err = plz_next(capsys, plan)
        assert (code, err) == (0, "")
        seen.append(out)
    assert seen == ["N01 exec haiku\n", "N02 exec haiku\nN03 check -\n", "N04 exec haiku\n"]


def test_lines_match_format_byte_for_byte(tmp_path, capsys):
    rows = [
        row("N01", "TODO"),
        row("N02", "VERIFYING"),
        row("N03", "TODO", type="check"),
        row("N04", "REPLAN"),
        row("N05", "WAITING", note="ask: D1"),
    ]
    plan = make_plan(tmp_path, rows, config="models: planner=big, verify=small\n")
    write_brief(plan, "N03", "review")
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_next(capsys, plan)
    assert (code, err) == (0, "")
    assert out == "N01 brief big\nN02 verify opus\nN03 verify sonnet\nN04 replan big\n"
    assert (plan / "plan.md").read_bytes() == before


def test_unbriefed_check_node_is_briefed_just_in_time(tmp_path, capsys):
    plan = make_plan(tmp_path, [row("N01", "TODO", type="check")], config="models: planner=big\n")
    before = (plan / "plan.md").read_bytes()
    assert plz_next(capsys, plan) == (0, "N01 brief big\n", "")
    assert (plan / "plan.md").read_bytes() == before
    (plan / "nodes" / "N01.md").write_text("# N01 t N01\nDo: x.\nDone when:\n- C1 [review] x\n")
    assert plz_next(capsys, plan) == (0, "N01 verify sonnet\n", "")


def test_nothing_printed_when_all_done(tmp_path, capsys):
    plan = make_plan(tmp_path, diamond(dict.fromkeys(DIAMOND, "DONE")), status="DONE")
    assert plz_next(capsys, plan) == (0, "", "")


def test_nothing_printed_when_all_blocked(tmp_path, capsys):
    plan = make_plan(tmp_path, diamond({"N01": "BLOCKED"}), status="BLOCKED")
    assert plz_next(capsys, plan) == (0, "", "")


def test_ask_lines_only_when_no_other_line(tmp_path, capsys):
    rows = [
        row("N01", "WAITING", note="ask: D1"),
        row("N02", "TODO", type="gate"),
        row("N03", "RETRY"),
    ]
    plan = make_plan(tmp_path, rows)
    assert plz_next(capsys, plan) == (0, "N03 exec haiku\n", "")
    rows[2] = row("N03", "BLOCKED")
    (plan / "plan.md").write_text(
        HEADER.format(status="WAITING") + GRAPH.format(rows="\n".join(rows))
    )
    assert plz_next(capsys, plan) == (0, "N01 ask -\nN02 ask -\n", "")


def test_cycle_exits_2_naming_the_cycle(tmp_path, capsys):
    rows = [row("N01", "TODO"), row("N03", "TODO", deps="N05"), row("N05", "TODO", deps="N03")]
    plan = make_plan(tmp_path, rows)
    assert plz_next(capsys, plan) == (2, "", "error: cycle N03 -> N05 -> N03\n")


def test_draft_plan_exits_2(tmp_path, capsys):
    plan = make_plan(tmp_path, [row("N01", "TODO")], status="DRAFT")
    code, out, err = plz_next(capsys, plan)
    assert (code, out) == (2, "") and "DRAFT" in err


def test_takes_no_lock(tmp_path, capsys):
    plan = make_plan(tmp_path, [row("N01", "TODO")])
    plan.with_name(plan.name + ".lock").mkdir()
    assert plz_next(capsys, plan) == (0, "N01 brief opus\n", "")


def test_slug_fragment(tmp_path, capsys, monkeypatch):
    make_plan(tmp_path, [row("N01", "TODO")])
    monkeypatch.chdir(tmp_path)
    assert cli.main(["next", "demo"]) == 0
    assert capsys.readouterr().out == "N01 brief opus\n"
