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


@pytest.mark.parametrize(
    ("token", "route", "name", "effort"),
    [
        ("copilot", "copilot", "copilot", None),
        ("copilot@high", "copilot", "copilot", "high"),
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


@pytest.mark.parametrize("route", ["copilot", "unknown"])
def test_unsupported_cli_never_falls_through_claude_helpers(route: str) -> None:
    with pytest.raises(ValueError, match="unavailable|unsupported"):
        runner.build_argv("executor", route, "gpt-6.1-sol", "high", "/repo", None)
    with pytest.raises(ValueError, match="unavailable|unsupported"):
        runner.login_argv(route)
    with pytest.raises(ValueError, match="unavailable|unsupported"):
        runner.logged_in(route, 0, '{"loggedIn": true}')
    with pytest.raises(ValueError, match="unavailable|unsupported"):
        runner.login_hint(route)
