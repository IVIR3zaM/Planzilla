"""The AGENTS.md block that install places between the markers (FORMAT §11)."""

import re
from pathlib import Path

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
BLOCK = (KIT / "AGENTS-block.md").read_text(encoding="utf-8")


def test_block_is_not_the_stub() -> None:
    assert not BLOCK.startswith("placeholder")


def test_block_is_short() -> None:
    assert 0 < len(BLOCK.splitlines()) <= 20


def test_block_holds_no_marker_text() -> None:
    assert "planzilla:begin" not in BLOCK
    assert "planzilla:end" not in BLOCK


def test_block_names_the_cli() -> None:
    assert ".planzilla/plz" in BLOCK


def test_block_names_both_skills_and_all_roles() -> None:
    assert "plz-new-plan" in BLOCK
    assert "plz-run-plan" in BLOCK
    for role in ("planner", "executor", "verifier", "visual"):
        assert f".planzilla/roles/{role}.md" in BLOCK


def test_named_roles_exist() -> None:
    roles = re.findall(r"\.planzilla/roles/([a-z]+)\.md", BLOCK)
    assert roles
    for role in roles:
        assert (KIT / "roles" / f"{role}.md").is_file()


def test_named_skills_exist() -> None:
    skills = set(re.findall(r"plz-[a-z]+(?:-[a-z]+)*", BLOCK))
    assert skills
    for skill in skills:
        assert (KIT / "skills" / skill / "SKILL.md").is_file()
