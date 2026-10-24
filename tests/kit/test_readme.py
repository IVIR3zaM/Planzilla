"""Public guidance must distinguish syntax, policy and demonstrated delivery."""

from pathlib import Path


def test_readme_dispatch_does_not_infer_tools_from_model_or_harness() -> None:
    text = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    for stale in (
        "Codex runs nothing natively",
        "Because Codex has no visual agent",
        "The name decides the provider",
        "Every other model (a `codex` or `gpt-` name",
        "Claude Code only, see below",
    ):
        assert stale not in text
    for contract in (
        "actual callable",
        "planzilla.commands.dispatch.dispatch",
        "independent exact ID, effort and route pins",
        "external Copilot remains disabled",
    ):
        assert contract in text
