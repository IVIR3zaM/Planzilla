"""`planzilla.runner`: the pure core of `plz run` (validate, prompt, argv, reply)."""

import pytest

from planzilla import runner

CODEX_TAIL = [
    "-s",
    "workspace-write",
    "-c",
    "sandbox_workspace_write.network_access=true",
    "-C",
    "/repo",
    "-o",
    "/tmp/x/reply.txt",
    "-",
]
CLAUDE_TAIL = ["--output-format", "text", "--no-session-persistence"]


@pytest.mark.parametrize("role", ["planner", "executor", "verifier"])
def test_validate_accepts_the_three_roles(role):
    assert runner.validate(role, "gpt-6-luna", "Plan: p") == ("codex", "gpt-6-luna", None)


def test_validate_splits_provider_name_and_effort():
    assert runner.validate("executor", "haiku@low", "x") == ("claude", "haiku", "low")
    assert runner.validate("verifier", "gpt-6-luna@xhigh", "x") == ("codex", "gpt-6-luna", "xhigh")


@pytest.mark.parametrize(
    ("role", "model", "line"),
    [
        ("visual", "haiku", "x"),
        ("", "haiku", "x"),
        ("Planner", "haiku", "x"),
        ("verifier", "gemini-3", "x"),
        ("verifier", "sonnet@xhigh", "x"),
        ("planner", "gpt-6-luna@huge", "x"),
        ("planner", "haiku@", "x"),
        ("planner", "", "x"),
        ("planner", "haiku", ""),
        ("planner", "haiku", "   \t"),
        ("planner", "haiku", "a\nb"),
        ("planner", "haiku", "a\n"),
        ("planner", "haiku", "a\rb"),
    ],
)
def test_validate_rejects(role, model, line):
    with pytest.raises(ValueError):
        runner.validate(role, model, line)


def test_prompt_is_three_lines_each_ending_in_newline():
    assert runner.build_prompt("verifier", "Plan: p · Node: N01 · Try: 1") == (
        "Follow .planzilla/roles/verifier.md: read it first; it is your whole role.\n"
        "Input: Plan: p · Node: N01 · Try: 1\n"
        "Reply with exactly the one line that role names, nothing else.\n"
    )


def test_codex_argv_without_effort():
    assert runner.build_argv(
        "executor", "codex", "gpt-6-luna", None, "/repo", "/tmp/x/reply.txt"
    ) == [
        "codex",
        "exec",
        "-m",
        "gpt-6-luna",
        *CODEX_TAIL,
    ]


def test_codex_argv_with_effort_is_one_item():
    argv = runner.build_argv("planner", "codex", "gpt-6-luna", "low", "/repo", "/tmp/x/reply.txt")
    assert argv == [
        "codex",
        "exec",
        "-m",
        "gpt-6-luna",
        "-c",
        'model_reasoning_effort="low"',
        *CODEX_TAIL,
    ]


def test_bare_codex_argv_has_no_model_flag():
    assert runner.build_argv("executor", "codex", "codex", None, "/repo", "/tmp/x/reply.txt") == [
        "codex",
        "exec",
        *CODEX_TAIL,
    ]


def test_bare_codex_argv_with_effort_keeps_the_effort_flag():
    argv = runner.build_argv("verifier", "codex", "codex", "high", "/repo", "/tmp/x/reply.txt")
    assert argv == ["codex", "exec", "-c", 'model_reasoning_effort="high"', *CODEX_TAIL]


@pytest.mark.parametrize(
    ("role", "tools"),
    [
        ("planner", "Read,Grep,Glob,Write,Edit,Bash"),
        ("executor", "Read,Grep,Glob,Edit,Write,Bash"),
        ("verifier", "Read,Grep,Glob,Bash"),
    ],
)
def test_bare_claude_argv_has_no_model_flag(role, tools):
    argv = runner.build_argv(role, "claude", "claude", None, "/repo", None)
    assert argv == [
        "claude",
        "-p",
        *CLAUDE_TAIL,
        "--tools",
        tools,
        "--allowedTools",
        tools,
        "--permission-mode",
        "dontAsk",
    ]


def test_bare_claude_argv_with_effort_keeps_the_effort_flag():
    argv = runner.build_argv("planner", "claude", "claude", "low", "/repo", None)
    assert argv[:4] == ["claude", "-p", "--effort", "low"]
    assert "--model" not in argv


def test_validate_accepts_bare_tokens():
    assert runner.validate("verifier", "codex@low", "x") == ("codex", "codex", "low")
    assert runner.validate("verifier", "claude", "x") == ("claude", "claude", None)


@pytest.mark.parametrize(
    ("role", "tools"),
    [
        ("planner", "Read,Grep,Glob,Write,Edit,Bash"),
        ("executor", "Read,Grep,Glob,Edit,Write,Bash"),
        ("verifier", "Read,Grep,Glob,Bash"),
    ],
)
def test_claude_argv_without_effort(role, tools):
    argv = runner.build_argv(role, "claude", "haiku", None, "/repo", None)
    assert argv == [
        "claude",
        "-p",
        "--model",
        "haiku",
        *CLAUDE_TAIL,
        "--tools",
        tools,
        "--allowedTools",
        tools,
        "--permission-mode",
        "dontAsk",
    ]


def test_claude_argv_with_effort():
    argv = runner.build_argv("verifier", "claude", "sonnet", "high", "/repo", None)
    assert argv[:6] == ["claude", "-p", "--model", "sonnet", "--effort", "high"]
    assert argv[6:9] == CLAUDE_TAIL


@pytest.mark.parametrize("role", ["planner", "executor", "verifier"])
def test_claude_argv_has_no_bypass_flag(role):
    argv = runner.build_argv(role, "claude", "opus", "max", "/repo", None)
    assert not [a for a in argv if "bypass" in a.lower() or "skip" in a.lower()]


def test_login_argv():
    assert runner.login_argv("codex") == ["codex", "login", "status"]
    assert runner.login_argv("claude") == ["claude", "auth", "status"]


def test_codex_login_ok_is_the_exit_code():
    assert runner.logged_in("codex", 0, "") is True
    assert runner.logged_in("codex", 1, "") is False


@pytest.mark.parametrize(
    ("code", "out", "ok"),
    [
        (0, '{"loggedIn": true}', True),
        (0, '{"loggedIn": false}', False),
        (0, "{}", False),
        (0, "not json", False),
        (0, "[true]", False),
        (0, '{"loggedIn": "yes"}', False),
        (1, '{"loggedIn": true}', False),
    ],
)
def test_claude_login_needs_exit_0_and_logged_in_true(code, out, ok):
    assert runner.logged_in("claude", code, out) is ok


def test_login_hint():
    assert runner.login_hint("codex") == "codex is not logged in; run codex login"
    assert runner.login_hint("claude") == "claude is not logged in; run claude auth login"


@pytest.mark.parametrize(
    ("text", "last"),
    [
        ("", ""),
        ("  \n\n", ""),
        ("one", "one"),
        ("a\nb\n\n", "b"),
        ("a\n  PASS N01  \n \n", "PASS N01"),
    ],
)
def test_last_line(text, last):
    assert runner.last_line(text) == last


def test_exit_message_prefers_stderr_then_stdout():
    assert runner.exit_message("codex", 7, "o1\no2\n", "e1\ne2\n\n") == "codex exited 7: e2"
    assert runner.exit_message("claude", 1, "o1\no2\n", " \n") == "claude exited 1: o2"
    assert runner.exit_message("claude", 1, "", "") == "claude exited 1"


def test_signal_message_reports_only_observed_signal_and_detail() -> None:
    assert runner.exit_message("codex", -15, "out", "detail") == (
        "codex terminated by signal 15: detail"
    )
    assert runner.exit_message("claude login check", -9, "", "") == (
        "claude login check terminated by signal 9"
    )


@pytest.mark.parametrize(
    ("token", "route", "name", "effort"),
    [
        ("copilot", "copilot", "copilot", None),
        ("copilot::claude-sonnet-5@high", "copilot", "claude-sonnet-5", "high"),
        ("copilot::gpt-6.1-sol@high", "copilot", "gpt-6.1-sol", "high"),
        ("claude::claude-sonnet-5@high", "claude", "claude-sonnet-5", "high"),
        ("codex::gpt-6.1-sol@medium", "codex", "gpt-6.1-sol", "medium"),
    ],
)
def test_validate_preserves_explicit_delivery(
    token: str, route: str, name: str, effort: str | None
) -> None:
    assert runner.validate("executor", token, "x") == (route, name, effort)


@pytest.mark.parametrize("token", ["codex::opus", "claude::sonnet@high"])
def test_qualified_portable_intent_needs_resolution(token: str) -> None:
    with pytest.raises(ValueError, match="resolve.*portable intent"):
        runner.validate("executor", token, "x")


def test_unknown_cli_never_falls_through_claude_helpers() -> None:
    route = "unknown"
    with pytest.raises(ValueError, match="unsupported"):
        runner.build_argv("executor", route, "gpt-6.1-sol", "high", "/repo", None)
    with pytest.raises(ValueError, match="unsupported"):
        runner.login_argv(route)
    with pytest.raises(ValueError, match="unsupported"):
        runner.logged_in(route, 0, '{"loggedIn": true}')
    with pytest.raises(ValueError, match="unsupported"):
        runner.login_hint(route)


@pytest.mark.parametrize("token", ["copilot::opus", "copilot::sonnet@high", "copilot::haiku"])
def test_qualified_copilot_portable_intent_needs_resolution(token: str) -> None:
    with pytest.raises(runner.UnsupportedSelection, match="resolve.*portable intent"):
        runner.validate("executor", token, "x")


@pytest.mark.parametrize("token", ["copilot@high", "copilot::copilot@low", "copilot@minimal"])
def test_copilot_effort_the_cli_cannot_enforce_is_unsupported(token: str) -> None:
    with pytest.raises(runner.UnsupportedSelection, match="effort"):
        runner.validate("executor", token, "x")


def test_copilot_enforceable_effort_and_bare_default_validate() -> None:
    assert runner.validate("executor", "copilot", "x") == ("copilot", "copilot", None)
    assert runner.validate("executor", "copilot::auto", "x") == ("copilot", "auto", None)
    assert runner.validate("executor", "copilot::claude-sonnet-5@high", "x") == (
        "copilot",
        "claude-sonnet-5",
        "high",
    )


COPILOT_COMMON = ["-s", "--no-ask-user", "--no-auto-update"]
COPILOT_DISABLE = "--disable-builtin-mcps"
EDIT_TOOLS = "bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep,create,edit,apply_patch"
READ_TOOLS = "bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep"


def copilot_argv(role: str, name: str, effort: str | None, entry=("copilot",)) -> list[str]:
    prompt = runner.build_prompt(role, "Plan: p")
    return runner.build_argv(role, "copilot", name, effort, "/repo", None, entry, prompt)


def test_copilot_argv_has_prompt_model_effort_and_common_flags() -> None:
    argv = copilot_argv("executor", "claude-sonnet-5", "high")
    assert argv[:2] == ["copilot", "-p"]
    assert argv[2] == runner.build_prompt("executor", "Plan: p")
    assert argv[3:6] == COPILOT_COMMON
    assert argv[6:10] == ["--model", "claude-sonnet-5", "--reasoning-effort", "high"]


def test_bare_copilot_omits_model_and_effort_is_optional() -> None:
    argv = copilot_argv("planner", "copilot", None)
    assert "--model" not in argv and "--reasoning-effort" not in argv
    assert argv[3:6] == COPILOT_COMMON


def test_gh_route_prefixes_the_entrypoint() -> None:
    argv = copilot_argv("verifier", "copilot", None, ("gh", "copilot", "--"))
    assert argv[:4] == ["gh", "copilot", "--", "-p"]


@pytest.mark.parametrize(
    ("role", "tools", "allow", "deny"),
    [
        ("planner", EDIT_TOOLS, "read,write,shell", "shell(git push)"),
        ("executor", EDIT_TOOLS, "read,write,shell", "shell(git push),shell(git commit)"),
        ("verifier", READ_TOOLS, "read,shell", "write,shell(git push),shell(git commit)"),
    ],
)
def test_copilot_tool_flags_are_least_privilege_per_role(
    role: str, tools: str, allow: str, deny: str
) -> None:
    argv = copilot_argv(role, "copilot", None)
    assert argv[6:] == [
        f"--available-tools={tools}",
        f"--allow-tool={allow}",
        f"--deny-tool={deny}",
        COPILOT_DISABLE,
    ]
    for banned in (
        "--allow-all-paths",
        "--allow-all-tools",
        "--allow-all",
        "--yolo",
        "--allow-url",
    ):
        assert banned not in argv


def test_verifier_cannot_write_files() -> None:
    argv = copilot_argv("verifier", "copilot", None)
    available = next(a for a in argv if a.startswith("--available-tools="))
    assert not {"create", "edit", "apply_patch"} & set(available.split("=", 1)[1].split(","))
    assert "--deny-tool=write,shell(git push),shell(git commit)" in argv


def test_copilot_login_detection_and_hints() -> None:
    assert runner.copilot_logged_out(1, "Error: No authentication information found\nmore")
    assert not runner.copilot_logged_out(1, "Error: Model x is not available.")
    assert not runner.copilot_logged_out(0, "No authentication information found")
    assert runner.login_hint("copilot") == "copilot is not logged in; run copilot login"
    assert runner.login_hint("copilot", ("gh", "copilot", "--")) == (
        "copilot is not logged in; run gh copilot -- login"
    )
    with pytest.raises(ValueError, match="no separate login check"):
        runner.login_argv("copilot")


def test_copilot_entry_offers_gh_only_when_it_will_not_download() -> None:
    assert runner.copilot_entry(True, False) == ("copilot",)
    assert runner.copilot_entry(True, True) == ("copilot",)
    assert runner.copilot_entry(False, True) == ("gh", "copilot", "--")
    assert runner.copilot_entry(False, False) is None
