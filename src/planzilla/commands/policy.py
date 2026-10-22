"""Atomically update existing plan harnesses, providers and role defaults."""

import argparse
import datetime
from pathlib import Path

from planzilla.commands._common import (
    LockTimeout,
    ResolveError,
    fail,
    plan_lock,
    resolve_plan,
    write_atomic,
)
from planzilla.config import load_config, plan_policy
from planzilla.plan import PlanError, load_plan, update_policy


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("plan", help="plan path or slug fragment")
    parser.add_argument("--harnesses")
    parser.add_argument("--providers")
    parser.add_argument("--models")


def today() -> str:
    return datetime.date.today().isoformat()


def run(args: argparse.Namespace) -> int:
    try:
        path = resolve_plan(args.plan, Path.cwd())
        with plan_lock(path):
            plan = load_plan(path)
            updates = {
                key: value
                for key in ("harnesses", "providers", "models")
                if (value := getattr(args, key)) is not None
            }
            changed = update_policy(plan, updates, today())
            plan_policy(load_config(plan.root), changed)
            write_atomic(plan.graph_file, changed.text)
    except (ResolveError, PlanError) as error:
        return fail(str(error), 2)
    except (LockTimeout, OSError) as error:
        return fail(str(error), 3)
    print(f"policy updated: {plan.name}")
    return 0
