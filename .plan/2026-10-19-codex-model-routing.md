# Claude and Codex model routing for any harness
status: RUNNING
created: 2026-10-19 · updated: 2026-10-19
goal: from any harness, a plan can run each node phase on a Claude model (claude CLI) or a Codex model (codex CLI), with per-node effort, next to natively dispatched nodes
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
commit: per-node
push: per-node
budgets: 2 tries per brief · 2 replans per node
tier: M

## Intent

Goal: Planzilla runs under any harness (Claude Code, Codex CLI, Copilot, Cursor and others), and from any of them
a plan can run a node's planner, exec or verify phase on a Claude model, billed to the user's Claude plan through
the `claude` CLI, or on a Codex model, billed to the user's ChatGPT/Codex plan through the `codex` CLI. The two
quotas then work side by side, and a node built on one provider can be graded on the other. Nothing in the
design is specific to one harness or to "Codex inside Claude Code".

In scope: a pure provider table that maps a model token to the CLI that runs it (claude: opus, sonnet, haiku,
fable, `claude-*`; codex: `gpt-*`; any other token has no provider and runs only natively); an optional
`@<effort>` suffix with levels per provider; a `providers` config key (default `claude`) that config parsing and
`lint` enforce; a `plz run <role> <model> <line>` command that builds the `claude` or `codex` command line, runs
it in the repo root and prints the one-line reply; a harness-neutral dispatch rule in plz-run-plan and
plz-new-plan (native when the harness's own subagents can run the model, else `plz run` through a thin adapter
subagent, `plz-run` in Claude Code, or through background shell jobs where the harness has no subagents);
planner guidance for plans with more than one provider; FORMAT and README updates; re-vendoring the kit here.

Out of scope: `plz run` for the visual role (`[visual]` always stays native); providers other than claude and
codex; adapter files for harnesses other than Claude Code; any change to how plz-planner, plz-executor,
plz-verifier or plz-visual behave; listing codex in this repo's own config.

Constraints: AGENTS.md rules: strict TDD, stdlib only at runtime, pure core with all IO in commands/, one module
per command, FORMAT is the contract, KISS/YAGNI, Write paths only, agents never commit. Tests never run the real
`claude` or `codex` CLI or touch the network; real model calls happen only in check-node criteria (N01 per D15,
N08 per D9). Machine: `claude` 2.1.89, `codex` 0.163.0 logged in via ChatGPT. This plan's own nodes run on
Claude models, dispatched natively. Decisions D1-D16.

Definition of done: the full verify passes; a Graph row with a `gpt-` token and an effort lints ok with
`providers: claude, codex` and fails lint with the default config; an effort the provider lacks is a parse
error; `plz next` and `plz set` print tokens verbatim; `plz run` with stubbed CLIs builds the exact command line
for both providers, prints the one-line reply and exits 3 on each external failure; the kit ships `plz-run`,
both updated skills and the planner role, and this repo's vendored copies match; FORMAT and README describe all
of it, including running nodes with `plz run` from harnesses without subagents; two real calls,
`plz run verifier gpt-6-luna@low …` and `plz run verifier haiku@low …`, each return a one-line reply.

## Decisions

- D1 Provider table and token grammar, in a new pure module `src/planzilla/providers.py`: provider claude for `opus`, `sonnet`, `haiku`, `fable` and names starting `claude-`; provider codex for names starting `gpt-`; any other name has none. A token is a name `[a-z0-9.-]+` with an optional `@<effort>`, allowed only on a token with a provider and only from its levels (claude: low, medium, high, max, the `claude --effort` choices; codex: low, medium, high, xhigh, max); anything else is a parse error wherever a token is read (Graph, `set --model`, config `models`); no suffix = that CLI's own default | confirmed
- D2 The model grammar and the provider table go in FORMAT §4 (the Graph model column, docs/FORMAT.md:124); §2 stays as is | confirmed
- D3 Routing by model, never by agent name: `next` and `set` output is unchanged and prints the token verbatim (`· dispatch plz-executor gpt-6.1-sol@high`); the orchestrator picks native or `plz run` from the token (D13) | confirmed
- D4 Config `providers: <list>`: comma-separated, a non-empty subset of claude and codex without repeats, default `claude` so today's plans stay valid. Config parse error, on the `models` line in either line order, for a `models` token (planner included, any provider allowed) whose provider is not listed. New lint rule `providers`: a Graph exec or verify token whose provider is not listed gives `providers: <id> model <token> needs config providers to list <provider>` on the row line; tokens without a provider and `-` never raise it | confirmed
- D5 `plz run <role> <model> <line>`: role planner, executor or verifier (visual and anything else: exit 2); model a token with a provider and a valid effort (else exit 2); line one non-empty line (else exit 2). It reads no config, runs the provider's CLI in the current directory (the repo root) with the prompt on stdin: `Follow .planzilla/roles/<role>.md: read it first; it is your whole role.` / `Input: <line>` / `Reply with exactly the one line that role names, nothing else.` codex argv: `codex exec -m <name> [-c model_reasoning_effort="<e>"] -s workspace-write -c sandbox_workspace_write.network_access=true -C <cwd> -o <temp file> -`; claude argv: `claude -p --model <name> [--effort <e>] --output-format text --no-session-persistence` plus the D14 permission flags. First checks the CLI is on PATH and logged in (`codex login status` exit 0; `claude auth status` exit 0 with JSON `loggedIn` true). Prints only the reply, the last non-blank line of codex's `-o` file or claude's stdout. Exit 3 with one `error:` line: `<cli> not found on PATH`; `<cli> is not logged in; run <codex login | claude auth login>`; `<cli> exited <n>: <last non-blank stderr line, else stdout line>` (claude prints its auth errors to stdout); `<cli> gave an empty reply`. No timeout of its own | confirmed
- D6 plz-run dispatch line `Run: <role> <model> · <the role's dispatch line>`; the adapter (haiku, tools Bash) starts `.planzilla/plz run` with nohup in the background, stdout, stderr and exit code going to files in a `mktemp -d` dir, then waits in repeated Bash calls each well under 10 minutes until the exit-code file exists; it replies the stdout verbatim, or the first stderr line on a non-zero exit (a malformed reply: re-dispatched once, then the run stops and tells the user) | confirmed
- D7 N01 C8 fails (a subagent cannot wait on a background job): the N01 replan drops C8 and rewrites N05 so the plz-run adapter runs the command in the foreground with the 600000 ms Bash timeout, and a run past the cap counts as a crash and is dispatched once more (as resume, FORMAT §5 row 28) | confirmed
- D8 This repo's `.plan/config.md` stays unchanged (no `providers` key, so claude only) and every node of this plan runs on a Claude model, dispatched natively | confirmed
- D9 Smoke target: N04 adds the fixture `tests/fixtures/run-smoke/` (config `providers: claude, codex`; one check node N01 VERIFYING try 1 with model `-/gpt-6-luna@low` and a `[review]` criterion on its `hello.txt`); N08 copies it into a temp git repo, vendors the kit there and makes two real calls against it, `plz run verifier gpt-6-luna@low …` and `plz run verifier haiku@low …`, each once, never touching this repo's plans | confirmed
- D10 N07 runs `uv run planzilla install` from the working tree, the sanctioned writer of `.planzilla/`, `.claude/agents/plz-*.md`, `.claude/skills/plz-*/`, `.agents/skills/plz-*/` and the AGENTS.md block; that one command overrides the executor role's rule against editing those files | confirmed
- D11 Each node commit is pushed to origin feat/codex-model-routing (config push per-node); no PR, merge or tag | confirmed
- D12 Tests never run the real `claude` or `codex` CLI or reach the network: they stub `subprocess.run` and `shutil.which`; real model calls happen only in check-node criteria | confirmed
- D13 Dispatch rule (plz-run-plan, and plz-new-plan for the planner): a phase runs natively when the harness's own subagent tool accepts the token as its model and the token has no `@<effort>`; in Claude Code that is a bare opus, sonnet, haiku or fable, dispatched to the plz-* agents as today. Every other token with a provider goes through `plz run`: via a thin adapter subagent where the harness has subagents (Claude Code: `plz-run`, D6), else as parallel background shell jobs the orchestrator waits on in the D6 shape. A `[visual]` verify never goes through `plz run`; it and a token with no provider that the harness cannot run natively stop the run with a message to the user. No lint rule for `[visual]` models (lint cannot know the harness) | confirmed
- D14 `plz run` claude permissions, mirroring the Claude adapter's tool list for the role (src/planzilla/kit/agents/claude/plz-*.md:4): `--tools <T> --allowedTools <T> --permission-mode dontAsk`, T = planner `Read,Grep,Glob,Write,Edit,Bash`, executor `Read,Grep,Glob,Edit,Write,Bash`, verifier `Read,Grep,Glob,Bash`; never `bypassPermissions` or `--dangerously-skip-permissions`; deny rules and hooks in the user's settings still apply | confirmed
- D15 N01 makes one minimal real call per CLI (haiku and gpt-6-luna, effort low, "reply ok") so auth problems surface before any node runs. Found while planning: on this machine `claude auth status` reports `loggedIn: true`, yet a `claude -p --model haiku` call returns 401 "OAuth access token has been revoked", with or without the inherited environment; the user runs `claude auth login` before this plan runs (confirmed by the user), else N01 C4 fails | confirmed
- D16 N01 C4 failed: the stored claude login is still revoked (`claude auth status` says loggedIn true, yet `claude -p --model haiku` returns 401 "OAuth access token has been revoked", also with a clean `env -i` environment), so the D15 login step has not happened; only the user can fix credentials; the user re-runs `claude auth login` in a terminal, then N01 runs again with its brief unchanged; the real claude calls (N01 C4, N08's `plz run verifier haiku@low …`) stay | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | preflight | check | - | -/haiku | 1 | 1 | DONE | |
| N02 | provider table, model tokens, providers key | exec | N01 | sonnet/sonnet | 1 | 0 | DONE | |
| N03 | lint rule providers | exec | N02 | sonnet/sonnet | 0 | 0 | TODO | |
| N04 | plz run command | exec | N02 | sonnet/opus | 0 | 0 | TODO | |
| N05 | plz-run adapter, dispatch rule, planner guidance | exec | N04 | opus/sonnet | 0 | 0 | TODO | |
| N06 | FORMAT and README for providers | exec | N03,N05 | sonnet/sonnet | 0 | 0 | TODO | |
| N07 | re-vendor the kit | exec | N03,N05 | haiku/- | 0 | 0 | TODO | |
| N08 | plan acceptance | check | N06,N07 | -/sonnet | 0 | 0 | TODO | |

## N01 preflight
Do: Confirm the starting point: verify passes on the untouched tree; codex 0.163.0 and claude 2.1.89 are
installed, logged in and have the flags `plz run` uses; one minimal real call per CLI authenticates on the user's
plans and proves both backends are reachable (D15); the work branch can push; `uv run` uses this working tree's
package (N07 vendors from it); and a Claude Code subagent can start a long command in the background and wait
for it across several short Bash calls, the waiting shape plz-run will use (D6, D7).
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `codex --version | grep -q 'codex-cli 0.163' && codex login status && codex exec --help | grep -q -- --output-last-message`
- C3 [cmd] `claude --version | grep -q '^2\.1\.89' && claude auth status | grep -q '"loggedIn": true' && h=$(claude --help) && for f in --effort --permission-mode dontAsk --allowedTools --tools --no-session-persistence --output-format; do printf '%s' "$h" | grep -q -- "$f" || exit 1; done`
- C4 [cmd] `printf 'Reply with the single word ok and nothing else.' | claude -p --model haiku --effort low --output-format text --no-session-persistence --tools "" --permission-mode dontAsk | grep -qiw ok`
- C5 [cmd] `d=$(mktemp -d) && printf 'Reply with the single word ok and nothing else.' | codex exec -m gpt-6-luna -c 'model_reasoning_effort="low"' -s read-only --skip-git-repo-check -C "$d" -o "$d/last" - > /dev/null 2>&1 && grep -qiw ok "$d/last" && rm -rf "$d"`
- C6 [cmd] `test "$(git branch --show-current)" = feat/codex-model-routing && git push --dry-run origin HEAD`
- C7 [cmd] `uv run python -c "import pathlib, planzilla; assert pathlib.Path(planzilla.__file__).resolve().parent == pathlib.Path('src/planzilla').resolve()"`
- C8 [smoke] With your own Bash tool, as separate calls, temp files only under a `mktemp -d` dir outside the
  repo: first `d=$(mktemp -d); nohup sh -c 'sleep 75; echo bg-ok > "$0/out"; echo 0 > "$0/rc"' "$d" > /dev/null 2>&1 & echo "$d"`,
  which must return at once with the dir; then repeat
  `for i in $(seq 6); do test -f <dir>/rc && break; sleep 5; done; cat <dir>/rc <dir>/out 2>/dev/null`
  (each call about 30 s at most) until it prints `0` and `bg-ok`. Expected: the first call returned before the
  job ended, at least two wait calls ran, then `0` and `bg-ok` appear. Remove the dir afterwards.

## N02 provider table, model tokens, providers key
Do: Teach the core providers, test first. New pure `src/planzilla/providers.py`: the provider of a name, the
effort levels per provider, splitting a token into name and effort, and the one token check. plan.py (Graph
model cell), state.py (`set --model`) and config.py (`models`) all use it. `next` and `set` print the token
verbatim, effort included. Config gains `providers` (field `providers: tuple[str, ...]`, default `("claude",)`).
The config template gets a `providers: claude` line and its format-rules comment names the key and its values.
Context: D1: claude = `opus`, `sonnet`, `haiku`, `fable`, `claude-*`; codex = `gpt-*`; others none. Token =
name `[a-z0-9.-]+` plus optional `@<effort>`, only on a provider token, only from its levels (claude low,
medium, high, max; codex low, medium, high, xhigh, max); else a parse error. D4: `providers` is a
comma-separated non-empty subset of claude, codex, no repeats; a `models` token (planner too) whose provider is
not listed is a parse error on the `models` line, whatever order the two lines come in. D3: dispatch agents
stay plz-executor / plz-verifier, only the model text changes. Today: src/planzilla/plan.py:34 and :434-448;
src/planzilla/state.py:29 and :222-226; printing state.py:291-297 (keep). src/planzilla/config.py:9-25 (keys),
:50-71 (parse loop), :89-95 (models). Template src/planzilla/kit/templates/config.md:1-19; the fixture config
tests/fixtures/plans/repo/.plan/config.md holds every key (add `providers: claude, codex`).
Read: `src/planzilla/plan.py`, `src/planzilla/state.py`, `src/planzilla/config.py`, `src/planzilla/kit/templates/config.md`, the tests below
Write: `src/planzilla/providers.py`, `src/planzilla/plan.py`, `src/planzilla/state.py`, `src/planzilla/config.py`,
  `src/planzilla/kit/templates/config.md`, `tests/test_providers.py`, `tests/test_plan.py`, `tests/test_state.py`,
  `tests/test_config.py`, `tests/commands/test_next.py`, `tests/commands/test_set.py`,
  `tests/fixtures/plans/repo/.plan/config.md`
Test first: rows `gpt-6.1-sol@high/opus`, `sonnet@max/gpt-6-luna`, `claude-opus-4-7@low/-`, `gemini-3/-` parse;
`sonnet@xhigh/-`, `gpt-6-astra@huge/-`, `gemini-3@high/-`, `gpt-6-luna@/-` are parse errors;
`set --model gpt-6-astra@xhigh/sonnet@high` rewrites the row; `next` prints `N02 exec gpt-6.1-sol@high` and
`set … RUNNING` prints `· dispatch plz-executor gpt-6.1-sol@high`; `providers: claude, codex` parses,
`providers: openai`, `providers:` and `providers: claude, claude` error, default `("claude",)`;
`models: planner=gpt-6.1-sol` errors unless codex is listed (before or after it); `models: exec=sonnet@max` and
`models: exec=gemini-3` parse. Name these tests with `provider`, `effort` or `gpt`; see them fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_providers.py tests/test_plan.py tests/test_state.py tests/test_config.py tests/commands/test_next.py tests/commands/test_set.py`
- C2 [cmd] `uv run python -c "from planzilla.config import parse_config as p; c = p('models: planner=gpt-6.1-sol@high\nproviders: claude, codex\n', 'c'); assert c.providers == ('claude', 'codex') and c.models['planner'] == 'gpt-6.1-sol@high' and p('', 'c').providers == ('claude',)"`
- C3 [review] providers.py is pure and is the only place that knows names, prefixes and effort levels; plan.py,
  state.py and config.py call it; the config check holds in either line order and names the `models` line;
  the template has `providers: claude` and its comment names `claude, codex`.
- C4 [cmd] `uv run pytest -q`

## N03 lint rule providers
Do: Add the lint rule `providers`, test first. `lint` loads the plan repo's `.plan/config.md` (missing =
defaults; a config parse error is printed as a `parse` problem at that file and line, exit 1) and passes its
providers into the pure `lint_plan`. A Graph row whose exec or verify token has a provider not in config
`providers` gets `providers: <id> model <token> needs config providers to list <provider>` on the row line, one
per token.
Context: D4. Tokens without a provider (`gemini-3`) and `-` never raise it. Tokens and the provider lookup per
D1 exist after N02 (src/planzilla/providers.py, src/planzilla/config.py). Lint today:
src/planzilla/commands/lint.py:134-149 (`lint_plan`), :168-193 (`run`), report format :152-162. Test helpers
tests/commands/test_lint.py:1-45 copy a fixture repo into tmp_path.
Read: `src/planzilla/commands/lint.py`, `src/planzilla/providers.py`, `src/planzilla/config.py`, `tests/commands/test_lint.py`, `tests/fixtures/lint/clean/.plan/2026-10-01-demo.md`
Write: `src/planzilla/commands/lint.py`, `tests/commands/test_lint.py`, `tests/fixtures/lint/providers*/**`
Test first: a fixture plan with rows `gpt-6.1-sol@high/opus`, `sonnet/gpt-6-astra` and `gemini-3/-` lints ok
with `providers: claude, codex`; with no config and with `providers: claude` it prints the two codex lines and
exits 1; with `providers: codex` it prints the `opus` and `sonnet` lines; `gemini-3` never appears; a broken
config line gives a `parse` line naming `.plan/config.md`. See them fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/commands/test_lint.py`
- C2 [review] `lint_plan` stays pure (providers passed in, no IO inside); the message reads exactly as in Do and
  sits on the row line; tokens without a provider and `-` never trigger it; the other lint rules and their
  output are unchanged; the run path reads the config of the plan's repo, not of the cwd.
- C3 [cmd] `uv run pytest -q`

## N04 plz run command
Do: Add the command `plz run <role> <model> <line>`, test first, plus the smoke fixture. Pure core in a new
`src/planzilla/runner.py`: validate role, model and line, build the prompt and the argv for the token's
provider, pick the reply from the output text. All IO in `src/planzilla/commands/run.py`: `shutil.which`, the
login check, then the CLI with the prompt on stdin and stdout/stderr captured (never printed); codex's last
message is read from a temp file that is then removed; print the reply. Append `run` last to `cli.COMMANDS`
(src/planzilla/cli.py:10-23) and to tests/test_cli.py:10.
Context: D5 holds the contract: roles, exit-2 inputs, prompt (three lines, on stdin), codex argv, claude argv,
login checks, reply rule, the four exit-3 `error:` lines. D14 adds to the claude argv, after the D5 flags:
`--tools <T> --allowedTools <T> --permission-mode dontAsk`, T planner `Read,Grep,Glob,Write,Edit,Bash`,
executor `Read,Grep,Glob,Edit,Write,Bash`, verifier `Read,Grep,Glob,Bash`. Effort pairs only with a suffix:
codex `-c` `model_reasoning_effort="<e>"`, claude `--effort <e>`; `-m`/`--model` get the name without the
suffix. Provider and effort come from src/planzilla/providers.py (N02). Argument list only, no shell; the
child gets the parent environment unchanged. D9 fixture `tests/fixtures/run-smoke/`: `.plan/config.md` with
`providers: claude, codex`; `.plan/2026-10-19-smoke.md`, header status RUNNING, one check node `N01 smoke`, model
`-/gpt-6-luna@low`, VERIFYING, try 1, brief: a Do line and `- C1 [review] hello.txt in the repo root holds the
word hello`; `hello.txt` with `hello`. D12: tests stub `subprocess.run` and `shutil.which`.
Read: `src/planzilla/cli.py`, `src/planzilla/commands/check.py`, `src/planzilla/commands/_common.py`, `src/planzilla/providers.py`, `tests/test_cli.py`
Write: `src/planzilla/runner.py`, `src/planzilla/commands/run.py`, `src/planzilla/cli.py`, `tests/test_runner.py`,
  `tests/commands/test_run.py`, `tests/test_cli.py`, `tests/fixtures/run-smoke/**`
Test first: the exact argv for each provider and role, with and without effort; the prompt; reply picking;
each exit-2 input; each exit-3 case per CLI (stderr, then stdout fallback) and the success line with stubbed
subprocess and which; the smoke fixture lints ok. See them fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_runner.py tests/commands/test_run.py tests/test_cli.py`
- C2 [cmd] `for m in gpt-6-luna haiku@low; do uv run python -c "import os, sys; os.environ['PATH'] = '/nonexistent'; from planzilla.cli import main; sys.exit(main(['run', 'verifier', sys.argv[1], 'Plan: x · Node: N01 · Try: 1']))" "$m"; test $? -eq 3 || exit 1; done`
- C3 [cmd] `for a in 'visual haiku' 'verifier gemini-3' 'verifier sonnet@xhigh' 'planner gpt-6-luna@huge'; do uv run planzilla run $a x; test $? -eq 2 || exit 1; done`
- C4 [cmd] `cd tests/fixtures/run-smoke && uv run planzilla lint smoke | grep -q '^lint ok'`
- C5 [review] runner.py does no IO and reads no environment; commands/run.py holds all IO, passes an argv list
  (no shell), prints only the reply or one `error:` line and removes its temp file; the claude argv never holds
  a bypass flag; no test can start a real CLI or reach the network.
- C6 [cmd] `uv run pytest -q`

## N05 plz-run adapter, dispatch rule, planner guidance
Do: Ship the plz-run adapter and teach the kit the dispatch rule. New `src/planzilla/kit/agents/claude/plz-run.md`
(front matter name plz-run, description, `tools: Bash`, `model: haiku`): input `Run: <role> <model> · <line>`;
it starts `.planzilla/plz run` as D6 says and replies with nothing but that reply; it never edits files. Shape:
`d=$(mktemp -d); nohup sh -c '.planzilla/plz run "$1" "$2" "$3" > "$0/out" 2> "$0/err"; echo $? > "$0/rc"' "$d" <role> <model> '<line>' > /dev/null 2>&1 & echo "$d"`
(the line single-quoted, each `'` written `'\''`), then wait calls of at most 5 minutes each, then remove the dir.
plz-run-plan gets a harness-neutral Dispatch rule (D13) used for every set line; plz-new-plan's planner dispatch
(Outline, Revise) follows that same rule. Planner role: the guidance below.
Context: D13 rule: native when the harness's subagent tool accepts `<m>` and it has no `@<effort>` (Claude Code:
bare opus, sonnet, haiku, fable → the named plz-* agent); every other provider token → `plz run`, via `plz-run`
with `Run: <role> <m> · <line>` (role from the named agent: planner, executor, verifier) where the harness has
subagents, else as parallel background shell jobs in the same D6 shape the orchestrator waits on; route the reply
as that role's reply; `[visual]` (plz-visual) never goes to `plz run`; a phase that cannot be dispatched stops
the run with a message. D3: set lines are unchanged. The skills ship in `.agents/skills/` too, so their wording
names no harness except as an example. Guidance (planner role, harness-neutral): tokens and `@<effort>` per
FORMAT §4, only providers listed in config `providers`; with more than one listed: exec gpt-6.1-sol or sonnet for
well-specified coding, opus or fable for judgement, haiku or gpt-6-luna for mechanical; verify on the other
provider than the node's exec, so nobody grades their own work; `[visual]` verify on a model the harness runs
natively; a replan may move a node to the other provider with `plz set --model` when one plan's usage is used up.
Files: src/planzilla/kit/roles/planner.md:15-16 and :25 (keep L8: plans name only the four agents),
src/planzilla/kit/skills/plz-run-plan/SKILL.md:52-63, src/planzilla/kit/skills/plz-new-plan/SKILL.md:35-36.
Limits: planner role at most 30 lines (it has 30: tighten wording, keep its `M/L plans` entry that
tests/kit/test_preflight.py reads); each skill at most 80 lines.
Read: the files above, `src/planzilla/kit/agents/claude/plz-verifier.md`, `tests/kit/test_roles.py`, `tests/kit/test_skills.py`, `tests/kit/test_preflight.py`
Write: `src/planzilla/kit/agents/claude/plz-run.md`, `src/planzilla/kit/skills/plz-run-plan/SKILL.md`,
  `src/planzilla/kit/skills/plz-new-plan/SKILL.md`, `src/planzilla/kit/roles/planner.md`, `tests/kit/test_roles.py`,
  `tests/kit/test_skills.py`
Test first: test_roles expects five adapters, plz-run with `tools: Bash`, `model: haiku` and a
`.planzilla/plz run` call instead of a role file; test_skills allows plz-run and requires plz-run-plan to name
plz-run and `plz run`. See them fail first.
Done when:
- C1 [cmd] `uv run pytest -q tests/kit`
- C2 [cmd] `f=src/planzilla/kit/agents/claude/plz-run.md; grep -qx 'model: haiku' $f && grep -qx 'tools: Bash' $f && grep -q '.planzilla/plz run' $f && grep -q 'plz-run' src/planzilla/kit/skills/plz-run-plan/SKILL.md && grep -q 'plz run' src/planzilla/kit/skills/plz-new-plan/SKILL.md && grep -q 'providers' src/planzilla/kit/roles/planner.md`
- C3 [review] The adapter waits as D6 says (no single Bash call can reach 10 minutes), quotes the line safely and
  replies only the reply or error line; the skills state the D13 rule harness-neutrally, keep native and
  `plz run` phases in one parallel batch and route replies by role; the planner role holds every guidance
  point and its other rules are intact.
- C4 [cmd] `uv run pytest -q`

## N06 FORMAT and README for providers
Do: Describe the feature in docs/FORMAT.md and README.md, matching N02-N05. FORMAT: §4 the token grammar,
`@<effort>` and the provider table with each provider's levels (D2: §4, not §2); §6's verifier-model sentence
gains the cross-provider note; §8 a `providers` row and the `models` limits; §9 a `run` table row, a Details
bullet (roles, argv per provider with the permission flags, prompt, reply, exit codes) and the `providers` lint
rule; §11 `kit/agents/claude/plz-run.md` in the kit list and a sentence that plz-run runs `.planzilla/plz run`
instead of following a role; §14 a plz-run row in the dispatch table and the native-or-`plz run` rule in the
loop. README: a `providers` row in the Config table; a short `## Models and providers` section (listing a
provider, token and effort syntax, cross-provider verify, billing to each plan); a `planzilla run` line in the
CLI reference; plz-run in "Use it in Claude Code"; "Use it in other harnesses" says how such a harness runs
nodes: natively where its subagents can, else `.planzilla/plz run <role> <model> <line>` as background jobs.
Link FORMAT, don't copy it.
Context: D1 grammar and table (src/planzilla/providers.py); D3 set lines unchanged; D4 config and lint message
(src/planzilla/config.py, src/planzilla/commands/lint.py); D5 and D14 command contract (src/planzilla/runner.py,
src/planzilla/commands/run.py); D6 dispatch line and replies; D13 rule (src/planzilla/kit/skills/plz-run-plan/SKILL.md).
FORMAT today: docs/FORMAT.md:118-128 (§4), :265-267 (§6), :327-340 (§8), :362-412 (§9), :443-461 (§11),
:551-595 (§14). README.md:71-109, :128-144, :178-198. tests/kit/test_preflight.py reads FORMAT and README.
Read: `docs/FORMAT.md`, `README.md`, the source files above, `src/planzilla/kit/templates/config.md`
Write: `docs/FORMAT.md`, `README.md`
Test first: -
Done when:
- C1 [cmd] `grep -q '^| .providers. |' docs/FORMAT.md && grep -q '^| .run. |' docs/FORMAT.md && grep -q 'plz-run' docs/FORMAT.md && grep -q '@<effort>' docs/FORMAT.md && grep -q 'sandbox_workspace_write.network_access=true' docs/FORMAT.md && grep -q 'dontAsk' docs/FORMAT.md && grep -q '^| .providers. |' README.md && grep -q 'planzilla run' README.md && grep -q '^## Models and providers' README.md`
- C2 [review] FORMAT states every rule above and matches the code exactly: grammar, provider table and levels,
  config errors, the lint message, the command's argv per provider, prompt, reply rule, stdout and exit codes,
  the dispatch line, rule and replies; §2 is unchanged; README's new text is short, harness-neutral and points
  to FORMAT for the details.
- C3 [cmd] `uv run pytest -q`

## N07 re-vendor the kit
Do: Re-vendor the kit into this repo from the working tree: run `uv run planzilla install` once at the repo
root, then make sure a second run changes nothing. Edit none of the vendored files by hand.
Context: D10 pre-authorizes this one command to rewrite `.planzilla/`, `.claude/agents/plz-*.md`,
`.claude/skills/plz-*/`, `.agents/skills/plz-*/` and the AGENTS.md block, despite the executor role's rule
against editing them. Install copies the running package (an editable install of `src/planzilla/`, proven by
N01 C7) per FORMAT §11 (docs/FORMAT.md:463-482).
Read: -
Write: `.planzilla/**`, `.claude/agents/plz-*.md`, `.claude/skills/plz-*/**`, `.agents/skills/plz-*/**`, `AGENTS.md`
Test first: -
Done when:
- C1 [cmd] `uv run planzilla install | grep -q ': 0 added, 0 changed, 0 removed$'`
- C2 [cmd] `diff -r -x __pycache__ src/planzilla .planzilla/lib/planzilla && cmp src/planzilla/kit/agents/claude/plz-run.md .claude/agents/plz-run.md && cmp src/planzilla/kit/roles/planner.md .planzilla/roles/planner.md && for s in plz-run-plan plz-new-plan; do cmp src/planzilla/kit/skills/$s/SKILL.md .claude/skills/$s/SKILL.md && cmp src/planzilla/kit/skills/$s/SKILL.md .agents/skills/$s/SKILL.md || exit 1; done && cmp src/planzilla/kit/templates/config.md .planzilla/templates/config.md`
- C3 [cmd] `.planzilla/plz --help | grep -qw run`
- C4 [cmd] `uv run pytest -q`

## N08 plan acceptance
Do: Check the whole plan against its definition of done: the full verify; lint with and without codex listed;
`next` and `set` showing a `gpt-` token; the kit and its vendored copy; and the two real `plz run` calls (D9).
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `r=$PWD; d=$(mktemp -d) && cp -R tests/fixtures/run-smoke/. "$d" && cd "$d" && "$r/.planzilla/plz" lint smoke | grep -q '^lint ok' && printf 'providers: claude\n' > .plan/config.md && "$r/.planzilla/plz" lint smoke | grep -q 'providers: N01 model gpt-6-luna@low needs config providers to list codex'`
- C3 [cmd] `r=$PWD; d=$(mktemp -d) && cp -R tests/fixtures/run-smoke/. "$d" && cd "$d" && "$r/.planzilla/plz" next smoke | grep -qx 'N01 verify gpt-6-luna@low' && "$r/.planzilla/plz" set smoke N01 VERIFYING | grep -q '· dispatch plz-verifier gpt-6-luna@low$'`
- C4 [cmd] `test -f .claude/agents/plz-run.md && grep -q plz-run .claude/skills/plz-run-plan/SKILL.md && grep -q plz-run .agents/skills/plz-run-plan/SKILL.md && grep -q 'plz run' .agents/skills/plz-new-plan/SKILL.md && grep -q providers .planzilla/roles/planner.md && grep -q plz-run docs/FORMAT.md && grep -q plz-run README.md`
- C5 [smoke] From the repo root, with a Bash timeout of 600000 ms, set up once:
  `r=$PWD; d=$(mktemp -d) && cp -R tests/fixtures/run-smoke/. "$d" && cd "$d" && git init -q && git add -A && git -c user.name=smoke -c user.email=smoke@example.invalid commit -qm smoke && uv run --project "$r" planzilla install --target . > /dev/null`,
  then in that dir run `.planzilla/plz run verifier gpt-6-luna@low "Plan: smoke · Node: N01 · Try: 1"` once.
  Expected: exit 0 and exactly one stdout line, `PASS N01` (or `FAIL N01: C1`, which still proves the
  plumbing); anything else fails.
- C6 [smoke] In the same temp dir run `.planzilla/plz run verifier haiku@low "Plan: smoke · Node: N01 · Try: 1"`
  once, Bash timeout 600000 ms. Expected as in C5. Remove the temp dir afterwards.
- C7 [review] Over the whole repo: tests cover a `gpt-` row with effort linting ok with codex listed and failing
  without, an effort the provider lacks failing to parse, `next`/`set` printing the token, and `plz run`
  building both providers' argv, printing the reply and exiting 3 on each external failure with the CLIs
  stubbed; FORMAT §4, §6, §8, §9, §11, §14 and README describe all of it, harness-neutrally.

## Log

### N01 try 1 · 2026-10-19
check: FAIL C4
- C4 exit 1:

### N01 replan 1 · 2026-10-19
plan: ASK D16
- C4 failed: claude -p returns 401 OAuth access token has been revoked although auth status says loggedIn, also with a clean env
- credentials need the user (D15 login step not done); brief unchanged, D16 proposed: user runs claude auth login then N01 reruns, alt drop real claude calls
plan: BRIEFED
- D16 confirmed: user re-runs claude auth login in a terminal; real claude calls in N01 C4 and N08 stay
- brief unchanged; N01 reruns as written

### N01 try 1 · 2026-10-19
check: FAIL C4
- C4 exit 1:
check: PASS 7/7
verify: PASS

### N02 try 1 · 2026-10-19
exec: DONE · 666 passed
- New pure providers.py (provider_of, efforts_of, split_token, check_token); plan.py Graph cell, state.py set --model and config.py models use it
- Config.providers (default claude, subset check, no repeats); models providers must be listed, checked after the parse loop and reported on the models line in either order
- Template and fixture config gain providers lines
check: PASS 3/3
verify: PASS
