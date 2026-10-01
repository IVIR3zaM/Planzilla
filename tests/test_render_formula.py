"""Tests for release/render_formula.py."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "render_formula", ROOT / "release" / "render_formula.py"
)
render_formula = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_formula)

VERSION = "9.8.7"
URL = "https://example.invalid/releases/download/v9.8.7/planzilla-9.8.7.tar.gz"
SHA = "a1" * 32


def render() -> str:
    return render_formula.render(VERSION, URL, SHA)


def test_each_value_once_in_right_stanza():
    out = render()
    assert out.count(f'url "{URL}"') == 1
    assert out.count(f'sha256 "{SHA}"') == 1
    assert out.count(f'version "{VERSION}"') == 1
    assert out.count(URL) == 1
    assert out.count(SHA) == 1


def test_no_unreplaced_placeholder():
    assert not re.search(r"@[A-Z0-9_]+@|\{\{|\$\{", render())


def test_formula_shape():
    out = render()
    assert "class Planzilla < Formula" in out
    assert "Language::Python::Virtualenv" in out
    assert "test do" in out
    assert "--version" in out


def test_main_prints_formula(capsys):
    assert render_formula.main(["1.2.3", "https://x.invalid/p.tar.gz", "b" * 64]) == 0
    assert 'sha256 "bbbb' in capsys.readouterr().out


def test_main_rejects_bad_args(capsys):
    assert render_formula.main(["1.2.3"]) == 2
    assert render_formula.main(["1.2.3", "https://x.invalid/p.tar.gz", "nothex"]) == 2
