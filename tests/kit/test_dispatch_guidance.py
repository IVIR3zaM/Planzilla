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


@pytest.mark.parametrize(
    "path",
    [
        "skills/plz-new-plan/SKILL.md",
        "skills/plz-run-plan/SKILL.md",
        "agents/claude/plz-run.md",
    ],
)
def test_external_job_lifecycle_keeps_quiet_pending_jobs_and_owned_evidence(path: str) -> None:
    require(
        read(path),
        "supported owned job handle",
        "at most 5 minutes per call, shorter where required",
        "quiet pending job",
        "continue waiting",
        "silence is not a hang",
        "explicit stop/cancel or demonstrated need",
        "cancel only the owned job",
        "never kill by broad process matching",
        "output, error and observed completion status",
        "extraction or cancellation is confirmed",
        "then clean up",
        "never delete live-job evidence",
        "no automatic execution deadline",
        "interruption does not consume a node retry",
        "resume uses existing plan state",
    )


def first_bullet(text: str) -> str:
    """The first bullet with its wrapped lines: the allowlist comes before anything else."""
    lines = text.strip("\n").splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].startswith("- ")), len(lines))
    return "\n".join(lines[:end])


@pytest.mark.parametrize("name", SKILLS)
def test_restricted_plan_excludes_probes_before_selection(name: str) -> None:
    dispatch = section(name, "Dispatch contract")
    require(
        first_bullet(dispatch),
        "actual coordinator against optional plan `harnesses` first",
        "intersect delivery with effective `providers` before defaults, aliases, "
        "capability selection or auth probes",
        "Never probe excluded providers",
        "plan providers/models override repository defaults without widening either allowlist",
    )
    require(section(name, "Phase policy"), "Before", "Dispatch contract", "resume")
    require(section(name, "Phase policy"), "plz policy", "--harnesses", "--providers", "--models")


@pytest.mark.parametrize("name", SKILLS)
def test_pins_survive_and_failures_are_classified(name: str) -> None:
    require(
        section(name, "Dispatch contract"),
        "never silently relax pins",
        "distinguish quota exhaustion, auth, permission, unsupported selection and unknown",
        "exclude only that delivery",
        "never log in interactively",
        "one focused handoff",
    )


@pytest.mark.parametrize("name", SKILLS)
def test_dispatch_rule_covers_every_harness(name: str) -> None:
    """D5: native in Claude Code, else `plz-run` there; a `plz run` shell job on Codex/Copilot."""
    require(
        section(name, "Dispatch contract"),
        "Claude Code, `<m>` is `opus`, `sonnet`, `haiku` or `fable` without `@<effort>`: "
        "dispatch the agent natively",
        "Claude Code, any other `<m>`",
        "`copilot::<id>` too",
        "dispatch `plz-run` with `Run: <role> <m> · <line>`",
        "Codex or Copilot: run `plz run <role> <m> '<line>'` as a shell job",
        "`plz-visual` never goes through `plz run`",
        "`<id>: cannot dispatch <agent> <m>`",
        "One batch may mix native, `plz-run` and shell-job dispatches in parallel",
    )


@pytest.mark.parametrize("name", SKILLS)
def test_copilot_is_harness_and_external_delivery_route(name: str) -> None:
    dispatch = section(name, "Dispatch contract")
    require(
        dispatch,
        "Copilot is a harness and an external delivery route",
        "`plz run <role> copilot::<model> '<line>'`",
        "exact Copilot model id",
        "docs/COPILOT.md",
    )
    assert "remain disabled" not in dispatch
    assert "remains disabled" not in dispatch


def test_new_plan_names_the_copilot_auth_check() -> None:
    require(
        section("plz-new-plan", "1. Clarify first, before any graph (req 6)"),
        "Copilot has no status command",
        "docs/COPILOT.md",
        "`error: copilot is not logged in; run copilot login`",
    )


@pytest.mark.parametrize("name", SKILLS)
def test_plz_dispatch_is_the_optional_advanced_path_with_the_example(name: str) -> None:
    require(
        section(name, "Dispatch contract"),
        "Advanced, optional",
        "`plz run` refuses qualified portable tokens",
        "`plz dispatch <plan> <role> '<line>' --actual-harness <h> --facts <file> --node <id>`",
        "`.planzilla/templates/capabilities.json`",
        '`"enabled": true` only on routes you have demonstrated',
    )


@pytest.mark.parametrize("name", SKILLS)
@pytest.mark.parametrize(
    "api", ["planzilla.commands.dispatch.dispatch", "NativeAdapter", "run_selection"]
)
def test_skills_never_require_the_python_dispatch_api(name: str, api: str) -> None:
    assert api not in read(f"skills/{name}/SKILL.md")


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


def test_planner_requires_completed_execution_history() -> None:
    require(
        read("roles/planner.md"),
        "completed_execution",
        "executor success",
        "resume",
        "prospective pair",
        "missing evidence",
    )
