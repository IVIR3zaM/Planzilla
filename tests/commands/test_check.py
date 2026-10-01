"""`planzilla check`: run a node's [cmd] criteria (FORMAT §7, §9)."""

import shutil
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import check as check_cmd
from planzilla.commands import log as log_cmd

FIXTURE = Path(__file__).parent.parent / "fixtures" / "check" / "repo"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    monkeypatch.setattr(log_cmd, "today", lambda: "2026-10-01")
    return root


def plan_l(repo: Path) -> Path:
    return repo / ".plan" / "2026-02-01-check-l"


def plan_s(repo: Path) -> Path:
    return repo / ".plan" / "2026-02-02-check-s.md"


def check(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = cli.main(["check", *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_one_pass_one_fail_names_only_the_failing_criterion(repo, capsys):
    code, out, err = check(capsys, str(plan_l(repo)), "N01")
    assert code == 1
    assert out == "N01 check FAIL C2 (1/2 passed)\n"
    assert err == ""


def test_all_pass(repo, capsys):
    code, out, _ = check(capsys, str(plan_l(repo)), "N02")
    assert (code, out) == (0, "N02 check PASS 2/2\n")


def test_node_without_cmd_criteria_passes_0_of_0(repo, capsys):
    code, out, _ = check(capsys, str(plan_l(repo)), "N04")
    assert (code, out) == (0, "N04 check PASS 0/0\n")


def test_evidence_is_saved_per_section_7(repo, capsys):
    check(capsys, str(plan_l(repo)), "N01")
    evidence = plan_l(repo) / "runs" / "N01" / "check-try1.txt"
    assert evidence.read_text() == (
        "== C1 echo fine\n"
        "exit 0\n"
        "fine\n"
        "== C2 printf 'noise\\nreal reason\\n\\n'; exit 3\n"
        "exit 3\n"
        "noise\n"
        "real reason\n"
        "\n"
    )


def test_evidence_is_overwritten_not_appended(repo, capsys):
    check(capsys, str(plan_l(repo)), "N01")
    first = (plan_l(repo) / "runs" / "N01" / "check-try1.txt").read_text()
    check(capsys, str(plan_l(repo)), "N01")
    assert (plan_l(repo) / "runs" / "N01" / "check-try1.txt").read_text() == first


def test_evidence_combines_stdout_and_stderr(repo, capsys):
    check(capsys, str(plan_l(repo)), "N08")
    text = (plan_l(repo) / "runs" / "N08" / "check-try1.txt").read_text()
    assert text == "== C1 echo to-out; echo to-err >&2\nexit 0\nto-out\nto-err\n"


def test_try_number_follows_the_node_state(repo, capsys):
    check(capsys, str(plan_l(repo)), "N02")  # RUNNING, t = 2 -> try 2
    check(capsys, str(plan_l(repo)), "N03")  # TODO check node, t = 0 -> try 1
    assert (plan_l(repo) / "runs" / "N02" / "check-try2.txt").is_file()
    assert (plan_l(repo) / "runs" / "N03" / "check-try1.txt").is_file()
    assert (plan_l(repo) / "log" / "N03.md").read_text().startswith("# N03 log\n\n## try 1 · ")


def test_l_log_entry_per_section_7(repo, capsys):
    check(capsys, str(plan_l(repo)), "N01")
    assert (plan_l(repo) / "log" / "N01.md").read_text() == (
        "# N01 log\n\n## try 1 · 2026-10-01\ncheck: FAIL C2\n- C2 exit 3: real reason\n"
    )


def test_pass_log_entry_has_no_bullets(repo, capsys):
    check(capsys, str(plan_l(repo)), "N02")
    assert (plan_l(repo) / "log" / "N02.md").read_text() == (
        "# N02 log\n\n## try 2 · 2026-10-01\ncheck: PASS 2/2\n"
    )


def test_second_check_of_the_same_try_adds_no_heading(repo, capsys):
    check(capsys, str(plan_l(repo)), "N01")
    check(capsys, str(plan_l(repo)), "N01")
    log = (plan_l(repo) / "log" / "N01.md").read_text()
    assert log.count("## try 1") == 1
    assert log.count("check: FAIL C2") == 2


def test_sm_plan_appends_to_the_log_section_and_has_no_runs(repo, capsys):
    before = plan_s(repo).read_bytes()
    code, out, _ = check(capsys, str(plan_s(repo)), "N01")
    assert (code, out) == (1, "N01 check FAIL C2 (1/2 passed)\n")
    after = plan_s(repo).read_bytes()
    assert after.startswith(before)
    assert after[len(before) :].decode() == (
        "\n### N01 try 1 · 2026-10-01\ncheck: FAIL C2\n- C2 exit 4: broken\n"
    )
    assert not (repo / ".plan" / "runs").exists()
    assert not list(repo.rglob("check-try*.txt"))


def test_check_never_changes_the_graph(repo, capsys):
    before = (plan_l(repo) / "plan.md").read_bytes()
    check(capsys, str(plan_l(repo)), "N01")
    assert (plan_l(repo) / "plan.md").read_bytes() == before


def test_commands_run_from_the_repo_root(repo, tmp_path, monkeypatch, capsys):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    code, out, _ = check(capsys, str(plan_l(repo)), "N05")
    assert (code, out) == (0, "N05 check PASS 1/1\n")


def test_only_the_backticked_command_runs(repo, capsys):
    code, out, _ = check(capsys, str(plan_l(repo)), "N06")
    assert (code, out) == (0, "N06 check PASS 1/1\n")
    assert not (repo / "evil.txt").exists()
    evidence = (plan_l(repo) / "runs" / "N06" / "check-try1.txt").read_text()
    assert evidence == "== C1 true\nexit 0\n"


def test_timeout_fails_the_criterion_and_the_rest_still_run(repo, capsys, monkeypatch):
    monkeypatch.setattr(check_cmd, "TIMEOUT", 0.3)
    code, out, _ = check(capsys, str(plan_l(repo)), "N07")
    assert (code, out) == (1, "N07 check FAIL C1 (1/2 passed)\n")
    log = (plan_l(repo) / "log" / "N07.md").read_text()
    assert "- C1 exit timeout: started\n" in log
    evidence = (plan_l(repo) / "runs" / "N07" / "check-try1.txt").read_text()
    assert evidence.startswith("== C1 echo started; sleep 5\nexit timeout\nstarted\n")
    assert evidence.endswith("== C2 true\nexit 0\n")


def test_slug_fragment_resolves_the_plan(repo, monkeypatch, capsys):
    monkeypatch.chdir(repo)
    code, out, _ = check(capsys, "check-l", "N02")
    assert (code, out) == (0, "N02 check PASS 2/2\n")


def test_draft_plan_exits_2(repo, capsys):
    plan = plan_l(repo) / "plan.md"
    plan.write_text(plan.read_text().replace("status: RUNNING", "status: DRAFT", 1))
    code, out, err = check(capsys, str(plan_l(repo)), "N01")
    assert code == 2
    assert out == ""
    assert err.startswith("error: ") and err.count("\n") == 1
    assert not (plan_l(repo) / "log").exists()


def test_unknown_node_exits_2(repo, capsys):
    code, out, err = check(capsys, str(plan_l(repo)), "N99")
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "N99" in err


def test_node_without_brief_exits_2(repo, capsys):
    (plan_l(repo) / "nodes" / "N01.md").unlink()
    code, out, err = check(capsys, str(plan_l(repo)), "N01")
    assert (code, out) == (2, "")
    assert err.startswith("error: ")


def test_cmd_criterion_without_backticked_command_exits_2(repo, capsys):
    brief = plan_l(repo) / "nodes" / "N05.md"
    brief.write_text(brief.read_text().replace("`test -f marker.txt`", "run the tests"))
    code, out, err = check(capsys, str(plan_l(repo)), "N05")
    assert (code, out) == (2, "")
    assert err.startswith("error: ") and "C1" in err
