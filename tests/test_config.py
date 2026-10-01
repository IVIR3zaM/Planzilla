from pathlib import Path

import pytest

from planzilla.config import Config, load_config, parse_config
from planzilla.plan import PlanError

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "plans" / "repo"


def write_config(repo: Path, text: str) -> Path:
    (repo / ".plan").mkdir(parents=True, exist_ok=True)
    path = repo / ".plan" / "config.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_file_gives_all_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config == Config()
    assert config.verify == ""
    assert config.verify_fast == ""
    assert config.commit == "per-node"
    assert config.push == "none"
    assert config.retention == "keep"
    assert config.visual_recipe == ""
    assert config.models == {"planner": "opus", "exec": "sonnet", "verify": "sonnet"}
    assert config.preauthorized == []
    assert config.always_review is False
    assert config.commit_trailer == ""


def test_every_key_from_fixture() -> None:
    config = load_config(FIXTURE_REPO)
    assert config.verify == "uv run pytest -q"
    assert config.verify_fast == "uv run pytest -q -x"
    assert config.commit == "none"
    assert config.push == "per-node"  # `yes` is an alias
    assert config.retention == "prune-logs"
    assert config.visual_recipe == "uv run demo serve, open http://127.0.0.1:8000/"
    assert config.models == {"planner": "opus", "exec": "haiku", "verify": "sonnet"}
    assert config.preauthorized == ["git push to the current branch", "pip install uv"]
    assert config.always_review is True
    assert config.commit_trailer == "Co-Authored-By: Bot <bot@example.com>\nSigned-off-by: Demo"


def test_verify_fast_defaults_to_verify() -> None:
    config = parse_config("verify: make test\n", "config.md")
    assert config.verify_fast == "make test"


def test_models_subset_keeps_other_defaults() -> None:
    config = parse_config("models: exec=haiku\n", "config.md")
    assert config.models == {"planner": "opus", "exec": "haiku", "verify": "sonnet"}


@pytest.mark.parametrize(
    ("text", "value"),
    [("push: no\n", "none"), ("push: per-node\n", "per-node"), ("push: none\n", "none")],
)
def test_push_aliases(text: str, value: str) -> None:
    assert parse_config(text, "config.md").push == value


@pytest.mark.parametrize("value", ["keep", "prune-logs", "delete", "branch-only"])
def test_retention_values(value: str) -> None:
    assert parse_config(f"retention: {value}\n", "config.md").retention == value


def test_comments_and_blank_lines_are_ignored() -> None:
    config = parse_config("# a comment\n\ncommit: none\n", "config.md")
    assert config.commit == "none"


def test_unknown_key_raises_with_file_and_line(tmp_path: Path) -> None:
    path = write_config(tmp_path, "verify: make\ncolour: blue\n")
    with pytest.raises(PlanError) as err:
        load_config(tmp_path)
    assert err.value.file == path
    assert err.value.line == 2
    assert "unknown config key: colour" in str(err.value)


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("verify: a\nverify: b\n", 2),
        ("just some prose\n", 1),
        ("commit: sometimes\n", 1),
        ("push: maybe\n", 1),
        ("retention: forever\n", 1),
        ("always_review: perhaps\n", 1),
        ("models: writer=opus\n", 1),
        ("models: exec\n", 1),
    ],
)
def test_bad_lines_raise(tmp_path: Path, text: str, line: int) -> None:
    path = write_config(tmp_path, text)
    with pytest.raises(PlanError) as err:
        load_config(tmp_path)
    assert (err.value.file, err.value.line) == (path, line)
