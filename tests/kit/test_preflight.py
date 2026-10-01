"""Every tier gets a real preflight (L3); L check nodes are briefed just in time (L2)."""

import re
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
PLANNER = KIT / "roles" / "planner.md"
SINGLE = KIT / "templates" / "plan-single.md"
NODE = KIT / "templates" / "node.md"
SKILL = KIT / "skills" / "plz-new-plan" / "SKILL.md"


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def planner_preflight() -> str:
    """The planner's `Every plan (L3)` entry: from its first line to the next unindented line."""
    lines = PLANNER.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Every plan"))
    rest = range(start + 1, len(lines))
    end = next((i for i in rest if not lines[i].startswith(" ")), len(lines))
    return "\n".join(lines[start:end])


def single_preflight() -> str:
    """The `## N01 preflight` section of plan-single.md, up to the next `## ` heading."""
    text = SINGLE.read_text(encoding="utf-8")
    return re.search(r"^## N01 preflight\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE).group(1)


SOURCES = [planner_preflight, single_preflight]


@pytest.mark.parametrize("source", SOURCES, ids=["planner", "plan-single"])
def test_preflight_names_auth_network_and_permissions(source) -> None:
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
