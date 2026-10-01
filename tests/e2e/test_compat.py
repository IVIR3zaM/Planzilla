"""Compatibility: the kit templates lint once filled, and this repo's own plan is valid (D7)."""

import re
import shutil
from pathlib import Path

import pytest

from planzilla import config
from tests.e2e.harness import DATE, NAME, REF, Cli, git, plan_dir

REPO = Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "src" / "planzilla" / "kit" / "templates"
THIS_PLAN = REPO / ".plan" / "2026-10-01-planzilla-v1"


def template(name: str, heading: str = "#") -> str:
    """A kit template with its format-rules comment dropped and every placeholder filled."""
    text = (TEMPLATES / name).read_text()
    text = re.sub(r"<!--.*?-->\n?", "", text, flags=re.DOTALL)
    text = text.replace("YYYY-MM-DD", DATE).replace("<plan verify command>", "true")
    text = text.replace("<verify_fast command; tier S: the full verify command>", "true")
    for placeholder in re.findall(r"<a command proving[^>\n]*>", text):
        text = text.replace(placeholder, "true")
    text = re.sub(r"<[^>\n]+>", "text", text)  # every other placeholder: plain text
    if heading == "##":  # a brief as a section of a single-file plan
        text = re.sub(r"^# ", "## ", text, count=1)
    return text.rstrip("\n") + "\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".plan").mkdir(parents=True)
    return root


def test_single_file_plan_template_with_a_minimal_node_lints_clean(repo: Path) -> None:
    text = template("plan-single.md")
    node = template("node.md", heading="##")
    assert "## N02 text" in node
    (repo / ".plan" / f"{NAME}.md").write_text(text.replace("## Log\n", node + "\n## Log\n"))

    cli = Cli(repo)
    assert cli("lint", REF).lines == ["lint ok: 3 nodes, 3 waves"]
    status = cli("status", REF)
    assert status.code == 0
    assert status.lines[0].startswith("text · DRAFT · 0/3 done")


def test_directory_plan_templates_with_a_minimal_node_lint_clean(repo: Path) -> None:
    directory = plan_dir(repo)
    (directory / "nodes").mkdir(parents=True)
    (directory / "log").mkdir()
    (directory / "plan.md").write_text(template("plan.md"))
    (directory / "intent.md").write_text(template("intent.md"))
    (directory / "nodes" / "N02.md").write_text(template("node.md"))
    (directory / "log" / "N02.md").write_text(template("log.md"))

    cli = Cli(repo)
    assert cli("lint", REF).lines == ["lint ok: 4 nodes, 3 waves"]
    assert cli("status", REF).code == 0
    # the log template is readable: `stats` counts its two `try` headings, `brief` shows the node
    assert "tries 2" in cli("stats", REF).out
    brief = cli("brief", REF, "N02")
    assert brief.code == 0
    assert brief.lines[0] == "# N02 text"


def test_config_template_parses_to_the_documented_defaults(repo: Path) -> None:
    (repo / ".plan" / "config.md").write_text((TEMPLATES / "config.md").read_text())
    loaded = config.load_config(repo)
    assert (loaded.commit, loaded.push, loaded.retention) == ("per-node", "none", "keep")
    assert loaded.models == {"planner": "opus", "exec": "sonnet", "verify": "sonnet"}


def test_this_plan_passes_status_and_lint_in_a_copy(tmp_path: Path) -> None:
    """D7: the bootstrap plan of this repo is valid format as it stands."""
    if not THIS_PLAN.is_dir():
        pytest.skip("the plan was removed by its retention policy")
    root = tmp_path / "repo"
    shutil.copytree(THIS_PLAN, root / ".plan" / THIS_PLAN.name)
    git(tmp_path, "init", "-q", "repo")
    cli = Cli(root)

    lint = cli("lint", THIS_PLAN.name)
    assert (lint.code, lint.err) == (0, "")
    assert re.fullmatch(r"lint ok: \d+ nodes, \d+ waves", lint.out.strip())
    status = cli("status", THIS_PLAN.name)
    assert (status.code, status.err) == (0, "")
    assert status.lines[0].startswith("Planzilla v1 · ")
    assert cli("stats", THIS_PLAN.name).code == 0
