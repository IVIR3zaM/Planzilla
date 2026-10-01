import shutil
from pathlib import Path

import pytest

from planzilla.plan import (
    PlanError,
    find_plans,
    load_brief,
    load_plan,
    node_paths,
    save_graph,
)

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "plans" / "repo"
S_NAME = "2026-01-02-demo-s.md"
L_NAME = "2026-01-03-demo-l"
REAL_NAME = "2026-10-01-planzilla-v1"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A writable copy of the fixture repo."""
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, target)
    return target


@pytest.fixture
def s_plan(repo: Path) -> Path:
    return repo / ".plan" / S_NAME


@pytest.fixture
def l_plan(repo: Path) -> Path:
    return repo / ".plan" / L_NAME


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def line_of(path: Path, needle: str) -> int:
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if needle in line:
            return number
    raise AssertionError(needle)


# --- find_plans and layouts ------------------------------------------------


def test_find_plans_lists_files_and_dirs_but_not_config(repo: Path) -> None:
    names = [p.name for p in find_plans(repo)]
    assert names == [S_NAME, L_NAME, REAL_NAME]


def test_find_plans_without_plan_dir(tmp_path: Path) -> None:
    assert find_plans(tmp_path) == []


def test_all_three_fixtures_load(repo: Path) -> None:
    plans = [load_plan(p) for p in find_plans(repo)]
    assert [p.tier for p in plans] == ["S", "L", "L"]
    assert [p.slug for p in plans] == ["demo-s", "demo-l", "planzilla-v1"]
    assert all(p.root == repo for p in plans)


def test_s_and_l_fixtures_yield_same_nodes(s_plan: Path, l_plan: Path) -> None:
    s_nodes = load_plan(s_plan).nodes
    l_nodes = load_plan(l_plan).nodes
    assert len(s_nodes) == 6
    assert s_nodes == l_nodes


def test_real_plan_copy_loads(repo: Path) -> None:
    plan = load_plan(repo / ".plan" / REAL_NAME)
    assert plan.title == "Planzilla v1"
    assert [n.id for n in plan.nodes][:3] == ["N01", "N02", "N03"]
    assert len(plan.nodes) == 17
    assert len(plan.decisions) == 25
    assert plan.decisions[24].state == "confirmed"
    n17 = plan.node("N17")
    assert (n17.type, n17.deps, n17.exec_model, n17.verify_model) == (
        "check",
        ["N15", "N16"],
        "-",
        "opus",
    )
    n03 = load_brief(plan, "N03")
    assert n03 is not None
    assert "src/planzilla/kit/**" in n03.write
    assert n03.criteria[3].command == 'test "$(cat CLAUDE.md)" = "@AGENTS.md"'
    n17_brief = load_brief(plan, "N17")
    assert n17_brief is not None
    assert n17_brief.write is None
    assert [c.tag for c in n17_brief.criteria].count("cmd") == 6


# --- header and decisions --------------------------------------------------


def test_header_fields_s(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    h = plan.header
    assert plan.title == "Demo small plan"
    assert (h.status, h.created, h.updated) == ("RUNNING", "2026-01-02", "2026-01-03")
    assert h.goal == "Demo plan used by the parser tests"
    assert h.verify == "uv run pytest -q"
    assert (h.commit, h.push) == ("per-node", "per-node")  # `yes` is an alias
    assert (h.tries_budget, h.replans_budget) == (3, 1)
    assert h.tier == "S"
    assert h.lines["status"] == 2


def test_header_defaults_l(l_plan: Path) -> None:
    h = load_plan(l_plan).header
    assert h.status == "DRAFT"
    assert h.commit == "none"
    assert h.push is None
    assert (h.tries_budget, h.replans_budget) == (2, 2)
    assert h.tier is None


def test_decisions(s_plan: Path, l_plan: Path) -> None:
    s = load_plan(s_plan).decisions
    assert [(d.id, d.state) for d in s] == [("D1", "confirmed"), ("D2", "confirmed")]
    assert s[0].text == "Use the standard library only"
    l_ = load_plan(l_plan).decisions
    assert l_[1].state == "proposed"
    assert l_[1].line == line_of(l_plan / "plan.md", "- D2 ")


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("status: RUNNING", "status: GOING", "status"),
        ("goal: Demo plan used by the parser tests\n", "", "goal"),
        ("commit: per-node", "commit: sometimes", "commit"),
        ("push: yes", "flavour: mint", "flavour"),
        ("budgets: 3 tries per brief · 1 replans per node", "budgets: lots", "budgets"),
    ],
)
def test_bad_header_raises(s_plan: Path, old: str, new: str, message: str) -> None:
    edit(s_plan, old, new)
    with pytest.raises(PlanError) as err:
        load_plan(s_plan)
    assert message in str(err.value)


def test_tier_not_allowed_in_directory(l_plan: Path) -> None:
    edit(l_plan / "plan.md", "commit: none\n", "commit: none\ntier: S\n")
    with pytest.raises(PlanError, match="tier"):
        load_plan(l_plan)


# --- Graph columns ---------------------------------------------------------


def test_every_graph_column(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    n02 = plan.node("N02")
    assert n02.id == "N02"
    assert n02.title == "render output"
    assert n02.type == "exec"
    assert n02.deps == ["N01"]
    assert (n02.exec_model, n02.verify_model) == ("haiku", "-")
    assert (n02.tries, n02.rp) == (2, 1)
    assert n02.status == "RETRY"
    assert n02.note == "fail C2"
    assert n02.line == line_of(s_plan, "| N02 |")


def test_deps_dash_and_comma_lists(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    assert plan.node("N01").deps == []
    assert plan.node("N03").deps == ["N01", "N02"]  # "N01, N02": spaces tolerated
    assert plan.node("N03a").deps == ["N01", "N02"]


def test_models_and_types(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    assert (plan.node("N01").exec_model, plan.node("N01").verify_model) == ("sonnet", "opus")
    assert (plan.node("N04").type, plan.node("N04").exec_model) == ("check", "-")
    assert plan.node("N04").verify_model == "opus"
    n05 = plan.node("N05")
    assert (n05.type, n05.exec_model, n05.verify_model) == ("gate", "-", "-")
    assert plan.node("N01").note == ""
    assert plan.node("N03a").note == "ask: D2"


def test_unknown_node_raises(s_plan: Path) -> None:
    with pytest.raises(PlanError, match="N99"):
        load_plan(s_plan).node("N99")


# --- malformed input: one PlanError with file and line ---------------------


def test_missing_graph_raises(l_plan: Path) -> None:
    edit(l_plan / "plan.md", "## Graph", "## Grid")
    with pytest.raises(PlanError) as err:
        load_plan(l_plan)
    assert err.value.file == l_plan / "plan.md"
    assert err.value.line >= 1
    assert "Graph" in str(err.value)


def test_unknown_status_raises(s_plan: Path) -> None:
    edit(s_plan, "| RETRY | fail C2 |", "| SLEEPING | fail C2 |")
    with pytest.raises(PlanError) as err:
        load_plan(s_plan)
    assert err.value.file == s_plan
    assert err.value.line == line_of(s_plan, "| SLEEPING |")
    assert "SLEEPING" in str(err.value)
    assert str(err.value).startswith(f"{s_plan}:{err.value.line}: ")


def test_duplicate_node_id_raises(l_plan: Path) -> None:
    graph = l_plan / "plan.md"
    edit(graph, "| N03a | docs page |", "| N02 | docs page |")
    with pytest.raises(PlanError) as err:
        load_plan(l_plan)
    assert err.value.file == graph
    assert err.value.line == line_of(graph, "| N02 | docs page |")
    assert "duplicate" in str(err.value)


def test_bad_row_cells_raise(s_plan: Path) -> None:
    edit(s_plan, "| N05 | sign-off | gate | N04 | -/- |", "| N05 | sign-off | gate | N04 | -- |")
    with pytest.raises(PlanError, match="model"):
        load_plan(s_plan)


def test_brief_without_done_when_raises(l_plan: Path) -> None:
    brief = l_plan / "nodes" / "N04.md"
    edit(brief, "Done when:\n", "")
    plan = load_plan(l_plan)
    with pytest.raises(PlanError) as err:
        load_brief(plan, "N04")
    assert err.value.file == brief
    assert err.value.line == 1
    assert "Done when" in str(err.value)


def test_brief_without_done_when_raises_s(s_plan: Path) -> None:
    edit(s_plan, "Do: Check the whole demo.\nDone when:\n", "Do: Check the whole demo.\n")
    plan = load_plan(s_plan)
    with pytest.raises(PlanError) as err:
        load_brief(plan, "N04")
    assert err.value.file == s_plan
    assert err.value.line == line_of(s_plan, "## N04 acceptance")


def test_unexpected_section_in_single_file_raises(s_plan: Path) -> None:
    edit(s_plan, "## Log", "## Notes")
    with pytest.raises(PlanError) as err:
        load_plan(s_plan)
    assert err.value.line == line_of(s_plan, "## Notes")


def test_sections_out_of_order_raise(s_plan: Path) -> None:
    edit(s_plan, "## Intent\n", "")
    edit(s_plan, "## Log\n", "## Log\n\n## Intent\n")
    with pytest.raises(PlanError) as err:
        load_plan(s_plan)
    assert err.value.line == line_of(s_plan, "## Intent")


# --- briefs and criteria ---------------------------------------------------


@pytest.mark.parametrize("which", ["s", "l"])
def test_brief_fields(which: str, s_plan: Path, l_plan: Path) -> None:
    plan = load_plan(s_plan if which == "s" else l_plan)
    brief = load_brief(plan, "N01")
    assert brief is not None
    assert (brief.id, brief.title) == ("N01", "parse input")
    assert brief.value("Do") == "Parse the input file into rows; reject empty input."
    assert "Note: this `Word:` line belongs to Context." in brief.value("Context")
    assert brief.value("Read") == "`docs/FORMAT.md`"
    assert brief.value("Log") is None
    assert brief.value("Test first").startswith("`tests/test_parse.py`")
    assert brief.fields["Write"].startswith("Write: `src/demo/parse.py`")
    heading = "## N01 parse input" if which == "s" else "# N01 parse input"
    assert brief.text.split("\n")[0] == heading
    assert brief.text.endswith("- C5 [human] the owner likes the output")


def test_write_paths_split(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    brief = load_brief(plan, "N01")
    assert brief is not None
    assert brief.write == [
        "src/demo/parse.py",
        "tests/test_parse.py",
        "docs/*.md",
        "src/demo/data/",
    ]
    assert brief.field_lines["Write"] == line_of(s_plan, "Write: `src/demo")
    assert load_brief(plan, "N05").write == []  # `-`
    assert load_brief(plan, "N04").write is None  # absent


@pytest.mark.parametrize(
    "value",
    [
        "src/a.py and more",
        "`/abs/path.py`",
        "`./src/a.py`",
        "`src/../a.py`",
        "`src\\a.py`",
        "`src/a?.py`",
        "`src/{a,b}.py`",
        "`src/[ab].py`",
        "`src/a**/b.py`",
        "`src/a.py` `b.py`; `c.py`",
    ],
)
def test_bad_write_paths_raise(s_plan: Path, value: str) -> None:
    edit(s_plan, "Write: -", f"Write: {value}")
    plan = load_plan(s_plan)
    with pytest.raises(PlanError) as err:
        load_brief(plan, "N05")
    assert err.value.line == line_of(s_plan, f"Write: {value}")


def test_exec_brief_requires_write(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N01.md", "Write: `src/demo/parse.py`, `tests/test_parse.py`,\n", "")
    edit(l_plan / "nodes" / "N01.md", "  `docs/*.md`, `src/demo/data/`\n", "")
    with pytest.raises(PlanError, match="Write"):
        load_brief(load_plan(l_plan), "N01")


def test_check_brief_rejects_write_paths(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N04.md", "Done when:", "Write: `src/x.py`\nDone when:")
    with pytest.raises(PlanError, match="Write"):
        load_brief(load_plan(l_plan), "N04")


def test_every_criterion_tag(s_plan: Path) -> None:
    brief = load_brief(load_plan(s_plan), "N01")
    assert brief is not None
    assert [(c.id, c.tag) for c in brief.criteria] == [
        ("C1", "cmd"),
        ("C2", "review"),
        ("C3", "smoke"),
        ("C4", "visual"),
        ("C5", "human"),
    ]
    c1, c2, c3 = brief.criteria[:3]
    assert c1.command == "uv run pytest -q tests/test_parse.py"
    assert c1.text == "`uv run pytest -q tests/test_parse.py` exits 0"
    assert c2.text == "the parser rejects empty input with a clear error"  # continuation joined
    assert c2.command is None
    assert c3.command is None  # only [cmd] criteria carry a command
    assert c1.line == line_of(s_plan, "- C1 [cmd] `uv run pytest -q tests/test_parse.py`")


def test_criterion_without_tag_or_command_is_kept_for_lint(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N04.md", "- C1 [cmd] `uv run pytest -q`", "- C1 [cmd] run pytest")
    edit(l_plan / "nodes" / "N04.md", "- C2 [review] README", "- C2 README")
    brief = load_brief(load_plan(l_plan), "N04")
    assert brief is not None
    assert (brief.criteria[0].tag, brief.criteria[0].command) == ("cmd", None)
    assert (brief.criteria[1].tag, brief.criteria[1].text) == (None, "README describes the parser")


def test_duplicate_criterion_raises(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N04.md", "- C2 [review]", "- C1 [review]")
    with pytest.raises(PlanError, match="C1"):
        load_brief(load_plan(l_plan), "N04")


def test_fields_out_of_order_raise(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N04.md", "Do: Check the whole demo.\n", "")
    edit(l_plan / "nodes" / "N04.md", "- C2 [review] README describes the parser", "Do: late")
    with pytest.raises(PlanError):
        load_brief(load_plan(l_plan), "N04")


def test_missing_brief_is_none(s_plan: Path, l_plan: Path) -> None:
    assert load_brief(load_plan(s_plan), "N02") is None
    assert load_brief(load_plan(l_plan), "N02") is None


def test_brief_heading_must_match_node(l_plan: Path) -> None:
    edit(l_plan / "nodes" / "N04.md", "# N04 acceptance", "# N4 acceptance")
    with pytest.raises(PlanError) as err:
        load_brief(load_plan(l_plan), "N04")
    assert err.value.line == 1


# --- node paths ------------------------------------------------------------


def test_node_paths_l(l_plan: Path) -> None:
    paths = node_paths(load_plan(l_plan), "N01")
    assert paths.plan == l_plan
    assert paths.graph == l_plan / "plan.md"
    assert paths.brief == l_plan / "nodes" / "N01.md"
    assert paths.log == l_plan / "log" / "N01.md"
    assert paths.runs == l_plan / "runs" / "N01"


def test_node_paths_s(s_plan: Path) -> None:
    paths = node_paths(load_plan(s_plan), "N01")
    assert paths.plan == paths.graph == paths.brief == paths.log == s_plan
    assert paths.runs is None


# --- save_graph ------------------------------------------------------------


@pytest.mark.parametrize("which", ["s", "l"])
def test_round_trip_changes_exactly_one_cell(which: str, s_plan: Path, l_plan: Path) -> None:
    path = s_plan if which == "s" else l_plan
    graph = path if which == "s" else path / "plan.md"
    before = graph.read_bytes()
    plan = load_plan(path)
    plan.node("N02").status = "RUNNING"
    save_graph(plan)
    after = graph.read_bytes()
    old_lines, new_lines = before.split(b"\n"), after.split(b"\n")
    assert len(old_lines) == len(new_lines)
    changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines, strict=True)) if a != b]
    assert len(changed) == 1
    old_cells = old_lines[changed[0]].split(b"|")
    new_cells = new_lines[changed[0]].split(b"|")
    diff = [(a, b) for a, b in zip(old_cells, new_cells, strict=True) if a != b]
    assert diff == [(b" RETRY ", b" RUNNING ")]


def test_changed_row_writes_deps_without_spaces(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    plan.node("N03").status = "VERIFYING"
    save_graph(plan)
    text = s_plan.read_text(encoding="utf-8")
    assert "| N03 | wire cli | exec | N01,N02 | sonnet/sonnet | 1 | 0 | VERIFYING | |" in text


def test_save_unchanged_is_byte_identical(l_plan: Path) -> None:
    graph = l_plan / "plan.md"
    before = graph.read_bytes()
    save_graph(load_plan(l_plan))
    assert graph.read_bytes() == before


def test_save_writes_canonical_row_and_returns_reloaded_plan(s_plan: Path) -> None:
    plan = load_plan(s_plan)
    n03a = plan.node("N03a")
    n03a.status, n03a.note, n03a.rp = "REPLAN", "", 1
    reloaded = save_graph(plan)
    assert "| N03a | docs page | exec | N01,N02 | sonnet/haiku | 0 | 1 | REPLAN | |" in (
        s_plan.read_text(encoding="utf-8")
    )
    assert reloaded.node("N03a").status == "REPLAN"


def test_save_appends_new_node_after_last_row(l_plan: Path) -> None:
    from planzilla.plan import Node

    plan = load_plan(l_plan)
    plan.nodes.append(Node("N06", "extra", "exec", ["N03", "N04"], "sonnet", "-", 0, 0, "TODO", ""))
    reloaded = save_graph(plan)
    lines = (l_plan / "plan.md").read_text(encoding="utf-8").split("\n")
    row = lines.index("| N06 | extra | exec | N03,N04 | sonnet/- | 0 | 0 | TODO | |")
    assert lines[row - 1].startswith("| N05 |")
    assert lines[row + 1] == ""
    assert [n.id for n in reloaded.nodes][-1] == "N06"
