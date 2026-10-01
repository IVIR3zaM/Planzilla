"""`planzilla log`: append entries per FORMAT §7, never touching earlier bytes."""

import os
import time
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import log as log_cmd

HEADER = (
    "# Demo\n"
    "status: RUNNING\n"
    "created: 2026-10-01 · updated: 2026-10-01\n"
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
ROW = "| {id} | thing | exec | - | sonnet/- | {t} | {rp} | {status} | |"


def rows(status: str, t: int, rp: int) -> str:
    return "\n".join(
        [
            ROW.format(id="N01", t=t, rp=rp, status=status),
            ROW.format(id="N02", t=1, rp=0, status="RUNNING"),
        ]
    )


def make_l(root: Path, status: str = "RUNNING", t: int = 1, rp: int = 0) -> Path:
    plan = root / ".plan" / "2026-10-01-demo"
    plan.mkdir(parents=True)
    (plan / "plan.md").write_text(HEADER + GRAPH.format(rows=rows(status, t, rp)))
    return plan


def make_s(root: Path, status: str = "RUNNING", t: int = 1, rp: int = 0, tail: str = "") -> Path:
    plan = root / ".plan" / "2026-10-01-demo.md"
    plan.parent.mkdir(parents=True)
    plan.write_text(HEADER + GRAPH.format(rows=rows(status, t, rp)) + tail)
    return plan


def set_row(plan: Path, status: str, t: int, rp: int = 0) -> None:
    graph = plan / "plan.md" if plan.is_dir() else plan
    text = graph.read_text().replace(
        ROW.format(id="N01", t=1, rp=0, status="RUNNING"),
        ROW.format(id="N01", t=t, rp=rp, status=status),
    )
    graph.write_text(text)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(log_cmd, "today", lambda: "2026-10-01")


def log(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = cli.main(["log", *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_l_first_entry_creates_the_log(tmp_path, capsys):
    plan = make_l(tmp_path)
    code, out, err = log(
        capsys, str(plan), "N01", "exec", "DONE · 3 passed", "-b", "added x", "-b", "chose y"
    )
    assert (code, out, err) == (0, "", "")
    assert (plan / "log" / "N01.md").read_text() == (
        "# N01 log\n\n## try 1 · 2026-10-01\nexec: DONE · 3 passed\n- added x\n- chose y\n"
    )


def test_l_same_key_appends_without_a_new_heading(tmp_path, capsys):
    plan = make_l(tmp_path)
    log(capsys, str(plan), "N01", "exec", "DONE · 3 passed")
    before = (plan / "log" / "N01.md").read_bytes()
    log(capsys, str(plan), "N01", "note", "second line", "-b", "why")
    after = (plan / "log" / "N01.md").read_bytes()
    assert after.startswith(before)
    assert after[len(before) :] == b"note: second line\n- why\n"


def test_l_new_key_appends_a_blank_line_and_heading(tmp_path, capsys):
    plan = make_l(tmp_path)
    log(capsys, str(plan), "N01", "exec", "DONE · 1 passed")
    before = (plan / "log" / "N01.md").read_bytes()
    set_row(plan, "RUNNING", 2)
    log(capsys, str(plan), "N01", "exec", "DONE · 2 passed")
    after = (plan / "log" / "N01.md").read_bytes()
    assert after.startswith(before)
    assert after[len(before) :].decode() == "\n## try 2 · 2026-10-01\nexec: DONE · 2 passed\n"


@pytest.mark.parametrize(
    ("status", "t", "rp", "key"),
    [
        ("BRIEFING", 0, 0, "brief"),
        ("REPLAN", 2, 1, "replan 1"),
        ("TODO", 0, 0, "try 1"),
        ("RETRY", 1, 0, "try 2"),
        ("RUNNING", 1, 0, "try 1"),
        ("VERIFYING", 2, 0, "try 2"),
        ("WAITING", 2, 0, "try 2"),
    ],
)
def test_attempt_key_follows_the_node_state(tmp_path, capsys, status, t, rp, key):
    plan = make_l(tmp_path)
    set_row(plan, status, t, rp)
    log(capsys, str(plan), "N01", "note", "x")
    assert f"\n## {key} · 2026-10-01\nnote: x\n" in (plan / "log" / "N01.md").read_text()


def test_existing_bytes_are_never_edited(tmp_path, capsys):
    plan = make_l(tmp_path)
    (plan / "log").mkdir()
    old = (
        "# N01 log\n\n## replan 1 · 2026-09-30\n- cause: x\n- new brief\n\n\n"
        "## try 1 · 2026-10-01 14:03\nexec: DONE · ok"
    )
    (plan / "log" / "N01.md").write_text(old)
    log(capsys, str(plan), "N01", "exec", "BLOCKED · stuck")
    after = (plan / "log" / "N01.md").read_text()
    assert after.startswith(old)
    # same key as the last heading (a time in the heading and another date are ignored)
    assert after == old + "\nexec: BLOCKED · stuck\n"


def test_sm_appends_to_the_log_section(tmp_path, capsys):
    plan = make_s(tmp_path, tail="\n## Log\n\n### N02 try 1 · 2026-09-30\nexec: DONE · 1 passed\n")
    before = plan.read_bytes()
    code, out, _ = log(capsys, str(plan), "N01", "exec", "DONE · 3 passed", "-b", "added x")
    assert (code, out) == (0, "")
    after = plan.read_bytes()
    assert after.startswith(before)
    assert after[len(before) :] == (
        b"\n### N01 try 1 \xc2\xb7 2026-10-01\nexec: DONE \xc2\xb7 3 passed\n- added x\n"
    )


def test_sm_same_node_and_key_continues_the_entry(tmp_path, capsys):
    plan = make_s(tmp_path, tail="\n## Log\n\n### N01 try 1 · 2026-09-30\nexec: DONE · 1 passed\n")
    before = plan.read_bytes()
    log(capsys, str(plan), "N01", "note", "more")
    assert plan.read_bytes() == before + b"note: more\n"


def test_sm_last_heading_of_another_node_starts_a_new_heading(tmp_path, capsys):
    tail = (
        "\n## Log\n\n### N01 try 1 · 2026-09-30\nexec: DONE · 1 passed\n"
        "\n### N02 try 1 · 2026-09-30\nexec: DONE · 2 passed\n"
    )
    plan = make_s(tmp_path, tail=tail)
    before = plan.read_bytes()
    log(capsys, str(plan), "N01", "verify", "PASS")
    assert plan.read_bytes() == before + "\n### N01 try 1 · 2026-10-01\nverify: PASS\n".encode()


def test_sm_without_a_log_section_creates_it_last(tmp_path, capsys):
    plan = make_s(tmp_path)
    before = plan.read_bytes()
    log(capsys, str(plan), "N01", "note", "hello")
    after = plan.read_bytes()
    assert after.startswith(before)
    assert after[len(before) :].decode() == (
        "\n## Log\n\n### N01 try 1 · 2026-10-01\nnote: hello\n"
    )


def test_sm_writes_do_not_touch_the_header(tmp_path, capsys):
    plan = make_s(tmp_path, tail="\n## Log\n")
    log(capsys, str(plan), "N01", "note", "x")
    assert plan.read_text().startswith(HEADER)


@pytest.mark.parametrize("kind", ["exec", "verify", "plan", "human", "note"])
def test_every_writable_kind_is_accepted(tmp_path, capsys, kind):
    plan = make_l(tmp_path)
    assert log(capsys, str(plan), "N01", kind, "text")[0] == 0
    assert f"\n{kind}: text\n" in (plan / "log" / "N01.md").read_text()


@pytest.mark.parametrize("kind", ["check", "resume", "bogus"])
def test_unknown_kind_exits_2_and_writes_nothing(tmp_path, capsys, kind):
    plan = make_l(tmp_path)
    code, out, err = log(capsys, str(plan), "N01", kind, "text")
    assert (code, out) == (2, "")
    assert err.startswith("error: unknown kind") and err.count("\n") == 1
    assert not (plan / "log").exists()


def test_unknown_node_and_unknown_plan_exit_2(tmp_path, capsys, monkeypatch):
    plan = make_l(tmp_path)
    code, out, err = log(capsys, str(plan), "N99", "note", "x")
    assert (code, out) == (2, "") and err.startswith("error: ")
    monkeypatch.chdir(tmp_path)
    code, out, err = log(capsys, "nothing-like-it", "N01", "note", "x")
    assert (code, out) == (2, "") and err.startswith("error: ")


def test_slug_fragment_and_ambiguity(tmp_path, capsys, monkeypatch):
    plan = make_l(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert log(capsys, "demo", "N01", "note", "x")[0] == 0
    assert (plan / "log" / "N01.md").is_file()
    make_s_dir = tmp_path / ".plan" / "2026-10-02-demo-two.md"
    make_s_dir.write_text((plan / "plan.md").read_text())
    code, _, err = log(capsys, "demo", "N01", "note", "x")
    assert code == 2 and "ambiguous" in err


def test_multiline_text_is_kept_on_one_line(tmp_path, capsys):
    plan = make_l(tmp_path)
    log(capsys, str(plan), "N01", "note", "a\nb", "-b", "c\n- d")
    assert (plan / "log" / "N01.md").read_text().endswith("note: a b\n- c - d\n")


def test_lock_is_released_and_no_temp_file_is_left(tmp_path, capsys):
    plan = make_l(tmp_path)
    log(capsys, str(plan), "N01", "note", "x")
    assert not (plan.parent / "2026-10-01-demo.lock").exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_held_lock_times_out_with_exit_3(tmp_path, capsys, monkeypatch):
    plan = make_l(tmp_path)
    (plan.parent / "2026-10-01-demo.lock").mkdir()
    monkeypatch.setattr(log_cmd, "LOCK_TIMEOUT", 0.2)
    code, out, err = log(capsys, str(plan), "N01", "note", "x")
    assert (code, out) == (3, "")
    assert err.startswith("error: ")
    assert not (plan / "log").exists()


def test_stale_lock_is_removed(tmp_path, capsys):
    plan = make_l(tmp_path)
    lock = plan.parent / "2026-10-01-demo.lock"
    lock.mkdir()
    old = time.time() - 120
    os.utime(lock, (old, old))
    assert log(capsys, str(plan), "N01", "note", "x")[0] == 0
    assert not lock.exists()
