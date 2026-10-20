# Planzilla

Plan, run and verify work with AI agents from Markdown plan files.

## What it is

Planzilla is graph-engineered AI coding. You describe a request; Planzilla turns it into a task graph in
`.plan/`, plain Markdown files kept in your repo. Then it works through the graph:

- every node gets a fresh executor agent and, where a node needs judgement, a fresh verifier agent, so no
  context piles up and nobody grades their own work;
- every finished node becomes one git commit, carrying the node's work and the plan state together;
- a failed node is retried with the verifier's findings, then replanned, within budgets (default 2 tries and 2
  replans per node); when the budgets are used up the node is BLOCKED and a human decides;
- a stop (usage limit, crash, closed session) is not a failure: `planzilla resume` picks up where it left off.

The program is a small Python CLI (standard library only, Python 3.10 or newer) that keeps the plan state. The
agents are driven by skills and role files that `planzilla install` copies into your repo. Planzilla is licensed
under Apache-2.0.

The full spec is [docs/FORMAT.md](docs/FORMAT.md); this README links to it instead of repeating it.

## Install

Pick one. All three give you the `planzilla` command (also available as `plz`).

```sh
# Homebrew (tap IVIR3zaM/homebrew-tap, formula planzilla with python@3.13)
brew install IVIR3zaM/tap/planzilla

# uvx, no install step
uvx --from git+https://github.com/IVIR3zaM/Planzilla planzilla --version

# pipx, from git
pipx install git+https://github.com/IVIR3zaM/Planzilla
```

Check it with `planzilla --version`, which prints `planzilla <version>`.

## Vendor it into a repo

Vendoring copies everything a repo needs into the repo itself, so teammates and agents need no global install
and no home-directory configuration. From the root of your repo:

```sh
planzilla install                  # install the version you are running
planzilla install --version v0.2.0 # or install a released tag from GitHub
planzilla install --target ../other-repo
```

It prints `installed planzilla <version> into <target>: <a> added, <c> changed, <r> removed`. The layout
(FORMAT §11):

```
.planzilla/VERSION             the installed version
.planzilla/plz                 launcher; runs the vendored copy with python3
.planzilla/lib/planzilla/      the whole package
.planzilla/roles/*.md          planner, executor, verifier, visual role prompts
.planzilla/templates/*         plan, intent, node and config templates
.claude/agents/plz-*.md        Claude Code subagents
.claude/skills/plz-*/          Claude Code skills (plz-new-plan, plz-run-plan)
.agents/skills/plz-*/          the same skills, for other harnesses (Agent Skills)
AGENTS.md                      a short block between <!-- planzilla:begin --> and <!-- planzilla:end -->
```

Commit all of it. Inside the repo the agents and skills call `.planzilla/plz`, so nothing else has to be
installed. To move a repo to a newer version, see [Upgrading a repo](#upgrading-a-repo).

## Use it in Claude Code

After vendoring, open Claude Code in the repo:

1. `/plz-new-plan <what you want>` clarifies the request, picks the tier, agrees the repo config with you,
   asks every open decision in as few rounds as possible, then has the `plz-planner` agent write the plan
   under `.plan/`.
2. `/plz-run-plan [slug]` runs it. The skill is the orchestrator: it drives the plan through one-line CLI
   outputs and dispatches the `plz-planner`, `plz-executor`, `plz-verifier` and `plz-visual` agents, in
   parallel where the graph allows, committing each finished node. With no slug it suggests the next open
   plan. Run it again to continue after a stop.

The agents live in `.claude/agents/` and the skills in `.claude/skills/` of the repo, so no `~/.claude`
configuration is needed.

Each dispatch has two routes (FORMAT §14 "Native or `plz run`"). A node whose model is `opus`, `sonnet`,
`haiku` or `fable`, with no `@<effort>`, runs natively: `/plz-run-plan` dispatches the named agent with that
model. Every other model (a `codex` or `gpt-` name, a bare `claude`, or anything with an `@<effort>`) goes through
the `plz-run` agent, which runs `planzilla run <role> <model> <line>` in the background and relays its one-line
reply. One batch may mix both routes, all in parallel. `[visual]` criteria are checked by `plz-visual`, which
never goes through `plz run`.

## Use it in other harnesses

Planzilla's roles are plain Markdown, not tied to one tool. The vendored repo carries four things any harness can
use:

- `AGENTS.md` holds the Planzilla block, kept between the `planzilla:begin` and `planzilla:end` markers, so every
  harness that reads `AGENTS.md` sees it.
- `.agents/skills/plz-new-plan/` and `.agents/skills/plz-run-plan/` are the same two skills in the Agent Skills
  `SKILL.md` format.
- `.planzilla/roles/planner.md`, `executor.md`, `verifier.md` and `visual.md` are the role prompts.
- `.planzilla/plz` is the CLI.

| harness | what it picks up |
|---------|------------------|
| Codex CLI | reads `AGENTS.md`; discovers the skills in `.agents/skills/` |
| opencode | reads `AGENTS.md`; loads Agent Skills, including `.agents/skills/` |
| Cursor | reads `AGENTS.md`; loads Agent Skills, including `.agents/skills/` |
| Gemini CLI | uses `AGENTS.md` once it is set as a context file; loads Agent Skills from `.agents/skills/` |

Skill discovery paths differ between harness versions. If yours does not look in `.agents/skills/`, point it
there with a symlink or copy; the skill files are the same bytes everywhere. Ask the agent to run the
`plz-new-plan` skill, then the `plz-run-plan` skill. Where the harness has no subagents, start one fresh
session per role and tell it to follow the role file, for example "follow `.planzilla/roles/executor.md` for
plan `<slug>`, node `N03`". The same files and CLI work from there on.

### Codex

Codex runs nothing natively (FORMAT §14): every step of a plan, planner, executor and verifier alike, is a
`.planzilla/plz run <role> <model> '<line>'` job, started as a background shell job, one per line. The
orchestrator waits in calls of at most 5 minutes and reads the last line of the job's output as the agent's
reply. `plz run` starts `codex exec` or `claude -p`, which need network and a login that live outside the repo,
so when Codex asks, approve `.planzilla/plz run` outside its sandbox. Never use
`--dangerously-bypass-approvals-and-sandbox`. Because Codex has no visual agent, a plan written for it uses
`[smoke]` or `[human]` criteria where a Claude Code plan would use `[visual]`.

Other harnesses with subagents use them where they can run the node's model; otherwise they use `plz run` jobs
as above.

## Using both providers

Planzilla can run a plan on Claude, on Codex or on both. To enable the other provider (FORMAT §14):

1. Install its CLI: `claude` (Claude Code) or `codex` (Codex CLI).
2. Log in: `claude auth login` or `codex login`. Check with `claude auth status` or `codex login status`.
3. List it in `.plan/config.md`: `providers: claude, codex` (see [Config](#config)).

So from Claude Code you enable Codex by installing and logging in to `codex`; from Codex you enable Claude the
same way with `claude`. Billing goes to the account each CLI is logged in to. In Codex, remember to approve
`.planzilla/plz run` outside the sandbox (above).

## Tiers

`plz-new-plan` picks a tier for each plan (FORMAT §1); tiers only ever escalate.

| tier | when | layout |
|------|------|--------|
| S | one executor context, no open decisions, 1 to 2 exec nodes | one file in `.plan/` |
| M | about 2 to 10 nodes, clear scope | one file, all briefs written in one planner call |
| L | more than 10 nodes, multi-session or multi-environment work, or evidence artifacts | a directory; each node is briefed just in time |

An S plan has no preflight and no final check: just its 1 to 2 exec nodes, each ending on the full `verify`. M and
L plans start with an N01 preflight check node (tools, auth, network, permissions) and end with a whole-plan check
node whose first criterion runs the full `verify`; their exec nodes end on `verify_fast`.

An S plan whose node is BLOCKED becomes M on replan; an M plan that outgrows the single file moves to an L
directory on replan.

## Config

`.plan/config.md` holds repo defaults, as `key: value` lines (FORMAT §8). `plz-new-plan` detects them on its
first run and proposes them to you (see [What plz-new-plan detects and asks](#what-plz-new-plan-detects-and-asks)).
A plan's own header wins over the config.

| key | meaning | default |
|-----|---------|---------|
| `verify` | full check command for the repo; the final check node of an M or L plan runs it | empty |
| `verify_fast` | command executors run before replying (the last criterion of an M or L exec node) | `verify` |
| `commit` | `per-node` or `none` | `per-node` |
| `push` | `per-node` or `none` | `none` |
| `retention` | `keep`, `prune-logs`, `delete` or `branch-only`: what happens to plan records in the finishing commit | `keep` |
| `visual_recipe` | one line: how to start the app and which URL to open | empty |
| `models` | `planner=<m>, exec=<m>, verify=<m>` (any subset); each `<m>` is `<name>` or `<name>@<effort>` | `planner=opus, exec=sonnet, verify=sonnet` |
| `providers` | `claude`, `codex` or both: the providers whose models the plans may use | `claude` |
| `harness` | `claude-code` or `codex`: the agent harness that runs the plans | `claude-code` |
| `preauthorized` | `;`-separated actions agents may take without asking | empty |
| `always_review` | `yes` or `no`: every exec node gets at least one `[review]` criterion | `no` |
| `commit_trailer` | text added to commit messages; `\n` separates lines | empty |

## Models and providers

A node's model is a token, `<name>` or `<name>@<effort>` (grammar, error messages and effort levels in FORMAT
§4). The name decides the provider:

| provider | names | `@<effort>` levels |
|----------|-------|--------------------|
| `claude` | `claude`, `opus`, `sonnet`, `haiku`, `fable`, or any name starting `claude-` | `low` · `medium` · `high` · `max` |
| `codex` | `codex`, or any name starting `gpt-` | `low` · `medium` · `high` · `xhigh` · `max` |

- Aliases such as `opus` and `sonnet` are versionless names that follow the newest model of that family.
- A bare `claude` or `codex` means that CLI's own default model; `codex@high` keeps that default and sets only the
  effort. Explicit names such as `gpt-5.5` pin one model and are used only when you name one.
- Without `@<effort>` the provider CLI's own default effort applies.
- Set models in `models`, for example `models: planner=opus, exec=codex@medium, verify=sonnet`, or per node in
  the plan's Graph (`<exec>/<verify>`, for example `codex@medium/sonnet`).
- List the providers you use in `providers`. Every model in `models` and in a plan's Graph must belong to a listed
  provider; `planzilla lint` reports the ones that do not. When `providers: codex` is the only provider,
  `plz-new-plan` also writes `models: planner=codex@high, exec=codex@medium, verify=codex@medium`.
- `planzilla run <role> <model> <line>` runs one agent step through the provider's CLI (`claude` or `codex`,
  installed and logged in) and prints its one-line reply (FORMAT §9). Each call bills to the account that CLI is
  logged in to.

### How the planner picks models

The planner writes models only of the providers you list, on one scale (FORMAT §4):

| work | Claude | Codex |
|------|--------|-------|
| mechanical | `haiku` | `codex@low` |
| well-specified coding | `sonnet` | `codex@medium` |
| judgement | `opus` or `fable` | `codex@high` |

- The verify model follows the hardest non-`cmd` criterion of the node (FORMAT §6), on the same scale.
- Claude models are chosen by their versionless alias, with no `@<effort>` where the harness should run them
  natively (see [Claude Code](#use-it-in-claude-code)). Codex is chosen by effort on bare `codex`.
- With both providers listed, a node is verified on the other provider than the one that executed it, so the
  model that wrote the code never grades it. The cold verifier sees only the brief's criteria.
- When one provider's usage runs out, a replan may move a node to the other provider
  (`planzilla set <plan> <id> --model M`).

## Verification tags

Every node ends in a list of criteria, each tagged by who checks it (FORMAT §6):

| tag | checked by |
|-----|------------|
| `[cmd]` | `planzilla check` runs the backticked command; exit 0 passes. No model involved |
| `[review]` | a verifier reads the code, tests and files |
| `[smoke]` | a verifier starts the app or calls an API and reports what it saw |
| `[visual]` | `plz-visual`: the verifier role plus browser tools (Claude Code only, see below) |
| `[human]` | you, in one batched round; used only when no other tag can check it |

Visual verification depends on the `harness` key (FORMAT §8, §14). With `harness: claude-code` a `[visual]`
criterion is checked by the `plz-visual` agent. With `harness: codex` there is no visual agent, so the planner
writes `[smoke]` or `[human]` criteria instead. `planzilla lint` (rule `visual`) reports a `[visual]` criterion
when the harness has no visual agent, and a `[visual]` node whose verify model the harness does not run natively. Set
`visual_recipe` so the verifier knows how to start the app and which URL to open.

## What plz-new-plan detects and asks

On a repo's first run, `plz-new-plan` detects (FORMAT §8):

- the verify commands and other defaults, from `pyproject.toml`, `package.json`, `Makefile`, `AGENTS.md` and
  `CLAUDE.md`;
- each provider's CLI (`command -v claude`, `command -v codex`) and whether it is logged in (`claude auth status`,
  `codex login status`);
- the harness it runs in: `claude-code` when `CLAUDECODE=1`, otherwise the name the agent gives (for example
  `codex`).

It then asks, in its one question round, `providers` (recommending each logged-in provider; for a logged-out one it
shows the login command, `claude auth login` or `codex login`) and `harness` (recommending the detected one),
together with the usual gaps and the tier. With an existing config, it asks again only when the request names a
provider that `providers` lacks, or when `harness` is absent and the detected harness is not `claude-code`; it
rewrites or adds only that one line.

## Resume

State lives in the plan files and is written before each dispatch, so a stop costs nothing (FORMAT §13). Run
`/plz-run-plan` again, or `planzilla resume <plan>` by hand.

- Same machine: uncommitted edits of in-flight nodes are still in the working tree and the node reruns from them.
- Another machine: check out the branch at its last pushed node commit (set `push: per-node` to have each node
  pushed). Work of nodes not yet committed is absent, so their rows rerun.

## Live view

```sh
planzilla status <plan>   # text: one line per node, grouped by wave
planzilla stats <plan>    # one line of totals
planzilla serve <plan>    # live page at http://127.0.0.1:8765/
```

`serve` binds to 127.0.0.1 only, polls the plan files and `git log` every 2 seconds, and never writes. Use
`--port N` to change the port. `<plan>` is a path or a slug fragment.

## CLI reference

`planzilla` and `plz` are the same program. `<plan>` is a path or a slug fragment of a plan in `.plan/`,
`<id>` a node id such as `N03`. Exit codes: 0 success, 1 negative result (`check` FAIL, `lint` problems), 2 usage
or plan error, 3 external failure (git, network, lock). Details in FORMAT §9.

- `planzilla install [--target DIR] [--version vX] [--archive-url URL]` vendors the kit into a repo.
- `planzilla next <plan>` prints one line per ready action: `<id> <action> <model>`.
- `planzilla set <plan> <id> [STATUS] [--note TEXT] [--add] [--title T] [--type exec|check|gate] [--deps D] [--model M]`
  changes a node's status or structure.
- `planzilla resume <plan>` lists in-flight nodes to rerun and held nodes, and fixes their state after a stop.
- `planzilla brief <plan> <id> [--verify | --ask]` prints the executor brief, the cold verifier view or the
  one-line question for the human.
- `planzilla log <plan> <id> <kind> <text> [-b BULLET]...` appends a log entry (kinds: exec, verify, plan, human,
  note).
- `planzilla check <plan> <id>` runs a node's `[cmd]` criteria and prints `PASS` or `FAIL`.
- `planzilla commit <plan> <id>` makes the one commit for a DONE node.
- `planzilla status <plan>` prints the per-node status text.
- `planzilla stats <plan>` prints the totals line.
- `planzilla lint <plan>` checks a plan against the planner rules and prints `lint ok: ...` when clean.
- `planzilla run <role> <model> <line>` runs one planner, executor or verifier step on the model's provider CLI
  and prints its one-line reply.
- `planzilla serve <plan> [--port N]` serves the live view.

## Upgrading a repo

To move a vendored repo to a newer Planzilla (FORMAT §11):

1. Run `planzilla install` from the repo root (the version you are running), or
   `planzilla install --version v0.2.0` for a released tag.
2. Check `.planzilla/VERSION` shows the version you expect.
3. Commit the result.
4. Start a fresh agent session: skills and agents load at session start, so a running session keeps the old ones.

Install rewrites only files whose bytes differ and removes files under `.planzilla/`, `.claude/agents/plz-*.md`,
`.claude/skills/plz-*/` and `.agents/skills/plz-*/` that the new kit no longer ships. In `AGENTS.md` it replaces
only the lines between the `planzilla:begin` and `planzilla:end` markers. It never writes `.plan/` and never
touches any other path under `.claude/` or `.agents/`. A second run changes nothing.

To get a newer `planzilla` command itself, upgrade the install first: `brew upgrade planzilla` for Homebrew, or
rerun the `uvx` or `pipx` install.

## Releasing

`__version__` in `src/planzilla/__init__.py` is the one version (FORMAT §11). To release:

1. Bump `__version__`.
2. Re-vendor this repo with `planzilla install` so its own `.planzilla/` matches, and commit.
3. Merge to `main`.
4. Push the tag `v<version>`, for example `v0.2.0`. The tag must equal `v` plus `__version__`, or the build fails.
5. The Release workflow (`.github/workflows/release.yml`) builds the sdist and wheel, runs the Homebrew tests
   (`brew test` and `brew audit`) against the built formula, then publishes the GitHub release and pushes the
   formula to the `IVIR3zaM/homebrew-tap` tap. It needs the `HOMEBREW_TAP_TOKEN` secret.
6. Users then run `brew upgrade planzilla`.

## Contributing

Work in this repo follows [AGENTS.md](AGENTS.md). In short:

- Strict TDD: write the failing test and see it fail, write the minimal code to pass, refactor, rerun.
- Python 3.10 or newer, standard library only at runtime; pytest and ruff are dev-only.
- Pure core (parsing, state, waves); all IO lives in `src/planzilla/commands/`, one module per command.
- `docs/FORMAT.md` is the contract for file layouts, CLI output lines and exit codes.

Before sending a change, run the full check:

```sh
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
```
