"""Shipped dispatch instructions are capability guarded; all delivery facts are fixtures."""

import re
from pathlib import Path

import pytest

from planzilla.config import Policy
from planzilla.resolver import Capability, Context, Model, Request, Selection, resolve

KIT = Path(__file__).resolve().parents[2] / "src" / "planzilla" / "kit"
SKILLS = ("plz-new-plan", "plz-run-plan")


def read(relative: str) -> str:
    return (KIT / relative).read_text(encoding="utf-8")


def section(name: str, heading: str) -> str:
    text = read(f"skills/{name}/SKILL.md").split(f"## {heading}\n", 1)[1]
    return text.split("\n## ", 1)[0]


def require(text: str, *phrases: str) -> None:
    flat = re.sub(r"\s+", " ", text).lower()
    for phrase in phrases:
        assert phrase.lower() in flat, f"guidance lacks action/guard: {phrase}"


def test_both_workflows_use_the_identical_dispatch_contract() -> None:
    assert section(SKILLS[0], "Dispatch contract") == section(SKILLS[1], "Dispatch contract")


@pytest.mark.parametrize("name", SKILLS)
def test_actual_codex_configured_claude_uses_evidence_and_enforceable_pins(name: str) -> None:
    dispatch = section(name, "Dispatch contract")
    require(
        dispatch,
        "actual Codex/configured Claude",
        "surface the mismatch and reconcile through allowed proven controls",
        "configuration is not tool evidence",
        "Record original request, actual/configured harness and resolved model/effort/route",
        "exposed `model` and `reasoning_effort` accepting the exact values",
        'fork_turns: "none"',
        "Neither prompt text nor inherited defaults enforces a pin; never invent fields",
        "proven pin-preserving CLI with demonstrated entrypoint and usable reply",
        "one focused handoff naming operation, failed constraint, "
        "evidence and minimal alternatives",
    )


@pytest.mark.parametrize("name", SKILLS)
def test_restricted_plan_excludes_probes_before_selection(name: str) -> None:
    dispatch = section(name, "Dispatch contract")
    require(
        dispatch.splitlines()[1],
        "actual coordinator against optional plan `harnesses` first",
        "intersect delivery with effective `providers` before defaults, aliases, "
        "capability selection or auth probes",
        "Never probe excluded providers",
        "plan providers/models override repository defaults without widening either allowlist",
    )
    require(section(name, "Phase policy"), "Before", "Dispatch contract", "resume")


@pytest.mark.parametrize("name", SKILLS)
def test_native_only_copilot_does_not_enable_external_or_browser(name: str) -> None:
    require(
        section(name, "Dispatch contract"),
        "Copilot needs callable delegation, enforceable effective model/effort "
        "and repo-instruction inheritance",
        "profile precedence",
        "modelPolicy: required",
        "include-custom-instructions: true",
        "reasoningEffort",
        "session overrides and shadowing",
        "native-only route works without an external executable",
        "A catalog, executable, profile, mock or tool name proves no delivery",
        "external Copilot and browser remain disabled on the researched host until demonstrated",
        "Check session startup and per-call delegation precedence separately",
    )


@pytest.mark.parametrize("name", SKILLS)
def test_aliases_and_qualified_pins_survive_pairwise_fallback(name: str) -> None:
    require(
        section(name, "Dispatch contract"),
        "`opus`/`sonnet`/`haiku` are portable intent",
        "Prefer supported native Claude/Copilot families",
        "active Codex maps to supported Sol high/medium/low, low only when task policy permits",
        "Preserve independent exact ID, effort and route pins",
        "Resolve and check bare CLI defaults",
        "`copilot::claude-sonnet-5@high` retains all three pins",
        "never send them to a legacy prefix runner",
        "resolve executor/reviewer together through fallback",
        "Claude Opus execution/Copilot Opus review needs different routes, "
        "distinct delivery identities and distinct known quota identities with evidence",
        "family diversity and route labels prove neither",
        "separate cold contexts on one permitted route are allowed by policy, "
        "with no quota separation",
        "Exclude only the concrete failed delivery",
        "distinguish quota exhaustion, auth, permission, unsupported selection and unknown",
        "never log in interactively, scan provider-wide quotas, "
        "rewrite config automatically or silently relax pins",
    )


def test_visual_requires_operations_and_routes_unsupported_work_to_planner() -> None:
    require(
        read("roles/visual.md"),
        "demonstrated usable navigation and snapshot/image operations on the selected surface",
        "under effective policy and actual callable controls",
        "catalog, installed browser, login window, tool name or mock proves no usable surface",
        "Codex may have browser tools",
        "Browser remains disabled on the researched host until demonstrated",
        "selected model must support this surface natively",
        "never dispatch visual verification through text-only `plz run`",
        "unsupported operation",
        "not evidenced",
        "request planner replan or focused handoff",
    )


def test_planner_preserves_ownership_and_does_not_dispatch_by_token_alone() -> None:
    text = read("roles/planner.md")
    require(
        text,
        "The planner alone authors all plans and briefs",
        "Outline/DRAFT, JIT Brief, Replan, Revise, exec, review and resume",
        "generic defaults versionless unless the user pins a version",
        "Codex needs exposed `model` and `reasoning_effort`",
        'fork_turns: "none"',
        "same-family Claude Opus/Copilot Opus",
    )
    assert "model token alone decides" not in text


def test_one_line_protocol_and_state_before_dependent_dispatch_survive() -> None:
    require(
        read("skills/plz-run-plan/SKILL.md"),
        "Every state change goes through `plz set` before the dispatch that depends on it",
        "one-line CLI outputs and one-line agent replies",
        "Every review is a separate role invocation",
        "planner owns JIT Brief, Replan and Revise",
    )
    require(read("skills/plz-new-plan/SKILL.md"), "planner-only authorship applies to every route")


def test_config_comments_keep_legacy_defaults_and_explain_policy() -> None:
    text = read("templates/config.md")
    settings = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert "models: planner=opus, exec=sonnet, verify=sonnet" in settings
    assert "providers: claude" in settings
    assert "harness: claude-code" in settings
    assert not any(line.startswith("harnesses:") for line in settings)
    require(
        text,
        "[<route>::]<name>[@<effort>]",
        "claude, codex, copilot",
        "claude-code, codex, copilot",
        "independent pins",
        "plan providers/models override repository defaults",
        "harnesses is a plan header, not a config key",
        "`copilot::claude-sonnet-5@high` pins delivery, ID and effort",
    )


@pytest.fixture
def codex_capability() -> Capability:
    return Capability(
        "codex",
        "native",
        "fixture-delivery",
        (Model("gpt-6.1-sol", "sol", efforts=("medium", "high")),),
        True,
        True,
        "callable_native",
        ("controlled fixture; no live provider",),
    )


@pytest.mark.parametrize("name", SKILLS)
@pytest.mark.parametrize(
    ("phase", "role", "token", "effort"),
    [
        ("Outline/DRAFT", "planner", None, "high"),
        ("JIT Brief", "planner", None, "high"),
        ("Replan", "replanner", None, "high"),
        ("Revise", "planner", None, "high"),
        ("exec", "executor", "gpt-6.1-sol@medium", "medium"),  # D8 N05
        ("exec", "executor", "gpt-6.1-sol@medium", "medium"),  # D8 N07
        ("exec", "executor", None, "high"),
        ("separate verifier", "verifier", None, "high"),
        ("final review", "verifier", None, "high"),
        ("resume", "planner", None, "high"),
    ],
    ids=[
        "outline",
        "jit",
        "replan",
        "revise",
        "N05",
        "N07",
        "other-exec",
        "verify",
        "final",
        "resume",
    ],
)
def test_d8_pins_cover_every_phase_with_fixtures_only(
    name: str, phase: str, role: str, token: str | None, effort: str, codex_capability: Capability
) -> None:
    policy_text = section(name, "Phase policy")
    require(policy_text, phase, "per-node Graph", "effective role defaults", "version/effort/route")
    policy = Policy(
        ("codex",),
        dict.fromkeys(("planner", "exec", "verify"), "gpt-6.1-sol@high"),
        ("codex",),
    )
    selection = resolve(
        policy,
        Request(role, token),
        Context("codex", "claude-code"),
        (codex_capability,),
    )
    assert isinstance(selection, Selection)
    assert (selection.exact_id, selection.effort, selection.route) == (
        "gpt-6.1-sol",
        effort,
        "codex",
    )
    assert selection.mismatch and selection.separate_context


@pytest.mark.parametrize("name", SKILLS)
def test_workflows_use_supported_policy_and_callable_dispatch(name: str) -> None:
    require(
        section(name, "Dispatch contract"),
        "planzilla.commands.dispatch.dispatch",
        "NativeAdapter",
        "plz dispatch",
        "run_selection",
        "only the current phase",
        "review=True",
    )
    require(section(name, "Phase policy"), "plz policy", "--harnesses", "--providers", "--models")
