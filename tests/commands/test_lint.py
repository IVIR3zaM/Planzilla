"""`planzilla lint`: one test per D12 rule, each fixture breaks only its rule (FORMAT §9)."""

import shutil
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands.lint import items_overlap
from tests.commands.test_status import tree

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "lint"
SM = ".plan/2026-10-01-demo.md"
L = ".plan/2026-10-01-demo"


def lint(capsys, name: str, monkeypatch, tmp_path: Path, ref: str = SM) -> tuple[int, str, str]:
    """Lint a copy of fixture `name` from its repo root (the copy lives under `tmp_path`)."""
    root = tmp_path / name
    shutil.copytree(FIXTURES / name, root)
    monkeypatch.chdir(root)
    code = cli.main(["lint", ref])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture
def run(capsys, monkeypatch, tmp_path):
    def call(name: str, ref: str = SM):
        return lint(capsys, name, monkeypatch, tmp_path, ref)

    return call


def test_clean_single_file_plan_exits_0(run):
    assert run("clean") == (0, "lint ok: 3 nodes, 2 waves\n", "")


def test_clean_directory_plan_exits_0(run):
    assert run("l-clean", L) == (0, "lint ok: 2 nodes, 2 waves\n", "")


def test_rule_parse_reports_the_parse_error_line(run):
    assert run("parse") == (1, f"{SM}:16: parse: bad status 'FINISHED'\n", "")


def test_rule_parse_covers_a_broken_brief(run):
    assert run("brief-parse") == (1, f"{SM}:18: parse: brief N01 has no 'Do:' field\n", "")


def test_rule_tag_names_the_untagged_criterion(run):
    assert run("tag") == (1, f"{SM}:23: tag: criterion C2 has no tag\n", "")


def test_rule_tag_in_a_directory_plan_names_the_brief_file(run):
    code, out, err = run("l-tag", L)
    assert (code, err) == (1, "")
    assert out == f"{L}/nodes/N01.md:6: tag: criterion C2 has unknown tag [maybe]\n"


def test_rule_cmd_needs_a_backticked_command(run):
    code, out, _ = run("cmd")
    assert (code, out) == (
        1,
        f"{SM}:22: cmd: criterion C1 [cmd] must start with a backticked command\n",
    )


def test_rule_length_flags_a_brief_over_40_lines(run):
    assert run("length") == (1, f"{SM}:18: length: brief N01 has 41 lines (max 40)\n", "")


def test_rule_deps_flags_a_dep_that_is_not_a_node(run):
    assert run("deps") == (1, f"{SM}:17: deps: N02 depends on N09, which is not a node\n", "")


def test_rule_cycle_is_reported_on_the_first_row_of_the_cycle(run):
    code, out, _ = run("cycle")
    assert (code, out) == (1, f"{SM}:16: cycle: Graph has a cycle: N01 -> N02 -> N01\n")


def test_rule_overlap_names_both_items_on_the_second_nodes_write_line(run):
    code, out, _ = run("overlap")
    assert code == 1
    assert out == (
        f"{SM}:27: overlap: N02 Write `src/a.py` overlaps N01 Write `src/**` (same wave 1)\n"
    )


def test_a_missing_brief_is_not_a_problem(tmp_path, monkeypatch):
    root = tmp_path / "nobrief"
    shutil.copytree(FIXTURES / "l-clean", root)
    (root / L / "nodes" / "N02.md").unlink()
    monkeypatch.chdir(root)
    assert cli.main(["lint", L]) == 0


def test_overlap_is_only_checked_within_a_wave(tmp_path, monkeypatch, capsys):
    root = tmp_path / "waves"
    shutil.copytree(FIXTURES / "overlap", root)
    plan = root / SM
    plan.write_text(
        plan.read_text().replace("| N02 | Node 2 | exec | - |", "| N02 | Node 2 | exec | N01 |")
    )
    monkeypatch.chdir(root)
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 2 nodes, 2 waves\n"


def test_lint_never_writes_a_file(tmp_path, monkeypatch):
    for name, ref in (("clean", SM), ("overlap", SM), ("l-tag", L)):
        root = tmp_path / name
        shutil.copytree(FIXTURES / name, root)
        monkeypatch.chdir(root)
        before = tree(root)
        cli.main(["lint", ref])
        assert tree(root) == before


def test_unknown_plan_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["lint", "nope"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_missing_plan_file_exits_2(tmp_path, monkeypatch, capsys):
    (tmp_path / ".plan" / "2026-10-01-demo").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["lint", ".plan/2026-10-01-demo"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_a_plan_is_found_by_slug_fragment(run):
    assert run("clean", "demo")[0] == 0


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("src/planzilla/kit/**", "src/planzilla/kit/roles/x.md", True),
        (".claude/skills/plz-*/**", ".claude/agents/plz-a.md", False),
        ("src/a.py", "src/a.py", True),
        ("src/a.py", "src/b.py", False),
        ("src/", "src/a/b.py", True),
        ("**", "src/a.py", True),
        ("src/**/x.py", "src/a/b/x.py", True),
        ("src/**/x.py", "src/a/b/y.py", False),
        ("src/*.py", "src/a.py", True),
        ("src/*.py", "src/a.md", False),
        ("src/*.py", "src/a*", True),
        ("src/**", "src", True),
        ("src/a", "src/a/b", False),
        ("plz-*/x", "plz-a/*", True),
    ],
)
def test_items_overlap(a, b, expected):
    assert items_overlap(a, b) is expected
    assert items_overlap(b, a) is expected


# --- providers (D4) ------------------------------------------------------------


def _line(node: str, token: str, provider: str, row: int) -> str:
    return (
        f"{SM}:{row}: providers: {node} model {token} needs config providers to list {provider}\n"
    )


CODEX_LINES = _line("N01", "gpt-6.1-sol@high", "one of codex, copilot", 16) + _line(
    "N02", "gpt-6-astra", "one of codex, copilot", 17
)


def _providers_repo(tmp_path: Path, monkeypatch, config: str | None) -> Path:
    root = tmp_path / "providers"
    shutil.copytree(FIXTURES / "providers", root)
    if config is not None:
        (root / ".plan" / "config.md").write_text(config)
    monkeypatch.chdir(root)
    return root


def test_providers_listing_both_lints_ok(tmp_path, monkeypatch, capsys):
    _providers_repo(tmp_path, monkeypatch, "providers: claude, codex\n")
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 3 nodes, 1 waves\n"


@pytest.mark.parametrize("config", [None, "providers: claude\n"])
def test_providers_without_codex_flags_the_codex_tokens(tmp_path, monkeypatch, capsys, config):
    _providers_repo(tmp_path, monkeypatch, config)
    assert cli.main(["lint", SM]) == 1
    assert capsys.readouterr().out == CODEX_LINES


def test_portable_aliases_lint_with_codex_only_policy(tmp_path, monkeypatch, capsys):
    _providers_repo(tmp_path, monkeypatch, "providers: codex\n")
    assert cli.main(["lint", SM]) == 0
    out = capsys.readouterr().out
    assert out == "lint ok: 3 nodes, 1 waves\n"
    assert "gemini-3" not in out


def test_providers_reads_the_config_of_the_plans_repo_not_the_cwd(tmp_path, monkeypatch, capsys):
    root = _providers_repo(tmp_path, monkeypatch, "providers: claude, codex\n")
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / ".plan").mkdir(parents=True)
    (elsewhere / ".plan" / "config.md").write_text("providers: claude\n")
    monkeypatch.chdir(elsewhere)
    assert cli.main(["lint", str(root / SM)]) == 0


def test_a_broken_config_is_a_parse_problem_on_the_config_line(tmp_path, monkeypatch, capsys):
    _providers_repo(tmp_path, monkeypatch, "commit: none\nnonsense\n")
    assert cli.main(["lint", SM]) == 1
    assert capsys.readouterr().out == (
        ".plan/config.md:2: parse: expected 'key: value', got 'nonsense'\n"
    )


# --- visual (D6) ---------------------------------------------------------------

BOTH = "providers: claude, codex\n"


def _row(node: str, token: str, harness: str, row: int) -> str:
    message = f"{node} verify {token} is not a model harness {harness} runs natively"
    return f"{SM}:{row}: visual: {message}\n"


def _criterion(node: str, harness: str, line: int) -> str:
    return (
        f"{SM}:{line}: visual: {node} [visual] needs a visual agent; harness {harness} has none\n"
    )


def _visual_repo(tmp_path: Path, monkeypatch, name: str, config: str | None) -> None:
    root = tmp_path / name
    shutil.copytree(FIXTURES / name, root)
    if config is not None:
        (root / ".plan" / "config.md").write_text(config)
    monkeypatch.chdir(root)


def test_visual_on_a_native_verify_model_lints_ok(tmp_path, monkeypatch, capsys):
    _visual_repo(tmp_path, monkeypatch, "visual-ok", BOTH)
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 2 nodes, 1 waves\n"


def test_visual_flags_a_verify_model_the_harness_does_not_run_natively(
    tmp_path, monkeypatch, capsys
):
    _visual_repo(tmp_path, monkeypatch, "visual", BOTH + "models: verify=gpt-5.5\n")
    assert cli.main(["lint", SM]) == 1
    assert capsys.readouterr().out == (
        _row("N02", "sonnet@high", "claude-code", 17)
        + _row("N03", "codex@high", "claude-code", 18)
        + _row("N04", "gpt-5.5", "claude-code", 19)
    )


def test_visual_with_a_dash_verify_uses_the_config_models_verify(tmp_path, monkeypatch, capsys):
    _visual_repo(tmp_path, monkeypatch, "visual", None)
    assert cli.main(["lint", SM]) == 1
    out = capsys.readouterr().out
    assert "N04" not in out  # default verify is sonnet, native


def test_visual_under_codex_flags_each_criterion_line(tmp_path, monkeypatch, capsys):
    _visual_repo(tmp_path, monkeypatch, "visual", BOTH + "harness: codex\n")
    assert cli.main(["lint", SM]) == 1
    assert capsys.readouterr().out == "".join(
        _criterion(node, "codex", line)
        for node, line in (("N01", 26), ("N02", 33), ("N03", 40), ("N04", 47))
    )


def test_visual_never_fires_without_a_visual_criterion(tmp_path, monkeypatch, capsys):
    _visual_repo(tmp_path, monkeypatch, "providers", BOTH + "harness: codex\n")
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 3 nodes, 1 waves\n"


def test_lint_uses_plan_restriction_and_partial_role_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _providers_repo(tmp_path, monkeypatch, "providers: claude, copilot\n")
    path = root / SM
    text = path.read_text()
    header, body = text.split("\n\n", 1)
    path.write_text(
        header + "\nproviders: codex\nmodels: planner=gpt-6.1-sol@high, "
        "verify=gpt-6.1-sol@high\n\n" + body
    )
    assert cli.main(["lint", SM]) == 0
    assert capsys.readouterr().out == "lint ok: 3 nodes, 1 waves\n"
    path.write_text(
        path.read_text().replace("gpt-6.1-sol@high/opus", "gpt-6.1-sol@high/copilot::opus")
    )
    assert cli.main(["lint", SM]) == 1
    output = capsys.readouterr().out
    assert "copilot::opus" in output
    assert "copilot" in output and "providers" in output


def test_lint_uses_plan_verify_default_for_visuals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _visual_repo(tmp_path, monkeypatch, "visual", BOTH)
    path = Path(SM)
    header, body = path.read_text().split("\n\n", 1)
    path.write_text(header + "\nmodels: verify=gpt-6.1-sol@high\n\n" + body)
    assert cli.main(["lint", SM]) == 1
    assert "N04 verify gpt-6.1-sol@high" in capsys.readouterr().out
