"""Run one agent step on a model: `run <role> <model> <line>` prints the agent's one-line reply."""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from planzilla import runner
from planzilla.commands._common import fail
from planzilla.resolver import Selection, Unavailable


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("role", help="planner, executor or verifier")
    parser.add_argument("model", help="model token [<route>::]<name>[@<effort>]")
    parser.add_argument("line", help="the one-line input, e.g. 'Plan: p · Node: N01 · Try: 1'")


def _call(
    argv: list[str], cli: str, cwd: str, phase: str, prompt: str | None = None
) -> subprocess.CompletedProcess[str] | None:
    """Capture a completed child or report the observed failure to launch this phase."""
    try:
        return subprocess.run(
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            errors="replace",
            cwd=cwd,
        )
    except OSError as error:
        missing = isinstance(error, FileNotFoundError) and error.filename != cwd
        fail(runner.launch_message(cli, phase, missing, str(error)), 3)
        return None


def run(args: argparse.Namespace) -> int:
    try:
        cli, name, effort = runner.validate(args.role, args.model, args.line)
    except runner.UnsupportedSelection as error:
        return fail(str(error), 3)
    except ValueError as error:
        return fail(str(error), 2)
    return _run(args.role, cli, name, effort, args.line)


def run_selection(
    role: str, selection: Selection | Unavailable, line: str, cwd: str | None = None
) -> int:
    """Execute a caller's resolved CLI selection using the same argv/reply lifecycle as `run`."""
    try:
        cli, name, effort = runner.validate_selection(role, selection, line)
    except runner.UnsupportedSelection as error:
        return fail(str(error), 3)
    except ValueError as error:
        return fail(str(error), 2)
    return _run(role, cli, name, effort, line, cwd)


def _run(
    role: str, cli: str, name: str, effort: str | None, line: str, cwd: str | None = None
) -> int:
    try:
        runner.require_cli(cli)
    except runner.UnsupportedSelection as error:
        return fail(str(error), 3)
    if shutil.which(cli) is None:
        return fail(f"{cli} not found on PATH", 3)
    cwd = cwd if cwd is not None else str(Path.cwd())
    login = _call(runner.login_argv(cli), cli, cwd, "login check")
    if login is None:
        return 3
    if not runner.logged_in(cli, login.returncode, login.stdout):
        return fail(
            runner.login_failure_message(cli, login.returncode, login.stdout, login.stderr), 3
        )

    prompt = runner.build_prompt(role, line)
    out_dir = tempfile.mkdtemp(prefix="plz-run-") if cli == "codex" else None
    try:
        out_file = str(Path(out_dir) / "reply.txt") if out_dir else None
        argv = runner.build_argv(role, cli, name, effort, cwd, out_file)
        result = _call(argv, cli, cwd, "execution", prompt)
        if result is None:
            return 3
        if result.returncode != 0:
            return fail(
                runner.exit_message(cli, result.returncode, result.stdout, result.stderr), 3
            )
        if out_file is None:
            text = result.stdout
        else:
            try:
                text = Path(out_file).read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                return fail(runner.reply_read_message(cli, str(error)), 3)
    finally:
        if out_dir:
            shutil.rmtree(out_dir, ignore_errors=True)
    reply = runner.last_line(text)
    if not reply:
        return fail(f"{cli} gave an empty reply", 3)
    print(reply)
    return 0
