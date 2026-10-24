"""Copilot CLI profiles delegate behavior to the shared Planzilla roles."""

import json
import re
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
ROLES = ("planner", "executor", "verifier")


def test_exactly_three_copilot_profiles_ship() -> None:
    profiles = KIT / "agents" / "copilot"
    assert {p.relative_to(profiles).as_posix() for p in profiles.rglob("*") if p.is_file()} == {
        f"plz-{role}.agent.md" for role in ROLES
    }


@pytest.mark.parametrize("role", ROLES)
def test_copilot_profile_schema_tools_and_role_binding(role: str) -> None:
    path = KIT / "agents" / "copilot" / f"plz-{role}.agent.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    fields = dict(line.split(":", 1) for line in lines[1:end])
    fields = {key: value.strip() for key, value in fields.items()}
    assert set(fields) == {"name", "description", "tools", "include-custom-instructions"}
    assert fields["name"] == path.name.removesuffix(".agent.md") == f"plz-{role}"
    assert fields["description"]
    assert fields["include-custom-instructions"] == "true"
    tools = json.loads(fields["tools"])
    expected = {"read", "search", "execute"}
    if role != "verifier":
        expected.add("edit")
    assert set(tools) == expected
    assert len(tools) == len(expected)
    body = "\n".join(lines[end + 1 :])
    assert "Read `AGENTS.md`" in body
    assert re.findall(r"\.planzilla/roles/([a-z]+)\.md", body) == [role]
    assert (KIT / "roles" / f"{role}.md").is_file()
    assert "read it first; it is your whole role" in body
    assert len(body.splitlines()) <= 3  # Keep boundaries, logging and replies in the shared role.
    assert not re.search(r"claude|browser|playwright|model|effort|quota", body, re.IGNORECASE)
