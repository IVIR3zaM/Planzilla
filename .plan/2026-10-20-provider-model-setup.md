# Provider model setup and the v0.2.0 release
status: RUNNING
created: 2026-10-20 · updated: 2026-10-20
goal: bare codex and claude tokens run each CLI's default model, a harness key steers visual verification, plz-new-plan sets up providers, README and FORMAT teach it all, and v0.2.0 ships to the Homebrew tap
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
commit: per-node
push: per-node
budgets: 2 tries per brief · 2 replans per node
tier: M

## Intent

Goal: Close what the codex-model-routing plan left open. A plan can name a provider without pinning a versioned
model (`codex@medium` runs whatever model the user's Codex CLI is set to), the planner picks models by difficulty
instead of by hard-coded version names, a repo records which harness runs its plans so visual checks land on a
verifier that can actually run, plz-new-plan sets providers and harness up from what is installed, and the docs
alone teach a human or an agent all of it. Then release this as v0.2.0.

In scope: bare provider tokens `claude` and `codex` with optional `@<effort>`, for which `plz run` passes no model
flag, only the effort flag; planner guidance by difficulty (Codex by effort on the default model, Claude by its
versionless aliases); a `harness` config key (claude-code or codex) with a default that keeps every existing
config valid, used by the planner and by a new lint rule for `[visual]` criteria; plz-new-plan detecting the
installed and logged-in provider CLIs and its own harness, asking which to list, and adding a missing provider
to an existing config; plz-run-plan dispatch wording for Claude Code and Codex; FORMAT first, then code, kit and
README, so README and FORMAT agree on tokens, providers, model choice, dispatch per harness, enabling the other
provider, the harness key, visual verification, releasing and upgrading; version 0.2.0, re-vendoring this repo
and listing both providers and the harness in its config; PR, merge, tag and a green release with the tap
formula at 0.2.0.

Out of scope: providers other than claude and codex; a plz-visual adapter or any other agent files for Codex;
migrating existing plan files; changes to the release workflow.

Constraints: AGENTS.md rules: strict TDD, stdlib only at runtime, pure core with all IO in commands/, one module
per command, FORMAT is the contract and changes first (D9), KISS/YAGNI, Write paths only, agents never commit.
Tests never run a real `claude` or `codex` or reach the network (D14). The PR, its merge, the tag and its push
are pre-authorized by the user (D12). The orchestrator runs the vendored 0.1.0 CLI until N07 re-vendors (D11).
Machine: claude 2.1.89 and codex-cli 0.163.0, both logged in; gh logged in as IVIR3zaM with the
HOMEBREW_TAP_TOKEN secret set. Decisions D1-D17.

Definition of done: the full verify passes and this plan lints ok; `plz run` with a bare token builds argv
without a model flag; config parses `harness` and lint rejects `[visual]` where the harness cannot run it; the
kit names no versioned Codex model; README and FORMAT agree on every topic in scope; v0.2.0 is tagged on main's
merge commit, its Release run is green in build, brew and publish, and the tap's formula points at the 0.2.0
sdist.

## Decisions

- D1 Bare provider tokens: `claude` and `codex` are names whose provider is themselves, valid alone or with that provider's `@<effort>` levels (claude low, medium, high, max; codex low, medium, high, xhigh, max). They mean that CLI's own configured default model: `plz run` omits `-m <name>` (codex) or `--model <name>` (claude) and keeps the effort flag when an effort is given; every other token keeps today's argv. Explicit names (`gpt-5.5`, `claude-*`, opus, sonnet, haiku, fable) stay valid | confirmed
- D2 Dispatch of bare tokens: no harness subagent tool accepts `claude` or `codex` as a model, so both always go through `plz run`, in Claude Code too, where `claude` becomes `claude -p` on the user's default model; the native-or-`plz run` rule keeps its shape | confirmed
- D3 Planner model guidance (planner role and FORMAT): only providers listed in config `providers`; by difficulty, mechanical haiku or codex@low, well-specified coding sonnet or codex@medium, judgement opus, fable or codex@high; the verify model follows the hardest non-`cmd` criterion on the same scale; Codex by effort on the bare `codex` token, never a versioned Codex name unless the request names one; Claude by the versionless aliases, without `@<effort>` where Claude Code should run them natively; with both providers listed, verify on the other provider than the node's exec; a replan may move a node to the other provider with `plz set <plan> <id> --model M` when one provider's usage runs out | confirmed
- D4 Config key `harness`: `claude-code` or `codex`, default `claude-code` (what every config so far assumed, so all stay valid); a bad value is the parse error `bad harness value '<v>': expected one of claude-code, codex` (the existing choice wording, src/planzilla/config.py:115-118); read by the CLI (`lint`) and the planner, never by executors or verifiers | confirmed
- D5 Harness facts, one pure table beside the provider table in src/planzilla/providers.py: claude-code runs opus, sonnet, haiku and fable natively (no `@<effort>`) and has the visual agent plz-visual; codex runs no model natively, because the kit ships no Codex agent files, and has no visual agent. So in Codex every dispatch is a `plz run` background shell job (the existing no-subagent path) | confirmed
- D6 No visual agent: with harness codex the planner writes no `[visual]` criterion; what a verifier can observe through commands becomes `[smoke]`, what only eyes can judge becomes `[human]`. New lint rule `visual`, from config `harness` and `models`: a `[visual]` criterion under a harness without a visual agent gives `visual: <id> [visual] needs a visual agent; harness <h> has none` on the criterion line; a node with a `[visual]` criterion whose verify model (Graph `<verify>`, config `models` verify when `-`) the harness does not run natively gives `visual: <id> verify <token> is not a model harness <h> runs natively` on the row line | confirmed
- D7 Codex as the harness, in the docs: Codex reads AGENTS.md and `.agents/skills/`; each step runs as a `.planzilla/plz run` background job; those jobs start `codex exec` or `claude -p`, which need the network and their login files outside the repo, so the docs tell Codex users to approve running `.planzilla/plz run` outside Codex's sandbox when Codex asks, and never recommend `--dangerously-bypass-approvals-and-sandbox`; every Codex flag the docs name is checked against `codex --help` | confirmed
- D8 plz-new-plan setup: before its one question round the skill detects, per provider, the CLI on PATH (`command -v claude`, `command -v codex`) and its login (`claude auth status` exit 0 with `"loggedIn": true`; `codex login status` exit 0), and its own harness (`CLAUDECODE=1` in the environment means claude-code; otherwise the agent names its harness, Codex is codex). The round asks which providers to list (recommended: every logged-in one) and the harness (recommended: the detected one) next to the other config values; a provider that is not logged in gets its login command (`claude auth login`, `codex login`). Codex only: the config also gets `models: planner=codex@high, exec=codex@medium, verify=codex@medium`. Config exists: when the request names a provider config does not list, or config has no `harness` and the detected one is not claude-code, the same round asks it and the skill rewrites only that one line (adding it when absent); nothing else in the file changes | confirmed
- D9 FORMAT first: N02 writes every FORMAT change before any code; the code nodes and the kit follow it; README comes last, written against FORMAT, the code and the kit | confirmed
- D10 This plan's own nodes run on Claude aliases dispatched natively, since this repo's config lists only claude until N07 adds codex; N09's verify stays on Claude | confirmed
- D11 N07 does three things together: bumps `__version__` to 0.2.0, runs `uv run planzilla install` from the working tree (the sanctioned writer of `.planzilla/`, `.claude/agents/plz-*.md`, `.claude/skills/plz-*/`, `.agents/skills/plz-*/` and the AGENTS.md block; that one command overrides the executor rule against editing them), and adds `providers: claude, codex` and `harness: claude-code` to `.plan/config.md`. Together, because the vendored 0.1.0 CLI the orchestrator runs rejects an unknown `harness` key | confirmed
- D12 Release, pre-authorized by the user, no gate node: N08 opens the PR feat/codex-model-routing into main with `gh pr create`, waits up to 20 minutes for its checks, merges only when all are success or skipped, fetches main, tags the merge commit v0.2.0 (lightweight, like v0.1.0), pushes it with `git push origin v0.2.0` and waits for the tag's Release run. It never force-pushes, never moves or deletes a tag or branch, never checks out main, never touches the tap, secrets or GitHub release by hand; a v0.2.0 tag at another commit means BLOCKED. The PR merges as a merge commit (`gh pr merge --merge`), as PR #1 and #2 | confirmed
- D13 Records after the merge: N08's and N09's own node commits (plan state only) land on feat/codex-model-routing after the merge and are pushed there; they reach main with the next PR, and neither the tag nor the release waits for them | confirmed
- D14 Tests never run the real `claude` or `codex` CLI or reach the network; they stub `subprocess.run` and `shutil.which`. Real model calls happen only in N01 | confirmed
- D15 N01 makes one minimal real call per CLI on its configured default model (no `--model`, no `-m`, effort low) to prove the bare-token meaning and the logins before any node runs | confirmed
- D16 Release done means: the tag's Release run is completed with build, brew and publish all success; the GitHub release v0.2.0 holds the sdist and the wheel; the tap's Formula/planzilla.rb points at the v0.2.0 sdist with its sha256 | confirmed
- D17 N01 C3 failed because this machine's Claude default model was `opus[1m]` (~/.claude/settings.json:2), on which `claude -p` returns 429 (usage credits required for long context). The user sets `"model": "opus"` in ~/.claude/settings.json or adds usage credits; N01 reruns unchanged with no model flag on either CLI, and D15 holds | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | preflight | check | - | -/- | 1 | 1 | DONE | |
| N02 | FORMAT contract for tokens, harness and docs topics | exec | N01 | opus/sonnet | 1 | 2 | DONE | |
| N03 | bare provider tokens in plz run | exec | N02 | sonnet/sonnet | 1 | 0 | DONE | |
| N04 | harness key and lint rule visual | exec | N03 | sonnet/sonnet | 1 | 0 | DONE | |
| N05 | planner role and both skills | exec | N02 | opus/sonnet | 1 | 0 | DONE | |
| N06 | README aligned with FORMAT | exec | N04,N05 | sonnet/opus | 1 | 0 | DONE | |
| N07 | version 0.2.0, re-vendor, repo config | exec | N04,N05 | haiku/- | 1 | 0 | DONE | |
| N08 | tag v0.2.0 and release | exec | N06,N07 | sonnet/- | 1 | 1 | DONE | |
| N09 | plan acceptance | check | N08 | -/opus | 0 | 0 | TODO | |

## N01 preflight
Do: Confirm the starting point: verify passes on the untouched tree; claude and codex are installed and logged
in; one minimal real call per CLI on its configured default model, with no model flag and effort low, answers
(D1, D15); the branch is feat/codex-model-routing, level with origin/main's history and pushable; tag v0.2.0
exists nowhere yet; gh can push to the repo, the HOMEBREW_TAP_TOKEN secret exists and the tap is readable; and
`uv run` uses this working tree's package (N07 vendors from it).
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `command -v claude && claude auth status | grep -q '"loggedIn": true' && command -v codex && codex login status && codex exec --help | grep -q -- '--model'`
- C3 [cmd] `printf 'Reply with the single word ok and nothing else.' | claude -p --effort low --output-format text --no-session-persistence --tools "" --permission-mode dontAsk | grep -qiw ok`
- C4 [cmd] `d=$(mktemp -d) && printf 'Reply with the single word ok and nothing else.' | codex exec -c 'model_reasoning_effort="low"' -s read-only --skip-git-repo-check -C "$d" -o "$d/last" - > /dev/null 2>&1; grep -qiw ok "$d/last"; r=$?; rm -rf "$d"; exit $r`
- C5 [cmd] `test "$(git branch --show-current)" = feat/codex-model-routing && git fetch -q origin && test -z "$(git log --oneline HEAD..origin/main)" && git push --dry-run origin HEAD`
- C6 [cmd] `test -z "$(git ls-remote origin refs/tags/v0.2.0)" && ! git rev-parse -q --verify refs/tags/v0.2.0`
- C7 [cmd] `gh api repos/IVIR3zaM/Planzilla --jq .permissions.push | grep -qx true && gh secret list -R IVIR3zaM/Planzilla | grep -q '^HOMEBREW_TAP_TOKEN' && gh api repos/IVIR3zaM/homebrew-tap/contents/Formula/planzilla.rb --jq .name | grep -qx planzilla.rb`
- C8 [cmd] `uv run python -c "import pathlib, planzilla; assert pathlib.Path(planzilla.__file__).resolve().parent == pathlib.Path('src/planzilla').resolve()"`

## N02 FORMAT contract for tokens, harness and docs topics
Do: Write every FORMAT change before any code (D9). In docs/FORMAT.md change only §4 :133, §6 :282, §8 :338,
  §9 :426, §11 :491 and §14 "Native or `plz run`" :610 so they state what C2-C8 say (the confirmed Decisions D1-D8
  in full), each once, where each names; the rest of FORMAT stays byte-identical.
Write: `docs/FORMAT.md`
Done when:
- C1 [cmd] `f=docs/FORMAT.md; grep -q '^| .harness. |' $f && grep -q 'claude-code' $f && grep -q 'codex@medium' $f && grep -q 'harness <h> has none' $f && grep -q 'runs natively' $f && grep -q 'codex login status' $f && grep -q 'fresh' $f && ! grep -q 'gpt-6' $f`
- C2 [review] §4: the token table's names gain bare `claude` and `codex`; after it, a bare `claude`/`codex` means
  that CLI's configured default model, alone or with its provider's `@<effort>`; `run` omits the model flag for it
  and keeps the effort flag; every other token keeps its argv.
- C3 [review] §4, once, harness-neutral: models only of config `providers`; mechanical haiku or `codex@low`,
  well-specified coding sonnet or `codex@medium`, judgement opus, fable or `codex@high`; verify model follows the
  hardest non-`cmd` criterion; Codex by effort on bare `codex` (versioned name only if the request names one); Claude
  by versionless aliases, no `@<effort>` where run natively; both providers: verify on the other one than exec; a
  replan may move a node (`plz set <plan> <id> --model M`) when one provider's usage runs out. §6 uses that scale.
- C4 [review] §8: a `harness` row, `claude-code` · `codex`, default `claude-code`, used by `lint` (rule `visual`)
  and the planner, never executors or verifiers; limits gain `bad harness value '<v>': expected one of claude-code,
  codex`; `providers` used-by adds plz-new-plan.
- C5 [review] §8 opening: plz-new-plan detects each provider's CLI (`command -v`), login (`claude auth status` exit 0
  with `"loggedIn": true`; `codex login status` exit 0), harness (`CLAUDECODE=1`: claude-code, else the agent says);
  asks providers (recommends logged-in ones; a logged-out one gets its login command) and harness (recommends the
  detected one); Codex alone adds `models: planner=codex@high, exec=codex@medium, verify=codex@medium`; existing
  config: a named provider it lacks, or no `harness` when detected is not claude-code, is asked; only that line changes.
- C6 [review] §9: `run` omits `-m <name>` / `--model <name>` for bare `codex` / `claude`, keeps the effort flag;
  lint gains `visual`: criterion line `<id> [visual] needs a visual agent; harness <h> has none`; row line, for a
  `[visual]` node whose verify model (Graph `<verify>`, else config `models` verify) the harness does not run
  natively, `<id> verify <token> is not a model harness <h> runs natively`.
- C7 [review] §11 "Versions and upgrades": `__version__` in src/planzilla/__init__.py is the one version; a release
  is tag `v<version>` on main, whose Release workflow publishes the GitHub release and tap formula; upgrading reruns
  `planzilla install` (or `--version vX`): rewrites only changed files, removes files the kit dropped, never writes
  `.plan/`; then commit and start a fresh agent session (skills and agents load at session start).
- C8 [review] §14 per-harness table: claude-code runs opus, sonnet, haiku, fable natively without `@<effort>`, others
  via the `plz-run` adapter, `[visual]` by plz-visual; codex runs nothing natively (each dispatch a background `plz
  run` job), no visual agent, so `[smoke]` or `[human]`; a bare `claude`/`codex` always goes through `plz run`, in
  Claude Code too. Then: enable the other provider by installing its CLI, logging in (`codex login`, `claude auth
  login`), listing it in `providers`; Codex reads AGENTS.md and `.agents/skills/`; its `plz run` jobs need network
  and logins outside the repo, so approve `.planzilla/plz run` outside Codex's sandbox when asked; never recommend
  `--dangerously-bypass-approvals-and-sandbox`; each Codex flag named exists in `codex --help`.
- C9 [review] `git diff HEAD -- docs/FORMAT.md` touches only §4, §6, §8, §9, §11, §14; nothing contradicts the rest.
- C10 [cmd] `uv run pytest -q`

## N03 bare provider tokens in plz run
Do: Test first, make the bare tokens `claude` and `codex` work as FORMAT §4 and §9 now say (D1). Their provider
is themselves; `@<effort>` takes that provider's levels; `plz run` builds argv without `-m <name>` for `codex`
and without `--model <name>` for `claude`, keeping the effort flag when given and every other item as today.
Context: provider lookup src/planzilla/providers.py:10-20, token split :27-40 (the one place that knows names);
argv src/planzilla/runner.py:39-72, keep `build_argv`'s signature; validation :16-28. Every other token's argv
stays byte-identical. D14: stub `subprocess.run` and `shutil.which` as tests/commands/test_run.py does.
Read: `docs/FORMAT.md` §4 and §9, `src/planzilla/providers.py`, `src/planzilla/runner.py`, `src/planzilla/commands/run.py`, the tests below
Write: `src/planzilla/providers.py`, `src/planzilla/runner.py`, `tests/test_providers.py`, `tests/test_runner.py`,
  `tests/commands/test_run.py`
Test first: provider of `claude` and `codex`; `codex@xhigh`, `claude@max` split; `codex@huge`, `claude@xhigh`
rejected; argv for `codex` and `codex@high` (no `-m`), `claude` and `claude@low` (no `--model`) per role;
`plz run verifier codex@low '<line>'` with stubs prints the reply and calls `codex exec` without `-m`. See them
fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_providers.py tests/test_runner.py tests/commands/test_run.py`
- C2 [cmd] `uv run python -c "from planzilla import runner; a = runner.build_argv('verifier', 'codex', 'codex', 'high', '/r', '/o'); assert '-m' not in a and 'model_reasoning_effort=\"high\"' in a; b = runner.build_argv('verifier', 'claude', 'claude', None, '/r', None); assert '--model' not in b and '--effort' not in b; c = runner.build_argv('executor', 'codex', 'gpt-5.5', None, '/r', '/o'); assert c[2:4] == ['-m', 'gpt-5.5']"`
- C3 [review] providers.py stays the only place that knows names and levels and stays pure; runner.py stays
  pure; only bare tokens change argv; tests stub every CLI call.
- C4 [cmd] `uv run pytest -q`

## N04 harness key and lint rule visual
Do: Test first, add config `harness` (D4) and lint rule `visual` (D6) as FORMAT §8 and §9 now say. The harness
facts (D5: which models each harness runs natively, whether it has a visual agent) go in a pure table in
src/planzilla/providers.py next to the provider table. Config gets field `harness`, default `claude-code`. Lint
passes the config's harness and `models` verify into the pure `lint_plan` and reports both D6 messages exactly,
the first on the `[visual]` criterion's line, the second on the node's Graph row. The config template gets a
`harness: claude-code` line and its format-rules comment names the key and its values; the full-config fixture
gets the key.
Context: config keys src/planzilla/config.py:11-23, defaults :29-41, values :80-112; lint rules
src/planzilla/commands/lint.py:136-164, run path :199-207 (reads the plan repo's config); criteria carry their
tag and line (src/planzilla/plan.py:144-150). Verify model when the Graph says `-`: config `models` verify, as
`next` does (src/planzilla/state.py:297-305). Template src/planzilla/kit/templates/config.md:1-22 (its last line
stays a `#` comment, tests/kit/test_roles.py:56-62). Fixture tests/fixtures/plans/repo/.plan/config.md holds
every §8 key (tests/test_config.py:33).
Read: `docs/FORMAT.md` §8 and §9, the files above, `tests/test_config.py`, `tests/commands/test_lint.py`
Write: `src/planzilla/providers.py`, `src/planzilla/config.py`, `src/planzilla/commands/lint.py`,
  `src/planzilla/kit/templates/config.md`, `tests/test_providers.py`, `tests/test_config.py`,
  `tests/commands/test_lint.py`, `tests/fixtures/lint/visual*/**`, `tests/fixtures/plans/repo/.plan/config.md`
Test first: `harness: codex` parses, default `claude-code`, `harness: cursor` is the D4 error; a fixture plan
with a `[visual]` node verified by `sonnet` lints ok under claude-code; with `sonnet@high`, `codex@high` or `-`
plus `models: verify=gpt-5.5` (providers both) it gives the row message; under `harness: codex` any `[visual]`
gives the criterion message; plans without `[visual]` never raise it. See them fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_providers.py tests/test_config.py tests/commands/test_lint.py tests/kit`
- C2 [cmd] `uv run python -c "from planzilla.config import parse_config as p; assert p('', 'c').harness == 'claude-code' and p('harness: codex', 'c').harness == 'codex'"`
- C3 [review] `lint_plan` stays pure; both messages read exactly as D6 and sit on the stated lines; the harness
  table lives only in providers.py; other lint rules and outputs are unchanged.
- C4 [cmd] `uv run pytest -q`

## N05 planner role and both skills
Do: Teach the kit the new rules, test first, as FORMAT §4, §8 and §14 now say.
- Planner role: replace the models guidance with D3 (no versioned Codex names) and add the harness rule: read
  config `harness`; claude-code puts `[visual]` verify on a bare Claude alias; codex writes no `[visual]`, using
  `[smoke]` or `[human]` instead (D6). Keep every other rule; tighten wording to stay within 30 lines.
- plz-new-plan: the D8 detection, question and config edit, in its existing config step and one round.
- plz-run-plan: the Dispatch rule per D2 and D5: bare tokens never native; the `plz-run` adapter only where
  the harness has it (Claude Code), else background shell jobs (Codex); `plz-visual` where there is none stops
  the run with the existing `cannot dispatch` line.
Context: planner role src/planzilla/kit/roles/planner.md:16 (the models line) and :25 (L8, keep), limit 30 lines
(tests/kit/test_roles.py:50-53) and its words test :66-71; plz-new-plan
src/planzilla/kit/skills/plz-new-plan/SKILL.md:21-31 and :35-38; plz-run-plan
src/planzilla/kit/skills/plz-run-plan/SKILL.md:63-71; each skill at most 80 lines (tests/kit/test_skills.py:50);
skills name only plz-* agents and skills and only registered `plz` commands (:43-60). Skills ship to
`.agents/skills/` too: harness names appear only as examples or in the per-harness rule.
Read: `docs/FORMAT.md` §4, §8, §14, the files above, `tests/kit/test_roles.py`, `tests/kit/test_skills.py`, `tests/kit/test_preflight.py`
Write: `src/planzilla/kit/roles/planner.md`, `src/planzilla/kit/skills/plz-new-plan/SKILL.md`,
  `src/planzilla/kit/skills/plz-run-plan/SKILL.md`, `tests/kit/test_roles.py`, `tests/kit/test_skills.py`
Test first: the planner words test requires `codex@low`, `codex@medium`, `codex@high`, `harness`, `fable`,
`natively`, `--model`, `providers` and forbids `gpt-6`; plz-new-plan must name `claude auth status`,
`codex login status`, `harness` and `providers`; plz-run-plan must name `Codex` and `plz-run`. See them fail.
Done when:
- C1 [cmd] `uv run pytest -q tests/kit`
- C2 [cmd] `k=src/planzilla/kit; ! grep -rq 'gpt-6' $k && grep -q 'codex@medium' $k/roles/planner.md && grep -q 'harness' $k/roles/planner.md && grep -q 'codex login status' $k/skills/plz-new-plan/SKILL.md && grep -q 'harness' $k/skills/plz-run-plan/SKILL.md`
- C3 [review] The role holds D3 and the D6 harness rule with its other rules intact; plz-new-plan does D8 in
  its single round and edits one line only; plz-run-plan routes per D2 and D5 and keeps native and `plz run`
  dispatches in one parallel batch.
- C4 [cmd] `uv run pytest -q`

## N06 README aligned with FORMAT
Do: Rewrite README.md so a reader learns from it alone what FORMAT now specifies, linking FORMAT for exact
grammar and outputs instead of copying it. Cover: model tokens and providers (aliases, `claude`, `codex`,
explicit names, `@<effort>`); how the planner picks models (D3 tiers, cross-provider verify, moving a node when
usage runs out); dispatch in Claude Code (native vs `plz-run`) and in Codex (every step a `plz run` job, D5);
enabling Codex from Claude and Claude from Codex (install, log in, `providers`, D7 sandbox approval); the
`harness` key in the Config table and visual verification per harness (D6, the `[visual]` row); what
plz-new-plan detects and asks (D8); upgrading a repo (`planzilla install`, `--version vX`, what install touches
and never touches, check `.planzilla/VERSION`, commit, start a fresh session); releasing (bump `__version__`,
re-vendor, merge to main, push tag `v<version>`, release.yml builds, brew-tests and publishes the GitHub release
and tap formula, users run `brew upgrade planzilla`). Update the `planzilla install --version` example to v0.2.0.
Context: FORMAT §4, §6, §8, §9, §11, §14 (written by N02) are the source of truth; also
src/planzilla/kit/roles/planner.md, both skills under src/planzilla/kit/skills/, .github/workflows/release.yml
(tag check :33, publish :116-180). README today: Vendor :40-69, Claude Code :71-88, other harnesses :90-117,
Config :136-153, Models :155-170, tags :172-182, CLI :204-226. tests/kit/test_preflight.py reads the Tiers section.
Read: `README.md`, `docs/FORMAT.md`, the files above
Write: `README.md`
Test first: -
Done when:
- C1 [cmd] `f=README.md; grep -q '^| .harness. |' $f && grep -q 'codex@medium' $f && grep -q 'claude auth login' $f && grep -q 'codex login' $f && grep -q 'brew upgrade planzilla' $f && grep -q 'v0.2.0' $f && grep -qi '^## .*upgrad' $f && grep -qi '^## .*releas' $f && ! grep -q 'gpt-6' $f`
- C2 [review] README covers every topic in Do and agrees with FORMAT on each (no rule stated differently,
  no rule FORMAT lacks); it links FORMAT sections rather than restating grammar and output lines.
- C3 [cmd] `uv run pytest -q`

## N07 version 0.2.0, re-vendor, repo config
Do: Test first, set the version to 0.2.0: change the expected `--version` line in tests/test_cli.py:37 to
`planzilla 0.2.0`, see it fail, then set `__version__` in src/planzilla/__init__.py:3. Then run
`uv run planzilla install` from the repo root (D11 authorizes this command to rewrite the vendored paths in
Write). Then add two lines to `.plan/config.md`, directly after its `models:` line: `providers: claude, codex`
and `harness: claude-code`; change no other line of that file.
Context: D11: these three steps belong together because the vendored 0.1.0 CLI rejects `harness`. Install
prints `installed planzilla 0.2.0 into <root>: …` and writes only changed files (FORMAT §11). Never edit a
vendored file by hand.
Read: `tests/test_cli.py`, `src/planzilla/__init__.py`, `.plan/config.md`
Write: `src/planzilla/__init__.py`, `tests/test_cli.py`, `.planzilla/**`, `.claude/agents/plz-*.md`,
  `.claude/skills/plz-*/**`, `.agents/skills/plz-*/**`, `AGENTS.md`, `.plan/config.md`
Test first: tests/test_cli.py expects `planzilla 0.2.0`; see it fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_cli.py`
- C2 [cmd] `test "$(cat .planzilla/VERSION)" = 0.2.0 && .planzilla/plz --version | grep -qx 'planzilla 0.2.0'`
- C3 [cmd] `uv run planzilla install | grep -q ': 0 added, 0 changed, 0 removed$'`
- C4 [cmd] `grep -qx 'providers: claude, codex' .plan/config.md && grep -qx 'harness: claude-code' .plan/config.md && test "$(git diff HEAD --numstat -- .plan/config.md | cut -f1,2)" = "$(printf '2\t0')" && .planzilla/plz lint provider-model-setup | grep -q '^lint ok'`
- C5 [cmd] `uv run pytest -q`

## N08 tag v0.2.0 and release
Do: Tag the merged release and let its Release run publish it (D12, pre-authorized). Stay on branch
feat/codex-model-routing throughout. PR #3 (feat/codex-model-routing into main) is merged; its merge commit is
478d1145a32847c2def9a44e6d296dc5bdcc14b9, the tip of origin/main.
1. `git fetch origin main --tags`; confirm `git rev-parse origin/main` and the PR's `merge_commit_sha` (C1's API
   call) both equal 478d1145a32847c2def9a44e6d296dc5bdcc14b9; any mismatch: BLOCKED with both shas.
2. `git ls-remote origin refs/tags/v0.2.0`: absent, `git tag v0.2.0 478d1145a32847c2def9a44e6d296dc5bdcc14b9`
   (lightweight, like v0.1.0) then `git push origin v0.2.0`; present at that sha, nothing to push; anywhere
   else, BLOCKED. A local v0.2.0 at another sha: BLOCKED, never delete or move it.
3. Wait, in Bash calls of at most 5 minutes each and up to 20 minutes in all, until the Release run for v0.2.0
   completes; any job not success: BLOCKED with the failing job and its last error line.
A command the permission system denies: reply BLOCKED naming it; never retry it another way.
Never force-push, move or delete a tag or branch, check out main, edit files, merge anything, or touch the tap,
secrets or the GitHub release by hand: the tag's Release run does those.
Context: D12 the release steps, pre-authorized; D16 done means the Release run's build, brew and publish jobs
are all success. release.yml:33-40 fails unless the tag equals `v` + `__version__`; src/planzilla/__init__.py:3
is 0.2.0.
Write: -
Test first: -
Done when:
- C1 [cmd] `test "$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=closed&base=main&head=IVIR3zaM:feat/codex-model-routing' --jq '[.[]|select(.merged_at!=null)]|length')" = 1`
- C2 [cmd] `m=$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=closed&base=main&head=IVIR3zaM:feat/codex-model-routing' --jq '[.[]|select(.merged_at!=null)][0].merge_commit_sha'); test -n "$m" && test "$(git ls-remote origin refs/tags/v0.2.0 'refs/tags/v0.2.0^{}' | tail -1 | cut -f1)" = "$m"`
- C3 [cmd] `test "$(git branch --show-current)" = feat/codex-model-routing`
- C4 [cmd] `gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=push&branch=v0.2.0' --jq '[.workflow_runs[]|select(.name=="Release")][0]|.status+" "+.conclusion' | grep -qx 'completed success'`
- C5 [cmd] `uv run pytest -q`

## N09 plan acceptance
Do: Check the whole plan: verify passes, the plan lints ok, v0.2.0 sits on main with version 0.2.0, its Release
run is green in all three jobs, the release holds sdist and wheel, the tap formula points at the 0.2.0 sdist
with its sha256 (D16), bare tokens build argv without a model flag, the kit and its vendored copies name no
versioned Codex model, and README and FORMAT agree. C4 waits up to 14 minutes for the run.
Context: D1-D8 are the features; D12-D13 the release; published sdist url
https://github.com/IVIR3zaM/Planzilla/releases/download/v0.2.0/planzilla-0.2.0.tar.gz. REST only.
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `.planzilla/plz lint provider-model-setup | grep -q '^lint ok'`
- C3 [cmd] `git fetch -q origin main --tags && git merge-base --is-ancestor v0.2.0 origin/main && git show v0.2.0:src/planzilla/__init__.py | grep -qx '__version__ = "0.2.0"'`
- C4 [cmd] `for i in $(seq 84); do r=$(gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=push&branch=v0.2.0' --jq '[.workflow_runs[]|select(.name=="Release")][0]|"\(.id) \(.status) \(.conclusion)"'); [ "$(echo "$r" | cut -d' ' -f2)" = completed ] && break; sleep 10; done; test "${r#* }" = "completed success" && gh api repos/IVIR3zaM/Planzilla/actions/runs/${r%% *}/jobs --jq '[.jobs[]|.name+"="+.conclusion]|sort|join(" ")' | grep -qx 'brew=success build=success publish=success'`
- C5 [cmd] `gh api repos/IVIR3zaM/Planzilla/releases/tags/v0.2.0 --jq '[.assets[].name]|sort|join(" ")' | grep -qx 'planzilla-0.2.0-py3-none-any.whl planzilla-0.2.0.tar.gz'`
- C6 [cmd] `f=$(curl -fsSL https://raw.githubusercontent.com/IVIR3zaM/homebrew-tap/HEAD/Formula/planzilla.rb) && s=$(curl -fsSL https://github.com/IVIR3zaM/Planzilla/releases/download/v0.2.0/planzilla-0.2.0.tar.gz | sha256sum | cut -d' ' -f1) && echo "$f" | grep -qF 'url "https://github.com/IVIR3zaM/Planzilla/releases/download/v0.2.0/planzilla-0.2.0.tar.gz"' && echo "$f" | grep -qF "sha256 \"$s\""`
- C7 [cmd] `uv run python -c "from planzilla import runner; a = runner.build_argv('planner', 'codex', 'codex', 'medium', '/r', '/o'); b = runner.build_argv('planner', 'claude', 'claude', 'high', '/r', None); assert '-m' not in a and '--model' not in b and '--effort' in b"`
- C8 [cmd] `! grep -rq 'gpt-6' src/planzilla/kit .planzilla/roles .planzilla/templates .claude/agents .claude/skills .agents/skills && diff -rq src/planzilla/kit/roles .planzilla/roles && diff -rq src/planzilla/kit/skills .agents/skills`
- C9 [review] README.md and docs/FORMAT.md agree, topic by topic: model tokens and providers; bare `claude` and
  `codex`; how the planner picks models (tiers, cross-provider verify, moving a node); native vs `plz run`
  dispatch in Claude Code and in Codex; enabling Codex from Claude and Claude from Codex; the `harness` key and
  visual verification with lint rule `visual`; plz-new-plan's detection and question; releasing and upgrading
  (`planzilla install`, `--version`, what install touches and never touches, a fresh session after upgrading).
- C10 [review] The planner role holds D3 and the D6 harness rule; plz-new-plan does D8 in one round editing one
  config line only; plz-run-plan routes per D2 and D5; the code matches FORMAT §4, §8 and §9 for D1, D4 and D6.

## Log

### N01 try 1 · 2026-10-20
check: FAIL C3
- C3 exit 1:

### N01 replan 1 · 2026-10-20
plan: ASK D17
- C3 cause: Claude default model opus[1m] in ~/.claude/settings.json; claude -p on it returns 429, usage credits required for long context
- Same call with --model opus answers ok, so login and CLI are fine
- D17 proposed: user switches the default to opus (recommended) or C3 pins --model opus; brief unchanged until answered
plan: BRIEFED
- D17 confirmed: user sets the Claude default model to opus in ~/.claude/settings.json or adds usage credits; D15 holds
- Brief unchanged: C3 keeps no model flag and reruns as written
- At revise time ~/.claude/settings.json:2 still read opus[1m]; C3 passes only once the user's change or credits are in place

### N01 try 1 · 2026-10-20
check: FAIL C3
- C3 exit 1:
check: PASS 8/8

### N02 try 1 · 2026-10-20
exec: BLOCKED · brief cites D3, D4, D6, D8 by number but does not give their content (D3 model scale per provider, D4 harness values/default/error text, D6 two lint messages and report lines, D8 detection rules); the FORMAT contract would have to guess them

### N02 replan 1 · 2026-10-20
plan: REPLANNED
- cause: the brief cited D3, D4, D6, D8 by number only, so the executor could not write their FORMAT text
- change: Context now restates D1-D8 in full (model scale, harness values/default/error, both lint visual messages and report lines, plz-new-plan detection and config update rules)
- change: Do keeps the same section list, compacted to fit 40 lines; C2 now checks D1-D8 and the 11 paragraph as restated

### N02 try 1 · 2026-10-20
exec: DONE · 747 passed, 1 skipped
- docs/FORMAT.md: bare claude/codex tokens and model-choice scale (§4), verifier scale for both providers (§6), harness key, error and plz-new-plan detection (§8), run omits model flag and lint visual rule (§9), Versions and upgrades (§11), per-harness native table, enabling a provider and Codex sandbox notes (§14)
- D3 rules stated once in §4 as Choosing models; §6 cites the §4 scale; argv shows -m/--model as optional brackets
- D7 verified: --dangerously-bypass-approvals-and-sandbox exists in codex --help
check: PASS 2/2
verify: FAIL C2
- C2 docs/FORMAT.md - D1-D8 and the §11 paragraph are referenced as 'above' but the brief does not state them, so the content cannot be compared to evidence - expected criterion to be self-contained

### N02 try 2 · 2026-10-20
exec: DONE · 747 passed, 1 skipped
- docs/FORMAT.md: §4 bare claude/codex names, D1 and model-choice rules; §6 verifier scale; §8 harness row, error and D8 detection; §9 run argv and lint visual; §11 versions paragraph; §14 per-harness table, D2, enabling the other provider and D7
- Try 1 finding concerned the brief lacking D1-D8; the brief now states them and the tree content matches each, so no further FORMAT edits were needed
check: PASS 2/2
verify: FAIL C2
- C2 docs/FORMAT.md - criterion refers to D1-D8 and the §11 paragraph 'as above', but the verify brief does not contain them, so the diff cannot be checked against them - not evidenced

### N02 replan 2 · 2026-10-20
plan: REPLANNED
- cause: the verifier sees only heading, Write and Done when (brief --verify); C2 said 'D1-D8 and the 11 paragraph as above', content that lived in Do and Context, so it failed twice as not evidenced
- change: Done when now restates D1-D8 and the versions paragraph per section as self-contained review criteria C2-C8, plus C9 for diff scope and no contradiction; C1 and the pytest criterion (now C10) unchanged
- change: Do points at C2-C8 and keeps the section list with line cites; Context dropped to fit 40 lines. The tree already holds the FORMAT edits, so the next try may need no edits

### N02 try 1 · 2026-10-20
exec: DONE · 747 passed, 1 skipped
- FORMAT.md §4/§6/§8/§9/§11/§14 state D1-D8: bare claude/codex tokens, model-choice scale, harness config key and lint rule visual, plz-new-plan detection, versions and upgrades, per-harness native table and Codex enablement
- tree already held the full edit; checked each of C1-C9 against it (C1 grep passes, only the six sections differ, the Codex flag named exists in codex --help) and kept it unchanged
check: PASS 2/2
verify: PASS

### N03 try 1 · 2026-10-20
exec: DONE · 766 passed
- provider_of returns a bare claude/codex token as its own provider, so split_token and validate accept it with that provider's efforts
- build_argv omits -m / --model when name == cli; effort flags and all other argv unchanged

### N05 try 1 · 2026-10-20
exec: DONE · 766 passed, 1 skipped
- planner role: D3 one-scale model guidance with codex@low/medium/high, no versioned Codex names, plus the harness rule ([visual] on a bare Claude alias in claude-code; [smoke] or [human] in codex)
- plz-new-plan detects CLIs, logins and harness in its config step, asks providers and harness in the one round, writes or edits one config line; plz-run-plan Dispatch rule routes per harness: native only for Claude aliases in Claude Code, plz-run there, background shell jobs in Codex, plz-visual in Codex hits cannot dispatch
- harness rule folded into the planner's models line to stay at 30 lines; run-plan kept at 80 lines

### N03 try 1 · 2026-10-20
check: PASS 3/3

### N05 try 1 · 2026-10-20
check: PASS 3/3

### N03 try 1 · 2026-10-20
verify: PASS

### N05 try 1 · 2026-10-20
verify: PASS

### N04 try 1 · 2026-10-20
exec: DONE · 785 passed
- config harness (default claude-code), providers.py harness table, lint rule visual with harness+verify passed into pure lint_plan; template and fixture updated
- under a harness with no visual agent only the criterion message is emitted (row message would be redundant)
check: PASS 3/3
verify: PASS

### N07 try 1 · 2026-10-20
exec: DONE · 785 passed, 1 skipped
- Version set to 0.2.0 in __init__.py and test_cli.py; re-vendored with planzilla install (16 files changed)
- Added providers and harness lines to .plan/config.md after models; no other line changed

### N06 try 1 · 2026-10-20
exec: DONE · 785 passed
- README rewritten: models/providers, planner picks, native vs plz run, Codex dispatch, both-provider setup, harness row, plz-new-plan detection, upgrading, releasing
- Kept Tiers and Config adjacent for test_preflight; linked FORMAT sections instead of copying grammar

### N07 try 1 · 2026-10-20
check: PASS 5/5

### N06 try 1 · 2026-10-20
check: PASS 2/2
verify: PASS

### N08 try 1 · 2026-10-20
exec: BLOCKED · PR #3 created, all checks pass, but permission system denied gh pr merge (merge without review)

### N08 replan 1 · 2026-10-20
human: PR 3 merged by the user
- merge commit 478d1145a32847c2def9a44e6d296dc5bdcc14b9 on main; remaining: tag v0.2.0 on it, push the tag, wait for the Release run
plan: REPLANNED
- cause: gh pr merge was denied by the permission system; the user merged PR 3 by hand, merge commit 478d1145 is origin/main
- new brief drops the push, PR and merge steps and keeps only: confirm the merge sha, tag v0.2.0 on it, push the tag, wait for the Release run
- a permission-denied command now means BLOCKED naming it, never a workaround; title is now tag v0.2.0 and release

### N08 try 1 · 2026-10-20
exec: DONE · 785 passed
- Tagged v0.2.0 (lightweight) at 478d114 and pushed; origin/main and PR merge sha matched
- Release run 39407994781: build, brew, publish all success
check: PASS 5/5
