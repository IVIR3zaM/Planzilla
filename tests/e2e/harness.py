"""End-to-end harness: tmp git repos holding S/M/L plans, a CLI runner and assertion helpers.

The orchestrator and the fake agents (`orchestrator.py`, `agents.py`) talk to the CLI only through
`Cli`; the helpers here that read plan files and git history are for the tests' assertions.
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATE = "2026-10-01"
SLUG = "demo"
NAME = f"{DATE}-{SLUG}"
REF = SLUG  # a slug fragment is a valid plan reference (FORMAT §9)
HEADER_BUDGETS = "2 tries per brief · 1 replans per node"
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def lines(self) -> list[str]:
        return self.out.splitlines()


class Cli:
    """Runs `python -m planzilla ARGS` in a repo and keeps every call for later assertions."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[tuple[tuple[str, ...], Result]] = []

    def __call__(self, *args: str) -> Result:
        proc = subprocess.run(
            [sys.executable, "-m", "planzilla", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            env={**os.environ, **GIT_ENV},
        )
        result = Result(proc.returncode, proc.stdout, proc.stderr)
        self.calls.append((args, result))
        return result

    @property
    def commands(self) -> list[str]:
        return [args[0] for args, _ in self.calls]


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **GIT_ENV},
    )
    return done.stdout


# --- plan builders ------------------------------------------------------------------------------


@dataclass
class NodeSpec:
    id: str
    title: str
    type: str = "exec"
    deps: str = "-"
    review: bool = False  # adds a [review] criterion, so a verifier is needed
    cmd: str | None = None  # the [cmd] criterion; default: out/<id>.txt holds `ok`
    write: tuple[str, ...] | None = None  # default: out/<id>.txt for exec nodes
    brief: bool = True  # False: written just in time by the fake planner

    @property
    def writes(self) -> tuple[str, ...]:
        if self.type != "exec":
            return ()
        return self.write if self.write is not None else (f"out/{self.id}.txt",)

    @property
    def model(self) -> str:
        if self.type == "exec":
            return "sonnet/sonnet" if self.review else "sonnet/-"
        return "-/sonnet" if self.review else "-/-"

    def brief_text(self, heading: str = "#") -> str:
        cmd = self.cmd or f"grep -qx ok out/{self.id}.txt"
        lines = [f"{heading} {self.id} {self.title}", f"Do: Make {self.title} true."]
        if self.type == "exec":
            lines.append("Write: " + ", ".join(f"`{path}`" for path in self.writes))
        lines += ["Done when:", f"- C1 [cmd] `{cmd}` exits 0"]
        if self.review:
            lines.append(f"- C2 [review] {self.title} reads well")
        return "\n".join(lines) + "\n"

    def row(self) -> str:
        cells = [self.id, self.title, self.type, self.deps, self.model, "0", "0", "TODO", ""]
        return "| " + " | ".join(cells) + " |"


def exec_node(id: str, title: str, deps: str = "-", **kw: Any) -> NodeSpec:
    return NodeSpec(id, title, "exec", deps, **kw)


def check_node(id: str, title: str, deps: str = "-", cmd: str = "true", **kw: Any) -> NodeSpec:
    return NodeSpec(id, title, "check", deps, cmd=cmd, **kw)


INTENT = """Goal: exercise the CLI end to end.

In scope: a fake run.

Out of scope: everything else.

Constraints: none.

Definition of done: every node DONE.
"""


def _header(fmt: str, budgets: str) -> str:
    lines = [
        "# Demo plan",
        "status: READY",
        f"created: {DATE} · updated: {DATE}",
        "goal: exercise the CLI end to end",
        "verify: true",
        "commit: per-node",
        "push: none",
        f"budgets: {budgets}",
    ]
    if fmt in ("S", "M"):
        lines.append(f"tier: {fmt}")
    return "\n".join(lines) + "\n"


def _graph(nodes: list[NodeSpec]) -> str:
    head = "| id | title | type | deps | model | try | rp | status | note |\n"
    sep = "|----|-------|------|------|-------|-----|----|--------|------|\n"
    return "## Graph\n\n" + head + sep + "\n".join(n.row() for n in nodes) + "\n"


DECISIONS = "## Decisions\n\n- D1 The run is faked | confirmed\n"


def plan_dir(root: Path) -> Path:
    return root / ".plan" / NAME


def plan_file(root: Path) -> Path:
    """The file holding the Graph: `plan.md` of an L plan, else the single plan file."""
    directory = plan_dir(root)
    return directory / "plan.md" if directory.is_dir() else root / ".plan" / f"{NAME}.md"


def build_plan(
    root: Path, fmt: str, nodes: list[NodeSpec], budgets: str = HEADER_BUDGETS, config: str = ""
) -> None:
    """Write a READY plan of tier `fmt` (S, M or L) under `root/.plan`."""
    (root / ".plan").mkdir(parents=True, exist_ok=True)
    if config:
        (root / ".plan" / "config.md").write_text(config)
    top = _header(fmt, budgets) + "\n"
    if fmt == "L":
        directory = plan_dir(root)
        (directory / "nodes").mkdir(parents=True)
        (directory / "plan.md").write_text(top + DECISIONS + "\n" + _graph(nodes))
        (directory / "intent.md").write_text("# Intent\n\n" + INTENT)
        for node in nodes:
            if node.brief:
                (directory / "nodes" / f"{node.id}.md").write_text(node.brief_text())
        return
    briefs = "\n".join(n.brief_text("##") for n in nodes if n.brief)
    text = top + "## Intent\n\n" + INTENT + "\n" + DECISIONS + "\n" + _graph(nodes) + "\n"
    (root / ".plan" / f"{NAME}.md").write_text(text + briefs + "\n## Log\n")


def make_repo(root: Path, fmt: str, nodes: list[NodeSpec], **kw: Any) -> Cli:
    """A git repo whose base commit holds the plan; returns a CLI runner for it."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    build_plan(root, fmt, nodes, **kw)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return Cli(root)


# --- assertion helpers ----------------------------------------------------------------------------


def graph_rows(root: Path) -> dict[str, dict[str, str]]:
    """The Graph cells of the plan on disk: `{id: {column: value}}`."""
    columns = ["id", "title", "type", "deps", "model", "try", "rp", "status", "note"]
    rows = {}
    for line in plan_file(root).read_text().splitlines():
        if line.startswith("| N"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows[cells[0]] = dict(zip(columns, cells, strict=True))
    return rows


def header_status(root: Path) -> str:
    for line in plan_file(root).read_text().splitlines():
        if line.startswith("status: "):
            return line.removeprefix("status: ")
    raise AssertionError("no status line")


def node_commits(root: Path) -> list[tuple[str, str]]:
    """`(subject, sha)` of every commit after the base commit, oldest first."""
    out = git(root, "log", "--reverse", "--format=%s %h").splitlines()
    return [tuple(line.rsplit(" ", 1)) for line in out[1:]]  # type: ignore[misc]


def commit_files(root: Path, sha: str) -> set[str]:
    return set(git(root, "show", "--name-only", "--format=", sha).split())


def tree_files(root: Path) -> set[str]:
    return set(git(root, "ls-files").split())
