import pytest

from planzilla.providers import (
    HARNESSES,
    PROVIDERS,
    check_token,
    efforts_of,
    has_visual_agent,
    provider_of,
    runs_natively,
    split_token,
)


@pytest.mark.parametrize(
    ("name", "provider"),
    [
        ("opus", "claude"),
        ("sonnet", "claude"),
        ("haiku", "claude"),
        ("fable", "claude"),
        ("claude-opus-4-7", "claude"),
        ("gpt-6.1-sol", "codex"),
        ("claude", "claude"),
        ("codex", "codex"),
        ("gemini-3", None),
        ("big", None),
        ("-", None),
    ],
)
def test_provider_of_a_name(name: str, provider: str | None) -> None:
    assert provider_of(name) == provider


def test_provider_effort_levels() -> None:
    assert PROVIDERS == ("claude", "codex", "copilot")
    assert efforts_of("claude") == ("low", "medium", "high", "max")
    assert efforts_of("codex") == ("low", "medium", "high", "xhigh", "max")


@pytest.mark.parametrize(
    ("token", "parts"),
    [
        ("gpt-6.1-sol@high", ("gpt-6.1-sol", "high")),
        ("sonnet@max", ("sonnet", "max")),
        ("claude-opus-4-7@low", ("claude-opus-4-7", "low")),
        ("gpt-6-astra@xhigh", ("gpt-6-astra", "xhigh")),
        ("gpt-6-luna", ("gpt-6-luna", None)),
        ("codex", ("codex", None)),
        ("claude", ("claude", None)),
        ("codex@xhigh", ("codex", "xhigh")),
        ("claude@max", ("claude", "max")),
        ("gemini-3", ("gemini-3", None)),
        ("-", ("-", None)),
    ],
)
def test_split_token_into_name_and_effort(token: str, parts: tuple[str, str | None]) -> None:
    assert split_token(token) == parts
    assert check_token(token) == token


@pytest.mark.parametrize(
    "token",
    [
        "sonnet@xhigh",
        "codex@huge",
        "claude@xhigh",
        "gpt-6-astra@huge",
        "gemini-3@high",
        "gpt-6-luna@",
        "Bad",
        "a b",
        "",
        "@high",
    ],
)
def test_bad_effort_tokens_raise(token: str) -> None:
    with pytest.raises(ValueError):
        check_token(token)


def test_harness_facts() -> None:
    assert HARNESSES == ("claude-code", "codex", "copilot")
    assert has_visual_agent("claude-code") is True
    assert has_visual_agent("codex") is False
    assert has_visual_agent("copilot") is False


@pytest.mark.parametrize(
    ("harness", "token", "native"),
    [
        ("claude-code", "opus", True),
        ("claude-code", "sonnet", True),
        ("claude-code", "haiku", True),
        ("claude-code", "fable", True),
        ("claude-code", "sonnet@high", False),
        ("claude-code", "claude", False),
        ("claude-code", "codex@high", False),
        ("claude-code", "gpt-5.5", False),
        ("codex", "sonnet", False),
        ("codex", "codex", False),
        ("codex", "gpt-5.5", False),
    ],
)
def test_runs_natively(harness: str, token: str, native: bool) -> None:
    assert runs_natively(harness, token) is native


@pytest.mark.parametrize(
    "token",
    [
        "claude::opus",
        "copilot::opus",
        "claude::claude-sonnet-5@high",
        "copilot::claude-sonnet-5@high",
        "codex::gpt-5.6-sol@medium",
        "copilot::gpt-5.6-sol@high",
        "gpt-6.1-sol@medium",
        "gpt-6.1-sol@high",
    ],
)
def test_qualified_tokens_keep_their_pins(token: str) -> None:
    assert check_token(token) == token
    assert split_token(token) == split_token(token.split("::")[-1])


@pytest.mark.parametrize(
    "token",
    [
        "other::opus",
        "::opus",
        "copilot::",
        "copilot:opus",
        "codex::claude::opus",
        "claude::gpt-5.6-sol",
        "codex::claude-sonnet-5",
        "copilot::-",
        "copilot::claude-sonnet-5@xhigh",
        "copilot::gpt-5.6-sol@huge",
    ],
)
def test_malformed_or_incompatible_qualifiers_raise(token: str) -> None:
    with pytest.raises(ValueError):
        check_token(token)


def test_route_identity_is_independent_of_family() -> None:
    from planzilla.providers import route_of

    assert route_of("opus") is None
    assert route_of("claude-sonnet-5") is None
    assert route_of("gpt-5.6-sol@high") is None
    assert route_of("claude::opus") == "claude"
    assert route_of("copilot::opus") == "copilot"
    assert route_of("copilot::gpt-5.6-sol@high") == "copilot"
    assert route_of("codex@high") == "codex"


def test_copilot_parsing_is_not_capability_evidence() -> None:
    assert not runs_natively("copilot", "copilot::opus")


def test_portable_intent_and_route_pins_have_different_constraints() -> None:
    from planzilla.providers import allowed_routes, check_allowed, route_of

    assert allowed_routes("opus") == PROVIDERS
    assert allowed_routes("opus@high") == PROVIDERS
    assert split_token("opus@high") == ("opus", "high")
    assert allowed_routes("claude::opus") == ("claude",)
    assert allowed_routes("copilot::opus") == ("copilot",)
    assert allowed_routes("claude-sonnet-5") == ("claude", "copilot")
    assert allowed_routes("gpt-5.6-sol@high") == ("codex", "copilot")
    check_allowed("opus", ("codex",))
    with pytest.raises(ValueError, match="provider claude is not in providers"):
        check_allowed("claude::opus", ("codex", "copilot"))
    # The same family can carry different route constraints; quota identity is not inferred.
    assert route_of("claude::opus") != route_of("copilot::opus")
