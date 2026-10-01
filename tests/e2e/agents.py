"""Fake agents: scripted executor, verifier and planner that talk to the CLI like the real ones.

They read their input with `brief`, write their log entry with `log` and return the one-line replies
of FORMAT §14. They may edit repo files (that is their job); the orchestrator never does.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from tests.e2e.harness import REF, Cli, plan_dir


@dataclass
class Script:
    """What the fake agents do, per node, one entry per call.

    exec: `ok` or `bad` (the content written to the Write paths), `BLOCKED <why>`, or `partial`
    (writes a partial edit, logs nothing, never replies: a stop mid-node).
    verify: `PASS` or `FAIL C2`. briefs: the brief texts the planner writes, one per Brief/Replan.
    """

    exec: dict[str, list[str]] = field(default_factory=dict)
    verify: dict[str, list[str]] = field(default_factory=dict)
    briefs: dict[str, list[str]] = field(default_factory=dict)


class FakeAgents:
    def __init__(self, root: Path, script: Script) -> None:
        self.root, self.script = root, script
        self.cli = Cli(root)
        self.calls: dict[tuple[str, str], int] = {}
        self.seen: dict[tuple[str, str], list[str]] = {}  # (role, node) -> brief output per call

    def _next(self, role: str, node: str) -> int:
        n = self.calls.get((role, node), 0)
        self.calls[(role, node)] = n + 1
        return n

    def _brief(self, role: str, node: str, *flags: str) -> str:
        out = self.cli("brief", REF, node, *flags)
        assert out.code == 0, out.err
        self.seen.setdefault((role, node), []).append(out.out)
        return out.out

    def _log(self, node: str, kind: str, text: str, *bullets: str) -> None:
        args = [arg for bullet in bullets for arg in ("-b", bullet)]
        result = self.cli("log", REF, node, kind, text, *args)
        assert result.code == 0, result.err

    def executor(self, node: str, try_: int) -> str:
        brief = self._brief("exec", node)
        action = self.script.exec[node][self._next("exec", node)]
        if action.startswith("BLOCKED"):
            why = action.removeprefix("BLOCKED").strip()
            self._log(node, "exec", f"BLOCKED · {why}")
            return f"BLOCKED {node}: {why}"
        write_line = next(line for line in brief.splitlines() if line.startswith("Write:"))
        for item in re.findall(r"`([^`]+)`", write_line):
            path = self.root / item
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{action}\n")
        if action == "partial":
            return ""
        self._log(node, "exec", "DONE · tests: 1 passed", f"wrote {action} content on try {try_}")
        return f"DONE {node} | tests: 1 passed"

    def verifier(self, node: str, agent: str) -> str:
        self._brief("verify", node, "--verify")
        verdict = self.script.verify[node][self._next("verify", node)]
        if verdict == "PASS":
            self._log(node, "verify", "PASS")
            return f"PASS {node}"
        ids = verdict.removeprefix("FAIL ")
        self._log(
            node,
            "verify",
            verdict,
            *(f"{i} nodes/{node}.md:1 - not good enough" for i in ids.split(",")),
        )
        return f"FAIL {node}: {ids}"

    def planner(self, kind: str, node: str) -> str:
        """Write the next scripted brief of an L plan, lint, log and reply."""
        text = self.script.briefs[node][self._next("plan", node)]
        path = plan_dir(self.root) / "nodes" / f"{node}.md"
        path.write_text(text)
        assert self.cli("lint", REF).code == 0
        word = "BRIEFED" if kind == "Brief" else "REPLANNED"
        self._log(node, "plan", word, f"{kind.lower()} written")
        return f"{word} {node}"
