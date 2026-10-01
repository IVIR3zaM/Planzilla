"""M and L plans get a preflight and a final check, S neither (L3, D26); L checks: just in time."""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
PLANNER = KIT / "roles" / "planner.md"
SINGLE = KIT / "templates" / "plan-single.md"
NODE = KIT / "templates" / "node.md"
SKILL = KIT / "skills" / "plz-new-plan" / "SKILL.md"
DOCS = Path(__file__).resolve().parents[2]
FORMAT = DOCS / "docs" / "FORMAT.md"
README = DOCS / "README.md"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def planner_preflight() -> str:
    """The planner's `M/L plans (L3)` entry: from its first line to the next unindented line."""
    lines = PLANNER.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("M/L plans"))
    rest = range(start + 1, len(lines))
    end = next((i for i in rest if not lines[i].startswith(" ")), len(lines))
    return "\n".join(lines[start:end])


def single_preflight() -> str:
    """The `## N01 preflight` section of plan-single.md, up to the next `## ` heading."""
    text = SINGLE.read_text(encoding="utf-8")
    return re.search(r"^## N01 preflight\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE).group(1)


SOURCES = [planner_preflight, single_preflight]


@pytest.mark.parametrize("source", SOURCES, ids=["planner", "plan-single"])
def test_preflight_names_auth_network_and_permissions(source: Callable[[], str]) -> None:
    text = flat(source())
    for word in ("auth", "network", "permission"):
        assert word in text, f"preflight text lacks {word}"


def test_single_preflight_criteria_are_cmd_placeholders() -> None:
    criteria = re.findall(r"^- C(\d+) \[cmd\]", single_preflight(), re.MULTILINE)
    assert [int(n) for n in criteria] == [1, 2, 3, 4]


@pytest.mark.parametrize("path", [PLANNER, SKILL], ids=["planner", "plz-new-plan"])
def test_l_check_nodes_just_in_time_and_gate_briefs_with_outline(path: Path) -> None:
    text = flat(path.read_text(encoding="utf-8"))
    assert "gate briefs" in text
    assert re.search(r"gate briefs[^.;]*outline|outline[^.;]*gate briefs", text)
    assert re.search(r"check nodes[^.;]*just in time|just in time[^.;]*check nodes", text)


def test_node_template_comment_says_l_check_nodes_just_in_time() -> None:
    text = flat(NODE.read_text(encoding="utf-8"))
    assert re.search(r"just in time[^.]*check nodes|check nodes[^.]*just in time", text)
    assert "gate briefs" in text


def section(path: Path, start: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    return text[text.index(start) : text.index(end)]


def single_comment() -> str:
    return re.search(r"<!--.*?-->", SINGLE.read_text(encoding="utf-8"), re.DOTALL).group(0)


S_RULE = [
    lambda: section(FORMAT, "## §1", "## §2"),
    lambda: section(README, "## Tiers", "## Config"),
    lambda: PLANNER.read_text(encoding="utf-8"),
    lambda: SKILL.read_text(encoding="utf-8"),
    single_comment,
]


@pytest.mark.parametrize(
    "source", S_RULE, ids=["format-s1", "readme-tiers", "planner", "plz-new-plan", "plan-single"]
)
def test_s_plan_has_no_preflight_and_no_final_check(source: Callable[[], str]) -> None:
    assert "no preflight and no final check" in flat(source())


@pytest.mark.parametrize("source", S_RULE[:3], ids=["format-s1", "readme-tiers", "planner"])
def test_m_and_l_plans_have_preflight_and_whole_plan_check(source: Callable[[], str]) -> None:
    text = flat(source())
    assert re.search(r"m(/| and )l[^.]*n01 preflight", text)
    assert "whole-plan check" in text


@pytest.mark.parametrize("source", [S_RULE[0], S_RULE[2]], ids=["format-s1", "planner"])
def test_final_check_runs_full_verify_and_executors_verify_fast(source: Callable[[], str]) -> None:
    text = flat(source())
    assert re.search(r"whole-plan check[^.]*first criterion[^.]*full `verify`", text)
    assert re.search(r"exec[^.]*`verify_fast`", text)


def test_format_section_8_names_final_check_and_exec_criteria() -> None:
    rows = {
        line.split("|")[1].strip(): flat(line)
        for line in section(FORMAT, "| key | values |", "## §9").splitlines()
        if line.startswith("| `")
    }
    assert "final check" in rows["`verify`"]
    assert "exec" in rows["`verify_fast`"]
