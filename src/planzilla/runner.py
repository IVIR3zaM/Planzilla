"""Pure core of `plz run`: validate the input, build the prompt and argv, pick the reply."""

import json

from planzilla.providers import PORTABLE_ALIASES, PROVIDERS, provider_of, route_of, split_token
from planzilla.resolver import Selection, Unavailable

ROLES = ("planner", "executor", "verifier")
_CLAUDE_TOOLS = {
    "planner": "Read,Grep,Glob,Write,Edit,Bash",
    "executor": "Read,Grep,Glob,Edit,Write,Bash",
    "verifier": "Read,Grep,Glob,Bash",
}
_LOGIN_HINT = {"codex": "codex login", "claude": "claude auth login"}


class UnsupportedSelection(ValueError):
    """Valid input requiring a supported delivery or a dispatch handoff (exit 3)."""


def validate_input(role: str, line: str) -> None:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}: expected {', '.join(ROLES)}")
    if not line.strip():
        raise ValueError("the input line is empty")
    if "".join(line.splitlines()) != line:
        raise ValueError("the input line holds a line break")


def validate(role: str, model: str, line: str) -> tuple[str, str, str | None]:
    """Preserve qualifiers; unqualified Claude/Codex callers keep legacy CLI behavior."""
    validate_input(role, line)
    name, effort = split_token(model)
    route = route_of(model)
    if "::" in model and name in PORTABLE_ALIASES and route != "copilot":
        raise UnsupportedSelection("resolve qualified portable intent before CLI dispatch/handoff")
    # Family classification is only the compatibility path for unqualified direct callers.
    provider = route or provider_of(name)
    if provider is None:
        raise ValueError(f"model {name!r} has no provider")
    return provider, name, effort


def require_cli(cli: str) -> None:
    """N02 did not demonstrate external Copilot; supplied mocks cannot enable it."""
    if cli == "copilot":
        raise UnsupportedSelection(
            "external Copilot unavailable: missing demonstrated entrypoint/reply evidence; "
            "use a supported delivery or native dispatch/handoff"
        )
    if cli not in ("claude", "codex"):
        raise UnsupportedSelection(f"unsupported CLI delivery {cli!r}; use dispatch/handoff")


def validate_selection(
    role: str, selection: Selection | Unavailable, line: str
) -> tuple[str, str, str | None]:
    """Consume a policy-resolved CLI tuple; policy/capability resolution stays with callers.

    Unlike legacy direct tokens, resolved requests always enforce the exact model and effort.
    Native selections remain usable by native dispatch even when this runner cannot launch them.
    """
    validate_input(role, line)
    if isinstance(selection, Unavailable):
        raise UnsupportedSelection(f"{selection.detail}; use dispatch/handoff")
    if selection.mode == "native":
        raise UnsupportedSelection(f"{selection.route} selection requires native dispatch/handoff")
    if selection.mode != "cli":
        raise UnsupportedSelection(f"unsupported delivery mode {selection.mode!r}")
    require_cli(selection.route)
    if selection.exact_id in (*PORTABLE_ALIASES, *PROVIDERS):
        raise UnsupportedSelection(
            "resolve portable intent/default to an exact model before dispatch"
        )
    return selection.route, selection.exact_id, selection.effort


def build_prompt(role: str, line: str) -> str:
    return (
        f"Follow .planzilla/roles/{role}.md: read it first; it is your whole role.\n"
        f"Input: {line}\n"
        "Reply with exactly the one line that role names, nothing else.\n"
    )


def build_argv(
    role: str, cli: str, name: str, effort: str | None, cwd: str, out_file: str | None
) -> list[str]:
    """The CLI call; codex needs `out_file` for its reply, claude replies on stdout.

    A bare token (`name == cli`) leaves the model flag out: the CLI picks its default model.
    """
    require_cli(cli)
    if cli == "codex":
        argv = ["codex", "exec"] + ([] if name == cli else ["-m", name])
        if effort is not None:
            argv += ["-c", f'model_reasoning_effort="{effort}"']
        return argv + [
            "-s",
            "workspace-write",
            "-c",
            "sandbox_workspace_write.network_access=true",
            "-C",
            cwd,
            "-o",
            str(out_file),
            "-",
        ]
    tools = _CLAUDE_TOOLS[role]
    argv = ["claude", "-p"] + ([] if name == cli else ["--model", name])
    if effort is not None:
        argv += ["--effort", effort]
    return argv + [
        "--output-format",
        "text",
        "--no-session-persistence",
        "--tools",
        tools,
        "--allowedTools",
        tools,
        "--permission-mode",
        "dontAsk",
    ]


def login_argv(cli: str) -> list[str]:
    require_cli(cli)
    return ["codex", "login", "status"] if cli == "codex" else ["claude", "auth", "status"]


def logged_in(cli: str, code: int, stdout: str) -> bool:
    """codex: exit 0. claude: exit 0 and stdout JSON with `loggedIn` true."""
    require_cli(cli)
    if code != 0:
        return False
    if cli == "codex":
        return True
    try:
        data = json.loads(stdout)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("loggedIn") is True


def login_hint(cli: str) -> str:
    require_cli(cli)
    return f"{cli} is not logged in; run {_LOGIN_HINT[cli]}"


def last_line(text: str) -> str:
    """The last non-blank line, stripped; empty when there is none."""
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def exit_message(cli: str, code: int, stdout: str, stderr: str) -> str:
    detail = last_line(stderr) or last_line(stdout)
    status = f"terminated by signal {-code}" if code < 0 else f"exited {code}"
    message = f"{cli} {status}"
    return f"{message}: {detail}" if detail else message


def login_failure_message(cli: str, code: int, stdout: str, stderr: str) -> str:
    """Failed status execution is not itself evidence that authentication is absent."""
    require_cli(cli)
    detail = last_line(stderr) or last_line(stdout)
    if code != 0:
        message = exit_message(f"{cli} login check", code, stdout, stderr)
        if cli == "codex" and code > 0 and detail.lower() == "not logged in":
            return f"{message}; {login_hint(cli)}"
        return message
    if cli == "claude":
        try:
            data = json.loads(stdout)
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("loggedIn") is False:
            return login_hint(cli)
    message = f"{cli} login check returned invalid authentication status"
    return f"{message}: {detail}" if detail else message


def launch_message(cli: str, phase: str, missing: bool, detail: str) -> str:
    if missing:
        return f"{cli} not found on PATH"
    message = f"{cli} {phase} launch failed"
    detail = last_line(detail)
    return f"{message}: {detail}" if detail else message


def reply_read_message(cli: str, detail: str) -> str:
    message = f"{cli} reply read failed"
    detail = last_line(detail)
    return f"{message}: {detail}" if detail else message
