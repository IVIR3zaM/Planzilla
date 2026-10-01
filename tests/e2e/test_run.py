"""End-to-end runs: a scripted orchestrator (FORMAT §14) drives the CLI over S, M and L plans.

Each test builds a plan in a tmp git repo, runs the loop with fake agents and asserts the three
records of a run: the CLI lines the orchestrator saw, the Graph cells, and the git history.
"""

import re
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.agents import FakeAgents, Script
from tests.e2e.harness import (
    NAME,
    REF,
    Cli,
    NodeSpec,
    check_node,
    commit_files,
    exec_node,
    git,
    graph_rows,
    header_status,
    make_repo,
    node_commits,
    tree_files,
)
from tests.e2e.orchestrator import Orchestrator, RunError, Stopped

SHA = r"[0-9a-f]{7}"
PLAN_FILE = f".plan/{NAME}.md"
DONE_LINE = rf"committed {SHA} · plan DONE · retention keep"


class Run:
    """A built repo plus the fake agents and an orchestrator over it."""

    def __init__(
        self, tmp_path: Path, fmt: str, nodes: list[NodeSpec], script: Script, **kw: Any
    ) -> None:
        self.root = tmp_path / "repo"
        self.nodes = nodes
        self.fmt = fmt
        self.cli = make_repo(self.root, fmt, nodes, **kw)
        self.agents = FakeAgents(self.root, script)

    def orchestrate(self, **kw: Any) -> Orchestrator:
        return Orchestrator(Cli(self.root), REF, self.agents, **kw)


def sha_free(lines: list[str]) -> list[str]:
    return [re.sub(SHA, "<sha>", line) for line in lines]


def calls(orch: Orchestrator) -> list[str]:
    """The orchestrator's CLI calls, as text with the plan reference dropped."""
    return [" ".join(a for a in args if a != REF) for args, _ in orch.cli.calls]


def run_to_end(
    tmp_path: Path, fmt: str, nodes: list[NodeSpec], script: Script, **kw: Any
) -> tuple[Run, Orchestrator, str]:
    run = Run(tmp_path, fmt, nodes, script, **kw)
    orch = run.orchestrate()
    return run, orch, orch.run()


# --- (a) S plan, one node, straight to DONE ---


def test_a_s_plan_one_node_goes_straight_to_done(tmp_path: Path) -> None:
    node = exec_node("N01", "greeting", review=True)
    script = Script(exec={"N01": ["ok"]}, verify={"N01": ["PASS"]})
    run, orch, outcome = run_to_end(tmp_path, "S", [node], script)

    assert outcome == "done"
    assert sha_free(calls(orch)) == [
        "resume",
        "next",
        "set N01 RUNNING",
        "check N01",
        "set N01 VERIFYING",
        "set N01 DONE",
        "commit N01",
        "next",
    ]
    lines = [result.out.strip() for _, result in orch.cli.calls]
    assert lines[1] == "N01 exec sonnet"
    assert lines[2] == "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet"
    assert lines[3] == "N01 check PASS 1/1"
    assert lines[4] == "N01 VERIFYING try 1 rp 0 · dispatch plz-verifier sonnet"
    assert lines[5] == "N01 DONE try 1 rp 0"
    assert re.fullmatch(rf"N01 {DONE_LINE}", lines[6])
    assert lines[7] == ""  # next prints nothing: the plan is done

    assert graph_rows(run.root)["N01"] | {"title": ""} == {
        "id": "N01", "title": "", "type": "exec", "deps": "-", "model": "sonnet/sonnet",
        "try": "1", "rp": "0", "status": "DONE", "note": "",
    }  # fmt: skip
    assert header_status(run.root) == "DONE"
    assert [subject for subject, _ in node_commits(run.root)] == ["demo N01: greeting"]
    sha = node_commits(run.root)[0][1]
    assert commit_files(run.root, sha) == {PLAN_FILE, "out/N01.txt"}
    assert git(run.root, "status", "--porcelain") == ""
    assert (run.root / "out/N01.txt").read_text() == "ok\n"


# --- (b) M plan with a diamond, one verifier FAIL then PASS ---

DIAMOND = [
    check_node("N01", "preflight", cmd="test -d .plan"),
    exec_node("N02", "left", deps="N01"),
    exec_node("N03", "right", deps="N01"),
    exec_node("N04", "join", deps="N02,N03", review=True),
    check_node("N05", "acceptance", deps="N04", cmd="grep -qx ok out/N04.txt"),
]


def test_b_m_diamond_with_one_fail_then_pass(tmp_path: Path) -> None:
    script = Script(
        exec={"N02": ["ok"], "N03": ["ok"], "N04": ["ok", "ok"]},
        verify={"N04": ["FAIL C2", "PASS"]},
    )
    run, orch, outcome = run_to_end(tmp_path, "M", DIAMOND, script)

    assert outcome == "done"
    lines = {args: result.out.strip() for args, result in orch.cli.calls}
    assert lines[("next", REF)] == ""  # the last call: nothing left
    # the diamond: N02 and N03 are ready together once the preflight is DONE
    nexts = [result.out for args, result in orch.cli.calls if args[0] == "next"]
    assert nexts[0] == "N01 check -\n"
    assert nexts[1] == "N02 exec sonnet\nN03 exec sonnet\n"
    assert nexts[2] == "N04 exec sonnet\n"
    assert nexts[3] == "N04 exec sonnet\n"  # RETRY after the verifier's FAIL
    assert nexts[4] == "N05 check -\n"

    outputs = [result.out.strip() for args, result in orch.cli.calls if args[0] == "set"]
    assert "N04 VERIFYING try 1 rp 0 · dispatch plz-verifier sonnet" in outputs
    assert "N04 RETRY try 1 rp 0" in outputs
    assert "N04 RUNNING try 2 rp 0 · dispatch plz-executor sonnet" in outputs
    assert outputs[-1] == "N05 DONE try 1 rp 0"
    assert "N01 DONE try 1 rp 0" in outputs  # a cmd-only check node is DONE at its first set

    assert {
        k: (v["try"], v["rp"], v["status"], v["note"]) for k, v in graph_rows(run.root).items()
    } == {
        "N01": ("1", "0", "DONE", ""),
        "N02": ("1", "0", "DONE", ""),
        "N03": ("1", "0", "DONE", ""),
        "N04": ("2", "0", "DONE", ""),
        "N05": ("1", "0", "DONE", ""),
    }
    assert header_status(run.root) == "DONE"

    # the retry brief carries the verifier's finding (FORMAT §9 brief, findings of try t-1)
    retry_brief = run.agents.seen[("exec", "N04")][1]
    assert "## Findings (try 1)" in retry_brief
    assert "verify: FAIL C2" in retry_brief
    # the cold verifier never sees findings or logs
    assert all("Findings" not in text for text in run.agents.seen[("verify", "N04")])

    commits = node_commits(run.root)
    assert [s for s, _ in commits] == [
        "demo N01: preflight",
        "demo N02: left",
        "demo N03: right",
        "demo N04: join",
        "demo N05: acceptance",
    ]
    files = {s.split(":")[0].split()[1]: commit_files(run.root, sha) for s, sha in commits}
    assert files == {
        "N01": {PLAN_FILE},
        "N02": {PLAN_FILE, "out/N02.txt"},
        "N03": {PLAN_FILE, "out/N03.txt"},
        "N04": {PLAN_FILE, "out/N04.txt"},
        "N05": {PLAN_FILE},
    }
    assert [node for node, _ in orch.commits] == ["N01", "N02", "N03", "N04", "N05"]
    assert re.fullmatch(rf"N05 {DONE_LINE}", orch.commits[-1][1])
    assert all(re.fullmatch(rf"N0\d committed {SHA}", line) for _, line in orch.commits[:-1])
    assert git(run.root, "status", "--porcelain") == ""


# --- (c) L plan: just-in-time briefs, a replan, a node that runs out of replans ---

L_NODES = [
    check_node("N01", "preflight", cmd="test -d .plan"),
    exec_node("N02", "alpha", deps="N01", brief=False),
    exec_node("N03", "beta", deps="N01", brief=False),
    exec_node("N04", "gamma", deps="N01", brief=False),
    exec_node("N05", "delta", deps="N03,N04", review=True, brief=False),
    check_node("N06", "final", deps="N05", cmd="grep -qx ok out/N05.txt"),
]
P = f".plan/{NAME}/"


def l_script() -> Script:
    alpha_v2 = exec_node("N02", "alpha", cmd="grep -qx ok out/N02.txt && true")
    beta_v2 = exec_node("N03", "beta", cmd="grep -qx ok out/N03.txt && true")
    return Script(
        exec={
            "N02": ["bad", "bad", "ok"],
            "N03": ["BLOCKED no api", "BLOCKED still no api"],
            "N04": ["ok"],
            "N05": ["ok"],
        },
        verify={"N05": ["PASS"]},
        briefs={
            "N02": [L_NODES[1].brief_text(), alpha_v2.brief_text()],
            "N03": [L_NODES[2].brief_text(), beta_v2.brief_text()],
            "N04": [L_NODES[3].brief_text()],
            "N05": [L_NODES[4].brief_text()],
        },
    )


def test_c_l_plan_just_in_time_briefs_replans_and_a_blocked_node(tmp_path: Path) -> None:
    run = Run(tmp_path, "L", L_NODES, l_script())
    seen = {}

    def human(line: str) -> tuple[str, ...]:
        seen["commits"] = [node for node, _ in orch.commits]
        seen["status"] = Cli(run.root)("status", REF).lines[0]
        return ("skip", "no api")

    orch = run.orchestrate(human=human)
    assert orch.run() == "done"

    # independent nodes kept running while N03 was BLOCKED; the human saw one line, the plan BLOCKED
    assert seen["commits"] == ["N01", "N04", "N02"]
    assert seen["status"].startswith("Demo plan · BLOCKED · 3/6 done")
    assert orch.asked == ["N03 blocked: still no api"]
    assert [node for node, _ in orch.commits] == ["N01", "N04", "N02", "N03", "N05", "N06"]

    sets = [r.out.strip() for args, r in orch.cli.calls if args[0] == "set"]
    # just-in-time briefs: BRIEFING first, the planner is dispatched on the planner model
    assert "N02 BRIEFING try 0 rp 0 · dispatch plz-planner opus" in sets
    assert "N02 TODO try 0 rp 0" in sets
    # N02 used both tries (B=2), then the redirect gave REPLAN and the planner was dispatched
    assert "N02 RETRY try 1 rp 0" in sets
    assert "N02 REPLAN try 2 rp 1 · dispatch plz-planner opus" in sets
    assert "N02 TODO try 0 rp 1" in sets
    # N03: a BLOCKED executor replans once (R=1), then the budget is out
    assert "N03 REPLAN try 1 rp 1 · dispatch plz-planner opus" in sets
    assert "N03 BLOCKED try 1 rp 1" in sets
    # the human skipped it: DONE with the note, committed
    assert "N03 DONE try 1 rp 1" in sets

    rows = graph_rows(run.root)
    assert {k: (v["try"], v["rp"], v["status"], v["note"]) for k, v in rows.items()} == {
        "N01": ("1", "0", "DONE", ""),
        "N02": ("1", "1", "DONE", ""),
        "N03": ("1", "1", "DONE", "skipped: no api"),
        "N04": ("1", "0", "DONE", ""),
        "N05": ("1", "0", "DONE", ""),
        "N06": ("1", "0", "DONE", ""),
    }
    assert header_status(run.root) == "DONE"

    commits = node_commits(run.root)
    assert [s for s, _ in commits] == [
        "demo N01: preflight",
        "demo N04: gamma",
        "demo N02: alpha",
        "demo N03: beta",
        "demo N05: delta",
        "demo N06: final",
    ]
    # §10: Write paths and the plan; log/ and runs/ only of the committed node
    expected = [
        {P + "plan.md", P + "log/N01.md", P + "runs/N01/check-try1.txt"},
        {
            P + "plan.md", P + "nodes/N02.md", P + "nodes/N03.md", P + "nodes/N04.md",
            P + "log/N04.md", P + "runs/N04/check-try1.txt", "out/N04.txt",
        },
        {
            P + "plan.md", P + "nodes/N02.md", P + "log/N02.md", "out/N02.txt",
            P + "runs/N02/check-try1.txt", P + "runs/N02/check-try2.txt",
        },
        {P + "plan.md", P + "log/N03.md"},  # skipped: its Write path matches nothing
        {
            P + "plan.md", P + "nodes/N05.md", P + "log/N05.md",
            P + "runs/N05/check-try1.txt", "out/N05.txt",
        },
        {P + "plan.md", P + "log/N06.md", P + "runs/N06/check-try1.txt"},
    ]  # fmt: skip
    assert [commit_files(run.root, sha) for _, sha in commits] == expected
    assert re.fullmatch(rf"N06 {DONE_LINE}", orch.commits[-1][1])
    assert git(run.root, "status", "--porcelain") == ""
    # L7: the orchestrator used only the loop's commands (and `brief` only for `--ask`)
    assert set(orch.cli.commands) == {"resume", "next", "set", "check", "commit", "brief"}
    assert [args for args, _ in orch.cli.calls if args[0] == "brief"] == [
        ("brief", REF, "N03", "--ask")
    ]

    # the finishing view
    status = Cli(run.root)("status", REF).lines
    assert status[0].startswith("Demo plan · DONE · 6/6 done")
    stats = Cli(run.root)("stats", REF).out.strip()
    assert re.fullmatch(
        r"nodes 6 · done 6 · tries 9 · replans 2 · blocked 0 · commits 6 · wall \S+", stats
    )


# --- (d) a stop mid-node, then `resume` reruns it with the try kept (D18) ---

CHAIN = [
    check_node("N01", "preflight", cmd="test -d .plan"),
    exec_node("N02", "first", deps="N01"),
    exec_node("N03", "second", deps="N02"),
]


def test_d_stop_mid_node_then_resume_reruns_it_with_try_kept(tmp_path: Path) -> None:
    script = Script(exec={"N02": ["partial", "ok"], "N03": ["ok"]})
    run = Run(tmp_path, "M", CHAIN, script)

    with pytest.raises(Stopped):
        run.orchestrate(stop_after=("N02", "plz-executor")).run()
    # the stop spent nothing: N02 is RUNNING at try 1, its partial edit is in the tree, uncommitted
    row = graph_rows(run.root)["N02"]
    assert (row["status"], row["try"], row["rp"]) == ("RUNNING", "1", "0")
    assert (run.root / "out/N02.txt").read_text() == "partial\n"
    assert [s for s, _ in node_commits(run.root)] == ["demo N01: preflight"]
    assert "N02 executing" in Cli(run.root)("status", REF).out

    second = run.orchestrate()
    assert second.run() == "done"
    first_calls = [(args[0], r.out.strip()) for args, r in second.cli.calls][:4]
    assert first_calls == [
        ("resume", "N02 RUNNING try 1 rp 0 · rerun"),
        ("next", "N02 exec sonnet"),
        ("set", "N02 RUNNING try 1 rp 0 · dispatch plz-executor sonnet"),  # try kept, not 2
        ("check", "N02 check PASS 1/1"),
    ]
    # the rerun brief names the interruption and has no findings (the try did not fail)
    rerun_brief = run.agents.seen[("exec", "N02")][1]
    assert "Rerun: this try was interrupted" in rerun_brief
    assert "Findings" not in rerun_brief
    assert "Rerun" not in run.agents.seen[("exec", "N02")][0]
    assert (
        "resume: rerun at try 1; partial edits of this try may be in the tree"
        in (run.root / ".plan" / f"{NAME}.md").read_text()
    )

    assert {k: (v["try"], v["rp"], v["status"]) for k, v in graph_rows(run.root).items()} == {
        "N01": ("1", "0", "DONE"),
        "N02": ("1", "0", "DONE"),
        "N03": ("1", "0", "DONE"),
    }
    assert [s for s, _ in node_commits(run.root)] == [
        "demo N01: preflight",
        "demo N02: first",
        "demo N03: second",
    ]
    assert (run.root / "out/N02.txt").read_text() == "ok\n"


# --- (e) the finishing commit applies retention (keep is the default) ---


@pytest.mark.parametrize("fmt", ["S", "M", "L"])
def test_e_finishing_commit_keeps_the_records_by_default(tmp_path: Path, fmt: str) -> None:
    nodes = [exec_node("N01", "one"), exec_node("N02", "two", deps="N01")]
    run, orch, outcome = run_to_end(
        tmp_path, fmt, nodes, Script(exec={"N01": ["ok"], "N02": ["ok"]})
    )

    assert outcome == "done"
    # exactly one commit per node: the finishing commit is N02's, never a separate one
    assert [s for s, _ in node_commits(run.root)] == ["demo N01: one", "demo N02: two"]
    assert re.fullmatch(rf"N01 committed {SHA}", orch.commits[0][1])
    assert re.fullmatch(rf"N02 {DONE_LINE}", orch.commits[1][1])
    # keep: the plan and its records are still in HEAD
    kept = tree_files(run.root)
    if fmt == "L":
        assert {
            P + "plan.md",
            P + "log/N01.md",
            P + "log/N02.md",
            P + "runs/N02/check-try1.txt",
        } <= kept
    else:
        assert PLAN_FILE in kept
        assert "### N02 try 1 ·" in (run.root / PLAN_FILE).read_text()
    assert header_status(run.root) == "DONE"
    assert {k: (v["try"], v["rp"], v["status"]) for k, v in graph_rows(run.root).items()} == {
        "N01": ("1", "0", "DONE"),
        "N02": ("1", "0", "DONE"),
    }


def test_e_prune_logs_removes_log_and_runs_in_the_finishing_commit_only(tmp_path: Path) -> None:
    nodes = [exec_node("N01", "one"), exec_node("N02", "two", deps="N01")]
    script = Script(exec={"N01": ["ok"], "N02": ["ok"]})
    run, orch, outcome = run_to_end(tmp_path, "L", nodes, script, config="retention: prune-logs\n")

    assert outcome == "done"
    assert re.fullmatch(
        rf"N02 committed {SHA} · plan DONE · retention prune-logs", orch.commits[1][1]
    )
    assert len(node_commits(run.root)) == 2  # no retention-only commit
    assert {k: (v["try"], v["rp"], v["status"]) for k, v in graph_rows(run.root).items()} == {
        "N01": ("1", "0", "DONE"),
        "N02": ("1", "0", "DONE"),
    }
    kept = tree_files(run.root)
    assert P + "plan.md" in kept
    assert not any(path.startswith((P + "log/", P + "runs/")) for path in kept)
    assert git(run.root, "status", "--porcelain") == ""


# --- the loop's own rules ---


class Garbling(FakeAgents):
    """An executor whose first `garbled` replies are not a valid reply line."""

    def __init__(self, root: Path, script: Script, garbled: int) -> None:
        super().__init__(root, script)
        self.garbled = garbled

    def executor(self, node: str, try_: int) -> str:
        reply = super().executor(node, try_)
        if self.garbled:
            self.garbled -= 1
            return "all done, I think"
        return reply


def test_a_malformed_reply_is_redispatched_once_with_the_same_status(tmp_path: Path) -> None:
    run = Run(tmp_path, "S", [exec_node("N01", "one")], Script(exec={"N01": ["ok", "ok"]}))
    run.agents = Garbling(run.root, run.agents.script, garbled=1)
    orch = run.orchestrate()

    assert orch.run() == "done"
    sets = [r.out.strip() for args, r in orch.cli.calls if args[0] == "set"]
    assert sets[:2] == [
        "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet",
        "N01 RUNNING try 1 rp 0 · dispatch plz-executor sonnet",  # row 28: same status, same try
    ]
    assert [s for s, _ in node_commits(run.root)] == ["demo N01: one"]


def test_a_malformed_reply_twice_stops_the_run(tmp_path: Path) -> None:
    run = Run(tmp_path, "S", [exec_node("N01", "one")], Script(exec={"N01": ["ok", "ok"]}))
    run.agents = Garbling(run.root, run.agents.script, garbled=2)

    with pytest.raises(RunError, match="replied badly twice"):
        run.orchestrate().run()
    assert graph_rows(run.root)["N01"]["status"] == "RUNNING"
    assert node_commits(run.root) == []


def test_the_orchestrator_never_opens_plan_files() -> None:
    """C3: the driver module has no file access at all; only CLI stdout drives it."""
    source = (Path(__file__).parent / "orchestrator.py").read_text()
    for forbidden in ("open(", "read_text", "read_bytes", "pathlib", "Path", "os.", "glob", "git"):
        assert forbidden not in source.replace("Orchestrator", ""), forbidden
