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
planzilla install --version v0.3.0 # or install a released tag from GitHub
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
.github/agents/plz-*.agent.md  Copilot CLI planner, executor and verifier profiles
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

The skills dispatch every role by one rule, keyed on the harness you actually run in (see
[Dispatch](#dispatch-and-runner-boundaries)): native agents in Claude Code for its own model names, the
`plz-run` adapter or a `plz run` shell job for everything else. Every phase is a separate role invocation; only
the planner authors DRAFT, Graph tokens and briefs. `[visual]` never goes through text-only `plz run`.

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
| Copilot CLI | discovers `.github/agents/plz-*.agent.md` profiles; shared skills live in `.agents/skills/` |
| opencode | reads `AGENTS.md`; loads Agent Skills, including `.agents/skills/` |
| Cursor | reads `AGENTS.md`; loads Agent Skills, including `.agents/skills/` |
| Gemini CLI | uses `AGENTS.md` once it is set as a context file; loads Agent Skills from `.agents/skills/` |

Skill discovery paths differ between harness versions. If yours does not look in `.agents/skills/`, point it
there with a symlink or copy; the skill files are the same bytes everywhere. Ask the agent to run the
`plz-new-plan` skill, then the `plz-run-plan` skill. Where the harness has no subagents, start one fresh
session per role and tell it to follow the role file, for example "follow `.planzilla/roles/executor.md` for
plan `<slug>`, node `N03`". The same files and CLI work from there on.

### Codex

Codex can dispatch natively when the exposed tool accepts the exact `model` and `reasoning_effort` values,
plus separate role/input controls and `fork_turns: "none"` for fresh overrides. Prompt text or inherited
defaults cannot enforce those pins. Surface any mismatch between actual Codex and configured Claude; use
the actual tool contract. If controls are missing, use only a proven pin-preserving CLI route or hand off.
Honor host permissions and sandbox rules; never add approval/sandbox bypass flags.

### Copilot CLI

Copilot is fully supported two ways. Details on flags, models, auth and the evidence behind them are in
[docs/COPILOT.md](docs/COPILOT.md).

**Copilot as a harness.** You work inside Copilot CLI and it coordinates a plan through the skills, `AGENTS.md`
and the `.github/agents` profiles. The installed `plz-planner.agent.md`, `plz-executor.agent.md` and
`plz-verifier.agent.md` are thin profiles bound to the shared `.planzilla/roles/` prompts. They read `AGENTS.md`
and set `include-custom-instructions: true`, preserving repository instruction inheritance. They ship no model
pin and no visual profile. Shared roles own boundaries, logging and the one-line reply protocol.

Before native dispatch, verify callable delegation and the effective model/effort controls. Check profile
selection and shadowing, `modelPolicy: required` where supported, session overrides and `reasoningEffort`.
Check session startup and per-call delegation precedence separately: a session flag does not necessarily
override a profile, and another client's field names are not evidence. Installed profiles prove no browser
availability.

**Copilot as a delivery route.** Any orchestrator, whatever its own harness, can hand a role to Copilot CLI
headlessly with `plz run <role> copilot::<model> '<line>'`, or through `plz dispatch` (see
[Dispatch](#dispatch-and-runner-boundaries)). You install the Copilot CLI and log in yourself; Planzilla never installs,
updates or logs in to it. The entrypoint is `copilot` when it is on `PATH`, otherwise `gh copilot --`, used only
when `gh` is on `PATH` and already holds its downloaded Copilot CLI (so Planzilla never triggers a download). With
neither, `plz run` exits 3.

- Auth check: Copilot has no status command, so the prompt call itself is the check. A logged-out CLI reports
  `error: copilot is not logged in; run copilot login` (`gh copilot -- login` on the `gh` route); run that
  yourself.
- A bare model, `copilot::<model>`, runs with that exact model. `@<effort>` maps to `--reasoning-effort`, and the
  effort needs an exact model id that supports it. A bare `copilot` selects Copilot's default model, which
  accepts no effort, so `copilot@high` exits 3 before any subprocess.
- `copilot::opus`, `copilot::sonnet` and `copilot::haiku` are portable intent, not model ids: they go through
  `plz dispatch`, which resolves them to an exact Copilot model; `plz run` exits 3 for them.
- Copilot has no visual agent: a Copilot delivery never carries browser evidence, so `[visual]` work needs a
  different, proven surface.

## Using multiple providers

Planzilla supports allowed Claude, Codex and Copilot delivery (FORMAT §14). Install the appropriate CLI and
explicitly log in if needed (`claude auth login`, `codex login`, or `copilot login` / `gh copilot -- login`).
Check noninteractive status only for permitted routes (`claude auth status` or `codex login status`); Copilot has
no status command, so its prompt call is the auth check (see [docs/COPILOT.md](docs/COPILOT.md)). Billing follows
the account used by each delivery. CLI presence and login alone prove no model support, usable reply or quota.

Repository `providers` supplies defaults; a plan may replace that list and restrict `harnesses`. Establish
usable delivery and exact selection controls before dispatch. Never probe excluded providers or silently
rewrite repository config to repair a mismatch. Different provider names do not establish independent quotas.

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
| `models` | `planner=<m>, exec=<m>, verify=<m>` (any nonempty subset, no repeated roles); model grammar below | `planner=opus, exec=sonnet, verify=sonnet` |
| `providers` | nonempty subset of `claude`, `codex`, `copilot`, no repeats: allowed delivery routes | `claude` |
| `harness` | `claude-code`, `codex` or `copilot`: configured client, not callable-tool evidence | `claude-code` |
| `preauthorized` | `;`-separated actions agents may take without asking | empty |
| `always_review` | `yes` or `no`: every exec node gets at least one `[review]` criterion | `no` |
| `commit_trailer` | text added to commit messages; `\n` separates lines | empty |

Plan headers may set `harnesses`, `providers` and partial `models` overrides (FORMAT §3). `harnesses` is a
plan header, not a config key: check the actual coordinator against it before defaults, selection or probes.
Map its delivery permissions (`claude-code` → `claude`, `codex` → `codex`, `copilot` → `copilot`) and intersect
with effective providers; neither allowlist widens the other. Multiple harnesses permit only listed
combinations. Absent harness restrictions preserve legacy permissions; absent providers inherit config.
Plan providers replace the repository list. Model precedence is explicit Graph token, plan role override,
repository role default, then built-in default, with each omitted role inheriting individually. Incompatible
inherited pins cause an error rather than expanding permissions.

Persist a confirmed plan policy change through the CLI, leaving repository config unchanged:

```sh
.planzilla/plz policy <plan> --harnesses codex --providers codex \
  --models 'planner=gpt-6.1-sol@high, exec=gpt-6.1-sol@high, verify=gpt-6.1-sol@high'
```

Supplied fields replace their plan field; omitted fields stay unchanged. `--models` replaces the override
field as a whole, so omitted roles inherit. Existing Graph pins must already be compatible; validation is
atomic and performs no provider probes. Policy applies before every planner, executor, separate reviewer
and resume phase, including initial planning before a header exists.

## Models and providers

A node's model token is `[<route>::]<name>[@<effort>]` (FORMAT §4). Preserve independent exact ID, effort and route pins.
The optional route is `claude`, `codex` or `copilot`; model-name prefixes classify syntax and effort levels,
never delivery, authentication or quota identity:

| name class | compatible routes | `@<effort>` levels |
|----------|-------|--------------------|
| `opus`, `sonnet`, `haiku` | portable across all three | `low` · `medium` · `high` · `max` |
| `fable`, `claude-*` | `claude`, `copilot` | `low` · `medium` · `high` · `max` |
| `gpt-*` | `codex`, `copilot` | `low` · `medium` · `high` · `xhigh` · `max` |
| bare `claude` | `claude` | `low` · `medium` · `high` · `max` |
| bare `codex` | its named route | `low` · `medium` · `high` · `xhigh` · `max` |
| bare `copilot` | its named route | `none` · `minimal` · `low` · `medium` · `high` · `xhigh` · `max` |

`opus`, `sonnet` and `haiku` express portable intent, valid even with Codex-only providers. A versioned ID
pins a model, `@high` pins effort, and `copilot::` pins delivery independently. For example,
`copilot::claude-sonnet-5@high` retains all three constraints; `codex::opus` maps intent on the Codex route.
An unqualified exact ID can use any compatible permitted delivery that demonstrably supports it.

A bare `claude`, `codex` or `copilot` selects that route's default model, not an exact ID; `codex@high` pins
only effort. Capability resolution must verify that default. Without `@effort` there is no explicit effort
pin; portable mappings below may still select an effort. Models can be set per role or in the Graph's
`<exec>/<verify>` cell, such as `claude::opus/copilot::opus`; every choice remains subject to effective policy.

### How the planner picks models

The planner chooses within effective permissions using demonstrated capabilities (FORMAT §14):

| work / intent | native Claude or Copilot | active Codex native mapping |
|------|--------|-------|
| mechanical / `haiku` | supported Haiku | supported Sol at low, only when task policy permits |
| coding / `sonnet` | supported Sonnet | `gpt-6.1-sol@medium` |
| judgement / `opus` | supported Opus | `gpt-6.1-sol@high` |

- The verify model follows the hardest non-`cmd` criterion of the node (FORMAT §6), on the same scale.
- Explicit pins override portable mapping and survive fallback. Missing native controls require proven
  pin-preserving CLI delivery or a handoff, never a silent default substitution.
- Every reviewer is a separate cold role invocation. One permitted route may supply both cold contexts;
  that provides separate judgement, not separate quotas. Deliberate delivery/quota independence requires
  distinct delivery identities and distinct known quota identities with evidence. Family or route names
  alone prove neither. Resolve prospective pairs together; resolve review against completed execution
  history to preserve that requirement.
- Fall back only after concrete delivery failure, excluding only the failed delivery and retaining pins and
  independence. Distinguish quota exhaustion, authentication, permission, unsupported selection and unknown
  failures. Generic exits, silence, signals or HTTP 429 without quota semantics do not prove exhaustion.
  Give auth recovery guidance without interactive login; never scan provider-wide quotas or rewrite config.
  If no supported tuple remains, hand off with evidence and minimal alternatives.

### Dispatch and runner boundaries

Both skills share one `## Dispatch contract`. It first checks the actual coordinator against the plan's
`harnesses` and intersects delivery with effective `providers`, never probing excluded providers. Then each
`plz set` line's agent `<agent>` and model `<m>` go by the harness you actually run in, whatever config `harness`
says (`<role>` is planner, executor or verifier):

- Claude Code, `<m>` is `opus`, `sonnet`, `haiku` or `fable` without `@<effort>`: dispatch the agent natively.
- Claude Code, any other `<m>` (`copilot::<id>` too): dispatch the `plz-run` adapter with
  `Run: <role> <m> · <line>`; it runs `plz run` and relays the one-line reply.
- Codex or Copilot: run `plz run <role> <m> '<line>'` as a shell job, with an owned job handle and its own
  `out`/`err`/`rc` files; the reply is the last non-blank line of `out` (rc 0), else of `err`.
- `plz-visual` never goes through `plz run`: it is dispatched natively in Claude Code with a native `<m>`, and
  anywhere else the run stops with `<id>: cannot dispatch plz-visual <m>`.

One batch may mix all three. An `error: …` reply is a crash. Pins are never silently relaxed; a line no allowed
route can dispatch stops the run with `<id>: cannot dispatch <agent> <m>` and one focused handoff.

**Advanced, optional: `plz dispatch`.** `plz run` refuses qualified portable tokens such as `copilot::opus`,
because a portable name is not a Copilot model id. To resolve them against plan policy and your own observed
capabilities, copy the shipped example `.planzilla/templates/capabilities.json`, replace each placeholder with
evidence you observed, set `"enabled": true` only on routes you have demonstrated, and run, as a shell job,
`plz dispatch <plan> <role> '<line>' --actual-harness <h> --facts <file> --node <id>`:

```sh
cp .planzilla/templates/capabilities.json ~/plz-capabilities.json   # then edit it
.planzilla/plz dispatch <plan> executor 'Plan: <plan> · Node: N03 · Try: 1' \
  --actual-harness codex --facts ~/plz-capabilities.json --node N03 --record selections.json
```

The example holds one CLI-mode record each for claude, codex and copilot, all `"enabled": false`, so as shipped
it selects nothing and `plz dispatch` exits 3 with a handoff. Facts describe demonstrated model controls,
delivery and evidence; they are not discovery results. Dispatch uses the Graph selection and in-flight phase,
records actual/configured harness mismatch and selections/handoffs, and preserves resolved pins. The
orchestrator must `set` the phase before dispatch; dispatch does not change plan state.

Hosts that embed Planzilla can call `planzilla.commands.dispatch.dispatch` with observed capability facts and
host-owned `NativeAdapter` schemas/callbacks for an actual callable tool (FORMAT §9); the skills never need it.
That API also resolves deliberate executor/reviewer pairs: only after executor dispatch succeeds does the host
retain its `Selection`, and after `set VERIFYING` it passes `review=True, completed_execution=<retained
Selection>`, so review resolves only supported reviewers against that fixed history. Missing evidence or a
contradiction with the bound executor request/Graph pins produces a focused handoff.

Legacy `planzilla run <role> <model> <line>` keeps direct Claude/Codex CLI behavior and the caller's working
directory; capability-aware dispatch uses the plan repository. Direct `run` accepts supported exact
Claude/Codex selections, but does not resolve intent against host capabilities or enforce plan policy.
Do not send unresolved portable or qualified intent to a legacy prefix runner: `copilot::opus` goes through
`plz dispatch`, while `plz run <role> copilot::<model> '<line>'` takes an exact Copilot model id. External
Copilot runs the Copilot CLI headlessly (see [docs/COPILOT.md](docs/COPILOT.md)). External Claude/Codex/Copilot
calls relay the final role line; an `error: …` reply is a crash.

Keep an owned job handle and per-role temporary output/error/status. Continue waiting for a quiet pending
job within host wait limits (at most five minutes per call, shorter where required); silence is not a hang
and wait-call limits create no automatic execution deadline. Cancel only for explicit stop/cancel or
demonstrated need, targeting only the owned job through supported controls. Retain handle and evidence until
reply extraction or confirmed cancellation; never delete live-job evidence or kill by broad process matching.
Clean only that job's temporary directory after confirmation. Report observed status without inventing a
termination cause. An interruption consumes no retry; resume through `plz resume` before continuing.

## Verification tags

Every node ends in a list of criteria, each tagged by who checks it (FORMAT §6):

| tag | checked by |
|-----|------------|
| `[cmd]` | `planzilla check` runs the backticked command; exit 0 passes. No model involved |
| `[review]` | a verifier reads the code, tests and files |
| `[smoke]` | a verifier starts the app or calls an API and reports what it saw |
| `[visual]` | `plz-visual`: the verifier role plus a demonstrated usable native browser surface |
| `[human]` | you, in one batched round; used only when no other tag can check it |

Visual verification requires usable navigation and snapshot/image operations on the selected native surface,
under effective policy and actual callable controls (FORMAT §14). Codex may expose browser tools; Copilot has
no visual agent and its profiles establish no browser capability. An installed browser, login window or tool name is insufficient.
The researched host has no proven Copilot browser surface. Never route visual verification through text-only
`plz run`. Without a proven surface ask the planner to use a valid `[smoke]` or `[human]` criterion or replan.
Legacy `lint` visual checks remain conservative static checks of configured harness/native models; they do
not establish live capability. Set `visual_recipe` to explain app startup and the URL.

## What plz-new-plan detects and asks

On a repo's first run, `plz-new-plan` detects (FORMAT §8):

- the verify commands and other defaults, from `pyproject.toml`, `package.json`, `Makefile`, `AGENTS.md` and
  `CLAUDE.md`;
- permitted routes' CLI presence and noninteractive auth status when needed (`claude auth status`,
  `codex login status`); excluded providers receive no probes. Copilot has no status command, so its auth is
  checked only by a real delivery's prompt call, never by a separate probe;
- the actual harness and callable tools separately from configured `harness`; environment hints such as
  `CLAUDECODE=1` do not establish callable controls.

It asks gaps, tier and missing config values together, recommending only permitted evidenced delivery and
the actual harness. Auth failures receive recovery guidance, never automatic login. With existing config,
ask only for requested policy changes or unresolved mismatches; change only explicitly agreed config lines.
Portable defaults remain valid under Codex-only policy. Confirmed existing-plan changes use `plz policy`,
without repairing repository config. The planner authors Outline/DRAFT and every subsequent brief or revision.

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
- `planzilla policy <plan> [--harnesses LIST] [--providers LIST] [--models ROLES]` persists confirmed plan policy.
- `planzilla dispatch <plan> <role> <line> --actual-harness H --facts FILE [--node ID] [--model TOKEN] [--allow-low] [--record FILE]`
  resolves supplied capabilities under plan policy and runs the current phase through a supported CLI.
  `FILE` is a path to a UTF-8 JSON file of Capability records. An explicit `@low` pin is kept; `--allow-low`
  only permits mapping a portable alias or role default to low effort.
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
- `planzilla run <role> <model> <line>` runs one planner, executor or verifier step through a supported direct CLI
  and prints its one-line reply.
- `planzilla serve <plan> [--port N]` serves the live view.

## Upgrading a repo

To move a vendored repo to a newer Planzilla (FORMAT §11):

1. Run `planzilla install` from the repo root (the version you are running), or
   `planzilla install --version v0.3.0` for a released tag.
2. Check `.planzilla/VERSION` shows the version you expect.
3. Commit the result.
4. Start a fresh agent session: skills and agents load at session start, so a running session keeps the old ones.

Install rewrites only files whose bytes differ and removes files under `.planzilla/`, `.claude/agents/plz-*.md`,
flat `.github/agents/plz-*.agent.md`, `.claude/skills/plz-*/` and `.agents/skills/plz-*/` that the new kit no
longer ships. In `AGENTS.md` it replaces
only the lines between the `planzilla:begin` and `planzilla:end` markers. It never writes `.plan/` and never
touches unrelated paths under `.claude/`, `.agents/` or `.github/`, including user agents, nested profiles,
`.github/copilot-instructions.md` and workflows. A second run changes nothing.

To get a newer `planzilla` command itself, upgrade the install first: `brew upgrade planzilla` for Homebrew, or
rerun the `uvx` or `pipx` install.

## Releasing

`__version__` in `src/planzilla/__init__.py` is the one version (FORMAT §11). To release:

1. Bump `__version__`.
2. In `CHANGELOG.md`, move the `## [Unreleased]` entries under a `## [<version>] - <date>` heading and update
   the compare links at the bottom.
3. Re-vendor this repo with `planzilla install` so its own `.planzilla/` matches, and commit.
4. Merge to `main`.
5. Push the tag `v<version>`, for example `v0.3.0`. The tag must equal `v` plus `__version__`, or the build fails.
6. The Release workflow (`.github/workflows/release.yml`) builds the sdist and wheel, runs the Homebrew tests
   (`brew test` and `brew audit`) against the built formula, then publishes the GitHub release and pushes the
   formula to the `IVIR3zaM/homebrew-tap` tap. It needs the `HOMEBREW_TAP_TOKEN` secret.
7. Users then run `brew upgrade planzilla`.

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
