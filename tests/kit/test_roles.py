"""Kit roles, adapters and templates (FORMAT §11)."""

import re
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
ROLES = ["planner", "executor", "verifier", "visual"]
ADAPTERS = sorted((KIT / "agents" / "claude").glob("*.md"))
TEMPLATES = ["plan-single.md", "plan.md", "intent.md", "node.md", "log.md", "config.md"]


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---", "adapter must start with front matter"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_four_adapters_ship() -> None:
    assert [p.stem for p in ADAPTERS] == sorted(f"plz-{role}" for role in ROLES)


@pytest.mark.parametrize("path", ADAPTERS, ids=lambda p: p.name)
def test_adapter_frontmatter_and_role(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    fields = frontmatter(text)
    for key in ("name", "description", "tools", "model"):
        assert fields.get(key), f"{path.name}: missing {key}"
    assert fields["name"].startswith("plz-")
    assert fields["name"] == path.stem
    roles = re.findall(r"\.planzilla/roles/([a-z]+)\.md", text)
    assert roles, f"{path.name}: references no role"
    for role in roles:
        assert (KIT / "roles" / f"{role}.md").is_file()


@pytest.mark.parametrize("role", ROLES)
def test_role_is_at_most_30_lines(role: str) -> None:
    text = (KIT / "roles" / f"{role}.md").read_text(encoding="utf-8")
    assert not text.startswith("placeholder")
    assert len(text.rstrip("\n").splitlines()) <= 30


@pytest.mark.parametrize("name", TEMPLATES)
def test_template_ends_with_format_rules_comment(name: str) -> None:
    text = (KIT / "templates" / name).read_text(encoding="utf-8").rstrip()
    assert "Format rules" in text
    if name == "config.md":  # FORMAT §8: config lines are blank, `#` comments or `key: value`
        assert text.splitlines()[-1].startswith("#")
    else:
        assert text.endswith("-->")
