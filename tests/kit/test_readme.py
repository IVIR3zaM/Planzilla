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


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = "`.planzilla/templates/capabilities.json`"
RULE = (
    "Claude Code, `<m>` is `opus`, `sonnet`, `haiku` or `fable` without `@<effort>`",
    "`plz-run`",
    "`plz run <role> <m> '<line>'` as a shell job",
    "`plz-visual` never goes through `plz run`",
    "`plz dispatch <plan> <role> '<line>' --actual-harness <h> --facts <file> --node <id>`",
    TEMPLATE,
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_readme_dispatch_leads_with_the_rule_then_plz_dispatch() -> None:
    text = _flat(_readme().split("### Dispatch and runner boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in RULE:
        assert phrase in text, phrase
    assert text.index(RULE[0]) < text.index("plz dispatch") < text.index("NativeAdapter")


def _format_section(number: int) -> str:
    text = (ROOT / "docs" / "FORMAT.md").read_text(encoding="utf-8")
    return text.split(f"## §{number} ", 1)[1].split("\n## §", 1)[0]


def test_format_14_leads_with_the_rule_then_plz_dispatch() -> None:
    text = _flat(_format_section(14))
    for phrase in RULE:
        assert phrase in text, phrase
    assert text.index(RULE[0]) < text.index("plz dispatch") < text.index("Capability resolution")


def test_format_11_lists_the_capabilities_template() -> None:
    assert "kit/templates/capabilities.json" in _format_section(11)


def test_format_11_adapters_lead_with_the_rule() -> None:
    text = _flat(_format_section(11))
    for phrase in (*RULE[:4], "`copilot::<id>[@<effort>]`", TEMPLATE):
        assert phrase in text, phrase
    assert text.index(RULE[0]) < text.index("Role prompts are plain")


def test_copilot_doc_gives_the_same_rule_and_advanced_path() -> None:
    text = _flat((ROOT / "docs" / "COPILOT.md").read_text(encoding="utf-8"))
    for phrase in RULE:
        assert phrase in text, phrase
    assert "`plz run <role> copilot::<model> '<line>'`" in text


def test_format_11_lists_the_copilot_profiles_install_writes() -> None:
    text = _format_section(11)
    assert "kit/agents/copilot/plz-planner.agent.md" in text
    assert "kit/templates/log.md" in text
    assert "| `.github/agents/plz-*.agent.md` | `kit/agents/copilot/` |" in text
    assert "`.github/agents/plz-*.agent.md`" in text.split("Rules:", 1)[1]


def test_release_steps_move_the_changelog_entries() -> None:
    release = _readme().split("## Releasing", 1)[1].split("\n## ", 1)[0]
    assert "CHANGELOG.md" in release
    assert "CHANGELOG.md" in _format_section(11)
