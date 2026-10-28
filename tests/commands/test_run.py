"""`planzilla run`: all IO of `plz run` with `subprocess.run` and `shutil.which` faked (D12)."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from planzilla import cli, resolver
from planzilla.commands import run as run_module
from planzilla.config import Policy

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


def test_codex_missing_output_file_reports_read_failure(capsys, fake):
    fake.reply = None
    code, out, err = call(capsys, "executor", "gpt-6-luna", LINE)
    assert (code, out) == (3, "")
    assert err.startswith("error: codex reply read failed: ")
    assert "No such file" in err and err.count("\n") == 1
    assert fake.out_dir is not None and not fake.out_dir.exists()


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
    fake.login = (1, "", "Not logged in")
    assert call(capsys, "planner", "gpt-6-luna", LINE) == (
        3,
        "",
        "error: codex login check exited 1: Not logged in; "
        "codex is not logged in; run codex login\n",
    )
    assert len(fake.calls) == 1


@pytest.mark.parametrize("stdout", ['{"loggedIn": false}'])
def test_claude_not_logged_in(capsys, fake, stdout):
    fake.login = (0, stdout, "")
    assert call(capsys, "planner", "haiku", LINE) == (
        3,
        "",
        "error: claude is not logged in; run claude auth login\n",
    )
    assert len(fake.calls) == 1


def test_claude_login_nonzero_exit_is_a_failed_check(capsys, fake):
    fake.login = (1, '{"loggedIn": true}', "")
    assert call(capsys, "planner", "haiku", LINE) == (
        3,
        "",
        'error: claude login check exited 1: {"loggedIn": true}\n',
    )


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


def resolved_selection(token: str, route: str = "codex", mode: str = "cli") -> resolver.Selection:
    """Controlled resolver facts; they never establish live provider availability."""
    harness = {"codex": "codex", "claude": "claude-code", "copilot": "copilot"}[route]
    capability = resolver.Capability(
        route,
        mode,
        "fixture-delivery",
        (
            resolver.Model("gpt-6.1-sol", "gpt", ("opus", "sonnet"), ("high", "medium")),
            resolver.Model("claude-sonnet-5", "claude", ("sonnet",), ("high", "medium")),
        ),
        True,
        True,
        "callable_native" if mode == "native" else "external_reply",
        ("controlled fixture, not live evidence",),
    )
    result = resolver.resolve(
        Policy((route,), {}),
        resolver.Request("executor", token),
        resolver.Context(harness, harness),
        (capability,),
    )
    assert isinstance(result, resolver.Selection)
    return result


def invoke_entrypoint(
    capsys: pytest.CaptureFixture[str], entrypoint: str, route: str
) -> tuple[int, str, str]:
    token = f"{route}::{'gpt-6.1-sol' if route == 'codex' else 'claude-sonnet-5'}@high"
    if entrypoint == "direct":
        return call(capsys, "executor", token, LINE)
    code = run_module.run_selection("executor", resolved_selection(token, route), LINE)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize("entrypoint", ["direct", "resolved"])
@pytest.mark.parametrize("route", ["codex", "claude"])
@pytest.mark.parametrize("phase", ["login check", "execution"])
@pytest.mark.parametrize(
    ("error_type", "detail"),
    [
        (FileNotFoundError, "missing"),
        (PermissionError, "permission denied"),
        (OSError, "other failure"),
    ],
)
def test_launch_failures_preserve_phase_and_observation(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
    route: str,
    phase: str,
    error_type: type[OSError],
    detail: str,
) -> None:
    out_dirs: list[Path] = []

    def launch(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        is_login = argv[1:3] in (["login", "status"], ["auth", "status"])
        if phase == "login check" or not is_login:
            if "-o" in argv:
                out_dirs.append(Path(argv[argv.index("-o") + 1]).parent)
            raise error_type(detail)
        return fake(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", launch)
    code, out, err = invoke_entrypoint(capsys, entrypoint, route)
    expected = (
        f"{route} not found on PATH"
        if error_type is FileNotFoundError
        else f"{route} {phase} launch failed: {detail}"
    )
    assert (code, out, err) == (3, "", f"error: {expected}\n")
    assert all(not path.exists() for path in out_dirs)


@pytest.mark.parametrize("entrypoint", ["direct", "resolved"])
@pytest.mark.parametrize("route", ["codex", "claude"])
@pytest.mark.parametrize("phase", ["login check", "execution"])
@pytest.mark.parametrize("status", [-15, -9, 7])
def test_failed_children_report_status_without_inventing_auth_or_quota(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    entrypoint: str,
    route: str,
    phase: str,
    status: int,
) -> None:
    observation = (status, "fallback", "first\nHTTP 429\n")
    if phase == "login check":
        fake.login = observation
    else:
        fake.main = observation
    code, out, err = invoke_entrypoint(capsys, entrypoint, route)
    label = f"{route} login check" if phase == "login check" else route
    status_text = f"terminated by signal {-status}" if status < 0 else f"exited {status}"
    assert (code, out, err) == (3, "", f"error: {label} {status_text}: HTTP 429\n")
    assert len(fake.calls) == (1 if phase == "login check" else 2)
    if fake.out_dir is not None:
        assert not fake.out_dir.exists()


@pytest.mark.parametrize("stdout", ["oops", "{}", "[]", '{"loggedIn": "false"}'])
def test_invalid_auth_status_is_not_logout(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    stdout: str,
) -> None:
    fake.login = (0, stdout, "status detail")
    assert call(capsys, "executor", "haiku", LINE) == (
        3,
        "",
        "error: claude login check returned invalid authentication status: status detail\n",
    )
    assert len(fake.calls) == 1


@pytest.mark.parametrize("entrypoint", ["direct", "resolved"])
@pytest.mark.parametrize("failure", ["missing", "unreadable", "empty", "success"])
def test_reply_lifecycle_preserves_read_failure_and_cleans_up(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
    failure: str,
) -> None:
    fake.reply = {"missing": None, "empty": " \n", "success": "PASS N01\n"}.get(failure, "reply")
    read_text = Path.read_text

    def read(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "reply.txt" and failure == "unreadable":
            raise PermissionError("read denied\nobserved detail")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    code, out, err = invoke_entrypoint(capsys, entrypoint, "codex")
    if failure == "success":
        assert (code, out, err) == (0, "PASS N01\n", "")
    elif failure == "empty":
        assert (code, out, err) == (3, "", "error: codex gave an empty reply\n")
    else:
        assert (code, out) == (3, "")
        assert err.startswith("error: codex reply read failed: ") and err.count("\n") == 1
        assert ("No such file" if failure == "missing" else "observed detail") in err
    assert fake.out_dir is not None and not fake.out_dir.exists()


def test_each_role_owns_a_distinct_temporary_reply_directory(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
) -> None:
    directories: list[Path] = []
    for role in ("planner", "executor", "verifier"):
        assert call(capsys, role, "gpt-6.1-sol@high", LINE) == (0, "PASS N01\n", "")
        assert fake.out_dir is not None and not fake.out_dir.exists()
        directories.append(fake.out_dir)
    assert len(set(directories)) == 3


def make_exe(directory: Path, name: str, stdout: str = "", stderr: str = "", code: int = 0) -> Path:
    """A fake executable that records argv and stdin as JSON, then answers canned output."""
    log = directory / f"{name}.json"
    path = directory / name
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "record = {'argv': sys.argv[1:], 'stdin': sys.stdin.read()}\n"
        f"open({str(log)!r}, 'w').write(json.dumps(record))\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({code})\n"
    )
    path.chmod(0o755)
    return log


def recorded(log: Path) -> dict:
    return json.loads(log.read_text())


@pytest.fixture
def bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "bin"
    directory.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    return directory


def test_copilot_on_path_delivers_the_verifier_and_prints_the_reply(
    capsys: pytest.CaptureFixture[str], bin_dir: Path
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="thinking\nPASS N01\n\n")
    assert call(capsys, "verifier", "copilot::claude-sonnet-5.5", LINE) == (0, "PASS N01\n", "")
    argv = recorded(log)["argv"]
    assert argv[0] == "-p" and "Follow .planzilla/roles/verifier.md" in argv[1]
    assert LINE in argv[1]
    assert "-s" in argv
    assert argv[argv.index("--model") + 1] == "claude-sonnet-5.5"
    assert "--available-tools=bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep" in argv
    assert "--deny-tool=write,shell(git push),shell(git commit)" in argv
    assert not any(a.startswith("--allow-all") for a in argv)
    assert "--allow-all-paths" not in argv and "--reasoning-effort" not in argv


@pytest.fixture
def gh_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated gh data dir (XDG_DATA_HOME), empty: gh has downloaded no Copilot CLI."""
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    return data


def download_copilot(data: Path) -> None:
    (data / "gh" / "copilot").mkdir(parents=True)
    (data / "gh" / "copilot" / "copilot").write_text("binary")


def test_gh_fallback_runs_gh_copilot_double_dash(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, gh_data: Path
) -> None:
    download_copilot(gh_data)
    log = make_exe(bin_dir, "gh", stdout="PASS N01\n")
    assert call(capsys, "executor", "copilot::claude-sonnet-5.5", LINE) == (0, "PASS N01\n", "")
    assert recorded(log)["argv"][:3] == ["copilot", "--", "-p"]


def test_copilot_binary_wins_over_gh(capsys: pytest.CaptureFixture[str], bin_dir: Path) -> None:
    copilot = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    gh = make_exe(bin_dir, "gh", stdout="WRONG\n")
    assert call(capsys, "executor", "copilot", LINE) == (0, "PASS N01\n", "")
    assert copilot.exists() and not gh.exists()


def test_neither_copilot_nor_gh_exits_3(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, gh_data: Path
) -> None:
    code, out, err = call(capsys, "executor", "copilot", LINE)
    assert (code, out) == (3, "")
    assert err == (
        "error: copilot not found on PATH (nor a Copilot CLI already downloaded by gh)\n"
    )


def test_gh_without_a_downloaded_copilot_is_never_run_because_it_would_install(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, gh_data: Path
) -> None:
    log = make_exe(bin_dir, "gh", stdout="PASS N01\n")
    code, out, err = call(capsys, "executor", "copilot::claude-sonnet-5.5", LINE)
    assert (code, out) == (3, "") and "downloaded by gh" in err
    assert not log.exists()


def test_bare_copilot_omits_the_model_flag(
    capsys: pytest.CaptureFixture[str], bin_dir: Path
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    assert call(capsys, "executor", "copilot", LINE)[0] == 0
    assert "--model" not in recorded(log)["argv"]


def test_pinned_effort_adds_the_reasoning_effort_flag(
    capsys: pytest.CaptureFixture[str], bin_dir: Path
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    assert call(capsys, "executor", "copilot::claude-sonnet-5.5@high", LINE)[0] == 0
    argv = recorded(log)["argv"]
    assert argv[argv.index("--reasoning-effort") + 1] == "high"
    assert argv[argv.index("--model") + 1] == "claude-sonnet-5.5"


@pytest.mark.parametrize("token", ["copilot@high", "copilot::copilot@low", "copilot@minimal"])
def test_unenforceable_copilot_effort_exits_3_before_any_subprocess(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, token: str
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    code, out, err = call(capsys, "executor", token, LINE)
    assert (code, out) == (3, "") and "effort" in err and err.count("\n") == 1
    assert not log.exists()


@pytest.mark.parametrize("token", ["copilot::opus", "copilot::sonnet@high", "copilot::haiku"])
def test_qualified_copilot_alias_exits_3_with_no_call(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, token: str
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    code, out, err = call(capsys, "executor", token, LINE)
    assert (code, out) == (3, "") and "portable intent" in err
    assert "external Copilot unavailable" not in err
    assert not log.exists()


@pytest.mark.parametrize(
    ("entry", "hint"), [("copilot", "copilot login"), ("gh", "gh copilot -- login")]
)
def test_logged_out_copilot_exits_3_with_the_login_hint(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, gh_data: Path, entry: str, hint: str
) -> None:
    download_copilot(gh_data)
    make_exe(
        bin_dir,
        entry,
        stderr="Error: No authentication information found\nCopilot can be authenticated\n",
        code=1,
    )
    code, out, err = call(capsys, "executor", "copilot::claude-sonnet-5.5", LINE)
    assert (code, out) == (3, "")
    assert err == f"error: copilot is not logged in; run {hint}\n"


def test_nonzero_copilot_exit_exits_3_with_the_last_stderr_line(
    capsys: pytest.CaptureFixture[str], bin_dir: Path
) -> None:
    make_exe(
        bin_dir, "copilot", stderr='Error: Model "x" from --model flag is not available.\n', code=1
    )
    code, out, err = call(capsys, "executor", "copilot::x", LINE)
    assert (code, out) == (3, "")
    assert err == 'error: copilot exited 1: Error: Model "x" from --model flag is not available.\n'


def test_empty_copilot_reply_exits_3(capsys: pytest.CaptureFixture[str], bin_dir: Path) -> None:
    make_exe(bin_dir, "copilot", stdout=" \n\n")
    assert call(capsys, "executor", "copilot", LINE) == (
        3,
        "",
        "error: copilot gave an empty reply\n",
    )


@pytest.mark.parametrize(
    ("role", "token", "line"),
    [
        ("visual", "copilot", LINE),
        ("executor", "copilot::gpt-6.1-sol@huge", LINE),
        ("executor", "copilot::", LINE),
        ("executor", "copilot", ""),
        ("executor", "copilot", "a\nb"),
    ],
)
def test_malformed_copilot_input_precedes_path_lookup(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    token: str,
    line: str,
) -> None:
    def no_path_lookup(name: str) -> None:
        pytest.fail("invalid input must fail before PATH lookup")

    monkeypatch.setattr(shutil, "which", no_path_lookup)
    code, out, err = call(capsys, role, token, line)
    assert code == 2 and out == "" and err.count("\n") == 1
    assert fake.calls == []


@pytest.mark.parametrize("token", ["opus", "sonnet"])
def test_resolved_cli_selection_enforces_exact_model_and_mapped_effort(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    token: str,
) -> None:
    selection = resolved_selection(token)
    assert run_module.run_selection("executor", selection, LINE) == 0
    assert capsys.readouterr().out == "PASS N01\n"
    argv = fake.calls[1][0]
    assert argv[:6] == [
        "codex",
        "exec",
        "-m",
        "gpt-6.1-sol",
        "-c",
        f'model_reasoning_effort="{selection.effort}"',
    ]
    assert selection.effort == {"opus": "high", "sonnet": "medium"}[token]
    assert token not in argv
    assert fake.out_dir is not None and not fake.out_dir.exists()


@pytest.mark.parametrize(
    ("token", "route", "prefix"),
    [
        (
            "codex::gpt-6.1-sol@high",
            "codex",
            ["codex", "exec", "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"'],
        ),
        (
            "codex::gpt-6.1-sol@medium",
            "codex",
            ["codex", "exec", "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="medium"'],
        ),
        (
            "claude::claude-sonnet-5@high",
            "claude",
            ["claude", "-p", "--model", "claude-sonnet-5", "--effort", "high"],
        ),
    ],
)
def test_explicit_pins_survive_direct_and_resolved_cli_execution(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    token: str,
    route: str,
    prefix: list[str],
) -> None:
    assert call(capsys, "executor", token, LINE) == (0, "PASS N01\n", "")
    assert fake.calls[1][0][:6] == prefix
    fake.calls.clear()
    assert run_module.run_selection("executor", resolved_selection(token, route), LINE) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("PASS N01\n", "")
    assert fake.calls[1][0][:6] == prefix


@pytest.mark.parametrize("token", ["copilot::claude-sonnet-5@high", "copilot::gpt-6.1-sol@high"])
def test_resolved_copilot_cli_selection_runs_through_the_fake_cli(
    capsys: pytest.CaptureFixture[str], bin_dir: Path, token: str
) -> None:
    log = make_exe(bin_dir, "copilot", stdout="PASS N01\n")
    selection = resolved_selection(token, "copilot")
    assert run_module.run_selection("executor", selection, LINE) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("PASS N01\n", "")
    argv = recorded(log)["argv"]
    assert argv[argv.index("--model") + 1] == selection.exact_id
    assert argv[argv.index("--reasoning-effort") + 1] == "high"


@pytest.mark.parametrize("route", ["codex", "copilot"])
def test_native_selection_is_handed_back_to_native_dispatch(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    route: str,
) -> None:
    token = "sonnet" if route == "copilot" else "opus"
    selection = resolved_selection(token, route, "native")
    assert run_module.run_selection("executor", selection, LINE) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and "native dispatch/handoff" in captured.err
    assert fake.calls == []


def test_unavailable_resolution_is_not_launched(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
) -> None:
    result = resolver.resolve(
        Policy(("codex",), {}),
        resolver.Request("executor", "sonnet"),
        resolver.Context("codex", "codex"),
        (),
    )
    assert isinstance(result, resolver.Unavailable)
    assert run_module.run_selection("executor", result, LINE) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and result.detail in captured.err
    assert fake.calls == []


@pytest.mark.parametrize(
    "changes",
    [{"mode": "unknown"}, {"route": "unknown"}, {"exact_id": "sonnet"}, {"exact_id": "codex"}],
)
def test_unsupported_or_unresolved_selection_never_launches(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    changes: dict[str, str],
) -> None:
    selection = replace(resolved_selection("opus"), **changes)
    assert run_module.run_selection("executor", selection, LINE) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.count("\n") == 1
    assert fake.calls == []


@pytest.mark.parametrize("token", ["codex::opus", "claude::sonnet@high"])
def test_unresolved_qualified_intent_is_handed_off_without_a_process(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
    token: str,
) -> None:
    code, out, err = call(capsys, "executor", token, LINE)
    assert code == 3 and out == "" and "resolve" in err and "portable intent" in err
    assert fake.calls == []


def test_resolved_command_boundary_validates_input_before_selection(
    capsys: pytest.CaptureFixture[str],
    fake: Fake,
) -> None:
    selection = resolved_selection("opus", mode="native")
    assert run_module.run_selection("executor", selection, "a\nb") == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "line break" in captured.err
    assert fake.calls == []
