"""Tests for `planzilla install` (FORMAT §9, §11)."""

import os
import shutil
import subprocess
import sys
import tarfile
from importlib import resources
from pathlib import Path

import pytest

import planzilla
from planzilla import cli
from planzilla.commands import install

BEGIN = "<!-- planzilla:begin -->"
END = "<!-- planzilla:end -->"

FAKE_KIT = {
    "__init__.py": '__version__ = "9.9.9"\n',
    "cli.py": "def main(argv=None):\n    return 0\n",
    "kit/roles/planner.md": "planner role\n",
    "kit/roles/executor.md": "executor role\n",
    "kit/roles/verifier.md": "verifier role\n",
    "kit/roles/visual.md": "visual role\n",
    "kit/templates/plan.md": "plan template\n",
    "kit/templates/node.md": "node template\n",
    "kit/agents/claude/plz-planner.md": "planner agent\n",
    "kit/agents/claude/plz-executor.md": "executor agent\n",
    "kit/skills/plz-new-plan/SKILL.md": "new plan skill\n",
    "kit/skills/plz-run-plan/SKILL.md": "run plan skill\n",
    "kit/AGENTS-block.md": "Use .planzilla/plz.\n",
}

FAKE_KIT_PATHS = {
    ".planzilla/VERSION",
    ".planzilla/plz",
    ".planzilla/lib/planzilla/__init__.py",
    ".planzilla/lib/planzilla/cli.py",
    ".planzilla/lib/planzilla/kit/roles/planner.md",
    ".planzilla/lib/planzilla/kit/roles/executor.md",
    ".planzilla/lib/planzilla/kit/roles/verifier.md",
    ".planzilla/lib/planzilla/kit/roles/visual.md",
    ".planzilla/lib/planzilla/kit/templates/plan.md",
    ".planzilla/lib/planzilla/kit/templates/node.md",
    ".planzilla/lib/planzilla/kit/agents/claude/plz-planner.md",
    ".planzilla/lib/planzilla/kit/agents/claude/plz-executor.md",
    ".planzilla/lib/planzilla/kit/skills/plz-new-plan/SKILL.md",
    ".planzilla/lib/planzilla/kit/skills/plz-run-plan/SKILL.md",
    ".planzilla/lib/planzilla/kit/AGENTS-block.md",
    ".planzilla/roles/planner.md",
    ".planzilla/roles/executor.md",
    ".planzilla/roles/verifier.md",
    ".planzilla/roles/visual.md",
    ".planzilla/templates/plan.md",
    ".planzilla/templates/node.md",
    ".claude/agents/plz-planner.md",
    ".claude/agents/plz-executor.md",
    ".claude/skills/plz-new-plan/SKILL.md",
    ".claude/skills/plz-run-plan/SKILL.md",
    ".agents/skills/plz-new-plan/SKILL.md",
    ".agents/skills/plz-run-plan/SKILL.md",
    "AGENTS.md",
}

BOOTSTRAP = {
    ".claude/skills/new-plan/SKILL.md": b"bootstrap new-plan\n",
    ".claude/skills/run-plan/SKILL.md": b"bootstrap run-plan\n",
    ".claude/agents/planner.md": b"bootstrap planner\n",
    ".claude/agents/executor.md": b"bootstrap executor\n",
    ".claude/agents/verifier.md": b"bootstrap verifier\n",
}


def make_pkg(root: Path, extra: dict[str, str] | None = None) -> Path:
    """Write the fake package tree under `root`, plus or overriding the `extra` files."""
    tree = {**FAKE_KIT, **(extra or {})}
    for rel, text in tree.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Relative path -> bytes (None for directories) for everything under `root`."""
    out: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        out[path.relative_to(root).as_posix()] = path.read_bytes() if path.is_file() else None
    return out


def files_only(snap: dict[str, bytes | None]) -> dict[str, bytes]:
    return {k: v for k, v in snap.items() if v is not None}


def run_cli(*argv: str) -> int:
    return cli.main(["install", *argv])


def seed_bootstrap(target: Path) -> None:
    for rel, data in BOOTSTRAP.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def make_archive(tmp_path: Path, version: str = "2.0.0") -> Path:
    """A GitHub-style tag archive (`Planzilla-<v>/src/planzilla/...`) as a tar.gz."""
    src = tmp_path / f"archive-src-{version}"
    pkg = src / f"Planzilla-{version}" / "src" / "planzilla"
    make_pkg(pkg, {"__init__.py": f'__version__ = "{version}"\n'})
    archive = tmp_path / f"v{version}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(src / f"Planzilla-{version}", arcname=f"Planzilla-{version}")
    return archive


@pytest.fixture
def pkg(tmp_path):
    return make_pkg(tmp_path / "pkg")


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    return path


# --- layout (§11) ---------------------------------------------------------------------------


def test_install_into_empty_repo_creates_exactly_the_section_11_file_set(pkg, target):
    counts = install.install_tree(pkg, "9.9.9", target)

    got = set(files_only(snapshot(target)))
    assert got == FAKE_KIT_PATHS
    assert counts == install.Counts(added=len(FAKE_KIT_PATHS), changed=0, removed=0)
    assert (target / ".planzilla/VERSION").read_text() == "9.9.9\n"
    assert os.access(target / ".planzilla/plz", os.X_OK)
    assert (target / ".planzilla/plz").stat().st_mode & 0o777 == 0o755


def test_cli_install_writes_package_version_and_prints_summary(target, capsys):
    assert run_cli("--target", str(target)) == 0

    out = capsys.readouterr().out
    assert (target / ".planzilla/VERSION").read_text() == f"{planzilla.__version__}\n"
    lines = out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"installed planzilla {planzilla.__version__} into {target}: ")
    assert lines[0].endswith(" added, 0 changed, 0 removed")


def test_install_defaults_to_cwd(target, monkeypatch, capsys):
    monkeypatch.chdir(target)
    assert run_cli() == 0
    assert (target / ".planzilla/VERSION").is_file()
    assert f"into {target}:" in capsys.readouterr().out


def test_missing_target_exits_2(tmp_path, capsys):
    assert run_cli("--target", str(tmp_path / "nope")) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert not (tmp_path / "nope").exists()


def test_every_real_kit_file_lands_at_a_section_11_target(target):
    assert run_cli("--target", str(target)) == 0
    kit = Path(str(resources.files("planzilla"))) / "kit"
    seen = 0
    for src in sorted(p for p in kit.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(kit).as_posix()
        data = src.read_bytes()
        head, _, rest = rel.partition("/")
        if rel == "AGENTS-block.md":
            expected = [target / "AGENTS.md"]
            assert data.decode().strip() in expected[0].read_text()
            seen += 1
            continue
        if head in ("roles", "templates"):
            expected = [target / ".planzilla" / rel]
        elif rel.startswith("agents/claude/"):
            expected = [target / ".claude/agents" / rel.removeprefix("agents/claude/")]
        elif head == "skills":
            expected = [target / ".claude" / rel, target / ".agents" / rel]
        else:
            pytest.fail(f"kit file with no section 11 target: {rel}")
        for dest in expected:
            assert dest.read_bytes() == data, dest
        assert (target / ".planzilla/lib/planzilla/kit" / rel).read_bytes() == data
        seen += 1
    assert seen > 0


def test_lib_copy_excludes_bytecode(pkg, target):
    (pkg / "__pycache__").mkdir()
    (pkg / "__pycache__/cli.cpython-312.pyc").write_bytes(b"x")
    (pkg / "stray.pyc").write_bytes(b"x")
    install.install_tree(pkg, "9.9.9", target)
    names = set(files_only(snapshot(target)))
    assert not [n for n in names if "__pycache__" in n or n.endswith(".pyc")]


# --- AGENTS.md ------------------------------------------------------------------------------


def test_agents_md_created_with_only_the_marked_block(pkg, target):
    install.install_tree(pkg, "9.9.9", target)
    assert (target / "AGENTS.md").read_text() == f"{BEGIN}\nUse .planzilla/plz.\n{END}\n"


def test_agents_md_without_markers_gets_blank_line_and_block_appended(pkg, target):
    (target / "AGENTS.md").write_text("# Mine\nkeep this")
    install.install_tree(pkg, "9.9.9", target)
    assert (target / "AGENTS.md").read_text() == (
        f"# Mine\nkeep this\n\n{BEGIN}\nUse .planzilla/plz.\n{END}\n"
    )


def test_agents_md_with_markers_replaces_only_between_them(pkg, target):
    before = f"# Top\n\n{BEGIN}\nold block\nmore old\n{END}\n\n## Bottom\ntail text"
    (target / "AGENTS.md").write_text(before)
    install.install_tree(pkg, "9.9.9", target)
    assert (target / "AGENTS.md").read_text() == (
        f"# Top\n\n{BEGIN}\nUse .planzilla/plz.\n{END}\n\n## Bottom\ntail text"
    )


def test_agents_md_with_unpaired_markers_exits_2_and_changes_nothing(pkg, target):
    (target / "AGENTS.md").write_text(f"{BEGIN}\nno end\n")
    before = snapshot(target)
    with pytest.raises(install.InstallError) as err:
        install.install_tree(pkg, "9.9.9", target)
    assert err.value.code == 2
    assert snapshot(target) == before


# --- idempotence and upgrade (C2) -------------------------------------------------------------


def test_second_install_changes_no_byte(pkg, target, capsys):
    (target / "AGENTS.md").write_text("# Mine\n")
    install.install_tree(pkg, "9.9.9", target)
    first = snapshot(target)
    mtimes = {p: (target / p).stat().st_mtime_ns for p in first if first[p] is not None}

    counts = install.install_tree(pkg, "9.9.9", target)

    assert snapshot(target) == first
    assert counts == install.Counts(0, 0, 0)
    assert {p: (target / p).stat().st_mtime_ns for p in mtimes} == mtimes


def test_second_cli_install_reports_zero_changes(target, capsys):
    assert run_cli("--target", str(target)) == 0
    capsys.readouterr()
    assert run_cli("--target", str(target)) == 0
    assert capsys.readouterr().out.endswith(": 0 added, 0 changed, 0 removed\n")


def test_upgrade_removes_dropped_files_and_keeps_every_other_file(tmp_path, target):
    old = make_pkg(
        tmp_path / "old",
        {
            "kit/roles/retired.md": "retired role\n",
            "kit/templates/old.md": "old template\n",
            "kit/agents/claude/plz-old.md": "old agent\n",
            "kit/skills/plz-old/SKILL.md": "old skill\n",
            "kit/skills/plz-old/extra/notes.md": "old notes\n",
            "__init__.py": '__version__ = "1.0.0"\n',
        },
    )
    new = make_pkg(tmp_path / "new", {"kit/roles/planner.md": "planner role v2\n"})
    user = {
        "src/app.py": b"print('hi')\n",
        ".claude/skills/custom/SKILL.md": b"custom skill\n",
        ".claude/agents/mine.md": b"mine\n",
        ".agents/skills/custom/SKILL.md": b"custom agents skill\n",
        ".plan/some-plan.md": b"plan\n",
    }
    for rel, data in user.items():
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_bytes(data)
    (target / "AGENTS.md").write_text(f"# Head\n\n{BEGIN}\nstale\n{END}\n\ntail\n")
    seed_bootstrap(target)

    install.install_tree(old, "1.0.0", target)
    assert (target / ".planzilla/roles/retired.md").is_file()
    assert (target / ".claude/skills/plz-old/extra/notes.md").is_file()
    assert (target / ".agents/skills/plz-old/SKILL.md").is_file()

    counts = install.install_tree(new, "9.9.9", target)

    got = files_only(snapshot(target))
    assert (target / ".planzilla/VERSION").read_text() == "9.9.9\n"
    for dropped in (
        ".planzilla/roles/retired.md",
        ".planzilla/templates/old.md",
        ".claude/agents/plz-old.md",
        ".claude/skills/plz-old/SKILL.md",
        ".agents/skills/plz-old/SKILL.md",
        ".planzilla/lib/planzilla/kit/roles/retired.md",
    ):
        assert dropped not in got
    assert not (target / ".claude/skills/plz-old").exists()
    assert not (target / ".agents/skills/plz-old").exists()
    assert counts.removed == 12
    assert (target / ".planzilla/roles/planner.md").read_text() == "planner role v2\n"
    for rel, data in {**user, **BOOTSTRAP}.items():
        assert got[rel] == data, rel
    assert (target / "AGENTS.md").read_text() == (
        f"# Head\n\n{BEGIN}\nUse .planzilla/plz.\n{END}\n\ntail\n"
    )
    assert set(got) - set(user) - set(BOOTSTRAP) == FAKE_KIT_PATHS


def test_unshipped_file_inside_planzilla_dir_is_removed_with_empty_dirs(pkg, target):
    install.install_tree(pkg, "9.9.9", target)
    stray = target / ".planzilla/extra/deep/file.txt"
    stray.parent.mkdir(parents=True)
    stray.write_text("x")
    counts = install.install_tree(pkg, "9.9.9", target)
    assert counts.removed == 1
    assert not (target / ".planzilla/extra").exists()


# --- vendored launcher (C3) -------------------------------------------------------------------


def test_vendored_launcher_runs_with_python3_and_a_clean_env(target):
    assert run_cli("--target", str(target)) == 0
    python3 = shutil.which("python3") or sys.executable
    env = {"PATH": os.environ.get("PATH", "")}
    help_run = subprocess.run(
        [python3, ".planzilla/plz", "--help"],
        cwd=target,
        env=env,
        capture_output=True,
        text=True,
    )
    assert help_run.returncode == 0, help_run.stderr
    assert "install" in help_run.stdout
    version_run = subprocess.run(
        [python3, ".planzilla/plz", "--version"],
        cwd=target,
        env=env,
        capture_output=True,
        text=True,
    )
    assert version_run.stdout.strip() == f"planzilla {planzilla.__version__}"
    # The launcher must not litter the vendored tree with bytecode.
    assert not list((target / ".planzilla").rglob("__pycache__"))


def test_launcher_is_executable_directly(target):
    assert run_cli("--target", str(target)) == 0
    result = subprocess.run(
        [str(target / ".planzilla/plz"), "--version"],
        cwd=target,
        env={"PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- --version / --archive-url (C4) -----------------------------------------------------------


def test_version_url_is_the_github_tag_archive():
    assert (
        install.ARCHIVE_URL.format(version="v1.2.3")
        == "https://github.com/IVIR3zaM/Planzilla/archive/refs/tags/v1.2.3.tar.gz"
    )


def test_install_from_file_url_archive_writes_that_version(tmp_path, target, capsys):
    archive = make_archive(tmp_path, "2.0.0")

    code = run_cli(
        "--target", str(target), "--version", "v2.0.0", "--archive-url", archive.as_uri()
    )

    assert code == 0
    out = capsys.readouterr().out
    assert out.startswith(f"installed planzilla 2.0.0 into {target}: ")
    assert (target / ".planzilla/VERSION").read_text() == "2.0.0\n"
    assert (target / ".planzilla/lib/planzilla/__init__.py").read_text() == (
        '__version__ = "2.0.0"\n'
    )
    assert set(files_only(snapshot(target))) == FAKE_KIT_PATHS


def test_archive_url_alone_installs_from_that_archive(tmp_path, target, capsys):
    archive = make_archive(tmp_path, "3.1.4")
    assert run_cli("--target", str(target), "--archive-url", archive.as_uri()) == 0
    assert (target / ".planzilla/VERSION").read_text() == "3.1.4\n"


def test_upgrade_from_archive_over_older_vendored_copy(tmp_path, target):
    seed_bootstrap(target)
    old = make_pkg(tmp_path / "old", {"kit/roles/retired.md": "r\n"})
    install.install_tree(old, "1.0.0", target)
    archive = make_archive(tmp_path, "2.0.0")

    assert run_cli("--target", str(target), "--archive-url", archive.as_uri()) == 0

    assert (target / ".planzilla/VERSION").read_text() == "2.0.0\n"
    assert not (target / ".planzilla/roles/retired.md").exists()
    for rel, data in BOOTSTRAP.items():
        assert (target / rel).read_bytes() == data


@pytest.mark.parametrize("kind", ["missing", "not-a-tarball", "no-package", "bad-scheme"])
def test_bad_archive_exits_3_and_leaves_target_unchanged(tmp_path, target, capsys, kind):
    (target / "keep.txt").write_text("keep")
    seed_bootstrap(target)
    (target / "AGENTS.md").write_text("# mine\n")
    before = snapshot(target)
    if kind == "missing":
        url = (tmp_path / "nope.tar.gz").as_uri()
    elif kind == "not-a-tarball":
        bad = tmp_path / "bad.tar.gz"
        bad.write_bytes(b"this is not a tarball")
        url = bad.as_uri()
    elif kind == "no-package":
        empty = tmp_path / "empty-src" / "Planzilla-1" / "docs"
        empty.mkdir(parents=True)
        (empty / "x.md").write_text("x")
        url = tmp_path / "empty.tar.gz"
        with tarfile.open(url, "w:gz") as tar:
            tar.add(tmp_path / "empty-src" / "Planzilla-1", arcname="Planzilla-1")
        url = url.as_uri()
    else:
        url = "nosuchscheme://example.invalid/x.tar.gz"

    code = run_cli("--target", str(target), "--version", "v9", "--archive-url", url)

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert captured.err.count("\n") == 1
    assert snapshot(target) == before


def test_archive_with_path_traversal_is_rejected(tmp_path, target, capsys):
    evil = tmp_path / "evil.tar.gz"
    payload = tmp_path / "payload.txt"
    payload.write_text("x")
    with tarfile.open(evil, "w:gz") as tar:
        tar.add(payload, arcname="../escaped.txt")
    before = snapshot(target)
    assert run_cli("--target", str(target), "--archive-url", evil.as_uri()) == 3
    assert snapshot(target) == before
    assert not (tmp_path.parent / "escaped.txt").exists()


# --- write boundaries (C5, C6) ----------------------------------------------------------------


ALLOWED_PREFIXES = (
    ".planzilla/",
    ".claude/agents/plz-",
    ".claude/skills/plz-",
    ".agents/skills/plz-",
)


def touched(before: dict[str, bytes | None], after: dict[str, bytes | None]) -> set[str]:
    return {
        p for p in set(before) | set(after) if before.get(p, "<absent>") != after.get(p, "<absent>")
    }


def test_install_writes_only_section_11_paths_and_never_plan(tmp_path, target):
    (target / ".plan").mkdir()
    (target / ".plan/p.md").write_text("plan")
    (target / ".plan/config.md").write_text("config")
    (target / "README.md").write_text("readme")
    seed_bootstrap(target)
    before = snapshot(target)

    assert run_cli("--target", str(target)) == 0

    after = snapshot(target)
    for rel in touched(before, after):
        assert rel in {
            "AGENTS.md",
            ".planzilla",
            ".claude",
            ".agents",
            ".claude/skills",
            ".claude/agents",
            ".agents/skills",
        } or rel.startswith(ALLOWED_PREFIXES), rel
    assert not [p for p in touched(before, after) if p.startswith(".plan/") or p == ".plan"]
    assert before[".plan/p.md"] == after[".plan/p.md"]
    assert before["README.md"] == after["README.md"]


def test_bootstrap_skills_and_agents_survive_install_and_upgrade_byte_identical(tmp_path, target):
    seed_bootstrap(target)
    first = make_pkg(tmp_path / "v1", {"kit/skills/plz-old/SKILL.md": "old\n"})
    second = make_pkg(tmp_path / "v2")

    install.install_tree(first, "1.0.0", target)
    for rel, data in BOOTSTRAP.items():
        assert (target / rel).read_bytes() == data, rel
    install.install_tree(second, "2.0.0", target)
    for rel, data in BOOTSTRAP.items():
        assert (target / rel).read_bytes() == data, rel
    assert not (target / ".claude/skills/plz-old").exists()


def test_kit_entries_without_plz_prefix_are_never_written_under_claude_or_agents(tmp_path, target):
    pkg = make_pkg(
        tmp_path / "pkg",
        {
            "kit/skills/new-plan/SKILL.md": "not ours\n",
            "kit/agents/claude/planner.md": "not ours\n",
        },
    )
    install.install_tree(pkg, "9.9.9", target)
    assert not (target / ".claude/skills/new-plan").exists()
    assert not (target / ".agents/skills/new-plan").exists()
    assert not (target / ".claude/agents/planner.md").exists()
