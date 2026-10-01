# Planzilla v1
status: RUNNING
created: 2026-10-01 · updated: 2026-10-01
goal: Planzilla v1 in this repo: stdlib-only `planzilla` CLI holding the plan state machine, cross-harness kit (roles, plz-* skills, Claude Code adapters, templates) vendored by `install`, CI/release/Homebrew, README; requirements 1–14 and lessons L1–L8 of request.md met
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
commit: per-node
push: per-node
budgets: 2 tries per brief · 2 replans per node

## Decisions

- D1 Scope is request.md: requirements 1–14 and lessons L1–L8 as written (tiers, commands, tags, retention values) | confirmed
- D2 This plan runs in a Claude Code cloud session holding only this repo + network, on the bootstrap new-plan/run-plan and agents in `.claude/` (D25); no node reads a home-directory or sibling path; prior art comes from `.claude/`, the raw.githubusercontent.com URLs in request.md, or an anonymous `git clone` of the public repo into a temp dir (api.github.com is 403 in this session); all briefs written after confirmation, no JIT briefing for this run | confirmed
- D3 Dogfooding in v1: yes, N16 vendors Planzilla into this repo after the CLI and kit pass (planner's call, delegated in request.md) | confirmed
- D4 Runtime Python >= 3.10, standard library only; dev-only tools pytest + ruff via uv, never shipped | confirmed · recommend: 3.10 · alt: 3.11 (stdlib tomllib)
- D5 Packaging: src layout `src/planzilla/`, hatchling, kit as package data in `src/planzilla/kit/`, first version 0.1.0, author "Reza Maghoul" (no email), scripts `planzilla` + alias `plz` (note: the Please build tool also ships `plz`) | confirmed · recommend: as stated · alt: version 1.0.0; no alias
- D6 N02 writes `docs/FORMAT.md`, the project spec every later node cites: plan formats, config keys, statuses, transitions, CLI output lines, commit message | confirmed · recommend: yes
- D7 Plan formats: S/M = one file `.plan/<date>-<slug>.md` (header, Intent, Decisions, Graph, `## N01` briefs, `## Log` last, appended only via `planzilla log`); L = dir `intent.md, plan.md, nodes/, log/, runs/`, layout-compatible with the bootstrap version (`.claude/skills/new-plan/templates/`) so the CLI reads this plan | confirmed · recommend: as stated · alt: S/M log in a sibling `<slug>.log.md`
- D8 State lives only in the markdown Graph table (no JSON state file); during a run the CLI is its only writer | confirmed · recommend: markdown table · alt: `state.json` beside it
- D9 Node statuses: TODO · BRIEFING · RUNNING · VERIFYING · RETRY · REPLAN · WAITING · DONE · BLOCKED (live view: planning, replanning, executing, verifying, done, blocked); `set` enforces transitions and budgets (2 tries, then REPLAN; 2 replans, then BLOCKED) | confirmed · recommend: as stated
- D10 `next` prints one line per ready action `<node> <action> <model>`, action in brief · exec · check · verify · replan · ask; the orchestrator reads only CLI lines and agent replies | confirmed · recommend: as stated
- D11 Criteria: `- C1 [tag] text`, tags cmd · review · visual · smoke · human; `[cmd]` carries one backticked command, pass = exit 0, run by `check`; verifier model set by the hardest non-cmd criterion; a node with only `[cmd]` criteria gets no verifier | confirmed · recommend: as stated
- D12 Add `planzilla lint`: tags present, brief <= 40 lines, deps acyclic, disjoint Write paths per wave; the planner runs it after writing (L1, L4) | confirmed · recommend: yes · alt: no lint in v1
- D13 Config `.plan/config.md` as `key: value` lines: verify, verify_fast, commit, push, retention (default keep), visual_recipe, models, preauthorized, always_review, commit_trailer | confirmed · recommend: as stated · alt: `.plan/config.toml`
- D14 Vendored layout: `.planzilla/` (VERSION, `plz` launcher, `lib/planzilla/` package copy, roles/, templates/), `.claude/skills/plz-new-plan|plz-run-plan`, `.claude/agents/plz-planner|plz-executor|plz-verifier|plz-visual`, `.agents/skills/plz-*` copies, an AGENTS.md block between markers; idempotent, touches only its own files, never `.plan/` | confirmed · recommend: as stated
- D15 `install --version vX` downloads the GitHub tag archive via urllib; tests use a local fixture archive, no network | confirmed · recommend: as stated · alt: `--version` only prints the uvx command
- D16 Harnesses: full adapters for Claude Code only; README covers Codex CLI, Gemini CLI, opencode, Cursor via AGENTS.md + Agent Skills | confirmed · recommend: as stated · alt: add Codex/opencode agent adapters
- D17 `[visual]` criteria go to `plz-visual` (verifier role + browser tools); the orchestrator never screenshots (L5) | confirmed · recommend: as stated
- D18 Resume: `planzilla resume` turns RUNNING/VERIFYING nodes into reruns with try kept; partial edits stay in the tree and the rerun is told so | confirmed · recommend: keep edits · alt: discard edits in the node's Write paths
- D19 `commit <node>` stages the node's Write paths + plan files + its log + `runs/<node>/`, message `<slug> N03: <title>` + config trailer; the commit that finishes a plan also applies retention | confirmed · recommend: as stated
- D20 `serve`: stdlib http.server on 127.0.0.1:8765 (`--port`), one self-contained HTML page polling a JSON endpoint every 2 s, light/dark | confirmed · recommend: as stated
- D21 Homebrew: owner's tap `IVIR3zaM/homebrew-tap`; release on tag `v*` builds sdist + wheel, creates the GitHub release, renders `Formula/planzilla.rb` from a template in this repo and pushes it to the tap with secret `HOMEBREW_TAP_TOKEN`; owner creates the tap, remote and secret | confirmed · recommend: as stated
- D22 Each verified node N01..N16 is committed (session's attribution trailer) and pushed to the session's current branch with `git push -u origin HEAD`, so another session can resume; no tags, releases, secrets, new remotes or pushes to other branches or repos during the run | confirmed · recommend: pre-authorize
- D23 Network: N01 `pip install uv` if missing; N01,N03 PyPI for `uv sync` of dev tools into `.venv`; N03 fetches https://www.apache.org/licenses/LICENSE-2.0.txt; N02,N09,N10 read-only raw.githubusercontent.com fetches of the request.md prior-art URLs, N01,N02 anonymous `git clone` of github.com/IVIR3zaM/Arboretum into a temp dir (no api.github.com); N01 fails fast if any is unreachable | confirmed · recommend: pre-authorize
- D24 Engineering rules in an `AGENTS.md` (N03; `CLAUDE.md` = `@AGENTS.md`): strict TDD, stdlib only, pure core (parse, state, waves) with IO in `commands/`, one module per command, KISS | confirmed · recommend: as stated
- D25 `.claude/skills/{new-plan,run-plan}` and `.claude/agents/{planner,executor,verifier}.md` are bootstrap files that run this plan: no node edits or deletes them; Planzilla's kit, `install` and N16 dogfooding use only `plz-*` names and leave them intact | confirmed (owner)

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | preflight: tools, git, network, permissions | exec | - | haiku/haiku | 1 | 1 | DONE | |
| N02 | project spec docs/FORMAT.md | exec | N01 | opus/opus | 2 | 0 | DONE | |
| N03 | scaffold: pyproject, cli dispatcher + stubs, AGENTS.md, LICENSE | exec | N02 | sonnet/haiku | 1 | 0 | DONE | |
| N04 | plan model + config parsing (both formats) | exec | N03 | opus/sonnet | 1 | 0 | DONE | |
| N05a | shared command IO: plan ref, lock, plan and log writes | exec | N04,N08a | sonnet/sonnet | 1 | 1 | RUNNING | |
| N05b | state machine: set, next, resume, waves | exec | N05a | opus/opus | 0 | 1 | TODO | |
| N06 | brief, log, check commands | exec | N04,N08a | sonnet/sonnet | 1 | 0 | VERIFYING | |
| N07 | commit + retention | exec | N04,N08a | sonnet/sonnet | 1 | 0 | VERIFYING | |
| N08a | self-maintaining CLI stub test | exec | N03 | sonnet/haiku | 1 | 1 | DONE | |
| N08b | install (vendoring, --version) | exec | N08a | sonnet/sonnet | 1 | 1 | VERIFYING | |
| N09 | kit: roles, templates, Claude Code adapters | exec | N03 | opus/opus | 1 | 0 | DONE | |
| N10 | kit: plz-new-plan, plz-run-plan skills | exec | N03 | opus/opus | 1 | 0 | DONE | |
| N11 | CI, release workflow, Homebrew formula | exec | N03 | sonnet/sonnet | 1 | 0 | DONE | |
| N12 | status, stats, lint | exec | N05b | sonnet/sonnet | 0 | 0 | TODO | |
| N13 | serve: live view | exec | N12 | sonnet/sonnet | 0 | 0 | TODO | |
| N14 | end-to-end CLI run test (S/M/L fixtures) | exec | N05b,N06,N07,N12,N18 | sonnet/opus | 0 | 0 | TODO | |
| N15 | README | exec | N08b,N09,N10,N11,N13,N14 | sonnet/sonnet | 0 | 0 | TODO | |
| N16 | dogfood: vendor Planzilla into this repo | exec | N08b,N09,N10,N14 | haiku/haiku | 0 | 0 | TODO | |
| N17 | plan acceptance | check | N15,N16 | -/opus | 0 | 0 | TODO | |
| N18 | consolidate brief, log, check, commit onto shared IO | exec | N05a,N06,N07 | sonnet/sonnet | 0 | 0 | TODO | |
