"""`planzilla run`: all IO of `plz run` with `subprocess.run` and `shutil.which` faked (D12)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import run as run_module

SMOKE = Path(__file__).resolve().parent.parent / "fixtures" / "run-smoke"
LINE = "Plan: smoke · Node: N01 · Try: 1"


class Fake:
    """Stands in for `subprocess.run`; records every call and answers by argv."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.login = (0, '{"loggedIn": true}', "")
        self.main = (0, "PASS N01\n", "")
        self.reply: str | None = "PASS N01\n"
        self.out_dir: Path | None = None

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if argv[1:3] in (["login", "status"], ["auth", "status"]):
            code, out, err = self.login
        else:
            code, out, err = self.main
            if argv[0] == "codex":
                path = Path(argv[argv.index("-o") + 1])
                self.out_dir = path.parent
                if self.reply is not None:
                    path.write_text(self.reply)
        return subprocess.CompletedProcess(argv, code, out, err)


@pytest.fixture
def fake(monkeypatch):
    f = Fake()
    monkeypatch.setattr(subprocess, "run", f)
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    return f


def call(capsys, *argv: str) -> tuple[int, str, str]:
    code = cli.main(["run", *argv])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_run_is_the_last_command():
    assert cli.COMMANDS[-1] == "run"
    assert run_module.__doc__


@pytest.mark.parametrize(
    "argv",
    [
        ("visual", "haiku", LINE),
        ("verifier", "gemini-3", LINE),
        ("verifier", "sonnet@xhigh", LINE),
        ("planner", "gpt-6-luna@huge", LINE),
        ("planner", "haiku", ""),
        ("planner", "haiku", "  "),
        ("planner", "haiku", "a\nb"),
    ],
)
def test_bad_input_exits_2_with_one_error_line_and_runs_nothing(capsys, fake, argv):
    code, out, err = call(capsys, *argv)
    assert code == 2
    assert out == ""
    assert err.startswith("error: ") and err.count("\n") == 1
    assert fake.calls == []


def test_codex_success_prints_only_the_last_line_of_the_output_file(capsys, fake, tmp_path):
    fake.reply = "thinking...\n\nPASS N01  \n\n"
    fake.main = (0, "SECRET STDOUT", "SECRET STDERR")
    code, out, err = call(capsys, "verifier", "gpt-6-luna@low", LINE)
    assert (code, out, err) == (0, "PASS N01\n", "")
    login, main = fake.calls
    assert login[0] == ["codex", "login", "status"]
    argv, kwargs = main
    assert argv[:4] == ["codex", "exec", "-m", "gpt-6-luna"]
    assert argv[4:6] == ["-c", 'model_reasoning_effort="low"']
    assert argv[argv.index("-C") + 1] == str(Path.cwd())
    assert argv[-1] == "-"
    assert kwargs["input"].splitlines()[0] == (
        "Follow .planzilla/roles/verifier.md: read it first; it is your whole role."
    )
    assert kwargs["input"].splitlines()[1] == f"Input: {LINE}"
    assert kwargs["cwd"] == str(Path.cwd())
    assert kwargs["capture_output"] is True and kwargs["text"] is True
    assert not kwargs.get("shell") and "env" not in kwargs and "timeout" not in kwargs


def test_bare_codex_runs_without_a_model_flag(capsys, fake):
    code, out, err = call(capsys, "verifier", "codex@low", LINE)
    assert (code, out, err) == (0, "PASS N01\n", "")
    argv = fake.calls[1][0]
    assert argv[:4] == ["codex", "exec", "-c", 'model_reasoning_effort="low"']
    assert "-m" not in argv


def test_bare_claude_runs_without_a_model_flag(capsys, fake):
    code, out, err = call(capsys, "verifier", "claude", LINE)
    assert (code, out, err) == (0, "PASS N01\n", "")
    argv = fake.calls[1][0]
    assert argv[:2] == ["claude", "-p"]
    assert "--model" not in argv


def test_codex_output_file_lives_outside_the_repo_and_is_removed(capsys, fake):
    call(capsys, "executor", "gpt-6-luna", LINE)
    assert fake.out_dir is not None
    assert not fake.out_dir.exists()
    assert Path.cwd() not in fake.out_dir.parents


def test_codex_output_dir_is_removed_on_failure(capsys, fake):
    fake.main = (1, "", "boom")
    assert call(capsys, "executor", "gpt-6-luna", LINE)[0] == 3
    assert fake.out_dir is not None and not fake.out_dir.exists()


def test_codex_missing_output_file_is_an_empty_reply(capsys, fake):
    fake.reply = None
    assert call(capsys, "executor", "gpt-6-luna", LINE) == (
        3,
        "",
        "error: codex gave an empty reply\n",
    )


def test_claude_success_prints_the_last_stdout_line(capsys, fake):
    fake.login = (0, json.dumps({"loggedIn": True}), "")
    fake.main = (0, "working\nFAIL N01: C2\n\n", "noise")
    code, out, err = call(capsys, "verifier", "haiku@low", LINE)
    assert (code, out, err) == (0, "FAIL N01: C2\n", "")
    login, main = fake.calls
    assert login[0] == ["claude", "auth", "status"]
    argv, kwargs = main
    assert argv[:6] == ["claude", "-p", "--model", "haiku", "--effort", "low"]
    assert argv[-2:] == ["--permission-mode", "dontAsk"]
    assert kwargs["input"].splitlines()[1] == f"Input: {LINE}"
    assert kwargs["cwd"] == str(Path.cwd())
    assert not kwargs.get("shell") and "env" not in kwargs and "timeout" not in kwargs


@pytest.mark.parametrize(("model", "cli_name"), [("gpt-6-luna", "codex"), ("haiku", "claude")])
def test_cli_not_on_path_exits_3(capsys, fake, monkeypatch, model, cli_name):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert call(capsys, "planner", model, LINE) == (
        3,
        "",
        f"error: {cli_name} not found on PATH\n",
    )
    assert fake.calls == []


def test_which_asks_for_the_provider_cli(capsys, fake, monkeypatch):
    asked: list[str] = []
    monkeypatch.setattr(shutil, "which", lambda name: asked.append(name) or "/bin/x")
    call(capsys, "planner", "haiku", LINE)
    assert asked == ["claude"]


def test_codex_not_logged_in(capsys, fake):
    fake.login = (1, "", "")
    assert call(capsys, "planner", "gpt-6-luna", LINE) == (
        3,
        "",
        "error: codex is not logged in; run codex login\n",
    )
    assert len(fake.calls) == 1


@pytest.mark.parametrize("stdout", ['{"loggedIn": false}', "oops", "{}"])
def test_claude_not_logged_in(capsys, fake, stdout):
    fake.login = (0, stdout, "")
    assert call(capsys, "planner", "haiku", LINE) == (
        3,
        "",
        "error: claude is not logged in; run claude auth login\n",
    )
    assert len(fake.calls) == 1


def test_claude_login_nonzero_exit_is_not_logged_in(capsys, fake):
    fake.login = (1, '{"loggedIn": true}', "")
    assert call(capsys, "planner", "haiku", LINE)[2].startswith("error: claude is not logged in")


@pytest.mark.parametrize(("model", "cli_name"), [("gpt-6-luna", "codex"), ("haiku", "claude")])
def test_nonzero_exit_reports_last_stderr_line(capsys, fake, model, cli_name):
    fake.main = (4, "out line\n", "first\nlast err\n\n")
    assert call(capsys, "executor", model, LINE) == (
        3,
        "",
        f"error: {cli_name} exited 4: last err\n",
    )


@pytest.mark.parametrize(("model", "cli_name"), [("gpt-6-luna", "codex"), ("haiku", "claude")])
def test_nonzero_exit_falls_back_to_last_stdout_line(capsys, fake, model, cli_name):
    fake.main = (2, "a\nlast out\n", "  \n")
    assert call(capsys, "executor", model, LINE) == (
        3,
        "",
        f"error: {cli_name} exited 2: last out\n",
    )


def test_claude_empty_reply_exits_3(capsys, fake):
    fake.main = (0, " \n\n", "")
    assert call(capsys, "executor", "haiku", LINE) == (3, "", "error: claude gave an empty reply\n")


def test_missing_binary_at_run_time_exits_3(capsys, fake, monkeypatch):
    def boom(argv, **kwargs):
        raise FileNotFoundError(argv[0])

    monkeypatch.setattr(subprocess, "run", boom)
    assert call(capsys, "executor", "haiku", LINE) == (3, "", "error: claude not found on PATH\n")


def test_smoke_fixture_lints_ok(capsys, monkeypatch):
    monkeypatch.chdir(SMOKE)
    assert cli.main(["lint", "smoke"]) == 0
    assert capsys.readouterr().out.startswith("lint ok")
