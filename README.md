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
# Homebrew (tap IVIR3zaM/homebrew-tap, formula planzilla)
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
planzilla install --version v0.1.0 # or install a released tag from GitHub
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
installed. To upgrade, run `planzilla install` again (or with `--version vX`): it rewrites only files whose bytes
differ and removes files the new kit no longer ships. It never writes `.plan/` and never touches other files
under `.claude/` or `.agents/`; in `AGENTS.md` it replaces only the lines between the markers.

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
first run and proposes them to you. A plan's own header wins over the config.

| key | meaning | default |
|-----|---------|---------|
| `verify` | full check command for the repo; the final check node of an M or L plan runs it | empty |
| `verify_fast` | command executors run before replying (the last criterion of an M or L exec node) | `verify` |
| `commit` | `per-node` or `none` | `per-node` |
| `push` | `per-node` or `none` | `none` |
| `retention` | `keep`, `prune-logs`, `delete` or `branch-only`: what happens to plan records in the finishing commit | `keep` |
| `visual_recipe` | one line: how to start the app and which URL to open | empty |
| `models` | `planner=<m>, exec=<m>, verify=<m>` (any subset) | `planner=opus, exec=sonnet, verify=sonnet` |
| `preauthorized` | `;`-separated actions agents may take without asking | empty |
| `always_review` | `yes` or `no`: every exec node gets at least one `[review]` criterion | `no` |
| `commit_trailer` | text added to commit messages; `\n` separates lines | empty |

## Verification tags

Every node ends in a list of criteria, each tagged by who checks it (FORMAT §6):

| tag | checked by |
|-----|------------|
| `[cmd]` | `planzilla check` runs the backticked command; exit 0 passes. No model involved |
| `[review]` | a verifier reads the code, tests and files |
| `[smoke]` | a verifier starts the app or calls an API and reports what it saw |
| `[visual]` | `plz-visual`: the verifier role plus browser tools |
| `[human]` | you, in one batched round; used only when no other tag can check it |

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
- `planzilla serve <plan> [--port N]` serves the live view.

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
