"""Shared pytest fixtures."""

import subprocess
import sys

import pytest


@pytest.fixture
def plz():
    """Run `python -m planzilla ARGS` and return the CompletedProcess."""

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "planzilla", *args],
            capture_output=True,
            text=True,
        )

    return run
