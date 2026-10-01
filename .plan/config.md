# Planzilla config (FORMAT §8). A missing key takes its default; a plan's header wins over this file.
# Keys with an empty default are commented out: uncomment and fill them.
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
verify_fast: uv run pytest -q
commit: per-node
push: per-node
retention: keep
# visual_recipe: <one line: how to start the app and which URL to open>
models: planner=opus, exec=sonnet, verify=sonnet
# preauthorized: <action agents may take without asking>; <another action>
always_review: no
# commit_trailer: <text; \n separates lines>

# Format rules (delete these lines if you like)
# - Lines are blank, `#` comments or `key: value` with a key above; any other line, an unknown key or a
#   repeated key is a parse error naming this file and line.
# - commit: per-node or none. push: per-node or none. retention: keep, prune-logs, delete or branch-only.
#   always_review: yes or no. models: any subset of planner=, exec=, verify=.
# - Engineering rules belong in AGENTS.md/CLAUDE.md, not here. Executors and verifiers never read this file.
