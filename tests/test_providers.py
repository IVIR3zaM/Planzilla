import pytest

from planzilla.providers import PROVIDERS, check_token, efforts_of, provider_of, split_token


@pytest.mark.parametrize(
    ("name", "provider"),
    [
        ("opus", "claude"),
        ("sonnet", "claude"),
        ("haiku", "claude"),
        ("fable", "claude"),
        ("claude-opus-4-7", "claude"),
        ("gpt-6.1-sol", "codex"),
        ("gemini-3", None),
        ("big", None),
        ("-", None),
    ],
)
def test_provider_of_a_name(name: str, provider: str | None) -> None:
    assert provider_of(name) == provider


def test_provider_effort_levels() -> None:
    assert PROVIDERS == ("claude", "codex")
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
        ("gemini-3", ("gemini-3", None)),
        ("-", ("-", None)),
    ],
)
def test_split_token_into_name_and_effort(token: str, parts: tuple[str, str | None]) -> None:
    assert split_token(token) == parts
    assert check_token(token) == token


@pytest.mark.parametrize(
    "token",
    ["sonnet@xhigh", "gpt-6-astra@huge", "gemini-3@high", "gpt-6-luna@", "Bad", "a b", "", "@high"],
)
def test_bad_effort_tokens_raise(token: str) -> None:
    with pytest.raises(ValueError):
        check_token(token)
