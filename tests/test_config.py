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


def test_providers_default_and_fixture() -> None:
    assert parse_config("", "c").providers == ("claude",)
    assert load_config(FIXTURE_REPO).providers == ("claude", "codex")
    assert parse_config("providers: claude, codex\n", "c").providers == ("claude", "codex")
    assert parse_config("providers: codex\n", "c").providers == ("codex",)


@pytest.mark.parametrize(
    "text",
    ["providers: openai\n", "providers:\n", "providers: claude, claude\n", "providers: claude,\n"],
)
def test_bad_providers_raise(text: str) -> None:
    with pytest.raises(PlanError) as err:
        parse_config(text, "c")
    assert err.value.line == 1


@pytest.mark.parametrize(
    "text",
    [
        "models: planner=gpt-6.1-sol\n",
        "models: planner=gpt-6.1-sol\nproviders: claude\n",
        "providers: claude\nmodels: planner=gpt-6.1-sol\n",
    ],
)
def test_models_provider_must_be_listed_in_either_order(text: str) -> None:
    with pytest.raises(PlanError) as err:
        parse_config(text, "c")
    assert "models" in str(err.value)
    assert err.value.line == [x.split(":")[0] for x in text.split("\n")].index("models") + 1


def test_models_provider_listed_in_either_order() -> None:
    for text in (
        "models: planner=gpt-6.1-sol@high\nproviders: claude, codex\n",
        "providers: claude, codex\nmodels: planner=gpt-6.1-sol@high\n",
    ):
        assert parse_config(text, "c").models["planner"] == "gpt-6.1-sol@high"


def test_models_effort_and_unknown_provider_tokens() -> None:
    assert parse_config("models: exec=sonnet@max\n", "c").models["exec"] == "sonnet@max"
    assert parse_config("models: exec=gemini-3\n", "c").models["exec"] == "gemini-3"
    for bad in ("sonnet@xhigh", "gemini-3@high", "gpt-6-luna@"):
        with pytest.raises(PlanError):
            parse_config(f"providers: claude, codex\nmodels: exec={bad}\n", "c")


def test_harness_default_and_values() -> None:
    assert parse_config("", "c").harness == "claude-code"
    assert parse_config("harness: codex\n", "c").harness == "codex"
    assert parse_config("harness: claude-code\n", "c").harness == "claude-code"
    assert load_config(FIXTURE_REPO).harness == "claude-code"


def test_bad_harness_is_the_choice_error() -> None:
    with pytest.raises(PlanError) as err:
        parse_config("commit: none\nharness: cursor\n", "c")
    assert err.value.line == 2
    assert err.value.message == (
        "bad harness value 'cursor': expected one of claude-code, codex, copilot"
    )


def test_portable_opus_with_codex_only_policy() -> None:
    config = parse_config("models: planner=opus\nproviders: codex\n", "c")
    assert config.models["planner"] == "opus"


def test_copilot_accepts_overlapping_exact_model_families() -> None:
    config = parse_config(
        "models: planner=copilot::claude-sonnet-5@high, exec=copilot::gpt-5.6-sol@medium\n"
        "providers: copilot\nharness: copilot\n",
        "c",
    )
    assert config.providers == ("copilot",)
    assert config.models["exec"] == "copilot::gpt-5.6-sol@medium"


@pytest.mark.parametrize("reverse", [False, True])
def test_explicit_route_restrictions_are_order_independent(reverse: bool) -> None:
    lines = ["models: planner=claude::opus", "providers: codex, copilot"]
    if reverse:
        lines.reverse()
    with pytest.raises(PlanError) as error:
        parse_config("\n".join(lines), "policy.md")
    assert error.value.line == lines.index("models: planner=claude::opus") + 1
    assert "provider claude is not in providers" in error.value.message


@pytest.mark.parametrize("value", ["", "exec=opus, exec=sonnet", "writer=opus", "exec=Bad"])
def test_models_reject_empty_duplicate_unknown_and_bad_tokens(value: str) -> None:
    with pytest.raises(PlanError):
        parse_config(f"models: {value}\n", "c")


@pytest.mark.parametrize(
    "token",
    [
        "opus",
        "opus@high",
        "codex::opus",
        "copilot::opus",
        "claude::claude-sonnet-5@high",
        "copilot::claude-sonnet-5@high",
        "codex::gpt-5.6-sol@medium",
        "copilot::gpt-5.6-sol@medium",
    ],
)
def test_config_graph_and_set_share_token_acceptance(token: str) -> None:
    from planzilla import state
    from tests.test_plan import policy_plan

    config = parse_config(f"providers: claude, codex, copilot\nmodels: exec={token}\n", "config.md")
    plan = policy_plan(model=f"{token}/-")
    nodes, _ = state.set_node(plan.nodes, "N01", None, model=f"{token}/-", facts={}, budgets=(2, 2))
    assert config.models["exec"] == plan.nodes[0].exec_model == nodes[0].exec_model == token
