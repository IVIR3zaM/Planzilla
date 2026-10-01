"""A scripted orchestrator that follows FORMAT §14.

It decides only from CLI stdout lines and agent replies (L7): it never opens a plan file, a brief, a
log or a diff, and it commits only through `planzilla commit` (L6). The agents are injected.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tests.e2e.harness import Cli, Result

_ID = r"N\d+[a-z]?"
SET_LINE = re.compile(
    rf"(?P<id>{_ID}) (?P<status>[A-Z]+) try (?P<t>\d+) rp (?P<r>\d+)"
    r"(?: · dispatch (?P<agent>\S+) (?P<model>\S+))?"
)
HELD_LINE = re.compile(rf"(?P<id>{_ID}) (?:BLOCKED|WAITING) try \d+ rp \d+ · held")
CHECK_FAIL = re.compile(rf"{_ID} check FAIL (?P<ids>\S+) \(\d+/\d+ passed\)")
MAX_ROUNDS = 100


class Stopped(Exception):
    """The run was interrupted (usage limit, crash, closed session): nothing is failed."""


class RunError(Exception):
    """The orchestrator must stop and tell the user (exit 3 of `commit`, a repeated bad reply)."""


@dataclass
class Dispatch:
    id: str
    status: str
    tries: int
    agent: str


class Orchestrator:
    """Runs the §14 loop. `human(ask_line)` answers the human round with `("skip", why)`,
    `("replan",)`, `("confirm",)` or `("stop",)`. `stop_after=(id, agent)` interrupts the run right
    after that dispatch returns, before its reply is routed."""

    def __init__(
        self,
        cli: Cli,
        plan: str,
        agents: Any,
        human: Callable[[str], tuple[str, ...]] | None = None,
        stop_after: tuple[str, str] | None = None,
    ) -> None:
        self.cli, self.plan, self.agents = cli, plan, agents
        self.human, self.stop_after = human, stop_after
        self.held: set[str] = set()
        self.commits: list[tuple[str, str]] = []  # (node id, the `commit` stdout line)
        self.asked: list[str] = []  # the `brief --ask` lines shown to the human

    # --- the loop (§14 steps 1-5) ---

    def run(self) -> str:
        """Returns `done`, `held` (nothing can run, no human to ask) or `stopped`."""
        for line in self._call("resume", self.plan).lines:
            if match := HELD_LINE.fullmatch(line):
                self.held.add(match["id"])
        for _ in range(MAX_ROUNDS):
            actions = [line.split() for line in self._call("next", self.plan).lines]
            if not actions and not self.held:
                return "done"
            if not actions or all(action == "ask" for _, action, _ in actions):
                outcome = self._human_round([node for node, _, _ in actions])
                if outcome != "continue":
                    return outcome
                continue
            for node, action, _model in actions:
                self._act(node, action)
        raise RunError(f"no end after {MAX_ROUNDS} rounds")

    def _act(self, node: str, action: str) -> None:
        if action == "check":
            self._check(node)
            return
        status = {"brief": "BRIEFING", "exec": "RUNNING", "verify": "VERIFYING", "replan": "REPLAN"}
        self._set(node, status[action])

    # --- CLI calls ---

    def _call(self, *args: str, ok: tuple[int, ...] = (0,)) -> Result:
        result = self.cli(*args)
        if result.code not in ok:
            raise RunError(f"{' '.join(args)} exited {result.code}: {result.err.strip()}")
        return result

    def _set(self, node: str, status: str, note: str | None = None) -> None:
        """Run `set`, then act on its line: commit a DONE, hold BLOCKED or WAITING, dispatch."""
        args = ["set", self.plan, node, status, *(["--note", note] if note else [])]
        line = SET_LINE.fullmatch(self._call(*args).out.strip())
        if line is None:
            raise RunError(f"unreadable set line for {node}")
        self._apply(line)

    def _apply(self, line: re.Match) -> None:
        node, status = line["id"], line["status"]
        if status == "DONE":
            self._commit(node)
        elif status in ("BLOCKED", "WAITING"):
            self.held.add(node)
        if line["agent"]:
            self._dispatch(Dispatch(node, status, int(line["t"]), line["agent"]))

    def _commit(self, node: str) -> None:
        result = self._call("commit", self.plan, node)  # exit 3 stops the run
        self.commits.append((node, result.out.strip()))

    def _check(self, node: str) -> None:
        result = self._call("check", self.plan, node, ok=(0, 1))
        if result.code == 0:
            self._set(node, "VERIFYING")
        else:
            fail = CHECK_FAIL.fullmatch(result.out.strip())
            if fail is None:
                raise RunError(f"unreadable check line for {node}")
            self._set(node, "RETRY", note=f"fail {fail['ids']}")

    # --- agents ---

    def _dispatch(self, work: Dispatch) -> None:
        """Dispatch, route the reply; one malformed reply is re-dispatched once (§14 step 4)."""
        for attempt in range(2):
            reply = self._agent_reply(work)
            if self.stop_after == (work.id, work.agent):
                raise Stopped(f"stopped after {work.agent} for {work.id}")
            if self._route(work, reply):
                return
            if attempt == 0:
                again = self._call("set", self.plan, work.id, work.status).out.strip()
                match = SET_LINE.fullmatch(again)
                if match is None or not match["agent"]:
                    raise RunError(f"cannot re-dispatch {work.id}")
                work = Dispatch(work.id, work.status, int(match["t"]), match["agent"])
        raise RunError(f"{work.agent} replied badly twice for {work.id}")

    def _agent_reply(self, work: Dispatch) -> str:
        if work.agent == "plz-planner":
            return self.agents.planner("Brief" if work.status == "BRIEFING" else "Replan", work.id)
        if work.agent == "plz-executor":
            return self.agents.executor(work.id, work.tries)
        return self.agents.verifier(work.id, work.agent)

    def _route(self, work: Dispatch, reply: str) -> bool:
        node = work.id
        if work.agent == "plz-executor":
            if re.fullmatch(rf"DONE {node} \| tests: \d+ passed", reply):
                self._check(node)
                return True
            if blocked := re.fullmatch(rf"BLOCKED {node}: (.+)", reply):
                self._set(node, "REPLAN", note=f"blocked: {blocked[1]}")
                return True
        elif work.agent == "plz-planner":
            if re.fullmatch(rf"(?:BRIEFED|REPLANNED) {node}(?: \+\S+)?", reply):
                self._set(node, "TODO")
                return True
            if ask := re.fullmatch(rf"ASK {node}: (D\d+)", reply):
                self._set(node, "WAITING", note=f"ask: {ask[1]}")
                return True
        else:
            if reply == f"PASS {node}":
                self._set(node, "DONE")
                return True
            if fail := re.fullmatch(rf"FAIL {node}: (\S+)", reply):
                self._set(node, "RETRY", note=f"fail {fail[1]}")
                return True
        return False

    # --- the human round (§14 step 5) ---

    def _human_round(self, ask_nodes: list[str]) -> str:
        if self.human is None:
            return "held"
        for node in dict.fromkeys([*ask_nodes, *sorted(self.held)]):
            line = self._call("brief", self.plan, node, "--ask").out.strip()
            self.asked.append(line)
            answer = self.human(line)
            self.held.discard(node)
            if answer[0] == "stop":
                return "stopped"
            if answer[0] == "skip":
                self._set(node, "DONE", note=f"skipped: {answer[1]}")
            elif answer[0] == "confirm":
                self._set(node, "DONE")
            elif answer[0] == "replan":
                self._set(node, "REPLAN")
        return "continue"
