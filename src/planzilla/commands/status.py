"""Print the status of a plan."""

import argparse
import sys


def add_arguments(parser: argparse.ArgumentParser) -> None:
    pass


def run(args: argparse.Namespace) -> int:
    print("not implemented: status", file=sys.stderr)
    return 2
