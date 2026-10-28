"""Kit skills plz-new-plan and plz-run-plan (FORMAT §11, §14)."""

import re
from pathlib import Path

import pytest

from planzilla import cli

SKILLS_DIR = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit" / "skills"
SKILLS = ["plz-new-plan", "plz-run-plan"]
AGENTS = {"plz-planner", "plz-executor", "plz-verifier", "plz-visual"}
RUN_ADAPTER = "plz-run"


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
    """D8: each shipped SKILL.md stays at most 80 lines."""
    assert len(skill_text(name).splitlines()) <= 80


@pytest.mark.parametrize("name", SKILLS)
def test_body_lines_fit_120_characters(name: str) -> None:
    """D8: every line after the front matter is at most 120 characters."""
    lines = skill_text(name).splitlines()
    body = lines[lines.index("---", 1) + 1 :]
    long = [line[:40] for line in body if len(line) > 120]
    assert not long, long


@pytest.mark.parametrize("name", SKILLS)
def test_only_plz_agent_and_skill_names(name: str) -> None:
    names = set(re.findall(r"\bplz-[a-z-]*[a-z]", skill_text(name)))
    allowed = AGENTS | {RUN_ADAPTER} | set(SKILLS)
    assert names <= allowed, names - allowed


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


def test_run_plan_uses_external_adapter_by_the_dispatch_rule() -> None:
    text = skill_text("plz-run-plan")
    assert re.search(r"\bplz-run\b(?!-)", text), "plz-run-plan must name the plz-run adapter"
    assert "plz run" in text
    assert "plz dispatch" in text


def test_run_plan_routes_by_the_actual_harness_instead_of_configured_harness() -> None:
    text = skill_text("plz-run-plan")
    assert "By the harness you actually run in, whatever config `harness` says" in text


def test_new_plan_checks_policy_before_allowed_auth_detection() -> None:
    text = skill_text("plz-new-plan")
    for word in (
        "claude auth status",
        "codex login status",
        "effective policy",
        "excluded providers",
    ):
        assert word in text
    assert text.index("effective policy") < text.index("claude auth status")


def test_new_plan_dispatches_the_planner_by_the_same_rule() -> None:
    assert "plz run" in skill_text("plz-new-plan")


def test_new_plan_never_stores_the_raw_prompt() -> None:
    text = skill_text("plz-new-plan")
    assert "request.md" not in text
    assert "intent.md" in text
    assert "## Intent" in text


def section_lines(name: str, heading: str) -> list[str]:
    text = skill_text(name).split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    return [line.strip() for line in text.splitlines()]


@pytest.mark.parametrize(
    "case",
    [
        "- `brief`:",
        "- `exec`:",
        "- `verify`:",
        "- `replan`:",
        "- `check`:",
        "- executor `DONE",
        "- executor `BLOCKED",
        "- verifier `PASS",
        "- verifier `FAIL",
        "- planner `BRIEFED",
        "- planner `ASK",
        "- Crash or malformed reply",
        "- `<id> D7:",
        "- `<id> human C5:",
        "- `<id> gate:",
        "- `<id> blocked:",
    ],
)
def test_run_plan_loop_lists_each_case_on_its_own_line(case: str) -> None:
    """D8: each Loop sub-case of steps 3-5 sits on its own `   - ` line."""
    text = skill_text("plz-run-plan").split("## Loop\n", 1)[1].split("\n## ", 1)[0]
    assert any(line.startswith("   " + case) for line in text.splitlines()), case


@pytest.mark.parametrize("tier", ["- S:", "- M:", "- L:"])
def test_new_plan_lists_each_tier_on_its_own_line(tier: str) -> None:
    lines = section_lines("plz-new-plan", "1. Clarify first, before any graph (req 6)")
    assert any(line.startswith(tier) for line in lines), tier


@pytest.mark.parametrize("name", SKILLS)
def test_numbered_steps_hold_no_inline_lists(name: str) -> None:
    """Readable steps: a list item never hides another one behind ` - ` or ` · ` inline."""
    body = skill_text(name).split("\n---\n", 1)[1]
    for line in body.splitlines():
        item = line.strip()[2:]
        assert " - `" not in item and "  · `" not in item, line
