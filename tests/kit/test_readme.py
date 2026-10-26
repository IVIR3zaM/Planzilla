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
    ):
        assert contract in text


def _readme() -> str:
    return (Path(__file__).resolve().parents[2] / "README.md").read_text()


def test_readme_describes_copilot_as_harness_and_delivery_route() -> None:
    text = _readme()
    assert "Copilot as a harness" in text
    assert "Copilot as a delivery route" in text
    assert "plz run <role> copilot::<model>" in text
    assert "gh copilot" in text
    assert "docs/COPILOT.md" in text
    assert "Copilot has no visual agent" in text


def test_readme_drops_stale_external_copilot_claims() -> None:
    text = _readme()
    for stale in (
        "external Copilot remains disabled",
        "External Copilot execution is disabled",
        "native Copilot delivery",
    ):
        assert stale not in text
