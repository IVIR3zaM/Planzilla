import pytest

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


@pytest.mark.parametrize("name", COMMANDS)
def test_stub_exits_2(plz, name):
    result = plz(name)
    assert result.returncode == 2
    assert f"not implemented: {name}" in result.stderr
    assert result.stdout == ""
