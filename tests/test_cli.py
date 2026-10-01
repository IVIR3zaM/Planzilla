import importlib
import inspect
import subprocess
import sys

import pytest

from planzilla import cli

COMMANDS = [
    "install",
    "next",
    "set",
    "resume",
    "brief",
    "log",
    "check",
    "commit",
    "status",
    "stats",
    "lint",
    "serve",
]


def test_help_lists_all_commands(plz):
    result = plz("--help")
    assert result.returncode == 0
    for name in COMMANDS:
        assert name in result.stdout


def test_version(plz):
    result = plz("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "planzilla 0.1.0"


def test_command_order_matches_format():
    from planzilla import cli

    assert list(cli.COMMANDS) == COMMANDS


def _stub_commands():
    """Names in cli.COMMANDS whose module `run` still prints `not implemented:`."""
    return [
        name
        for name in cli.COMMANDS
        if "not implemented:"
        in inspect.getsource(importlib.import_module(f"planzilla.commands.{name}").run)
    ]


@pytest.mark.parametrize("name", _stub_commands())
def test_stub_exits_2(tmp_path, name):
    result = subprocess.run(
        [sys.executable, "-m", "planzilla", name],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert f"not implemented: {name}" in result.stderr
    assert result.stdout == ""
