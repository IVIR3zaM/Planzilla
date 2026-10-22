"""Synthetic supplied facts only; none of these tests probe a provider or account."""

from copy import deepcopy
from dataclasses import replace

import pytest

from planzilla.config import Policy
from planzilla.resolver import (
    Capability,
    Context,
    Failure,
    Independence,
    Model,
    Request,
    Selection,
    Unavailable,
    resolve,
    resolve_pair,
)

POLICY = Policy(
    ("claude", "codex", "copilot"), {"planner": "opus", "exec": "sonnet", "verify": "sonnet"}
)
CLAUDE = "claude-code"


def capability(
    route: str,
    mode: str = "native",
    *,
    quota: str | None = None,
    delivery: str | None = None,
) -> Capability:
    models = (
        (Model("gpt-6.1-sol", "gpt", (), ("low", "medium", "high")),)
        if route == "codex"
        else tuple(
            Model(f"claude-{alias}-5", "claude", (alias,), ("low", "medium", "high"))
            for alias in ("opus", "sonnet", "haiku")
        )
    )
    return Capability(
        route=route,
        mode=mode,
        delivery_id=delivery or f"{route}-{mode}",
        models=models,
        model_control=True,
        effort_control=True,
        availability="callable_native" if mode == "native" else "external_reply",
        evidence=(f"observed:{route}:{mode}",),
        quota_id=quota,
        quota_evidence=(f"quota:{quota}",) if quota else (),
    )


def context(actual: str = "codex", configured: str = CLAUDE) -> Context:
    return Context(actual, configured)


def selected(result: Selection | Unavailable) -> Selection:
    assert isinstance(result, Selection), result
    return result


def unavailable(result: Selection | Unavailable, constraint: str) -> Unavailable:
    assert isinstance(result, Unavailable), result
    assert result.constraint == constraint
    assert result.alternatives
    return result


@pytest.mark.parametrize(
    "actual,route", [(CLAUDE, "claude"), ("codex", "codex"), ("copilot", "copilot")]
)
@pytest.mark.parametrize("alias,effort", [("opus", "high"), ("sonnet", "medium"), ("haiku", "low")])
def test_portable_aliases_use_actual_native_controls(
    actual: str, route: str, alias: str, effort: str
) -> None:
    cap = capability(route)
    result = selected(
        resolve(POLICY, Request("exec", alias, allow_low=True), context(actual), (cap,))
    )
    assert result.exact_id == ("gpt-6.1-sol" if route == "codex" else f"claude-{alias}-5")
    assert result.effort == (effort if route == "codex" else None)
    assert result.original == alias
    assert result.route == route
    assert result.actual_harness == actual
    assert result.mode == "native"
    assert result.evidence == cap.evidence
    assert result.family == ("gpt" if route == "codex" else "claude")
    assert result.mismatch == (actual != CLAUDE)


def test_native_preference_over_list_order_and_cli() -> None:
    caps = (capability("claude", "cli"), capability("codex", "cli"), capability("codex"))
    result = selected(resolve(POLICY, Request("exec", "opus"), context(), caps))
    assert (result.route, result.mode) == ("codex", "native")


@pytest.mark.parametrize("role", ["planner", "replanner", "exec", "verify"])
def test_codex_only_reconciles_configured_claude_and_inherited_defaults(role: str) -> None:
    policy = replace(POLICY, providers=("codex",), harnesses=("codex",))
    result = selected(resolve(policy, Request(role), context(), (capability("codex"),)))
    assert result.exact_id == "gpt-6.1-sol"
    assert result.original is None
    assert result.intent == ("opus" if role in ("planner", "replanner") else "sonnet")
    assert result.mismatch


@pytest.mark.parametrize("actual", [CLAUDE, "copilot"])
def test_disallowed_actual_coordinator_fails_even_with_codex_agents(actual: str) -> None:
    policy = replace(POLICY, harnesses=("codex",))
    result = unavailable(
        resolve(policy, Request("planner"), context(actual), (capability("codex"),)), "coordinator"
    )
    assert actual in result.detail


def test_allowlist_checks_every_delivery_even_for_manually_composed_policy() -> None:
    policy = replace(POLICY, harnesses=("codex",))
    unavailable(
        resolve(
            policy, Request("exec", "copilot::opus"), context(), (capability("copilot", "cli"),)
        ),
        "policy",
    )


def test_explicit_multiple_harnesses_allow_cross_harness_delivery() -> None:
    policy = replace(POLICY, harnesses=("codex", "copilot"))
    result = selected(
        resolve(
            policy, Request("exec", "copilot::opus"), context(), (capability("copilot", "cli"),)
        )
    )
    assert result.route == "copilot"


@pytest.mark.parametrize(
    "token,route,exact,effort",
    [
        ("copilot::claude-sonnet-5@high", "copilot", "claude-sonnet-5", "high"),
        ("codex::opus", "codex", "gpt-6.1-sol", "high"),
        ("opus@medium", "codex", "gpt-6.1-sol", "medium"),
        ("gpt-6.1-sol@high", "copilot", "gpt-6.1-sol", "high"),
        ("claude-sonnet-5", "claude", "claude-sonnet-5", None),
        ("claude-sonnet-5", "copilot", "claude-sonnet-5", None),
    ],
)
def test_independent_exact_effort_and_route_pins(
    token: str, route: str, exact: str, effort: str | None
) -> None:
    cap = capability(route, "cli")
    if exact == "gpt-6.1-sol" and route == "copilot":
        cap = replace(cap, models=capability("codex").models)
    result = selected(resolve(POLICY, Request("exec", token), context(), (cap,)))
    assert (result.route, result.exact_id, result.effort) == (route, exact, effort)
    assert result.pins.route == (token.split("::")[0] if "::" in token else None)
    assert result.pins.exact_id == (
        exact if token.split("::")[-1].split("@")[0] not in ("opus",) else None
    )
    assert result.pins.effort == (token.split("@")[1] if "@" in token else None)


@pytest.mark.parametrize(
    "token", ["claude::opus", "claude-opus-5", "copilot::claude-sonnet-5@high"]
)
def test_pins_cannot_fall_back_to_sol(token: str) -> None:
    unavailable(
        resolve(POLICY, Request("exec", token), context(), (capability("codex"),)), "selection"
    )


@pytest.mark.parametrize("token", ["haiku", "gpt-6.1-sol@low"])
def test_low_effort_requires_task_permission(token: str) -> None:
    unavailable(
        resolve(POLICY, Request("exec", token), context(), (capability("codex"),)), "low_effort"
    )


@pytest.mark.parametrize("field", ["model_control", "effort_control"])
def test_unsupported_native_controls_need_a_proven_cli_alternative(field: str) -> None:
    cap = replace(capability("codex"), **{field: False})
    unavailable(resolve(POLICY, Request("exec", "opus"), context(), (cap,)), "selection_control")
    result = selected(
        resolve(POLICY, Request("exec", "opus"), context(), (cap, capability("codex", "cli")))
    )
    assert result.mode == "cli"


@pytest.mark.parametrize(
    "availability", ["catalog", "mock", "executable", "unknown", "external_reply"]
)
def test_non_callable_native_evidence_is_insufficient(availability: str) -> None:
    cap = replace(capability("codex"), availability=availability)
    unavailable(resolve(POLICY, Request("exec", "opus"), context(), (cap,)), "availability")


@pytest.mark.parametrize(
    "availability", ["catalog", "mock", "executable", "unknown", "callable_native"]
)
def test_external_requires_demonstrated_reply(availability: str) -> None:
    cap = replace(capability("copilot", "cli"), availability=availability)
    unavailable(
        resolve(POLICY, Request("exec", "copilot::opus"), context(), (cap,)), "availability"
    )


@pytest.mark.parametrize("change", [{"evidence": ()}, {"enabled": False}])
def test_missing_evidence_or_disabled_capability_cannot_succeed(change: dict) -> None:
    cap = replace(capability("codex"), **change)
    unavailable(resolve(POLICY, Request("exec", "opus"), context(), (cap,)), "availability")


def test_missing_capabilities_are_unavailable() -> None:
    unavailable(resolve(POLICY, Request("exec", "opus"), context(), ()), "availability")


def test_native_copilot_does_not_enable_external_copilot_or_other_harnesses() -> None:
    cap = capability("copilot")
    selected(resolve(POLICY, Request("exec", "opus"), context("copilot"), (cap,)))
    unavailable(
        resolve(POLICY, Request("exec", "copilot::opus"), context(), (cap,)), "availability"
    )


@pytest.mark.parametrize("default_id", [None, "missing"])
def test_bare_cli_default_must_resolve_exactly(default_id: str | None) -> None:
    cap = replace(capability("codex", "cli"), default_id=default_id)
    unavailable(resolve(POLICY, Request("exec", "codex@high"), context(), (cap,)), "default")


def test_bare_cli_default_retains_exact_resolution_and_effort() -> None:
    cap = replace(capability("codex", "cli"), default_id="gpt-6.1-sol")
    result = selected(resolve(POLICY, Request("exec", "codex@high"), context(), (cap,)))
    assert (result.exact_id, result.effort, result.pins.route) == ("gpt-6.1-sol", "high", "codex")


@pytest.mark.parametrize(
    "navigation,snapshot,evidence",
    [
        (False, False, ()),
        (True, False, ("browser",)),
        (False, True, ("browser",)),
        (True, True, ()),
    ],
)
def test_visual_requires_navigation_snapshot_and_evidence(
    navigation: bool, snapshot: bool, evidence: tuple[str, ...]
) -> None:
    cap = replace(
        capability("codex"), navigation=navigation, snapshot=snapshot, visual_evidence=evidence
    )
    unavailable(
        resolve(POLICY, Request("verify", "opus", visual=True), context(), (cap,)), "visual"
    )


def test_visual_uses_proven_surface() -> None:
    cap = replace(
        capability("codex"), navigation=True, snapshot=True, visual_evidence=("navigate+snapshot",)
    )
    assert (
        selected(
            resolve(POLICY, Request("verify", "opus", visual=True), context(), (cap,))
        ).visual_evidence
        == cap.visual_evidence
    )


@pytest.mark.parametrize(
    "reason",
    [
        "missing_entrypoint",
        "unsupported_selection",
        "quota_exhausted",
        "auth",
        "permission",
        "unknown",
    ],
)
def test_classified_failures_are_preserved_and_scope_fallback(reason: str) -> None:
    failure = Failure(reason, (f"observed:{reason}",))
    failed = replace(capability("claude", "cli"), failure=failure)
    request = Request("exec", "opus")
    result = selected(
        resolve(POLICY, request, context(CLAUDE), (failed, capability("codex", "cli")))
    )
    assert (result.route, result.exact_id, result.effort) == ("codex", "gpt-6.1-sol", "high")
    assert result.failures == (failure,)
    problem = unavailable(resolve(POLICY, request, context(CLAUDE), (failed,)), reason)
    assert problem.evidence == failure.evidence
    if reason == "auth":
        assert "authentication" in " ".join(problem.alternatives)
        assert any("authentication" in notice for notice in result.notices)


def test_failed_cli_does_not_disable_other_delivery_of_same_route() -> None:
    failed = replace(
        capability("codex", "cli"), failure=Failure("quota_exhausted", ("cli-budget",))
    )
    result = selected(
        resolve(POLICY, Request("exec", "opus"), context(), (failed, capability("codex")))
    )
    assert result.mode == "native"


def test_unknown_failure_never_becomes_quota_exhaustion() -> None:
    cap = replace(
        capability("codex"),
        failure=Failure("unknown", ("HTTP 429 without semantics; signal; empty output",)),
    )
    result = unavailable(resolve(POLICY, Request("exec", "opus"), context(), (cap,)), "unknown")
    assert "quota" not in result.detail


def test_pair_distinct_claude_and_copilot_opus_with_proven_quotas() -> None:
    caps = (
        capability("claude", "cli", quota="budget-a"),
        capability("copilot", "cli", quota="budget-b"),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "claude::opus"),
        Request("verify", "copilot::opus"),
        context(),
        caps,
        Independence(delivery=True, quota=True),
    )
    assert not isinstance(result, Unavailable)
    executor, reviewer = result
    assert executor.family == reviewer.family == "claude"
    assert executor.exact_id == reviewer.exact_id == "claude-opus-5"
    assert executor.quota_id != reviewer.quota_id
    assert executor.quota_evidence and reviewer.quota_evidence


@pytest.mark.parametrize("quotas", [(None, None), ("shared", "shared"), ("a", None)])
def test_different_routes_do_not_prove_quota_independence(
    quotas: tuple[str | None, str | None],
) -> None:
    caps = (
        capability("claude", "cli", quota=quotas[0]),
        capability("copilot", "cli", quota=quotas[1]),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "claude::opus"),
        Request("verify", "copilot::opus"),
        context(),
        caps,
        Independence(quota=True),
    )
    assert isinstance(result, Unavailable)
    assert result.constraint == "quota_independence"


def test_different_model_families_do_not_prove_independent_quotas() -> None:
    caps = (capability("claude", "cli"), capability("codex", "cli"))
    result = resolve_pair(
        POLICY,
        Request("exec", "claude::opus"),
        Request("verify", "codex::opus"),
        context(),
        caps,
        Independence(quota=True),
    )
    assert isinstance(result, Unavailable)


def test_quota_labels_without_separation_evidence_are_insufficient() -> None:
    caps = tuple(
        replace(capability(route, "cli", quota=route), quota_evidence=())
        for route in ("claude", "copilot")
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "claude::opus"),
        Request("verify", "copilot::opus"),
        context(),
        caps,
        Independence(quota=True),
    )
    assert isinstance(result, Unavailable)


def test_pair_search_keeps_review_route_independent_during_fallback() -> None:
    caps = (
        replace(
            capability("claude", "cli"), failure=Failure("quota_exhausted", ("claude-cli-only",))
        ),
        capability("codex"),
        capability("copilot", "cli"),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "opus"),
        Request("verify", "opus"),
        context(),
        caps,
        Independence(delivery=True),
    )
    assert not isinstance(result, Unavailable)
    assert (result[0].route, result[1].route) == ("codex", "copilot")
    collapsed = resolve_pair(
        POLICY,
        Request("exec", "opus"),
        Request("verify", "opus"),
        context(),
        caps[:2],
        Independence(delivery=True),
    )
    assert isinstance(collapsed, Unavailable)
    assert collapsed.constraint == "delivery_independence"


def test_delivery_names_alone_cannot_evade_distinct_route_requirement() -> None:
    caps = (capability("codex", delivery="one"), capability("codex", delivery="two"))
    result = resolve_pair(
        POLICY,
        Request("exec", "opus"),
        Request("verify", "opus"),
        context(),
        caps,
        Independence(delivery=True),
    )
    assert isinstance(result, Unavailable)


def test_same_route_cold_review_is_allowed_without_claiming_quota_independence() -> None:
    result = resolve_pair(
        POLICY,
        Request("exec", "opus"),
        Request("verify", "opus"),
        context(),
        (capability("codex"),),
    )
    assert not isinstance(result, Unavailable)
    assert result[0].route == result[1].route == "codex"
    assert result[0].quota_id is result[1].quota_id is None
    assert result[0].separate_context and result[1].separate_context


def test_identical_inputs_are_deterministic_and_never_mutated() -> None:
    args = (deepcopy(POLICY), Request("planner"), context(), (capability("codex"),))
    before = deepcopy(args)
    assert resolve(*args) == resolve(*args)
    assert args == before


@pytest.mark.parametrize(
    "role,key", [("executor", "exec"), ("verifier", "verify"), ("replan", "planner")]
)
def test_dispatch_role_names_share_policy_defaults(role: str, key: str) -> None:
    result = selected(resolve(POLICY, Request(role), context(), (capability("codex"),)))
    assert result.intent == POLICY.models[key]


def test_unsupported_effort_is_not_silently_reduced() -> None:
    cap = replace(
        capability("codex"), models=(replace(capability("codex").models[0], efforts=("medium",)),)
    )
    unavailable(resolve(POLICY, Request("exec", "opus@high"), context(), (cap,)), "selection")


def test_disabled_provider_cannot_be_used_even_with_live_controls() -> None:
    policy = replace(POLICY, providers=("codex",))
    unavailable(
        resolve(
            policy, Request("exec", "copilot::opus"), context(), (capability("copilot", "cli"),)
        ),
        "policy",
    )


def test_verified_bare_cli_default_can_use_its_proven_inherited_selection() -> None:
    cap = replace(capability("codex", "cli"), default_id="gpt-6.1-sol", model_control=False)
    result = selected(resolve(POLICY, Request("exec", "codex@high"), context(), (cap,)))
    assert result.exact_id == "gpt-6.1-sol"
    # An exact pin still requires an actual selection control.
    unavailable(
        resolve(POLICY, Request("exec", "gpt-6.1-sol@high"), context(), (cap,)), "selection_control"
    )


def test_pair_search_uses_quota_evidence_instead_of_greedy_single_resolution() -> None:
    caps = (
        capability("codex", quota="shared"),
        capability("copilot", "cli", quota="shared"),
        capability("copilot", "cli", quota="independent", delivery="independent-copilot"),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "codex::opus"),
        Request("verify", "copilot::opus"),
        context(),
        caps,
        Independence(delivery=True, quota=True),
    )
    assert not isinstance(result, Unavailable)
    assert result[1].delivery_id == "independent-copilot"


def test_pair_pin_failure_cannot_be_replaced_by_another_route() -> None:
    caps = (
        replace(
            capability("claude", "cli"), failure=Failure("quota_exhausted", ("observed-limit",))
        ),
        capability("codex"),
        capability("copilot", "cli"),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "claude::opus"),
        Request("verify", "copilot::opus"),
        context(),
        caps,
        Independence(delivery=True),
    )
    assert isinstance(result, Unavailable)
    assert result.constraint == "quota_exhausted"


def test_pair_handoff_retains_failed_route_evidence_and_auth_recovery() -> None:
    failure = Failure("auth", ("claude-cli-auth-failure",))
    caps = (
        replace(capability("claude", "cli"), failure=failure),
        capability("codex"),
    )
    result = resolve_pair(
        POLICY,
        Request("exec", "opus"),
        Request("verify", "opus"),
        context(),
        caps,
        Independence(delivery=True),
    )
    assert isinstance(result, Unavailable)
    assert result.constraint == "delivery_independence"
    assert result.failures == (failure,)
    assert "claude-cli-auth-failure" in result.evidence
    assert any("authentication" in alternative for alternative in result.alternatives)
