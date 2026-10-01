# Check demo L
status: RUNNING
created: 2026-02-01 · updated: 2026-02-01
goal: Fixture for the check command tests
verify: true
commit: none

## Decisions

- D1 Commands run from the repo root | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | one pass one fail | exec | - | sonnet/opus | 1 | 0 | RUNNING | |
| N02 | all pass | exec | - | sonnet/- | 2 | 0 | RUNNING | |
| N03 | check node | check | - | -/opus | 0 | 0 | TODO | |
| N04 | no cmd | exec | - | sonnet/opus | 1 | 0 | RUNNING | |
| N05 | cwd is repo root | exec | - | sonnet/- | 1 | 0 | RUNNING | |
| N06 | only the backticked span runs | exec | - | sonnet/- | 1 | 0 | RUNNING | |
| N07 | slow | exec | - | sonnet/- | 1 | 0 | RUNNING | |
| N08 | stdout and stderr | exec | - | sonnet/- | 1 | 0 | RUNNING | |
