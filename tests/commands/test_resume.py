"""`planzilla resume`: rows 29-32 of FORMAT §5, §13, in a temporary git repo."""

import subprocess
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import resume as resume_cmd

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
RERUN = "rerun at try {t}; partial edits of this try may be in the tree"


def row(
    node_id: str, status: str, t: int = 1, rp: int = 0, type: str = "exec", note: str = ""
) -> str:
    model = "-/sonnet" if type == "check" else "sonnet/opus"
    cells = [node_id, f"t {node_id}", type, "-", model, str(t), str(rp), status, note]
    return "|" + "".join(f" {cell} |" if cell else " |" for cell in cells)


def brief(node_id: str, write: str, heading: str = "# ") -> str:
    return (
        f"{heading}{node_id} t {node_id}\nDo: x.\nWrite: `{write}`\nDone when:\n- C1 [review] ok\n"
    )


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "c.py").write_text("c\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resume_cmd, "today", lambda: "2026-10-01")


ROWS = [
    row("N01", "RUNNING", t=2, rp=1),
    row("N02", "VERIFYING"),
    row("N03", "VERIFYING"),
    row("N04", "VERIFYING", type="check"),
    row("N05", "BRIEFING", t=0),
    row("N06", "REPLAN", t=0, rp=1),
    row("N07", "WAITING", t=0, note="ask: D1"),
    row("N08", "BLOCKED", t=2, rp=2, note="blocked: x"),
    row("N09", "DONE"),
    row("N10", "TODO", t=0),
    row("N11", "RETRY"),
    row("N12", "VERIFYING"),
]


def make_l(root: Path, rows: list[str], status: str = "RUNNING") -> Path:
    plan = root / ".plan" / "2026-09-01-demo"
    (plan / "nodes").mkdir(parents=True)
    (plan / "plan.md").write_text(HEADER.format(status=status) + GRAPH.format(rows="\n".join(rows)))
    briefs = {"N02": "src/a.py", "N03": "src/b.py", "N12": "src/c.py"}
    for node_id, write in briefs.items():
        (plan / "nodes" / f"{node_id}.md").write_text(brief(node_id, write))
    return plan


def plz_resume(capsys: pytest.CaptureFixture[str], plan: Path) -> tuple[int, str, str]:
    code = cli.main(["resume", str(plan)])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_rows_29_to_32(repo, capsys):
    plan = make_l(repo, ROWS)
    (repo / "src" / "b.py").write_text("partial\n")  # N03: untracked change under Write
    (repo / "src" / "c.py").write_text("changed\n")  # N12: modified tracked file under Write
    code, out, err = plz_resume(capsys, plan)
    assert (code, err) == (0, "")
    assert out == (
        "N01 RUNNING try 2 rp 1 · rerun\n"
        "N02 RUNNING try 1 rp 0 · rerun\n"
        "N03 VERIFYING try 1 rp 0 · rerun\n"
        "N04 VERIFYING try 1 rp 0 · rerun\n"
        "N05 BRIEFING try 0 rp 0 · rerun\n"
        "N06 REPLAN try 0 rp 1 · rerun\n"
        "N12 VERIFYING try 1 rp 0 · rerun\n"
        "N07 WAITING try 0 rp 0 · held\n"
        "N08 BLOCKED try 2 rp 2 · held\n"
    )
    text = (plan / "plan.md").read_text()
    assert "| N01 | t N01 | exec | - | sonnet/opus | 2 | 1 | RUNNING | |\n" in text
    assert "| N02 | t N02 | exec | - | sonnet/opus | 1 | 0 | RUNNING | |\n" in text
    assert "| N03 | t N03 | exec | - | sonnet/opus | 1 | 0 | VERIFYING | |\n" in text
    assert "status: RUNNING\ncreated: 2026-09-01 · updated: 2026-10-01\n" in text
    assert (plan / "log" / "N01.md").read_text() == (
        f"# N01 log\n\n## try 2 · 2026-10-01\nresume: {RERUN.format(t=2)}\n"
    )
    assert (plan / "log" / "N02.md").read_text() == (
        f"# N01 log\n\n## try 1 · 2026-10-01\nresume: {RERUN.format(t=1)}\n".replace("N01", "N02")
    )
    assert sorted(p.name for p in (plan / "log").iterdir()) == ["N01.md", "N02.md"]
    assert not plan.with_name(plan.name + ".lock").exists()


def test_try_is_kept_and_existing_log_is_appended(repo, capsys):
    plan = make_l(repo, [row("N01", "RUNNING", t=3)])
    (plan / "log").mkdir()
    (plan / "log" / "N01.md").write_text("# N01 log\n\n## try 3 · 2026-09-30\nexec: started\n")
    assert plz_resume(capsys, plan) == (0, "N01 RUNNING try 3 rp 0 · rerun\n", "")
    assert (plan / "log" / "N01.md").read_text() == (
        f"# N01 log\n\n## try 3 · 2026-09-30\nexec: started\nresume: {RERUN.format(t=3)}\n"
    )


def test_held_only(repo, capsys):
    rows = [row("N01", "WAITING", note="ask: C1"), row("N02", "BLOCKED", rp=2, note="blocked: y")]
    plan = make_l(repo, rows)
    code, out, _ = plz_resume(capsys, plan)
    assert (code, out) == (0, "N01 WAITING try 1 rp 0 · held\nN02 BLOCKED try 1 rp 2 · held\n")
    assert "status: WAITING\n" in (plan / "plan.md").read_text()


def test_done_plan_prints_nothing_and_writes_nothing(repo, capsys):
    plan = make_l(repo, [row("N01", "DONE"), row("N02", "DONE")], status="DONE")
    before = (plan / "plan.md").read_bytes()
    assert plz_resume(capsys, plan) == (0, "", "")
    assert (plan / "plan.md").read_bytes() == before
    assert not (plan / "log").exists()


def test_draft_plan_exits_2(repo, capsys):
    plan = make_l(repo, ROWS, status="DRAFT")
    before = (plan / "plan.md").read_bytes()
    code, out, err = plz_resume(capsys, plan)
    assert (code, out) == (2, "") and "DRAFT" in err
    assert (plan / "plan.md").read_bytes() == before


def test_single_file_plan_appends_to_the_log_section(repo, capsys):
    plan = repo / ".plan" / "2026-09-01-demo.md"
    plan.parent.mkdir()
    text = HEADER.format(status="RUNNING") + GRAPH.format(rows=row("N01", "VERIFYING"))
    plan.write_text(text + "\n" + brief("N01", "src/a.py", heading="## "))
    code, out = cli.main(["resume", str(plan)]), capsys.readouterr().out
    assert (code, out) == (0, "N01 RUNNING try 1 rp 0 · rerun\n")
    assert plan.read_text().endswith(
        f"- C1 [review] ok\n\n## Log\n\n### N01 try 1 · 2026-10-01\nresume: {RERUN.format(t=1)}\n"
    )


def test_git_failure_exits_3(tmp_path, capsys):
    plan = make_l(tmp_path, [row("N02", "VERIFYING")])
    before = (plan / "plan.md").read_bytes()
    plan.parent.parent.joinpath(".git").write_text("gitdir: /nonexistent\n")
    code, out, err = plz_resume(capsys, plan)
    assert (code, out) == (3, "") and err.startswith("error: ")
    assert (plan / "plan.md").read_bytes() == before
