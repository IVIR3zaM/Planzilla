"""Append a log entry for a node.

Also holds the helpers `brief` and `check` share: plan resolution, the plan lock, atomic writes and
log reading and appending (FORMAT §7, §9).
"""

import argparse
import contextlib
import datetime
import os
import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from planzilla.plan import PLAN_NAME, Node, Plan, PlanError, find_plans, load_plan, node_paths

KINDS = ("exec", "verify", "plan", "human", "note")
LOCK_TIMEOUT = 10.0
LOCK_INTERVAL = 0.05
LOCK_STALE = 60.0

_FAIL_RE = re.compile(r"(check|verify): FAIL( |$)")


class CliError(Exception):
    """A command failure: printed as `error: <message>`, exit `code` (FORMAT §9)."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def guarded(func: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> int:
    """Run a command body; turn its errors into the one-line `error:` form."""
    try:
        return func(args)
    except (CliError, PlanError) as error:
        print(f"error: {error}", file=sys.stderr)
        return error.code if isinstance(error, CliError) else 2


def today() -> str:
    return datetime.date.today().isoformat()


# --- plan reference, lock, atomic write ------------------------------------


def _plan_name(path: Path) -> str:
    return path.name if path.is_dir() else path.stem


def _is_plan_path(path: Path) -> bool:
    if path.parent.name != ".plan":
        return False
    if path.is_dir():
        return PLAN_NAME.fullmatch(path.name) is not None
    return path.is_file() and path.suffix == ".md" and PLAN_NAME.fullmatch(path.stem) is not None


def resolve_plan(ref: str, cwd: Path) -> Path:
    """A path to a plan under some `.plan/`, or a slug fragment matched in `<cwd>/.plan/`."""
    candidate = (cwd / ref).resolve()
    if candidate.exists() and _is_plan_path(candidate):
        return candidate
    matches = [path for path in find_plans(cwd) if ref in _plan_name(path)]
    if not matches:
        raise CliError(f"no plan matches {ref!r}")
    if len(matches) > 1:
        names = ", ".join(_plan_name(path) for path in matches)
        raise CliError(f"plan {ref!r} is ambiguous: {names}")
    return matches[0].resolve()


@contextlib.contextmanager
def locked(path: Path, timeout: float | None = None) -> Iterator[None]:
    """Hold the lock directory `<path>.lock` (FORMAT §9): retry every 50 ms, stale after 60 s."""
    lock = path.with_name(path.name + ".lock")
    deadline = time.monotonic() + (LOCK_TIMEOUT if timeout is None else timeout)
    while True:
        try:
            os.mkdir(lock)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > LOCK_STALE:
                    os.rmdir(lock)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise CliError(f"timed out waiting for lock {lock}", 3) from None
            time.sleep(LOCK_INTERVAL)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.rmdir(lock)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    tmp.replace(path)


# --- log reading (pure) ------------------------------------------------------


@dataclass
class Entry:
    """One log entry of a node: its key (`try 1`, `brief`, `replan 1`) and the lines under it."""

    key: str
    lines: list[str]


def heading_key(heading: str) -> str:
    """The attempt key of a heading text: everything before ` · <date>`."""
    return heading.split(" · ")[0].strip()


def _log_start(lines: list[str]) -> int | None:
    return lines.index("## Log") if "## Log" in lines else None


def parse_entries(text: str, is_dir: bool, node_id: str) -> list[Entry]:
    """The node's entries, in order. L: the log file text; S/M: the plan file text."""
    lines = text.split("\n")
    if not is_dir:
        start = _log_start(lines)
        lines = [] if start is None else lines[start + 1 :]
    prefix = "## " if is_dir else "### "
    entries: list[Entry] = []
    current: Entry | None = None
    for line in lines:
        if line.startswith(prefix):
            key = heading_key(line[len(prefix) :])
            if not is_dir:
                owner, _, key = key.partition(" ")
                if owner != node_id:
                    current = None
                    continue
            current = Entry(key, [])
            entries.append(current)
        elif current is not None:
            current.lines.append(line)
    return entries


def last_findings(entries: list[Entry]) -> list[str]:
    """The last `check: FAIL` or `verify: FAIL` line with its bullets (FORMAT §7)."""
    for entry in reversed(entries):
        for index in range(len(entry.lines) - 1, -1, -1):
            if not _FAIL_RE.match(entry.lines[index]):
                continue
            found = [entry.lines[index]]
            for line in entry.lines[index + 1 :]:
                if line.startswith("- "):
                    found.append(line)
                elif line.strip():
                    break
            return found
    return []


def has_rerun_marker(entries: list[Entry], tries: int) -> bool:
    """A `resume:` line after the last heading whose key is `try <tries>` (FORMAT §7)."""
    for index in range(len(entries) - 1, -1, -1):
        if entries[index].key == f"try {tries}":
            return any(
                line.startswith("resume:") for entry in entries[index:] for line in entry.lines
            )
    return False


def read_log(plan: Plan, node_id: str) -> str:
    """The text `parse_entries` reads: the node's log file (L, may be missing) or the plan file."""
    path = node_paths(plan, node_id).log
    return path.read_bytes().decode("utf-8") if path.is_file() else ""


# --- log writing -------------------------------------------------------------


def try_number(node: Node) -> int:
    """The attempt number: t + 1 for an attempt about to start (TODO, RETRY), else t."""
    return node.tries + 1 if node.status in ("TODO", "RETRY") else node.tries


def entry_key(node: Node) -> str:
    if node.status == "BRIEFING":
        return "brief"
    if node.status == "REPLAN":
        return f"replan {node.rp}"
    return f"try {try_number(node)}"


def _last_heading_key(text: str, is_dir: bool) -> str | None:
    lines = text.split("\n")
    if not is_dir:
        start = _log_start(lines)
        lines = [] if start is None else lines[start + 1 :]
    prefix = "## " if is_dir else "### "
    for line in reversed(lines):
        if line.startswith(prefix):
            return heading_key(line[len(prefix) :])
    return None


def append_entry(
    text: str, is_dir: bool, node_id: str, key: str, today: str, lines: list[str]
) -> str:
    """`text` plus the entry lines; a new heading first when the last heading's key differs."""
    if text and not text.endswith("\n"):
        text += "\n"
    if not is_dir and _log_start(text.split("\n")) is None:
        text += ("" if text.endswith("\n\n") else "\n") + "## Log\n\n"
    label = key if is_dir else f"{node_id} {key}"
    if _last_heading_key(text, is_dir) != label:
        if not text.endswith("\n\n"):
            text += "\n"
        text += f"{'##' if is_dir else '###'} {label} · {today}\n"
    return text + "\n".join(lines) + "\n"


def append_log(plan: Plan, node_id: str, lines: list[str], today: str) -> None:
    """Append an entry to the node's log (L file or S/M `## Log`); the caller holds the lock."""
    node = plan.node(node_id)
    target = node_paths(plan, node_id).log
    text = target.read_bytes().decode("utf-8") if target.is_file() else f"# {node_id} log\n\n"
    write_atomic(target, append_entry(text, plan.is_dir, node_id, entry_key(node), today, lines))


def _one_line(text: str) -> str:
    return " ".join(text.split())


def entry_lines(kind: str, text: str, bullets: list[str]) -> list[str]:
    head = f"{kind}: {_one_line(text)}".rstrip()
    return [head, *(f"- {_one_line(bullet)}" for bullet in bullets)]


# --- command -----------------------------------------------------------------


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("plan", help="plan path or slug fragment")
    parser.add_argument("node", help="node id")
    parser.add_argument("kind", help=f"entry kind: {', '.join(KINDS)}")
    parser.add_argument("text", help="text after the kind")
    parser.add_argument(
        "-b", "--bullet", dest="bullets", action="append", default=[], help="a bullet line"
    )


def _run(args: argparse.Namespace) -> int:
    if args.kind not in KINDS:
        raise CliError(f"unknown kind {args.kind!r}; expected one of {', '.join(KINDS)}")
    path = resolve_plan(args.plan, Path.cwd())
    with locked(path):
        plan = load_plan(path)
        append_log(plan, args.node, entry_lines(args.kind, args.text, args.bullets), today())
    return 0


def run(args: argparse.Namespace) -> int:
    return guarded(_run, args)
