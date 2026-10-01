# Demo plan
status: RUNNING
created: 2026-10-01 · updated: 2026-10-01
goal: Fixture for the commit tests
verify: true
commit: per-node

## Decisions

- D1 Keep it small | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | parse input | exec | - | sonnet/sonnet | 1 | 0 | DONE | |
| N02 | render output | exec | N01 | sonnet/sonnet | 0 | 0 | TODO | |
