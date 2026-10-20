"""Model providers: a name's provider and the effort levels it takes (pure)."""

import re

PROVIDERS = ("claude", "codex")
_EFFORTS = {
    "claude": ("low", "medium", "high", "max"),
    "codex": ("low", "medium", "high", "xhigh", "max"),
}
_CLAUDE_NAMES = ("opus", "sonnet", "haiku", "fable")
_TOKEN_RE = re.compile(r"([a-z0-9.-]+)(?:@([a-z]+))?")


def provider_of(name: str) -> str | None:
    """The provider of a model name (a bare provider token is its own), or None."""
    if name in PROVIDERS:
        return name
    if name in _CLAUDE_NAMES or name.startswith("claude-"):
        return "claude"
    if name.startswith("gpt-"):
        return "codex"
    return None


def efforts_of(provider: str) -> tuple[str, ...]:
    return _EFFORTS[provider]


def split_token(token: str) -> tuple[str, str | None]:
    """`name[@effort]` into (name, effort); an effort needs a provider name and its level."""
    match = _TOKEN_RE.fullmatch(token)
    if not match:
        raise ValueError(f"bad model token {token!r}: expected <name> or <name>@<effort>")
    name, effort = match.group(1), match.group(2)
    if effort is not None:
        provider = provider_of(name)
        if provider is None:
            raise ValueError(f"bad model token {token!r}: {name} takes no effort")
        if effort not in _EFFORTS[provider]:
            levels = ", ".join(_EFFORTS[provider])
            raise ValueError(f"bad model token {token!r}: {provider} efforts are {levels}")
    return name, effort


def check_token(token: str) -> str:
    """The one token check: return the token unchanged or raise ValueError."""
    split_token(token)
    return token
