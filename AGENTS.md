# Planzilla: rules for agents working in this repo

- Strict TDD: write the failing test, see it fail, write the minimal code to pass, refactor, rerun.
- Python >= 3.10, standard library only at runtime; pytest and ruff are dev-only (uv dev group), never shipped.
- Pure core: parsing, state and waves are pure functions over data, with no IO, clock or environment reads.
- All IO (files, git, subprocess, network, stdout/stderr) lives in `src/planzilla/commands/`.
- One module per command: `commands/<name>.py` exposes `add_arguments(parser)` and `run(args) -> int`.
- `cli.py` keeps the ordered command list and only dispatches; it holds no command logic.
- Pass `today` and `now` in as arguments; never call the clock inside the core.
- KISS and YAGNI: build only what the current node needs; no speculative options or abstractions.
- Type hints on every function signature.
- Format is the contract: `docs/FORMAT.md` decides file layouts, CLI output lines and exit codes.
- Keep to a node's Write paths; never commit unless asked.
- Verify before finishing: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`.
- The kit under `src/planzilla/kit/` is package data and ships with the package.

<!-- planzilla:begin -->
placeholder: AGENTS block
<!-- planzilla:end -->
