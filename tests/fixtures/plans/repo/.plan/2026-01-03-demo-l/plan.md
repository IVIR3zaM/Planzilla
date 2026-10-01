# Demo large plan
status: DRAFT
created: 2026-01-03 · updated: 2026-01-03
goal: Demo plan used by the parser tests
verify: uv run pytest -q
commit: none

Prose between sections is ignored and kept.

## Decisions

- D1 Use the standard library only | confirmed
- D2 Name of the docs page | proposed · recommend: docs.md · alt: guide.md

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | parse input | exec | - | sonnet/opus | 1 | 0 | DONE | |
| N02 | render output | exec | N01 | haiku/- | 2 | 1 | RETRY | fail C2 |
| N03 | wire cli | exec | N01, N02 | sonnet/sonnet | 1 | 0 | RUNNING | |
| N03a | docs page | exec | N01,N02 | sonnet/haiku | 0 | 0 | WAITING | ask: D2 |
| N04 | acceptance | check | N03,N03a | -/opus | 0 | 0 | TODO | |
| N05 | sign-off | gate | N04 | -/- | 0 | 0 | TODO | |

## Notes

Anything else in plan.md is preserved byte for byte.
