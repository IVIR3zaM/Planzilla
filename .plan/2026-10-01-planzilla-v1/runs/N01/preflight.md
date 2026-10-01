# N01 Preflight Check Results

| Check | Command | Result | Details |
|-------|---------|--------|---------|
| 1a | git rev-parse --is-inside-work-tree | PASS | true |
| 1b | git branch --show-current | PASS | claude/sleepy-newton-vg1mrs |
| 1c | git config user.name | PASS | Claude |
| 1d | git config user.email | PASS | noreply@anthropic.com |
| 2 | python3 --version | PASS | Python 3.11.15 |
| 3 | uv --version | PASS | uv 0.8.17 |
| 4a | uv tool run --from ruff ruff --version | PASS | ruff 0.16.9 |
| 4b | uv tool run --from pytest pytest --version | PASS | pytest 9.1.1 |
| 5.1 | curl .claude/skills/new-plan/SKILL.md | PASS | HTTP 200 |
| 5.2 | curl .claude/skills/new-plan/template.md | PASS | HTTP 200 |
| 5.3 | curl .claude/skills/run-plan/SKILL.md | PASS | HTTP 200 |
| 5.4 | curl .claude/agents/planner.md | PASS | HTTP 200 |
| 5.5 | curl .claude/agents/executor.md | PASS | HTTP 200 |
| 5.6 | curl .claude/agents/verifier.md | PASS | HTTP 200 |
| 5.7 | curl CLAUDE.md | PASS | HTTP 200 |
| 5.8 | curl Arboretum plan.md | PASS | HTTP 200 |
| 5.9 | curl Apache License 2.0 | PASS | HTTP 200 |
| 5b.1 | git ls-remote Arboretum archive tag | PASS | SHA 25de39f2995a03dd291a455bc179f6265e73c953 |
| 5b.2 | git clone + log Arboretum | PASS | 60 lines in history |
| 6 | Write/delete scratch file | PASS | runs/N01/test_write.txt |
| 7 | git commit --allow-empty | PASS | Created commit f9efc76 |
| 8 | git push -u origin HEAD | PASS | Branch pushed |
| 9.1 | .claude/skills/new-plan/SKILL.md tracked | PASS | exists and tracked |
| 9.2 | .claude/skills/new-plan/templates/node.md tracked | PASS | exists and tracked |
| 9.3 | .claude/skills/new-plan/templates/plan.md tracked | PASS | exists and tracked |
| 9.4 | .claude/skills/new-plan/templates/log.md tracked | PASS | exists and tracked |
| 9.5 | .claude/skills/run-plan/SKILL.md tracked | PASS | exists and tracked |
| 9.6 | .claude/agents/executor.md tracked | PASS | exists and tracked |
| 9.7 | .claude/agents/planner.md tracked | PASS | exists and tracked |
| 9.8 | .claude/agents/verifier.md tracked | PASS | exists and tracked |
| 10 (opt) | gh --version | NOTE | 2.89.0 |
| 10 (opt) | gh auth status | NOTE | auth not available (GH_TOKEN invalid) |

## Summary

All required checks (1-9, 5b) PASS. All network URLs respond with HTTP 200. All bootstrap files are tracked and exist. Git operations (commit, push) work without hook failures. Python environment and PyPI tools (uv, ruff, pytest) are available.

Optional GitHub CLI is available but auth is not configured (not needed for this run).
