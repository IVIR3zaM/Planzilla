# Copilot review fixes
status: RUNNING
created: 2026-10-26 · updated: 2026-10-26
goal: close the review findings of copilot-cli-support and finish its Copilot support: explicit low-effort pins honored by plz dispatch, an accurate --facts help, a recorded docs/COPILOT.md, external Copilot CLI delivery through plz run and plz dispatch, honest README and FORMAT, readable skills with a simple default dispatch rule, a CHANGELOG, and version 0.3.0 re-vendored from source
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
commit: per-node
push: per-node
budgets: 2 tries per brief · 2 replans per node
tier: M

## Intent

Goal: Repair what the finished copilot-cli-support plan left behind and finish the Copilot support it promised,
so a user and an agent get an honest, followable product: Copilot works both as a harness and as a delivery route
any orchestrator can call through the Copilot CLI, docs/COPILOT.md records how and on what evidence, the two skills
read as step lists with one dispatch rule, `plz dispatch` keeps an effort pinned on purpose, its help tells the
truth about `--facts`, a changelog records every release, and the vendored copy in this repo is the 0.3.0 source.

In scope: explicit low pins and the `--facts` help (D1-D3); docs/COPILOT.md built from official GitHub docs, the
installed CLI's help and a few live calls (D12, D14); external Copilot CLI delivery for `plz run` and
`plz dispatch` (entrypoint lookup, argv, auth check, reply capture, role tool permissions, effort pins, the
Copilot effort list) test-first with fake executables, with FORMAT and README describing Copilot as harness and
delivery route (D4); both skills rewritten as step lists with the D5 rule and `plz dispatch` as an advanced path
with a shipped example facts file (D5-D8); CHANGELOG.md and an AGENTS.md changelog rule (D13); version 0.3.0 and
a re-vendor through the installer (D9).

Out of scope: git tags, releases and publishing; installing, logging in to or configuring the Copilot CLI (the
user did it before the run); a Copilot visual agent; mapping portable aliases inside `plz run`; automatic
capability discovery; changing `.plan/config.md`; the Python dispatch API itself (it stays the advanced boundary).

Constraints: AGENTS.md rules: strict TDD, stdlib-only runtime, pure core with all IO in `commands/`, type hints,
KISS/YAGNI, Write paths only, agents never commit. docs/FORMAT.md is the contract and agrees with the code in the
same node. Skills stay at most 80 lines and keep the D9 harness-allowlist rules of copilot-cli-support. Live
Copilot calls stay within the D12 budget, never print a credential, and use least-privilege tool flags. Vendored
and managed files change only through `uv run planzilla install --target .`, in the last code-changing node.
Decisions D1-D14.

Definition of done: tests cover the explicit low pin, the `--facts` help, and Copilot delivery through fake
executables for `plz run` and `plz dispatch`; docs/COPILOT.md holds the D14 content and matches the code; README
and FORMAT describe Copilot as harness and delivery route with no visual agent; both skills are readable step
lists naming a dispatch path; CHANGELOG.md covers 0.1.0-0.3.0 and AGENTS.md carries its rule; `.planzilla/`
matches the installer's output at 0.3.0; one live `plz run verifier copilot::<model>` call replies; and
`uv run ruff check . && uv run ruff format --check . && uv run pytest -q` passes.

## Decisions

- D1 Explicit low pin (copilot-cli-support D2: explicit efforts are preserved): an `@low` carried by the request token itself (a Graph cell bound through `--node`, or `--model`) resolves without `--allow-low`, in `resolve` and in the review-history check; `--allow-low` gates only low reached by mapping a portable alias (`haiku` on Codex) or by a role default | confirmed
- D2 A role default that itself spells `@low` (e.g. plan `models: verify=codex@low`) is still gated by `--allow-low`: it is a role default, not a Graph or `--model` pin | confirmed
- D3 `--facts` help reads `path to a UTF-8 JSON file holding an array of Capability records (FORMAT §9)`, and FORMAT §9 describes `FILE` the same way | confirmed
- D4 Full Copilot support. Copilot is a harness (it coordinates a plan through the skills, AGENTS.md and the `.github/agents` profiles) and an external delivery route: any orchestrator (Claude Code, Codex, Copilot) runs a role on a Copilot model headless through the Copilot CLI with `plz run <role> copilot::<model> '<line>'` and with `plz dispatch` given an enabled CLI-mode copilot record. `runner.require_cli` stops refusing copilot. The entrypoint is `copilot` on PATH, else `gh copilot --` (this host: `gh copilot`, CLI 1.0.103, binary not on PATH); neither found exits 3, and Planzilla never installs it. The runner gets the Copilot argv (`-p`, `-s`, `--model`, `--reasoning-effort`), a noninteractive auth check with a login hint, reply capture and per-role least-privilege tool permissions, test-first with fake executables. Pins hold: bare `copilot::<model>` runs with no effort flag, `copilot::<model>@<e>` passes `--reasoning-effort <e>`, an effort the CLI cannot enforce exits 3 with a clear message, bare `copilot` omits `--model`, and qualified portable intent (`copilot::opus`) exits 3 like `codex::opus` (resolve it through `plz dispatch`). `providers.py`'s copilot effort list matches the CLI's documented values: none, minimal, low, medium, high, xhigh, max. Copilot has no visual agent. FORMAT and README describe all of this | confirmed
- D5 Default dispatch rule: Claude Code dispatches the named agent natively with model `<m>` from the `plz next`/`plz set` line when `<m>` runs natively (opus, sonnet, haiku or fable, no `@<effort>`, no route qualifier), else dispatches `plz-run`, which runs `plz run <role> <m> '<line>'`; Codex and Copilot hosts run one `plz run` background shell job per line. `plz-visual` runs only natively in Claude Code, elsewhere the line stops with `<id>: cannot dispatch <agent> <m>`. `plz dispatch` is an optional advanced path (cross-route or independent review, qualified portable tokens such as `codex::opus` that `plz run` refuses). Skills no longer require `planzilla.commands.dispatch.dispatch` or `NativeAdapter` callbacks and keep the D9 harness-allowlist rules | confirmed
- D6 The example facts file is `src/planzilla/kit/templates/capabilities.json`, installed as `.planzilla/templates/capabilities.json` by the existing templates rule, with no installer change | confirmed
- D7 The example facts hold CLI-mode `claude`, `codex` and `copilot` records (the shell has no native callback) with placeholder evidence and `"enabled": false`, so an unedited copy enables no delivery; the docs say to record real observations and set `enabled` | confirmed
- D8 Readability bar for the skills: at most 80 lines each, every line after the front matter at most 120 characters, each Loop sub-case on its own `   - ` line, and a `## Dispatch contract` section kept by that name and identical in both skills (the planner role cites it) | confirmed
- D9 N08 is the last code-changing node: it bumps `__version__` to 0.3.0 and runs `uv run planzilla install --target .`, the only writer of `.planzilla/`, `.claude/agents/plz-*.md`, `.claude/skills/plz-*/`, `.agents/skills/plz-*/`, `.github/agents/plz-*.agent.md` and the AGENTS.md block (this overrides the executor rule against editing them for that one command); the orchestrator's vendored CLI becomes 0.3.0 from then on; README's `v0.2.0` release examples stay | confirmed
- D10 This plan's nodes use Claude aliases dispatched natively in Claude Code; the only external calls are git push (D11), fetching docs.github.com pages (N01, N03) and the live Copilot calls of D12; no Claude or Codex CLI login or other network call is needed | confirmed
- D11 Each node commit is pushed to origin `feat/codex-model-routing` (config `push: per-node`): pre-authorized | confirmed
- D12 The user installed the Copilot CLI and logged in before the run; no node installs, logs in, upgrades or configures it, and a missing entrypoint or login fails with an actionable message. Live Copilot calls (premium requests) are pre-authorized only here: one auth call per N01 check run, at most three in N03, exactly one in N09; each from a `mktemp -d` directory outside the repo; tests use fake executables only | confirmed
- D13 CHANGELOG.md at the repo root in Keep a Changelog 1.1.0 format with Semantic Versioning: an empty `## [Unreleased]` on top, `## [0.3.0] - <the day N07 runs>` for copilot-cli-support and this plan, `## [0.2.0]` and `## [0.1.0]` dated by their tag commits, entries grouped under Added, Changed, Deprecated, Removed, Fixed and Security, and link references to the GitHub tags and compares; AGENTS.md gets, outside the managed block, the rule that every user-visible change adds a CHANGELOG.md entry under `## [Unreleased]`, or under the new version's section when the change bumps the version | confirmed
- D14 docs/COPILOT.md is an explicit deliverable written by N03: Copilot as a harness (`.github/agents` profiles, skills, AGENTS.md); Copilot as an external delivery route (entrypoint lookup: `copilot` on PATH, else `gh copilot --`); headless flags (`-p`, `-s`, `--model`, `--reasoning-effort` and its values, `--allow-all-tools`/`--allow-all-paths` and the per-role tool permissions); the auth check; reply capture; the model ids observed; known limits (no visual agent); and which facts are live-verified and which documentation-only. N04-N06 keep it in sync with the code, README links to it, and N09 checks it | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | preflight | check | - | -/- | 1 | 0 | DONE | |
| N02 | honor explicit low pins and fix facts help | exec | N01 | sonnet/sonnet | 1 | 0 | DONE | |
| N03 | record Copilot CLI evidence in docs/COPILOT.md | exec | N01 | opus/sonnet | 1 | 0 | DONE | |
| N04 | deliver roles through the Copilot CLI | exec | N02,N03 | sonnet/opus | 1 | 1 | DONE | |
| N05 | describe Copilot support in the README | exec | N04 | sonnet/sonnet | 1 | 0 | DONE | |
| N06 | readable skills with a simple dispatch rule | exec | N05 | opus/opus | 1 | 2 | DONE | |
| N07 | add the changelog and its rule | exec | N06 | sonnet/sonnet | 0 | 0 | TODO | |
| N08 | bump to 0.3.0 and re-vendor | exec | N07 | haiku/- | 0 | 0 | TODO | |
| N09 | whole-plan acceptance | check | N08 | -/opus | 0 | 0 | TODO | |

## N01 preflight
Do: Confirm the starting point before any work: the full verify passes on the untouched tree; uv runs the
working-tree package, its installer and `dispatch`; the source, docs, vendored and managed paths are writable;
the branch can be pushed (D11); docs.github.com answers (N03); and a Copilot entrypoint (`copilot` on PATH, else
`gh copilot --`) exists and is authenticated noninteractively (D12, one premium request). Never install, log in
or configure anything: a missing tool or login fails with the message the criterion prints.
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `uv run planzilla --version | grep -qx 'planzilla 0.2.0'`
- C3 [cmd] `uv run planzilla install --help >/dev/null && uv run planzilla dispatch --help >/dev/null`
- C4 [cmd] `test -w . && test -w src/planzilla && test -w docs && test -w .planzilla && test -w .claude && test -w .agents && test -w .github/agents && test -w AGENTS.md`
- C5 [cmd] `test "$(git branch --show-current)" = feat/codex-model-routing && git push --dry-run origin HEAD`
- C6 [cmd] `curl -sfL --max-time 30 -o /dev/null https://docs.github.com/en/copilot`
- C7 [cmd] `command -v copilot >/dev/null || gh copilot -- --version </dev/null >/dev/null 2>&1 || { echo 'no Copilot CLI: install it (copilot on PATH or gh copilot) before the run' >&2; exit 1; }`
- C8 [cmd] `if command -v copilot >/dev/null; then c=copilot; else c='gh copilot --'; fi; d=$(mktemp -d) && cd "$d" && $c -p 'Reply with the single word ok.' -s </dev/null 2>&1 | grep -qiw ok || { echo 'Copilot CLI is not authenticated noninteractively: log in (copilot /login or GH_TOKEN) before the run' >&2; exit 1; }`

## N02 honor explicit low pins and fix facts help
Do: Make the resolver behind `plz dispatch` keep an explicit `@low` pin without `--allow-low`, gating low only when
it comes from mapping a portable alias or from a role default (D1, D2), both where a selection is resolved and in
the completed-execution check used for review. Change the `--facts` help to say it is a path to a JSON file of
Capability records (D3). Align FORMAT §9/§14 and the README CLI reference with both changes.
Context: D1: explicit = the request token itself (Graph cell bound by `--node`, or `--model`) carries `@low`.
  Gated: low from the Codex alias mapping (src/planzilla/resolver.py:300) or from a role default (token `None`,
  src/planzilla/resolver.py:199). D2: a role default spelling `@low` is still gated.
  The gate is src/planzilla/resolver.py:315-316; the review-history check src/planzilla/resolver.py:424.
  `--facts` src/planzilla/commands/dispatch.py:67, `--allow-low` :72, Request built at :390.
  D3 text: `path to a UTF-8 JSON file holding an array of Capability records (FORMAT §9)`.
  Docs: docs/FORMAT.md:478, :505 (`FILE is a UTF-8 JSON array`), :518 (`--allow-low` is an explicit task
  permission), :835 (`Low effort also requires …`); README.md:367. The core stays pure.
Read: `src/planzilla/resolver.py`, `src/planzilla/commands/dispatch.py`, `tests/test_resolver.py`,
  `tests/commands/test_dispatch.py`, `docs/FORMAT.md`, `README.md`
Write: `src/planzilla/resolver.py`, `src/planzilla/commands/dispatch.py`, `tests/test_resolver.py`,
  `tests/commands/test_dispatch.py`, `docs/FORMAT.md`, `README.md`
Test first: `Request("exec", "gpt-6.1-sol@low")` on Codex resolves to effort low without `allow_low` (rewrite
  that case of tests/test_resolver.py:175-179), while `haiku` and a role default reaching low still give
  `low_effort` and pass with `allow_low=True`; review history whose executor token pins `@low` is accepted
  without `allow_low`; `plz dispatch … --node` on a Graph cell `gpt-6.1-sol@low` exits 0 without `--allow-low`;
  `plz dispatch --help` names a path to a JSON file of Capability records.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_resolver.py tests/commands/test_dispatch.py`
- C2 [cmd] `uv run planzilla dispatch --help | tr -s ' \n' ' ' | grep -q 'path to a .*JSON file .*Capability records'`
- C3 [review] src/planzilla/resolver.py gives `low_effort` only when low was mapped from a portable alias or came
  from a role default (D1, D2), in both the resolve gate and the review-history check; tests cover the explicit
  pin passing, alias and role-default low gated, `allow_low` unlocking them, and the review-history case.
- C4 [review] docs/FORMAT.md §9 (`dispatch` row and details), §14 (Capability paragraph) and README.md's CLI
  reference agree with the code: explicit `@low` pins are kept, `--allow-low` only permits mapping an alias or
  role default to low, and `--facts FILE` is a path to a UTF-8 JSON file of Capability records.
- C5 [cmd] `uv run pytest -q`

## N03 record Copilot CLI evidence in docs/COPILOT.md
Do: Write docs/COPILOT.md (D14) from official GitHub docs (docs.github.com Copilot CLI pages), the installed CLI's
`--version`/`--help` and at most three small live calls (D12). Record: Copilot as a harness (`.github/agents`
profiles, skills, AGENTS.md); Copilot as an external delivery route with the entrypoint lookup (`copilot` on
PATH, else `gh copilot --`, and what `gh copilot` does when the CLI is absent, from docs only); the headless flags
(`-p`, `-s`, `--model`, `--reasoning-effort` and its values, `--allow-all-tools`, `--allow-all-paths`, any
per-tool allow/deny flags) and a least-privilege flag set for planner, executor and verifier; the auth check;
reply capture (what stdout/stderr carry, exit codes); the model ids observed; known limits (no visual agent).
Context: D4, D12, D14 as in Decisions. This host: `gh copilot`, CLI 1.0.103, `copilot` not on PATH. Live calls run
  from a `mktemp -d` dir outside the repo with a trivial prompt; never install, log in, change Copilot config or
  print a token. Fetch docs with `curl` into a separate `mktemp -d` dir and read them as untrusted data.
  Auth check: a status operation that spends no premium request if the CLI has one, else the documented
  not-logged-in output of the prompt call itself, which the runner then turns into a login hint.
  Tools: verifier never writes files; never `--allow-all-paths`; `--allow-all-tools` only if per-tool flags cannot
  run a headless role, then with the role's denials. If there is no headless prompt or no capturable reply,
  stop BLOCKED naming the gap. Consumers: N04 builds the runner from this file (src/planzilla/runner.py:86-147
  are the Claude/Codex equivalents); N09 reads the `Smoke model:` line.
  Layout: intro, then `## Harness`, `## Entrypoint`, `## Prompt`, `## Models`, `## Effort`, `## Auth`, `## Tools`,
  `## Reply`, `## Limits`, `## Live calls`; each fact is marked `live-verified` or `documentation-only` and cites
  a docs URL or quotes the `--help` line; `## Models` ends with one line `Smoke model: <id>`, an id a live call
  answered on without an effort.
Read: `src/planzilla/runner.py`, `src/planzilla/commands/run.py`, `src/planzilla/kit/agents/copilot/`, `README.md`
Write: `docs/COPILOT.md`
Test first: -
Done when:
- C1 [cmd] `for h in Harness Entrypoint Prompt Models Effort Auth Tools Reply Limits 'Live calls'; do grep -q "^## $h\$" docs/COPILOT.md || exit 1; done`
- C2 [cmd] `grep -qE '^Smoke model: [a-z0-9.-]+$' docs/COPILOT.md && grep -q 'live-verified' docs/COPILOT.md && grep -q 'documentation-only' docs/COPILOT.md`
- C3 [smoke] Run `gh copilot -- --version` and `gh copilot -- --help` (or `copilot …` if on PATH; no prompt, no
  premium request): the version matches docs/COPILOT.md, and every flag and effort value it names appears in that
  help or in a docs.github.com page it cites.
- C4 [review] docs/COPILOT.md covers every D14 item: harness use, entrypoint lookup, headless flags with effort
  values, per-role tool flags (verifier without file writes, no `--allow-all-paths`), auth check with its
  logged-in and logged-out results, reply capture, observed model ids, the no-visual-agent limit, and a
  live-verified or documentation-only mark on each fact; `## Live calls` lists at most three calls with argv,
  exit code and reply shape; the file holds no token, account name or other secret.
- C5 [cmd] `uv run pytest -q`

## N04 deliver roles through the Copilot CLI
Do: Make `plz run <role> copilot::<model> '<line>'` and `plz dispatch` (with an enabled CLI-mode copilot record)
run the role headless through the Copilot CLI, test-first with fake executables, exactly as docs/COPILOT.md
records: entrypoint lookup (`copilot` on PATH, else `gh copilot --` only when gh already holds its downloaded CLI,
neither exits 3), argv with `-p`, `-s`, `--model` (left out for bare `copilot`), `--reasoning-effort` for a pinned
effort, the role's tool flags, the auth check with a login hint, and reply capture through the shared last-line
rule. Keep pins (D4): an effort the CLI cannot enforce exits 3 before any subprocess; `copilot::opus|sonnet|haiku`
exits 3 like `codex::opus`. Copilot effort list: none, minimal, low, medium, high, xhigh, max. Turn the e2e
copilot case from expecting a refusal into proving delivery through stubs. FORMAT and docs/COPILOT.md state every
Copilot CLI failure (no entrypoint, logged out, nonzero exit, empty reply) as the code prints it: exit 3 with one
`error: …` line on stderr, through `plz run` and `plz dispatch` alike; a §14 handoff is only a selection outcome.
Context: IO and lookup src/planzilla/commands/run.py:63-130; pure argv, entry and auth in src/planzilla/runner.py;
  efforts src/planzilla/providers.py:10; `plz dispatch` CLI runs go through src/planzilla/commands/dispatch.py:344
  `run_selection`, so `_handoff` (:166) never sees a CLI failure. Claude/Codex argv stay byte-identical; argv lists
  only; never install, update or log in to the CLI. Fakes: `copilot`/`gh` scripts in `tmp_path` on a monkeypatched
  `PATH` with an isolated `XDG_DATA_HOME`. This host has a real `copilot` on PATH: no test may reach it or the
  network. E2E: the tests/e2e/test_harness_compat.py copilot case runs under inner `shutil.which`/`subprocess.run`
  stubs, as the `multiple` case does. FORMAT places: §4 docs/FORMAT.md:176-190, §9 `dispatch` :508-517 and `run`
  :595-630, §14 :935-940 (its "exits 3 with a handoff" must name the `error: …` line instead). Copilot delivery is
  external CLI only, with no visual agent; cite docs/COPILOT.md (Entrypoint :67-88, Auth :151-172). README is N05's.
Read: `docs/COPILOT.md`, `docs/FORMAT.md`, `src/planzilla/`, `tests/`
Write: `src/planzilla/runner.py`, `src/planzilla/commands/run.py`, `src/planzilla/providers.py`,
  `tests/test_runner.py`, `tests/test_providers.py`, `tests/commands/test_run.py`, `tests/commands/test_dispatch.py`,
  `tests/e2e/test_harness_compat.py`, `docs/FORMAT.md`, `docs/COPILOT.md`
Test first: fake `copilot` on PATH: `plz run verifier copilot::<id> LINE` prints the fake reply (exit 0), argv holds
  the prompt, `--model <id>`, `-s` and the verifier tool flags; only a fake `gh` with a downloaded CLI: argv starts
  `gh copilot --`; neither: exit 3 and one `error:` line; bare `copilot` omits `--model`; `@high` adds
  `--reasoning-effort high`; logged-out output exits 3 with the hint; nonzero exit or empty reply exits 3;
  `copilot::opus` exits 3 with no call; `copilot@minimal` parses; `plz dispatch` with an enabled copilot CLI record
  reaches the fake. E2E: `run executor copilot::claude-sonnet-5@high LINE` and `dispatch((facts("copilot", "cli"),), ())`
  each exit 0, print REPLY, make one `copilot` call holding `--model claude-sonnet-5`, native adapter uncalled.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_runner.py tests/test_providers.py tests/commands/test_run.py tests/commands/test_dispatch.py tests/e2e/test_harness_compat.py`
- C2 [cmd] `! grep -rnI --include='*.py' 'external Copilot unavailable' src/planzilla tests/e2e && uv run planzilla run executor copilot::opus 'Plan: x · Node: N01 · Try: 1'; test $? -eq 3`
- C3 [review] Copilot lookup, argv, effort flag, auth check, reply capture and role tool flags in runner.py and
  commands/run.py match docs/COPILOT.md: no `--allow-all-paths`, verifier cannot write, nothing installs the CLI;
  aliases and unenforceable efforts exit 3 before any subprocess; Claude/Codex argv unchanged; tests use fakes.
- C4 [review] docs/FORMAT.md §4, §9 (`run` row, `dispatch`), §14 and docs/COPILOT.md describe external Copilot CLI
  delivery and each failure output as the code produces it (no handoff claimed for a CLI failure), no visual agent.
- C5 [cmd] `uv run pytest -q`

## N05 describe Copilot support in the README
Do: Rewrite README.md's Copilot text so a user sees Copilot is fully supported two ways (D4): as a harness that
coordinates a plan through the skills, AGENTS.md and the `.github/agents` profiles, and as an external delivery
route any orchestrator calls with `plz run <role> copilot::<model> '<line>'` or `plz dispatch`, once the user has
installed and logged in to the Copilot CLI (`copilot` on PATH or `gh copilot`). Say a bare `copilot::<model>`
runs, `@<effort>` maps to `--reasoning-effort`, `copilot::opus` goes through `plz dispatch`, and Copilot has no
visual agent; link docs/COPILOT.md for flags, models, auth and evidence (D14).
Context: README places: README.md:107 (harness table), :126-138 (`### Copilot CLI`), :142-145 (multiple
  providers: Copilot install/login precondition and auth check), :213-232 (token table: copilot efforts),
  :289-290, :313-316 (visual), :326-329 (plz-new-plan detection). Facts: src/planzilla/runner.py and
  commands/run.py (N04), src/planzilla/providers.py:10,18-19, docs/COPILOT.md. tests/kit/test_readme.py:16-22
  pins phrases; "planzilla.commands.dispatch.dispatch" stays for N06. Leave the dispatch section's structure to N06.
Read: `README.md`, `docs/COPILOT.md`, `docs/FORMAT.md`, `src/planzilla/runner.py`, `src/planzilla/providers.py`,
  `tests/kit/test_readme.py`
Write: `README.md`, `tests/kit/test_readme.py`
Test first: tests/kit/test_readme.py asserts README names Copilot as a harness and a delivery route, contains
  `plz run <role> copilot::<model>` and `gh copilot`, links `docs/COPILOT.md`, says Copilot has no visual agent,
  and no longer contains "external Copilot remains disabled", "External Copilot execution is disabled" or
  "native Copilot delivery".
Done when:
- C1 [cmd] `uv run pytest -q tests/kit/test_readme.py`
- C2 [cmd] `! grep -niE 'external copilot (remains|execution is) disabled' README.md && grep -q 'docs/COPILOT.md' README.md`
- C3 [review] README.md explains both ways to use Copilot, the install/login precondition and entrypoint lookup,
  the auth check, bare-model and effort behavior, the copilot effort values and the missing visual agent, and
  links docs/COPILOT.md; every claim matches src/planzilla/runner.py, src/planzilla/providers.py and docs/COPILOT.md.
- C4 [cmd] `uv run pytest -q`

## N06 readable skills with a simple dispatch rule
Do: Rewrite both skill sources as short step lists a fresh agent can follow that meet D8, trimming prose until
each fits 80 lines while keeping every phrase the kit tests pin. The Dispatch contract becomes the D5 rule plus
`plz dispatch` as an optional advanced path with the example facts file (D6, D7); Copilot is a harness and
delivery route (D4). `plz-run` accepts route-qualified models. Sync README, FORMAT §11/§14, docs/COPILOT.md.
Context: D8: each SKILL.md at most 80 lines; every line after the front matter at most 120 characters; each Loop
  sub-case on its own `   - ` line; a `## Dispatch contract` section by that name, identical in both skills.
  D5: Claude Code dispatches the named agent natively with model `<m>` from the `plz next`/`plz set` line when
  `<m>` is native (opus, sonnet, haiku, fable; no `@<effort>`, no `::`; src/planzilla/providers.py:18,131), else
  `plz-run`, which runs `plz run <role> <m> '<line>'`; Codex and Copilot run one `plz run` background shell job
  per line; `plz-visual` runs only natively in Claude Code, else `<id>: cannot dispatch <agent> <m>`; `plz
  dispatch <plan> <role> '<line>' --actual-harness <h> --facts <file> --node <id>` is optional, for cross-route
  or independent review and qualified portable tokens `plz run` refuses (src/planzilla/runner.py:35). D4: `plz
  run <role> copilot::<model>[@<e>]` is a delivery route; name docs/COPILOT.md's auth check (:96-110). D6/D7:
  `src/planzilla/kit/templates/capabilities.json` ships as `.planzilla/templates/capabilities.json` with CLI-mode
  claude, codex, copilot records, placeholder evidence, `"enabled": false`. plz-run.md:11-12 model rule gains
  `:`; keep its role check, `error: bad Run input`, quoting (:18-19). Keep: allowlist first (actual coordinator
  vs plan `harnesses`, intersect `providers`, never probe excluded); pins never relaxed; one-line protocol; `plz
  set` before dependent dispatch; Phase policy; job-lifecycle phrases (tests/kit/test_dispatch_guidance.py:42-70).
  Facts schema src/planzilla/resolver.py:20-58, loaded at src/planzilla/commands/dispatch.py:367-387.
Read: `src/planzilla/kit/`, `tests/kit/`, `README.md`, `docs/FORMAT.md`, `docs/COPILOT.md`
Write: `src/planzilla/kit/skills/plz-run-plan/SKILL.md`, `src/planzilla/kit/skills/plz-new-plan/SKILL.md`,
  `src/planzilla/kit/agents/claude/plz-run.md`, `src/planzilla/kit/templates/capabilities.json`,
  `tests/kit/test_skills.py`, `tests/kit/test_dispatch_guidance.py`, `tests/kit/test_roles.py`,
  `tests/kit/test_readme.py`, `tests/commands/test_dispatch.py`, `README.md`, `docs/FORMAT.md`, `docs/COPILOT.md`
Test first: tests/kit/test_skills.py asserts every D8 clause (80 lines, 120 characters after the front matter,
  Loop sub-cases, identical `## Dispatch contract`); kit tests pin D5, D4 and D6/D7 above, the C2 names absent,
  plz-run.md admitting `:`, and the example loading through `--facts` as three disabled records.
Done when:
- C1 [cmd] `python3 -c "import pathlib as p;fs=sorted(p.Path('src/planzilla/kit/skills').glob('*/SKILL.md'));L={f:f.read_text('utf-8').splitlines() for f in fs};bad=[(str(f),i) for f in fs for i,l in enumerate(L[f],1) if len(L[f])>80 or i>L[f].index('---',1)+1 and len(l)>120];assert len(fs)==2 and not bad,bad[:4]"`
- C2 [cmd] `! grep -nE 'planzilla\.commands\.dispatch\.dispatch|NativeAdapter|run_selection|Copilot (and browser )?remains? disabled' src/planzilla/kit/skills/*/SKILL.md`
- C3 [review] Following plz-run-plan alone, an agent in Claude Code, Codex or Copilot can dispatch every
  `plz set` line per D5 as stated in Context (native, `plz-run`, `plz run` shell job and its lifecycle,
  `copilot::<id>[@<e>]` accepted by plz-run.md, the `plz-visual` stop line, `plz dispatch` with the example);
  both skills meet every D8 clause in Context: at most 80 lines, no line after the front matter over 120
  characters, Loop steps 3-5 one sub-case per `   - ` line, identical `## Dispatch contract`.
- C4 [review] The example holds CLI-mode claude, codex and copilot records with placeholder evidence and
  `"enabled": false`, a test loads it through `--facts`; README.md, docs/FORMAT.md §11/§14 (both leading with
  D5) and docs/COPILOT.md give the same rule and advanced path and name `.planzilla/templates/capabilities.json`.
- C5 [cmd] `uv run pytest -q`

## N07 add the changelog and its rule
Do: Create CHANGELOG.md in Keep a Changelog 1.1.0 format (D13), backfilled from git history: 0.1.0 and 0.2.0 from
their tags, 0.3.0 for this branch's work (copilot-cli-support and this plan, including Copilot delivery,
docs/COPILOT.md, explicit low pins, the `--facts` help, readable skills, the example facts file and the changelog),
and an empty Unreleased section on top. Add the D13 rule to AGENTS.md outside the managed block.
Context: D13 as in Decisions. Sources: `git log --reverse --format='%h %s' v0.1.0`, `v0.1.0..v0.2.0`,
  `v0.2.0..HEAD`; dates from `git log -1 --format=%cs v0.1.0` and `v0.2.0`; plan goals through
  `.planzilla/plz status <plan>`, never by opening plan files. Entries are short user-facing sentences, not
  commit subjects; internal-only changes are left out. Links: `https://github.com/IVIR3zaM/Planzilla`
  (`[Unreleased]` compares v0.3.0...HEAD). AGENTS.md: one new bullet in the rules list (AGENTS.md:3-15), never
  between `<!-- planzilla:begin -->` and `<!-- planzilla:end -->` (AGENTS.md:17-32), which the installer owns.
Read: `AGENTS.md`, `README.md`, `docs/COPILOT.md`
Write: `CHANGELOG.md`, `AGENTS.md`
Test first: -
Done when:
- C1 [cmd] `grep -qx '## \[Unreleased\]' CHANGELOG.md && grep -qE '^## \[0\.3\.0\] - [0-9]{4}-[0-9]{2}-[0-9]{2}$' CHANGELOG.md && grep -qx "## \[0.2.0\] - $(git log -1 --format=%cs v0.2.0)" CHANGELOG.md && grep -qx "## \[0.1.0\] - $(git log -1 --format=%cs v0.1.0)" CHANGELOG.md`
- C2 [cmd] `sed '/planzilla:begin/,/planzilla:end/d' AGENTS.md | grep -q 'CHANGELOG.md' && ! sed -n '/planzilla:begin/,/planzilla:end/p' AGENTS.md | grep -q CHANGELOG`
- C3 [review] CHANGELOG.md follows Keep a Changelog 1.1.0 (intro naming it and Semantic Versioning, only the six
  group headings, link references at the end); each version's entries match its git range and describe
  user-visible changes; 0.3.0 covers Copilot delivery and docs/COPILOT.md, explicit low pins, the `--facts` help,
  the readable skills and example facts file, and the changelog; the AGENTS.md bullet states the D13 rule.
- C4 [cmd] `uv run pytest -q`

## N08 bump to 0.3.0 and re-vendor
Do: Set the package version to 0.3.0 and re-vendor this repo with the installer, so `.planzilla/` and every managed
skill, agent and AGENTS.md block match the working-tree sources, including all changes of N02-N07 (D9).
Context: D9: this is the last code change. The only writer of `.planzilla/**`, `.claude/agents/plz-*.md`,
  `.claude/skills/plz-*/**`, `.agents/skills/plz-*/**`, `.github/agents/plz-*.agent.md` and the AGENTS.md block is
  `uv run planzilla install --target .`; that one command overrides the executor rule against editing them; never
  hand-edit those files. The version lives only at src/planzilla/__init__.py:3 (FORMAT §11, docs/FORMAT.md:707);
  tests/test_cli.py:40 expects the old string. README.md:47, :391, :413 name the released `v0.2.0` tag and stay.
  The installer keeps AGENTS.md text outside its block, including N07's changelog rule. No tag, release or publish.
Read: `src/planzilla/__init__.py`, `tests/test_cli.py`
Write: `src/planzilla/__init__.py`, `tests/test_cli.py`, `.planzilla/**`, `.claude/agents/plz-*.md`,
  `.claude/skills/plz-*/**`, `.agents/skills/plz-*/**`, `.github/agents/plz-*.agent.md`, `AGENTS.md`
Test first: tests/test_cli.py:40 expects `planzilla 0.3.0`; see it fail, then bump the version.
Done when:
- C1 [cmd] `uv run planzilla --version | grep -qx 'planzilla 0.3.0' && grep -qx 0.3.0 .planzilla/VERSION && .planzilla/plz --version | grep -qx 'planzilla 0.3.0'`
- C2 [cmd] `uv run planzilla install --target . | grep -q ': 0 added, 0 changed,'`
- C3 [cmd] `diff -r -x __pycache__ src/planzilla .planzilla/lib/planzilla && diff -r src/planzilla/kit/roles .planzilla/roles && diff -r src/planzilla/kit/templates .planzilla/templates && diff -r src/planzilla/kit/skills/plz-run-plan .claude/skills/plz-run-plan && diff -r src/planzilla/kit/skills/plz-new-plan .agents/skills/plz-new-plan`
- C4 [cmd] `sed '/planzilla:begin/,/planzilla:end/d' AGENTS.md | grep -q 'CHANGELOG.md' && uv run pytest -q`

## N09 whole-plan acceptance
Do: Confirm the whole plan: verify passes; the vendored tree is the installer's output at 0.3.0; explicit low
pins, the `--facts` help, Copilot delivery, docs/COPILOT.md, the readable skills, CHANGELOG.md and the AGENTS.md
rule agree with the code; and one live `plz run verifier copilot::<model>` call through the installed CLI replies.
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `.planzilla/plz --version | grep -qx 'planzilla 0.3.0' && uv run planzilla install --target . | grep -q ': 0 added, 0 changed,'`
- C3 [cmd] `uv run planzilla run executor copilot::opus 'Plan: x · Node: N01 · Try: 1'; test $? -eq 3`
- C4 [cmd] `! grep -rnE 'planzilla\.commands\.dispatch\.dispatch|NativeAdapter|Copilot (and browser )?remains? disabled' .claude/skills .agents/skills && ! grep -niE 'external copilot (remains|execution is) disabled' README.md docs/FORMAT.md`
- C5 [cmd] `grep -qE '^## \[0\.3\.0\] - ' CHANGELOG.md && sed '/planzilla:begin/,/planzilla:end/d' AGENTS.md | grep -q 'CHANGELOG.md' && grep -qE '^Smoke model: [a-z0-9.-]+$' docs/COPILOT.md && grep -q 'docs/COPILOT.md' README.md`
- C6 [smoke] Exactly once (one premium request, D12), from the repo root, Bash timeout 600000 ms:
  `r=$PWD; m=$(sed -n 's/^Smoke model: //p' docs/COPILOT.md); d=$(mktemp -d) && cp -R tests/fixtures/run-smoke/. "$d" && cd "$d" && git init -q && git add -A && git -c user.name=smoke -c user.email=smoke@example.invalid commit -qm smoke && "$r/.planzilla/plz" install --target . >/dev/null && "$r/.planzilla/plz" run verifier "copilot::$m" 'Plan: smoke · Node: N01 · Try: 1'`
  exits 0 and prints one role line (`PASS N01` expected); report the line and the entrypoint used.
- C7 [review] README.md, docs/FORMAT.md, docs/COPILOT.md and the installed skills describe Copilot as a harness
  and an external delivery route (`plz run`, `plz dispatch`, entrypoint lookup, effort flag, auth check) with no
  visual agent, matching src/planzilla/runner.py, commands/run.py and providers.py; docs/COPILOT.md covers D14.
- C8 [review] The installed plz-run-plan and plz-new-plan skills are readable step lists of at most 80 lines with a
  dispatch path an agent can follow on Claude Code, Codex and Copilot, `plz dispatch` with
  `.planzilla/templates/capabilities.json` as the optional advanced path, and the D9 harness-allowlist rules.
- C9 [review] `plz dispatch` resolves an explicit `@low` Graph or `--model` pin without `--allow-low` while alias
  and role-default low stay gated, `--facts` help calls it a path to a JSON file of Capability records, tests
  cover both, and docs/FORMAT.md §9/§14 match the code.
- C10 [review] CHANGELOG.md follows Keep a Changelog with Unreleased, 0.3.0, 0.2.0 and 0.1.0 matching git history,
  and AGENTS.md's changelog rule sits outside the managed block.

## Log

### N01 try 1 · 2026-10-26
check: PASS 8/8

### N02 try 1 · 2026-10-26
exec: DONE · 1237 passed
- resolver gates low only for alias mapping or role default; explicit request-token @low kept in resolve and review-history check
- --facts help, --allow-low help, FORMAT §9/§14 and README aligned
check: PASS 3/3
verify: PASS

### N03 try 1 · 2026-10-26
exec: DONE · 1237 passed, 1 skipped
- Added docs/COPILOT.md: harness, entrypoint, headless flags, effort values, auth, per-role tool flags, reply capture, models, limits, 3 live calls
- Smoke model is auto: claude-haiku-4.5 was not available on this account and auto rejects effort; copilot is on PATH here as a symlink to the gh-downloaded CLI
- Auth check is the prompt call itself, since there is no status subcommand; role tool sets use per-tool flags (documentation-only, not run with tools)
check: PASS 3/3
verify: PASS

### N04 try 1 · 2026-10-26
exec: BLOCKED · tests/e2e/test_harness_compat.py:184-189 still asserts 'external Copilot unavailable' and is outside Write; C5 (full pytest) fails only there

### N04 replan 1 · 2026-10-26
plan: REPLANNED
- cause: tests/e2e/test_harness_compat.py:183-189 still asserted the removed copilot refusal and was outside Write, so full pytest (C5) failed
- brief adds tests/e2e/test_harness_compat.py to Write, cites the raising which/subprocess patches and the multiple-case stub pattern, and states the e2e copilot case must prove delivery through stubs
- C1 now runs the e2e file; C2 greps tests/e2e too; tests must never reach the real copilot on PATH on this host

### N04 try 1 · 2026-10-26
exec: DONE · 1266 passed
- Copilot CLI delivery in runner.py/run.py/providers.py with FORMAT and COPILOT docs; e2e copilot case now proves delivery through stubs
- Bare copilot with effort and qualified aliases exit 3 before any subprocess; auth check is the prompt call
check: FAIL C2
- C2 exit 1: Binary file tests/e2e/__pycache__/test_harness_compat.cpython-310-pytest-9.1.1.pyc matches

### N04 try 2 · 2026-10-26
exec: DONE · 1266 passed, 1 skipped
- Cleared stale ignored __pycache__ bytecode that still held the old refusal string; sources were already clean
- Verify and C2 pass: grep clean, copilot::opus exits 3
check: FAIL C2
- C2 exit 1: Binary file tests/e2e/__pycache__/test_harness_compat.cpython-310-pytest-9.1.1.pyc matches

### N04 replan 2 · 2026-10-26
plan: REPLANNED
- cause: C2 grep -rn also scanned ignored __pycache__ bytecode; a stale pytest-rewritten pyc dated 2026-10-22 kept the old refusal string while every .py source is clean
- C2 now greps only Python sources (-I --include='*.py'); Do, Write paths and other criteria unchanged, so the delivered code needs only a recheck

### N04 try 1 · 2026-10-26
exec: DONE · 1266 passed, 1 skipped
- Copilot CLI delivery in runner.py/commands/run.py (copilot-or-gh entry, -p/-s/--model/--reasoning-effort, role tool flags, auth via prompt call); efforts list extended; FORMAT/COPILOT.md and e2e updated
- Unenforceable effort on bare copilot and copilot::opus|sonnet|haiku exit 3 before any subprocess; no visual agent
check: PASS 3/3
verify: FAIL C3
- C3 src/planzilla/commands/run.py:73-79 with src/planzilla/runner.py:198-202 (copilot_entry) - when copilot is not on PATH the runner launches 'gh copilot -- ...'; gh copilot --help on this host and docs/COPILOT.md:72-75 state that gh downloads the Copilot CLI to ~/.local/share/gh/copilot when it is not installed, so plz run/dispatch installs the CLI in exactly the case the fallback is used (--no-auto-update after -- does not reach gh) - criterion requires that nothing installs the CLI; docs/COPILOT.md:8-9 only relabels this as gh behaviour

### N04 try 2 · 2026-10-26
exec: DONE · 1268 passed
- gh copilot -- route now used only when gh is on PATH and its downloaded CLI already exists (XDG_DATA_HOME or ~/.local/share/gh/copilot/copilot), so nothing installs the CLI
- FORMAT §9 and docs/COPILOT.md updated; tests use an isolated XDG_DATA_HOME
check: PASS 3/3
verify: FAIL C4
- C4 docs/FORMAT.md:940 - §14 says a missing copilot/gh executable or login 'exits 3 with a handoff', but the code (commands/run.py _run via dispatch run_selection) exits 3 with a plain 'error: copilot not found on PATH (nor a Copilot CLI already downloaded by gh)' or 'error: copilot is not logged in; run copilot login' line, not a §14 handoff naming operation, constraint, evidence and alternatives (dispatch._handoff is never reached on that path) - expected §14 to describe the outcome the code produces

### N04 replan 1 · 2026-10-26
plan: REPLANNED
- cause: verify FAIL C4, FORMAT §14 (docs/FORMAT.md:940) claimed a missing copilot/gh executable or login exits 3 with a handoff, while the code exits 3 with one plain error line (dispatch CLI runs go through run_selection, never _handoff)
- brief now requires FORMAT and COPILOT.md to state every Copilot CLI failure as exit 3 with one error line via plz run and plz dispatch, a handoff being only a selection outcome; C4 checks each failure output against the code
- Context line refs refreshed to the current tree; code, Write paths and C1-C3, C5 unchanged, so only the doc wording needs fixing

### N04 try 1 · 2026-10-26
exec: DONE · 1268 passed
- Copilot CLI delivery in runner.py/run.py with fake-executable tests and e2e stubs; FORMAT §4/§9/§14 and COPILOT.md state each CLI failure as exit 3 with one error line
- Bare copilot with an effort and copilot::opus|sonnet|haiku exit 3 before any subprocess
check: PASS 3/3
verify: PASS

### N05 try 1 · 2026-10-26
exec: DONE · 1270 passed
- README: Copilot described as harness and delivery route (entrypoint, auth check, bare model, effort, dispatch for copilot::opus, no visual agent), links docs/COPILOT.md; stale disabled claims removed
- tests/kit/test_readme.py: new tests for the above; dropped the old 'external Copilot remains disabled' pin
check: PASS 3/3
verify: PASS

### N06 try 1 · 2026-10-26
exec: BLOCKED · src/planzilla/kit/agents/claude/plz-run.md (outside Write) accepts only letters, digits, '.', '_', '@', '-' in the model, so the D5 route copilot::<id> -> plz-run answers 'error: bad Run input'; add plz-run.md (allow '::') to Write. Rest of N06 is in the tree: both skills, template, docs, tests; uv run pytest -q passes (1301)

### N06 replan 1 · 2026-10-26
plan: REPLANNED
- cause: exec BLOCKED, src/planzilla/kit/agents/claude/plz-run.md:11-12 limits the model to letters, digits, '.', '_', '@', '-', so the D5 route copilot::<id> -> plz-run answers 'error: bad Run input', and that file was outside Write
- brief adds plz-run.md (admit ':' in the model rule, keep role check and quoting) and tests/kit/test_roles.py to Write, with a test-first pin and C3 checking plz-run.md accepts copilot::<id>[@<e>]; rest of the brief, model and C1-C5 unchanged

### N06 try 1 · 2026-10-26
resume: rerun at try 1; partial edits of this try may be in the tree
exec: DONE · 1302 passed, 1 skipped
- Skills rewritten as step lists sharing one Dispatch contract (D5 rule, plz dispatch advanced path with shipped capabilities.json example, Copilot as harness and delivery route); README, FORMAT 11/14, COPILOT.md match
- plz-run.md model rule now admits colon so copilot::<id>[@<effort>] passes; role check, bad Run input and single-quoting kept; test_roles asserts it
- Example facts file: CLI claude/codex/copilot records with placeholder evidence, all enabled false; test loads it through dispatch --facts and expects exit 3
check: PASS 3/3
verify: FAIL C3
- C3 src/planzilla/kit/skills/plz-run-plan/SKILL.md, src/planzilla/kit/skills/plz-new-plan/SKILL.md - not evidenced: the criterion requires both skills to meet D8, but the verify brief does not state D8, so conformance cannot be judged cold; every other C3 clause holds (native/plz-run/shell-job rule, copilot::<id>[@<e>] in plz-run.md, plz-visual and undispatchable stop, plz dispatch advanced path, Loop steps 3-5 one case per line, identical ## Dispatch contract) - expected: D8 stated in the criterion itself so it can be verified

### N06 try 2 · 2026-10-26
exec: BLOCKED · finding C3 needs D8 stated in the criterion text, a plan edit outside Write; the work itself passes (1302 passed, both skills at most 80 lines, tests/kit/test_skills.py now labels the 80-line test as D8)

### N06 replan 2 · 2026-10-26
plan: REPLANNED
- cause: verify could not judge D8 cold because C3 did not state it, and the tree in fact breaks D8: both skills have many lines after the front matter over 120 characters (up to 629), and wrapped they need about 115 lines against the 80-line limit
- brief restates D8 and D5 in Context, adds C1 as a cmd that checks 80 lines and 120 characters per skill (fails on the current tree), has C3 spell out every D8 clause, and asks for trimming prose and a D8 width test first; Write, model and the other criteria unchanged

### N06 try 1 · 2026-10-26
exec: DONE · 1305 passed, 1 skipped
- Both SKILL.md rewrapped to 80 lines, body lines at most 120 chars, Loop sub-cases on own 3-space lines, identical shorter Dispatch contract (D5 rule, Copilot route, plz dispatch with the example)
- New D8 tests (120 chars, 3-space Loop sub-cases) and FORMAT 11 leads with the dispatch rule and names .planzilla/templates/capabilities.json
- Dropped blank lines before headings and condensed prose to fit 80 lines while keeping every pinned phrase
check: PASS 3/3
verify: PASS
