"""Pure state machine (FORMAT §3, §4, §5, §9, §13): transitions, budgets, waves, actions."""

import ast
from pathlib import Path

import pytest

from planzilla import state
from planzilla.plan import Node
from planzilla.state import Facts, StateError

BUDGETS = (2, 2)
MODELS = {"planner": "opus", "exec": "sonnet", "verify": "sonnet"}
BRIEF = Facts(brief=True, cmd=True, verifier=True)
CMD_ONLY = Facts(brief=True, cmd=True)


def node(
    node_id: str = "N01",
    type: str = "exec",
    status: str = "TODO",
    t: int = 0,
    r: int = 0,
    note: str = "",
    deps: tuple[str, ...] = (),
    model: str = "sonnet/opus",
) -> Node:
    exec_model, verify_model = model.split("/")
    return Node(node_id, "title", type, list(deps), exec_model, verify_model, t, r, status, note)


# --- §5 transition table, rows 1-28 ------------------------------------------

ROWS = [
    # row, node kwargs, facts, requested, --note, expected (status, t, r, note)
    (1, dict(status="TODO"), Facts(), "BRIEFING", None, ("BRIEFING", 0, 0, "")),
    (2, dict(status="BRIEFING", note="x"), Facts(), "TODO", None, ("TODO", 0, 0, "")),
    (3, dict(status="BRIEFING"), Facts(), "WAITING", "ask: D7", ("WAITING", 0, 0, "ask: D7")),
    (4, dict(status="TODO"), BRIEF, "RUNNING", None, ("RUNNING", 1, 0, "")),
    (
        4,
        dict(status="RETRY", t=1, note="fail C1"),
        BRIEF,
        "RUNNING",
        None,
        ("RUNNING", 2, 0, "fail C1"),
    ),
    (5, dict(status="RUNNING", t=1), BRIEF, "VERIFYING", None, ("VERIFYING", 1, 0, "")),
    (
        6,
        dict(status="RUNNING", t=1, note="fail C1"),
        CMD_ONLY,
        "VERIFYING",
        None,
        ("DONE", 1, 0, ""),
    ),
    (7, dict(status="RUNNING", t=1), BRIEF, "RETRY", "fail C1", ("RETRY", 1, 0, "fail C1")),
    (8, dict(status="RUNNING", t=2), BRIEF, "RETRY", "fail C1", ("REPLAN", 2, 1, "fail C1")),
    (
        9,
        dict(status="RUNNING", t=1),
        BRIEF,
        "REPLAN",
        "blocked: why",
        ("REPLAN", 1, 1, "blocked: why"),
    ),
    (10, dict(type="check"), BRIEF, "VERIFYING", None, ("VERIFYING", 1, 0, "")),
    (11, dict(type="check"), CMD_ONLY, "VERIFYING", None, ("DONE", 1, 0, "")),
    (12, dict(type="check"), BRIEF, "RETRY", "fail C1", ("REPLAN", 1, 1, "fail C1")),
    (
        13,
        dict(type="check"),
        Facts(brief=True, verifier=True),
        "VERIFYING",
        None,
        ("VERIFYING", 1, 0, ""),
    ),
    (14, dict(status="VERIFYING", t=1), BRIEF, "DONE", None, ("DONE", 1, 0, "")),
    (
        15,
        dict(status="VERIFYING", t=1),
        Facts(brief=True, verifier=True, human=("C5", "C6")),
        "DONE",
        None,
        ("WAITING", 1, 0, "ask: C5,C6"),
    ),
    (16, dict(status="VERIFYING", t=1), BRIEF, "RETRY", "fail C2", ("RETRY", 1, 0, "fail C2")),
    (17, dict(status="VERIFYING", t=2), BRIEF, "RETRY", "fail C2", ("REPLAN", 2, 1, "fail C2")),
    (
        17,
        dict(type="check", status="VERIFYING", t=1),
        BRIEF,
        "RETRY",
        "fail C2",
        ("REPLAN", 1, 1, "fail C2"),
    ),
    (18, dict(status="REPLAN", t=2, r=1, note="fail C2"), BRIEF, "TODO", None, ("TODO", 0, 1, "")),
    (19, dict(status="REPLAN", r=1), BRIEF, "WAITING", "ask: D7", ("WAITING", 0, 1, "ask: D7")),
    (
        20,
        dict(status="WAITING", r=2, note="ask: D7"),
        BRIEF,
        "REPLAN",
        None,
        ("REPLAN", 0, 2, "ask: D7"),
    ),
    (21, dict(status="WAITING", t=1, note="ask: C5"), BRIEF, "DONE", None, ("DONE", 1, 0, "")),
    (
        22,
        dict(status="WAITING", t=1, note="ask: C5"),
        BRIEF,
        "RETRY",
        "fail C5",
        ("RETRY", 1, 0, "fail C5"),
    ),
    (
        22,
        dict(status="WAITING", t=2, note="ask: C5"),
        BRIEF,
        "RETRY",
        "fail C5",
        ("REPLAN", 2, 1, "fail C5"),
    ),
    (
        23,
        dict(type="gate", model="-/-"),
        Facts(brief=True, verifier=True),
        "DONE",
        None,
        ("DONE", 0, 0, ""),
    ),
    (24, dict(type="gate"), Facts(), "REPLAN", "gate: no logo", ("REPLAN", 0, 1, "gate: no logo")),
    (
        25,
        dict(status="RUNNING", t=2, r=2),
        BRIEF,
        "RETRY",
        "fail C1",
        ("BLOCKED", 2, 2, "blocked: fail C1"),
    ),
    (
        25,
        dict(status="RUNNING", t=1, r=2),
        BRIEF,
        "REPLAN",
        "blocked: why",
        ("BLOCKED", 1, 2, "blocked: why"),
    ),
    (25, dict(type="check", r=2), BRIEF, "RETRY", "fail C1", ("BLOCKED", 1, 2, "blocked: fail C1")),
    (
        26,
        dict(status="BLOCKED", t=2, r=2, note="blocked: x"),
        BRIEF,
        "REPLAN",
        None,
        ("REPLAN", 2, 1, "blocked: x"),
    ),
    (
        27,
        dict(status="BLOCKED", r=2),
        BRIEF,
        "DONE",
        "skipped: later",
        ("DONE", 0, 2, "skipped: later"),
    ),
    (28, dict(status="BRIEFING", note="n"), Facts(), "BRIEFING", None, ("BRIEFING", 0, 0, "n")),
    (28, dict(status="RUNNING", t=1), BRIEF, "RUNNING", None, ("RUNNING", 1, 0, "")),
    (28, dict(status="VERIFYING", t=1), BRIEF, "VERIFYING", None, ("VERIFYING", 1, 0, "")),
    (28, dict(status="REPLAN", r=1), BRIEF, "REPLAN", None, ("REPLAN", 0, 1, "")),
]


@pytest.mark.parametrize(
    "row, kwargs, facts, requested, note, expected", ROWS, ids=[f"row{r[0]}" for r in ROWS]
)
def test_transition_rows(row, kwargs, facts, requested, note, expected) -> None:
    after = state.transition(node(**kwargs), requested, note, facts, BUDGETS)
    assert (after.status, after.tries, after.rp, after.note) == expected


def test_every_row_1_to_28_has_a_case() -> None:
    assert {row[0] for row in ROWS} == set(range(1, 29))


def test_transition_returns_a_new_node() -> None:
    before = node(status="TODO")
    after = state.transition(before, "RUNNING", None, BRIEF, BUDGETS)
    assert before.status == "TODO" and after is not before


def test_note_option_replaces_the_note() -> None:
    after = state.transition(node(status="RUNNING", t=1), "VERIFYING", "hi", BRIEF, BUDGETS)
    assert after.note == "hi"


# --- budgets -----------------------------------------------------------------


@pytest.mark.parametrize("b", [1, 2, 3])
def test_failure_at_t_equal_b_becomes_replan(b: int) -> None:
    below = state.transition(node(status="RUNNING", t=b - 1), "RETRY", "fail C1", BRIEF, (b, 2))
    at = state.transition(node(status="RUNNING", t=b), "RETRY", "fail C1", BRIEF, (b, 2))
    assert (at.status, at.tries, at.rp) == ("REPLAN", b, 1)
    if b > 1:
        assert below.status == "RETRY"


@pytest.mark.parametrize("r", [1, 3])
def test_entering_replan_at_r_equal_r_budget_blocks(r: int) -> None:
    before = node(status="VERIFYING", t=2, r=r, note="old")
    after = state.transition(before, "RETRY", "fail C2", BRIEF, (2, r))
    assert (after.status, after.tries, after.rp, after.note) == (
        "BLOCKED",
        2,
        r,
        "blocked: fail C2",
    )
    under = state.transition(
        node(status="VERIFYING", t=2, r=r - 1), "RETRY", "fail C2", BRIEF, (2, r)
    )
    assert (under.status, under.rp) == ("REPLAN", r)


def test_blocked_note_keeps_the_incoming_note_when_no_option() -> None:
    after = state.transition(
        node(type="gate", r=2, note="gate: x"), "REPLAN", None, Facts(), BUDGETS
    )
    assert after.note == "blocked: gate: x"


# --- illegal transitions ------------------------------------------------------

ILLEGAL = [
    (dict(status="DONE", t=1), BRIEF, "DONE"),
    (dict(status="DONE", t=1), BRIEF, "REPLAN"),
    (dict(status="TODO"), BRIEF, "DONE"),
    (dict(status="TODO"), Facts(), "RUNNING"),
    (dict(status="TODO"), BRIEF, "BRIEFING"),
    (dict(status="TODO", type="check"), BRIEF, "RUNNING"),
    (dict(status="TODO", type="gate"), Facts(), "VERIFYING"),
    (dict(status="TODO"), BRIEF, "RETRY"),
    (dict(status="TODO"), BRIEF, "TODO"),
    (dict(status="RETRY", t=1), BRIEF, "VERIFYING"),
    (dict(status="WAITING", note="ask: D7"), BRIEF, "DONE"),
    (dict(status="WAITING", note="ask: C5"), BRIEF, "REPLAN"),
    (dict(status="WAITING", note="ask: D7"), BRIEF, "WAITING"),
    (dict(status="BLOCKED", r=2), BRIEF, "TODO"),
    (dict(status="RUNNING", t=1), BRIEF, "DONE"),
    (dict(status="REPLAN", r=1), BRIEF, "RUNNING"),
]


@pytest.mark.parametrize("kwargs, facts, requested", ILLEGAL)
def test_illegal_transition_raises(kwargs, facts, requested) -> None:
    with pytest.raises(StateError, match="illegal transition"):
        state.transition(node(**kwargs), requested, None, facts, BUDGETS)


def test_leaving_todo_or_retry_needs_all_deps_done() -> None:
    nodes = [node("N01", status="RUNNING", t=1), node("N02", deps=("N01",))]
    with pytest.raises(StateError, match="deps"):
        state.set_node(nodes, "N02", "RUNNING", facts={"N02": BRIEF}, budgets=BUDGETS)
    nodes = [node("N01", status="DONE", t=1), node("N02", status="RETRY", t=1, deps=("N01",))]
    changed, _ = state.set_node(nodes, "N02", "RUNNING", facts={"N02": BRIEF}, budgets=BUDGETS)
    assert changed[1].status == "RUNNING"


def test_set_unknown_node_raises() -> None:
    with pytest.raises(StateError, match="unknown node N09"):
        state.set_node([node()], "N09", "RUNNING", facts={}, budgets=BUDGETS)


def test_note_with_a_pipe_is_refused() -> None:
    with pytest.raises(StateError):
        state.set_node(
            [node()], "N01", "RUNNING", note="a | b", facts={"N01": BRIEF}, budgets=BUDGETS
        )


# --- structure edits ----------------------------------------------------------


def test_add_appends_a_todo_row() -> None:
    nodes = [node("N01", status="DONE", t=1)]
    changed, status = state.set_node(
        nodes,
        "N02",
        None,
        add=True,
        title="new",
        deps="N01",
        model="sonnet/-",
        facts={},
        budgets=BUDGETS,
    )
    added = changed[-1]
    assert (added.id, added.title, added.type, added.deps) == ("N02", "new", "exec", ["N01"])
    assert (
        added.exec_model,
        added.verify_model,
        added.tries,
        added.rp,
        added.status,
        added.note,
    ) == (
        "sonnet",
        "-",
        0,
        0,
        "TODO",
        "",
    )
    assert added.line is None and status == "RUNNING"


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (dict(title="t", deps="-"), "--model"),
        (dict(title="t", model="a/b"), "--deps"),
        (dict(deps="-", model="a/b"), "--title"),
        (dict(title="t", deps="N09", model="a/b"), "unknown dep N09"),
        (dict(title="t", deps="-", model="Bad"), "model"),
        (dict(title="a|b", deps="-", model="a/b"), "title"),
    ],
)
def test_add_validates_its_options(kwargs, message) -> None:
    with pytest.raises(StateError, match=message):
        state.set_node([node()], "N02", None, add=True, facts={}, budgets=BUDGETS, **kwargs)


def test_add_existing_id_or_bad_id_raises() -> None:
    with pytest.raises(StateError, match="exists"):
        state.set_node(
            [node()],
            "N01",
            None,
            add=True,
            title="t",
            deps="-",
            model="a/b",
            facts={},
            budgets=BUDGETS,
        )
    with pytest.raises(StateError, match="id"):
        state.set_node(
            [node()],
            "X1",
            None,
            add=True,
            title="t",
            deps="-",
            model="a/b",
            facts={},
            budgets=BUDGETS,
        )


def test_edit_title_deps_model() -> None:
    nodes = [node("N01"), node("N02"), node("N03")]
    changed, _ = state.set_node(
        nodes,
        "N03",
        None,
        title="renamed",
        deps="N01, N02",
        model="haiku/opus",
        facts={},
        budgets=BUDGETS,
    )
    edited = changed[2]
    assert (edited.title, edited.deps, edited.exec_model, edited.verify_model) == (
        "renamed",
        ["N01", "N02"],
        "haiku",
        "opus",
    )
    assert nodes[2].title == "title"


def test_edit_refuses_a_cycle_and_done_nodes() -> None:
    nodes = [node("N01", deps=("N02",)), node("N02"), node("N03", status="DONE", t=1)]
    with pytest.raises(StateError, match="cycle N01 -> N02 -> N01"):
        state.set_node(nodes, "N02", None, deps="N01", facts={}, budgets=BUDGETS)
    with pytest.raises(StateError, match="DONE"):
        state.set_node(nodes, "N03", None, title="x", facts={}, budgets=BUDGETS)


def test_type_only_with_add_and_status_needed_without_structure() -> None:
    with pytest.raises(StateError, match="--type"):
        state.set_node([node()], "N01", None, type="check", facts={}, budgets=BUDGETS)
    with pytest.raises(StateError, match="STATUS"):
        state.set_node([node()], "N01", None, facts={}, budgets=BUDGETS)


def test_add_then_status_applies_both() -> None:
    nodes = [node("N01", status="DONE", t=1)]
    changed, _ = state.set_node(
        nodes,
        "N02",
        "BRIEFING",
        add=True,
        title="t",
        deps="N01",
        model="a/b",
        facts={"N02": Facts()},
        budgets=BUDGETS,
    )
    assert changed[-1].status == "BRIEFING"


# --- §3 plan status -----------------------------------------------------------


def test_plan_status_all_done() -> None:
    assert state.plan_status([node(status="DONE"), node("N02", status="DONE")]) == "DONE"


@pytest.mark.parametrize("status", ["BRIEFING", "RUNNING", "VERIFYING", "REPLAN"])
def test_plan_status_running_when_in_flight(status: str) -> None:
    nodes = [node(status=status), node("N02", status="BLOCKED"), node("N03", status="WAITING")]
    assert state.plan_status(nodes) == "RUNNING"


def test_plan_status_running_when_a_non_ask_action_is_ready() -> None:
    nodes = [
        node(status="DONE"),
        node("N02", status="RETRY", t=1, deps=("N01",)),
        node("N03", status="WAITING"),
    ]
    assert state.plan_status(nodes) == "RUNNING"


def test_plan_status_waiting() -> None:
    blocked = node("N03", status="BLOCKED")
    assert state.plan_status([node(status="WAITING", note="ask: D1"), blocked]) == "WAITING"
    gate = node("N02", type="gate", deps=("N01",))
    assert state.plan_status([node(status="DONE"), gate, blocked]) == "WAITING"


def test_plan_status_blocked() -> None:
    nodes = [
        node(status="BLOCKED"),
        node("N02", deps=("N01",)),
        node("N03", type="gate", deps=("N01",)),
    ]
    assert state.plan_status(nodes) == "BLOCKED"


# --- §4 waves -------------------------------------------------------------------


def test_waves_are_topological_levels() -> None:
    nodes = [
        node("N01"),
        node("N02", deps=("N01",)),
        node("N03", deps=("N01",)),
        node("N04", deps=("N02", "N03")),
        node("N05"),
    ]
    assert state.waves(nodes) == {"N01": 1, "N02": 2, "N03": 2, "N04": 3, "N05": 1}


def test_waves_cycle_names_the_cycle() -> None:
    nodes = [node("N01"), node("N03", deps=("N01", "N05")), node("N05", deps=("N03",))]
    with pytest.raises(StateError, match="^cycle N03 -> N05 -> N03$"):
        state.waves(nodes)


def test_waves_unknown_dep() -> None:
    with pytest.raises(StateError, match="unknown dep N09"):
        state.waves([node("N01", deps=("N09",))])


# --- §5 ready actions / §9 next lines ------------------------------------------


def test_next_lines_map_ready_statuses_to_actions_and_models() -> None:
    nodes = [
        node("N01", status="TODO"),
        node("N02", status="TODO", model="haiku/opus"),
        node("N03", type="check", model="-/opus"),
        node("N04", type="check", model="-/-"),
        node("N05", status="RETRY", t=1),
        node("N06", status="RUNNING", t=1),
        node("N07", status="VERIFYING", t=1, model="sonnet/-"),
        node("N08", status="BRIEFING"),
        node("N09", status="REPLAN", r=1),
        node("N10", status="DONE"),
        node("N11", status="BLOCKED"),
        node("N12", status="WAITING", note="ask: D1"),
        node("N13", deps=("N06",)),
    ]
    facts = {
        "N02": BRIEF,
        "N03": BRIEF,
        "N04": Facts(brief=True, verifier=True),
        "N05": BRIEF,
        "N06": BRIEF,
        "N07": BRIEF,
    }
    models = {"planner": "opus", "exec": "sonnet", "verify": "haiku"}
    assert state.next_lines(nodes, facts, models) == [
        "N01 brief opus",
        "N02 exec haiku",
        "N03 check -",
        "N04 verify haiku",
        "N05 exec sonnet",
        "N06 exec sonnet",
        "N07 verify haiku",
        "N08 brief opus",
        "N09 replan opus",
    ]


def test_ask_lines_only_when_no_other_line() -> None:
    nodes = [node("N01", status="WAITING", note="ask: D1"), node("N02", type="gate", model="-/-")]
    assert state.next_lines(nodes, {}, MODELS) == ["N01 ask -", "N02 ask -"]
    nodes.append(node("N03"))
    assert state.next_lines(nodes, {}, MODELS) == ["N03 brief opus"]


def test_next_nothing_when_all_done_or_blocked() -> None:
    assert state.next_lines([node(status="DONE"), node("N02", status="DONE")], {}, MODELS) == []
    blocked = [node(status="BLOCKED"), node("N02", deps=("N01",))]
    assert state.next_lines(blocked, {}, MODELS) == []


def test_next_orders_by_wave_then_row() -> None:
    nodes = [node("N02", deps=("N03",)), node("N01"), node("N03", status="DONE")]
    assert state.next_lines(nodes, {}, MODELS) == ["N01 brief opus", "N02 brief opus"]


# --- §9 set line and dispatch -------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, facts, line",
    [
        (dict(status="TODO"), BRIEF, "N01 TODO try 0 rp 0"),
        (dict(status="BRIEFING"), Facts(), "N01 BRIEFING try 0 rp 0 · dispatch plz-planner opus"),
        (dict(status="REPLAN", r=1), BRIEF, "N01 REPLAN try 0 rp 1 · dispatch plz-planner opus"),
        (
            dict(status="RUNNING", t=1),
            BRIEF,
            "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet",
        ),
        (
            dict(status="VERIFYING", t=1),
            BRIEF,
            "N01 VERIFYING try 1 rp 0 · dispatch plz-verifier opus",
        ),
        (
            dict(status="VERIFYING", t=1),
            Facts(brief=True, verifier=True, visual=True),
            "N01 VERIFYING try 1 rp 0 · dispatch plz-visual opus",
        ),
        (
            dict(status="VERIFYING", t=1, model="sonnet/-"),
            BRIEF,
            "N01 VERIFYING try 1 rp 0 · dispatch plz-verifier sonnet",
        ),
        (dict(status="DONE", t=1), BRIEF, "N01 DONE try 1 rp 0"),
        (dict(status="BLOCKED", t=2, r=2), BRIEF, "N01 BLOCKED try 2 rp 2"),
    ],
)
def test_set_line(kwargs, facts, line) -> None:
    assert state.set_line(node(**kwargs), facts, MODELS) == line


# --- §13 resume (rows 29-32) ------------------------------------------------------


def test_resume_rows_29_to_32() -> None:
    nodes = [
        node("N01", status="RUNNING", t=2, r=1),
        node("N02", status="VERIFYING", t=1),
        node("N03", status="VERIFYING", t=1),
        node("N04", type="check", status="VERIFYING", t=1),
        node("N05", status="BRIEFING"),
        node("N06", status="REPLAN", r=1),
        node("N07", status="WAITING", note="ask: D1"),
        node("N08", status="BLOCKED", t=2, r=2),
        node("N09", status="DONE", t=1),
        node("N10", status="TODO"),
        node("N11", status="RETRY", t=1),
    ]
    result = state.resume(nodes, dirty={"N03"})
    assert [(n.status, n.tries, n.rp) for n in result.nodes] == [
        ("RUNNING", 2, 1),
        ("RUNNING", 1, 0),
        ("VERIFYING", 1, 0),
        ("VERIFYING", 1, 0),
        ("BRIEFING", 0, 0),
        ("REPLAN", 0, 1),
        ("WAITING", 0, 0),
        ("BLOCKED", 2, 2),
        ("DONE", 1, 0),
        ("TODO", 0, 0),
        ("RETRY", 1, 0),
    ]
    assert result.lines == [
        "N01 RUNNING try 2 rp 1 · rerun",
        "N02 RUNNING try 1 rp 0 · rerun",
        "N03 VERIFYING try 1 rp 0 · rerun",
        "N04 VERIFYING try 1 rp 0 · rerun",
        "N05 BRIEFING try 0 rp 0 · rerun",
        "N06 REPLAN try 0 rp 1 · rerun",
        "N07 WAITING try 0 rp 0 · held",
        "N08 BLOCKED try 2 rp 2 · held",
    ]
    assert result.logs == [
        ("N01", "rerun at try 2; partial edits of this try may be in the tree"),
        ("N02", "rerun at try 1; partial edits of this try may be in the tree"),
    ]
    assert result.status == "RUNNING"
    assert nodes[1].status == "VERIFYING"


def test_resume_done_plan_prints_nothing() -> None:
    result = state.resume([node(status="DONE", t=1)], dirty=set())
    assert (result.lines, result.logs, result.status) == ([], [], "DONE")


# --- purity -----------------------------------------------------------------------


def test_state_module_has_no_io_imports() -> None:
    source = Path(state.__file__).read_text()
    imported = set()
    for item in ast.walk(ast.parse(source)):
        if isinstance(item, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in item.names}
        elif isinstance(item, ast.ImportFrom):
            imported.add((item.module or "").split(".")[0])
    assert imported <= {"__future__", "dataclasses", "re", "planzilla", "collections", "typing"}
    assert "open(" not in source and "print(" not in source
