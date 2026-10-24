"""Plan/config IO belongs to commands; parsing and path construction stay pure."""

import ast
import inspect
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from planzilla import config, plan
from planzilla.commands import _common
from tests.test_plan import FIXTURE_REPO, L_NAME, S_NAME


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE_REPO, target)
    return target


@pytest.mark.parametrize(
    ("core", "name"),
    [
        (plan, "find_plans"),
        (plan, "load_plan"),
        (plan, "load_brief"),
        (plan, "save_graph"),
        (config, "load_config"),
    ],
)
def test_filesystem_helpers_are_owned_only_by_commands(core: ModuleType, name: str) -> None:
    helper = getattr(_common, name, None)
    assert callable(helper), f"commands boundary must provide {name}"
    assert helper.__module__ == _common.__name__
    assert not hasattr(core, name), f"core must not forward or re-export {name}"


@pytest.mark.parametrize("module", [plan, config])
def test_core_has_no_io_imports_or_operations(module: ModuleType) -> None:
    tree = ast.parse(inspect.getsource(module))
    forbidden = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "tempfile",
        "time",
        "datetime",
        "io",
        "urllib",
        "importlib",
    }
    operations = {
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
        "is_dir",
        "is_file",
        "exists",
        "iterdir",
        "glob",
        "rglob",
        "stat",
        "resolve",
        "mkdir",
        "unlink",
        "rename",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".")[0] for alias in node.names} & forbidden
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden
            assert not (node.module or "").startswith("planzilla.commands")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "print", "input", "__import__"}
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in operations


def test_discovery_filters_and_sorts_only_plan_paths(repo: Path) -> None:
    directory = repo / ".plan"
    for name in ("notes.md", "2026-01-01-demo.txt", "2026-01-01-empty"):
        (directory / name).write_text("ignored unless named as a markdown plan")
    (directory / "notes").mkdir()
    assert [path.name for path in _common.find_plans(repo)] == [
        S_NAME,
        L_NAME,
        "2026-10-01-planzilla-v1",
    ]
    assert _common.find_plans(repo / "missing") == []


@pytest.mark.parametrize("directory", [False, True])
def test_missing_plan_reports_graph_file(tmp_path: Path, directory: bool) -> None:
    path = tmp_path / "2026-01-01-missing.md"
    if directory:
        path.mkdir()
    graph = path / "plan.md" if directory else path
    with pytest.raises(plan.PlanError) as error:
        _common.load_plan(path)
    assert str(error.value) == f"{graph}:1: plan file not found"


@pytest.mark.parametrize("tier", ["S", "M", "L"])
def test_boundary_loads_utf8_plans_and_jit_briefs(repo: Path, tier: str) -> None:
    path = repo / ".plan" / (L_NAME if tier == "L" else S_NAME)
    graph = path / "plan.md" if tier == "L" else path
    text = graph.read_bytes().decode("utf-8").replace("# ", "# démo ", 1)
    if tier == "M":
        text = text.replace("tier: S\n", "tier: M\n")
    graph.write_bytes(text.encode("utf-8"))
    loaded = _common.load_plan(path)
    assert loaded.tier == tier
    assert loaded.text == text
    assert "démo" in loaded.text
    brief = _common.load_brief(loaded, "N04")
    assert brief is not None and brief.id == "N04"
    assert _common.load_brief(loaded, "N02") is None


def test_config_boundary_preserves_defaults_utf8_and_diagnostics(repo: Path) -> None:
    path = repo / ".plan" / "config.md"
    path.unlink()
    assert _common.load_config(repo) == config.Config()
    path.write_bytes("# réglages\nverify: écho\n".encode())
    assert _common.load_config(repo).verify_fast == "écho"
    path.write_bytes("# réglages\nunknown: value\n".encode())
    with pytest.raises(plan.PlanError) as error:
        _common.load_config(repo)
    assert str(error.value) == f"{path}:2: unknown config key: unknown"


@pytest.mark.parametrize("name", [S_NAME, L_NAME])
def test_graph_save_skips_unchanged_and_atomically_replaces_changed(
    repo: Path, name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = _common.load_plan(repo / ".plan" / name)
    before = loaded.graph_file.read_bytes()
    replacements: list[tuple[Path, Path]] = []
    replace = _common.os.replace

    def record_replace(source: Path, destination: Path) -> None:
        assert destination.read_bytes() == before
        assert source.read_bytes() == plan.render_graph(loaded).encode("utf-8")
        replacements.append((source, destination))
        replace(source, destination)

    monkeypatch.setattr(_common.os, "replace", record_replace)
    _common.save_graph(loaded)
    assert replacements == []
    loaded.node("N02").status = "RUNNING"
    saved = _common.save_graph(loaded)
    assert replacements == [
        (loaded.graph_file.with_name(loaded.graph_file.name + ".tmp"), loaded.graph_file)
    ]
    assert saved.node("N02").status == "RUNNING"
    assert loaded.graph_file.read_bytes() == plan.render_graph(loaded).encode("utf-8")
    assert not replacements[0][0].exists()


def test_failed_atomic_replace_keeps_original_graph(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = _common.load_plan(repo / ".plan" / L_NAME)
    before = loaded.graph_file.read_bytes()
    loaded.node("N02").status = "RUNNING"

    def refuse_replace(source: Path, destination: Path) -> None:
        raise OSError("fixture replace failure")

    monkeypatch.setattr(_common.os, "replace", refuse_replace)
    with pytest.raises(OSError, match="fixture replace failure"):
        _common.save_graph(loaded)
    assert loaded.graph_file.read_bytes() == before
