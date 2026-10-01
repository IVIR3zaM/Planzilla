"""Kit skills plz-new-plan and plz-run-plan (FORMAT §11, §14)."""

import re
from pathlib import Path

import pytest

from planzilla import cli

SKILLS_DIR = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit" / "skills"
SKILLS = ["plz-new-plan", "plz-run-plan"]
AGENTS = {"plz-planner", "plz-executor", "plz-verifier", "plz-visual"}


def skill_text(name: str) -> str:
    return (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---", "SKILL.md must start with front matter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_exactly_the_two_skills_ship() -> None:
    assert sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir()) == SKILLS


@pytest.mark.parametrize("name", SKILLS)
def test_name_matches_directory_and_description_is_set(name: str) -> None:
    fields = frontmatter(skill_text(name))
    assert fields.get("name") == name
    assert fields.get("description")


@pytest.mark.parametrize("name", SKILLS)
def test_every_plz_command_is_registered(name: str) -> None:
    mentioned = set(re.findall(r"\bplz ([a-z][a-z-]*)", skill_text(name)))
    assert mentioned, "a skill must call the CLI"
    assert mentioned <= set(cli.COMMANDS), mentioned - set(cli.COMMANDS)


@pytest.mark.parametrize("name", SKILLS)
def test_at_most_80_lines(name: str) -> None:
    assert len(skill_text(name).splitlines()) <= 80


@pytest.mark.parametrize("name", SKILLS)
def test_only_plz_agent_and_skill_names(name: str) -> None:
    names = set(re.findall(r"\bplz-[a-z-]*[a-z]", skill_text(name)))
    assert names <= AGENTS | set(SKILLS), names - AGENTS - set(SKILLS)


@pytest.mark.parametrize("name", SKILLS)
def test_cli_resolved_as_vendored_launcher_first(name: str) -> None:
    text = skill_text(name)
    assert ".planzilla/plz" in text
    assert "`planzilla`" in text


def test_run_plan_never_names_plan_files() -> None:
    text = skill_text("plz-run-plan")
    for path in ("plan.md", "nodes/", "log/", "intent.md", "git diff"):
        assert path not in text


def test_run_plan_dispatches_every_agent() -> None:
    text = skill_text("plz-run-plan")
    for agent in AGENTS:
        assert agent in text


def test_new_plan_never_stores_the_raw_prompt() -> None:
    text = skill_text("plz-new-plan")
    assert "request.md" not in text
    assert "intent.md" in text
    assert "## Intent" in text
