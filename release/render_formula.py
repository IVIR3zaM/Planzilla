"""Render the Homebrew formula from release/planzilla.rb.tmpl (stdlib only).

Usage: render_formula.py URL SHA256   (prints the formula to stdout)
"""

import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "planzilla.rb.tmpl"


def render(url: str, sha256: str) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, value in (("@URL@", url), ("@SHA256@", sha256)):
        text = text.replace(key, value)
    return text


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: render_formula.py URL SHA256", file=sys.stderr)
        return 2
    url, sha256 = argv
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
        print("sha256 must be 64 hex characters", file=sys.stderr)
        return 2
    sys.stdout.write(render(url, sha256.lower()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
