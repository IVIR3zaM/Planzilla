# Planzilla format and CLI spec

This file is the one spec for Planzilla v1. Code, kit files and tests cite it as `FORMAT §n`. Where it says
"must", the CLI enforces it (parse error, lint problem or exit code); where it says "the planner", it is a rule
for the planner role that `lint` checks where it can.

Conventions used below: `<plan>` is a plan reference (§9), `<id>` a node id, `t` the node's try cell, `r` its rp
cell, `B` the tries budget and `R` the replans budget (§3, default 2 and 2). All files are UTF-8 with `\n` line
ends. Dates are `YYYY-MM-DD`; `today` and `now` are passed into the pure core, never read inside it.

## §1 Tiers and escalation

The tier is chosen by `plz-new-plan` after clarification (§3 Intent) and before any graph is drawn. It is a
property of the plan, never of the repo.

| tier | when | layout (§2) | briefs | who orchestrates |
|------|------|-------------|--------|------------------|
| S | one executor context, no open decisions, 1-2 exec nodes | single file | all written with the plan | the current thread, with subagents |
| M | about 2-10 nodes, clear scope | single file | all written in one planner call | `plz-run-plan`; planner called again only on replan or a missing brief |
| L | more than 10 nodes, multi-session or multi-environment, or evidence artifacts (`runs/`) | directory | just in time: a node is briefed when it becomes ready (§5 row 1) | `plz-run-plan` |

- The tier is recorded by the layout plus the optional header line `tier: S|M` (§3). A directory is always L. A
  single file without `tier:` is M.
- Tiers only escalate, never de-escalate:
  - S to M: when an S node is BLOCKED, the planner (on replan) sets `tier: M` and may add nodes in the same file.
  - M to L: only through a replan whose graph outgrows M (more than 10 nodes, or `runs/` evidence needed). The
    planner moves the file to a directory: header, `## Decisions`, `## Graph` go to `plan.md`; `## Intent` body to
    `intent.md`; each `## <id> <title>` section to `nodes/<id>.md` with heading `# <id> <title>`; each node's
    `## Log` entries to `log/<id>.md` (headings `### <id> <h>` become `## <h>`). Graph cells are unchanged.
- Node rules by tier (D26):
  - S has 1-2 exec nodes, no preflight and no final check; each exec node's last criterion runs the full `verify`.
  - M and L plans start with the N01 preflight `check` node (the full `verify` passes on the untouched tree; a
    `[cmd]` criterion proves each tool and its auth, each network endpoint and each permission the plan needs)
    and end with a whole-plan check node whose first criterion runs the full `verify`. Executors run
    `verify_fast`, so each exec node's last criterion runs `verify_fast`.
- The CLI treats S and M identically; only the layout (file or directory) changes its behavior.

## §2 Plan layouts

Plans live in `<root>/.plan/`, where `<root>` is the repo root (the directory holding `.plan/`). A plan's name is
`<YYYY-MM-DD>-<slug>` with `<slug>` matching `[a-z0-9]+(-[a-z0-9]+)*`. `.plan/config.md` (§8) is not a plan. The
slug is the name without the date prefix and without `.md`.

**S/M: one file** `.plan/<date>-<slug>.md`, top-level sections in exactly this order:

1. `# <title>` and the header lines (§3)
2. `## Intent` (§3)
3. `## Decisions` (§3)
4. `## Graph` (§4)
5. one `## <id> <title>` section per node, in Graph row order: the brief (§6)
6. `## Log` (§7), always last; written only through `planzilla log`, `check` and `resume`

A brief section ends at the next line starting with `## `. No other `## ` headings are allowed.

**L: one directory** `.plan/<date>-<slug>/`:

| path | content | written by |
|------|---------|------------|
| `plan.md` | `# <title>`, header (§3), `## Decisions`, `## Graph` (§4); nothing else is parsed | planner (structure), CLI (Graph cells, header `status:`/`updated:`) |
| `intent.md` | the Intent (§3); plans written by the bootstrap version have `request.md` instead | planner |
| `nodes/<id>.md` | the brief (§6), first line `# <id> <title>` | planner |
| `log/<id>.md` | the node's log (§7), first line `# <id> log` | CLI only (`log`, `check`, `resume`) |
| `runs/<id>/` | evidence: `check` output and any files the brief's Write lists there | CLI, executor |

Neither `intent.md` nor `request.md` is read by the CLI or required by `lint`. Any other content of `plan.md`
(comments, prose between sections) is ignored and preserved byte for byte on write.

`.plan/2026-10-01-planzilla-v1/` is valid L format as it stands: its `plan.md` header, Decisions and Graph follow
§3/§4, its briefs follow §6 (`Log:` and `Test first:` fields are allowed, a check node has no `Write:`), its logs
follow §7 (date-only headings are allowed; the bullet-only `## replan 1` entry of `log/N01.md` reads as an
implicit `note:` per §7 reading rules), and `runs/N01/` is an evidence folder.

## §3 Header and Intent

**Header.** The line after `# <title>` starts the header: consecutive `key: value` lines up to the first blank
line, in this order (optional lines may be absent):

| key | value | required | written by |
|-----|-------|----------|------------|
| `status` | `DRAFT` · `READY` · `RUNNING` · `WAITING` · `BLOCKED` · `DONE` | yes | planner (DRAFT, READY), CLI (rest, derived below) |
| `created` | `YYYY-MM-DD · updated: YYYY-MM-DD` (one line, two dates) | yes | planner; CLI rewrites `updated:` to `today` on every write |
| `goal` | one line | yes | planner |
| `verify` | one shell command that must exit 0 for the whole repo | yes | planner (from config `verify`) |
| `commit` | `per-node` · `none` | yes | planner (from config `commit`) |
| `push` | `per-node` · `none` (`yes`/`no` accepted) | no, default config `push` | planner (from config `push`) |
| `budgets` | `<B> tries per brief · <R> replans per node` | no, default `2 tries per brief · 2 replans per node` | planner |
| `tier` | `S` · `M` (single file only) | no, default M | planner |
| `harnesses` | nonempty comma-separated subset of `claude-code`, `codex`, `copilot`, no repeats | no, legacy harness permissions | planner |
| `providers` | nonempty comma-separated subset of `claude`, `codex`, `copilot`, no repeats | no, inherit repository providers | planner |
| `models` | `planner=<m>, exec=<m>, verify=<m>` (any nonempty subset, no repeated roles) | no, inherit repository role defaults individually | planner |

An unknown key, a missing required key or a bad value is a parse error. Normal Graph writes rewrite only the `status:` value and the `updated:` date. The supported `policy`
command below additionally replaces confirmed policy fields without rewriting Graph or prose.

Optional policy lines follow `tier` (or the last present earlier header key), in order `harnesses`,
`providers`, `models`. A plan's providers **replace** the repository list; they are never unioned with it. Merge models
by role: explicit Graph tokens take precedence for their phase, then plan role defaults, then repository
role defaults, then built-in defaults (§8). A Graph `-` still means an absent phase or the existing verify
default rule (§9), rather than an exec-model override. Missing plan policy preserves existing behavior.
Validate the merged role defaults against the effective provider list; an inherited incompatible exact
default is an error, never a reason to expand the plan's allowed routes. Explicit plan model errors point
to `models:`; an inherited default disabled by a plan restriction points to `providers:`.
Empty policy fields, with or without a space after `:`, give the field-specific errors in §8. Header key
ordering still applies; models-before-providers is an out-of-order header error, not an alternate spelling.

`harnesses` restricts both the actual coordinator and every role's delivery, independently of configured
`harness` and effective providers. Check actual coordinator membership before resolving defaults or aliases.
Map delivery permissions `claude-code` → `claude`, `codex` → `codex`, `copilot` → `copilot`, then intersect
with effective providers; never widen either list. Multiple entries permit listed cross-harness combinations.
Omission adds no harness restriction and preserves legacy behavior. Empty, duplicate or unknown entries give
`bad harnesses value '<v>': expected a comma-separated subset of claude-code, codex, copilot, no repeats`
at that header line. A supplied disallowed coordinator gives `coordinator <h> is not in harnesses` there;
an empty intersection gives `harnesses and providers have no allowed delivery`. Incompatible merged defaults
remain errors; an inherited default disabled by the harness intersection points at `harnesses:`. These pure
checks are reusable for planner/replanner, executor and verifier; dispatch enforcement and CLI persistence
are separate integration work. This schema does not migrate an existing plan or change repository config.

Plan status: DRAFT while any Decision is `proposed`; the planner sets READY once all are confirmed. From then on
the CLI derives it after every write (`set`, `resume`), in this order:
1. every node DONE → `DONE`;
2. any node BRIEFING, RUNNING, VERIFYING or REPLAN, or any non-`ask` action ready (§5 "ready") → `RUNNING`;
3. any node WAITING, or a gate node whose deps are all DONE → `WAITING`;
4. otherwise → `BLOCKED`.
`next`, `set`, `resume`, `check` and `commit` on a DRAFT plan exit 2 (§9).

**Decisions.** Under `## Decisions`, one line each: `- D<n> <text> | <state>[ · recommend: <a>][ · alt: <b>]`,
state `proposed` or `confirmed` (optionally followed by a parenthesised remark, e.g. `confirmed (owner)`). The
state is the first word after the last ` | ` on the line. Written by the planner only.

**Intent** (req 6; the raw prompt is never stored). L: `intent.md` starting `# Intent`; S/M: the `## Intent`
section. Both hold these five labeled paragraphs, each starting at column 0, in this order: `Goal:`,
`In scope:`, `Out of scope:`, `Constraints:`, `Definition of done:`. The CLI never reads the Intent.

## §4 Graph table and node types

Under `## Graph`: a blank line, then exactly this header and separator, then one row per node, then a blank line
or end of section:

```
| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
```

| column | grammar | meaning |
|--------|---------|---------|
| id | `N[0-9]{2,}[a-z]?`, unique | node id; a split adds a letter (`N03a`) or takes the next free number |
| title | text without `\|` | short title; used in commit messages (§10) |
| type | `exec` · `check` · `gate` | see below |
| deps | `-` or ids joined by `,` (spaces after commas tolerated on read, never written) | must exist; graph must be acyclic |
| model | `<exec>/<verify>`, each a model token (below) or `-` | `-` where the phase does not exist |
| try | integer ≥ 0 | attempts of the current brief (§5) |
| rp | integer ≥ 0 | replans used (§5) |
| status | one of §5 | node state |
| note | text without `\|`, may be empty | `fail C2,C4` · `blocked: <reason>` · `ask: D7` · `ask: C5` · `skipped: <reason>` · empty |

Cells are written as `| <value> |` with one space on each side; an empty note is `| |`. On write the CLI
replaces only the changed row lines; every other byte of the file is kept.

**Model tokens.** The shared grammar for config models, plan models, Graph and `set --model` is
`[<route>::]<name>[@<effort>]`. Names match `[a-z0-9.-]+`, efforts `[a-z]+`, and a route is `claude`, `codex`
or `copilot`. There are no spaces inside a token. `::` qualifies delivery and leaves the existing `/`
exec/verify separator unambiguous: `claude::opus/copilot::opus`. Graph accepts `-` as its phase sentinel;
role defaults cannot be `-`. `split_token` returns the unqualified name and effort; `route_of` returns only
an explicit route or a bare CLI-default route. Callers must preserve the original token's constraints.

Ordinary `opus`, `sonnet` and `haiku` are portable intent, with no route prefix required. They remain valid
with Codex-only policy. `fable` remains a legacy Claude-family alias. A versioned ID pins the exact model;
`@effort` pins effort; `route::` pins delivery. These are independent constraints. `claude-` and `gpt-`
prefixes classify model families for syntax and effort validation, never delivery, authentication or quota
identity. Both families may be delivered by Copilot: `claude::claude-sonnet-5` and
`copilot::claude-sonnet-5`, or `codex::gpt-5.6-sol@high` and `copilot::gpt-5.6-sol@high`, are distinct route
constraints for the same exact model. Name compatibility does not demonstrate availability.

| name class | syntactically compatible routes | `@<effort>` levels |
|------------|----------------------------------|--------------------|
| portable `opus`, `sonnet`, `haiku` | all three | `low` · `medium` · `high` · `max` |
| `fable`, `claude-*` | `claude`, `copilot` | `low` · `medium` · `high` · `max` |
| `gpt-*` | `codex`, `copilot` | `low` · `medium` · `high` · `xhigh` · `max` |
| bare `claude` | `claude` only | `low` · `medium` · `high` · `max` |
| bare `codex` or `copilot` | that route only | `low` · `medium` · `high` · `xhigh` · `max` |
| other names (legacy syntax) | unconstrained until capability resolution | none |

A bare route names that CLI's configured default, optionally with effort (`codex@high`); it does not pin an
exact ID. A resolver must verify the selected default against any other constraints. For legacy Claude/Codex
CLI execution (§9), the bare name omits the model flag. Copilot parsing does not authorize external execution.
Without an effort suffix no explicit effort is pinned; portable mappings use §14. Existing valid tokens,
including `gpt-6.1-sol@medium` and `gpt-6.1-sol@high`, keep their spelling and round-trip unchanged.

**Choosing models.** Mechanical work uses haiku/low, coding sonnet/medium, judgement opus/high (§14).
Verify uses the hardest non-`cmd` criterion (§6). Planners can deliberately qualify Claude Opus execution
and Copilot Opus review. Neither the same family nor different families proves route/quota independence.
Effective plan policy (§3) constrains every selection, including planner defaults.

A grammar error has reason `bad model token '<token>': expected [<route>::]<name>[@<effort>]`;
an unknown qualifier gives `… : unknown route <route>`; a contradictory qualifier gives
`… : <name> is incompatible with route <route>` (including qualified `-`). Bad efforts give
`… : <name> takes no effort` or `… : <family> efforts are <levels>`. A malformed qualifier such as
`copilot:opus`, an empty name/route, or multiple qualifiers is a grammar error. Each path wraps the reason:
Graph reports `bad model '<cell>'` at its row's file/line; `set --model` reports
`bad --model '<m>': <reason>` (or `… : expected <exec>/<verify>` if not two tokens); config and header models
report `bad models value '<value>': <reason>` at the models line. Disabled explicit routes report
`bad models value '<token>': provider <route> is not in providers`. An unqualified exact ID requires at least
one compatible allowed route; failure names `provider one of <routes> is not in providers`. Unknown legacy
names remain parseable but need capability evidence to execute.

Node types:
- `exec`: an executor does the work, `check` runs its `[cmd]` criteria, a verifier judges the rest. Model e.g.
  `sonnet/opus`; `<verify>` is `-` when all criteria are `[cmd]`.
- `check`: no executor; `check` runs `[cmd]` criteria, a verifier judges the rest. Model `-/<verify>`.
- `gate`: no agent; the human approves when its deps are DONE (only when a Decision keeps a human stop live).
  Model `-/-`, criteria `[human]`.

**Waves.** wave(n) = 1 if n has no deps, else 1 + max(wave(d) for d in deps). Waves order `next` output, lint's
disjointness rule and the live view. A cycle is a plan error naming the cycle (`N03 -> N05 -> N03`).

## §5 Statuses, transitions, budgets

| status | meaning | in flight | live view (§12) |
|--------|---------|-----------|-----------------|
| TODO | not started (or new brief after a replan) | no | todo |
| BRIEFING | planner is writing the brief just in time | yes | planning |
| RUNNING | executor working on try `t` | yes | executing |
| VERIFYING | `[cmd]` criteria passed; verifier judging | yes | verifying |
| RETRY | failed try `t`, waits for try `t+1` | no | retry |
| REPLAN | planner rewriting the brief | yes | replanning |
| WAITING | needs a human answer (note `ask: D<n>` or `ask: C<n>`) | no | waiting |
| DONE | verified (or skipped by the human); final | no | done |
| BLOCKED | budgets used up; human decides | no | blocked |

**Ready.** A node is ready when all its deps are DONE. `next` (§9) maps ready nodes to actions:
TODO exec or check without brief → `brief`; TODO exec with brief, RETRY, RUNNING → `exec`; TODO check with brief
and any `[cmd]` criterion → `check`; TODO check with brief, without → `verify`; VERIFYING → `verify`; BRIEFING →
`brief`; REPLAN → `replan`; WAITING, and TODO gate → `ask`. DONE and BLOCKED give nothing. Gates are not briefed
just in time: the planner writes a gate's brief with the outline (req 7). In-flight statuses map to their own action again
because `next` is only called when nothing is in flight (§14): an in-flight status there means a stop
interrupted it.

**Verifier needed** for a node when it has a non-`[cmd]` criterion (D11); a node with only `[cmd]` criteria gets
no verifier.
**Human criteria** are the node's `[human]` criteria.

**Budgets.** `B` tries per brief, `R` replans per node, from the `budgets:` header (default 2 and 2). A failure
at `t < B` on an exec node gives RETRY; a failure at `t ≥ B`, any failure of a check node, an executor BLOCKED,
and gate defects give REPLAN. Entering REPLAN adds 1 to `r` (except rows 20 and 26); if `r` is already `R`, the
node becomes BLOCKED instead (r unchanged) with note `blocked: <note>` (`<note>` = the incoming note without a leading `blocked: `).

**Transition table.** "event" is the agent reply or human answer, "command" is what the orchestrator runs. `t`
and `r` columns: `+1`, `0` (reset) or `·` (unchanged). Note column: the note after the transition (`·` kept,
`∅` cleared). The CLI writes the Graph and header before it prints (req 11).

| # | from | event | command | to | t | r | note |
|---|------|-------|---------|----|---|---|------|
| 1 | TODO (exec or check, no brief) | `next`: brief | `set <id> BRIEFING` | BRIEFING | · | · | · |
| 2 | BRIEFING | planner `BRIEFED` | `set <id> TODO` | TODO | · | · | ∅ |
| 3 | BRIEFING | planner `ASK <id>: D7` | `set <id> WAITING --note "ask: D7"` | WAITING | · | · | ask: D7 |
| 4 | TODO (exec, brief) or RETRY | `next`: exec | `set <id> RUNNING` | RUNNING | +1 | · | · |
| 5 | RUNNING | executor `DONE`, `check` PASS, verifier needed | `set <id> VERIFYING` | VERIFYING | · | · | · |
| 6 | RUNNING | executor `DONE`, `check` PASS, no verifier needed | `set <id> VERIFYING` | DONE | · | · | ∅ |
| 7 | RUNNING | executor `DONE`, `check` FAIL, `t < B` | `set <id> RETRY --note "fail C1"` | RETRY | · | · | fail C1 |
| 8 | RUNNING | executor `DONE`, `check` FAIL, `t ≥ B` | `set <id> RETRY --note "fail C1"` | REPLAN | · | +1 | fail C1 |
| 9 | RUNNING | executor `BLOCKED <id>: <why>` | `set <id> REPLAN --note "blocked: <why>"` | REPLAN | · | +1 | blocked: <why> |
| 10 | TODO (check, brief) | `check` PASS, verifier needed | `set <id> VERIFYING` | VERIFYING | +1 | · | · |
| 11 | TODO (check, brief) | `check` PASS, no verifier needed | `set <id> VERIFYING` | DONE | +1 | · | ∅ |
| 12 | TODO (check, brief) | `check` FAIL | `set <id> RETRY --note "fail C1"` | REPLAN | +1 | +1 | fail C1 |
| 13 | TODO (check, brief, no `[cmd]`) | `next`: verify | `set <id> VERIFYING` | VERIFYING | +1 | · | · |
| 14 | VERIFYING | verifier `PASS`, no human criteria | `set <id> DONE` | DONE | · | · | ∅ |
| 15 | VERIFYING | verifier `PASS`, human criteria C5,C6 | `set <id> DONE` | WAITING | · | · | ask: C5,C6 |
| 16 | VERIFYING (exec) | verifier `FAIL <id>: C2`, `t < B` | `set <id> RETRY --note "fail C2"` | RETRY | · | · | fail C2 |
| 17 | VERIFYING | verifier `FAIL`, `t ≥ B` or node is check | `set <id> RETRY --note "fail C2"` | REPLAN | · | +1 | fail C2 |
| 18 | REPLAN | planner `REPLANNED <id>` | `set <id> TODO` | TODO | 0 | · | ∅ |
| 19 | REPLAN | planner `ASK <id>: D7` | `set <id> WAITING --note "ask: D7"` | WAITING | · | · | ask: D7 |
| 20 | WAITING (`ask: D…`) | human answered | `set <id> REPLAN` | REPLAN | · | · | · |
| 21 | WAITING (`ask: C…`) | human confirms | `set <id> DONE` | DONE | · | · | ∅ |
| 22 | WAITING (`ask: C…`) | human rejects C5 | `set <id> RETRY --note "fail C5"` | RETRY, or REPLAN by budget | · | · or +1 | fail C5 |
| 23 | TODO (gate) | human approves | `set <id> DONE` | DONE | · | · | ∅ |
| 24 | TODO (gate) | human lists defects | `set <id> REPLAN --note "gate: <defects>"` | REPLAN | · | +1 | gate: … |
| 25 | any row entering REPLAN with `r = R` | budget exhausted | (same command) | BLOCKED | as row | · | blocked: <note> |
| 26 | BLOCKED | human: new brief | `set <id> REPLAN` | REPLAN | · | set to 1 | · |
| 27 | BLOCKED | human: skip | `set <id> DONE --note "skipped: <why>"` | DONE | · | · | skipped: <why> |
| 28 | BRIEFING / RUNNING / VERIFYING / REPLAN | re-dispatch (stop, crash, malformed reply) | `set <id> <same status>` | same | · | · | · |
| 29 | RUNNING | stop, then `resume` | `resume` | RUNNING (rerun) | · | · | · |
| 30 | VERIFYING (exec), no uncommitted change under its Write paths | stop, then `resume` | `resume` | RUNNING (rerun) | · | · | · |
| 31 | VERIFYING, otherwise | stop, then `resume` | `resume` | VERIFYING | · | · | · |
| 32 | BRIEFING / REPLAN / others | stop, then `resume` | `resume` | unchanged | · | · | · |

Every other (from, to) pair is illegal: `set` exits 2 and leaves every file byte-identical. DONE is final.
Rows 6, 11, 15, 8, 12, 17, 22 and 25 are redirects: the command names the requested status, `set` applies the
rule and prints the status it wrote. Leaving TODO or RETRY requires all deps DONE, and `set <id> RUNNING`
from TODO requires the brief to exist (exit 2 otherwise); so do `VERIFYING` and `RETRY` from TODO on a check
node, which can only go to BRIEFING until it is briefed.
`--note` replaces the note; without it the note follows the table.

## §6 Briefs and criteria

A brief is the L file `nodes/<id>.md` (first line `# <id> <title>`) or the S/M section starting `## <id> <title>`.
At most 40 lines including the heading, trailing blank lines not counted (lint). It holds the current brief only:
history lives in the log (L1); a replan rewrites it clean.

**Fields.** A field starts at a line beginning (column 0) with one of these labels, in this order:
`Do:`, `Context:`, `Read:`, `Write:`, `Log:`, `Test first:`, `Done when:`. Its value is the rest of that line
plus every following line up to the next field label. Any other `Word:` line is part of the current field.

| field | required | content |
|-------|----------|---------|
| `Do:` | yes | the change, in a few sentences |
| `Context:` | no | restated Decisions and facts, citing `path:line`, never pasted code |
| `Read:` | no | paths the executor reads (free text with backticked paths) |
| `Write:` | exec: yes; check, gate: absent or `-` | the only paths the node may change (grammar below) |
| `Log:` | no | legacy, ignored by the CLI |
| `Test first:` | no | the failing test to write first, or `-` |
| `Done when:` | yes, last | the criteria |

**Write paths (parser needs no judgement).** The value is `-`, or a list of items each wrapped in single
backticks and separated by `,` and whitespace (line breaks allowed); any other character outside backticks is a
parse error. Each item is a repo-relative POSIX path: no leading `/`, no `./`, no `..` segment, no `\`.
Segments may contain `*` (any characters within one segment, e.g. `plz-*`). `**` must be a whole segment and
matches zero or more segments. No `?`, `[...]` or `{...}` (no brace expansion). A trailing `/` means `/**`.
A path matches an item when `fnmatch.fnmatchcase` matches segment by segment with `**` as above.

Two items overlap when some path could match both. With `a`, `b` their segment lists, `overlap(a, b)` is:
- `a` empty: true iff every segment of `b` is `**` (likewise with `b` empty);
- `a[0]` is `**`: `overlap(a[1:], b) or overlap(a, b[1:])` (likewise when `b[0]` is `**`);
- otherwise the heads must be compatible and `overlap(a[1:], b[1:])`; heads are compatible when equal, when
  exactly one contains `*` and `fnmatchcase(plain, pattern)` is true, or when both contain `*`. (Example: `src/planzilla/kit/**` overlaps
`src/planzilla/kit/roles/x.md`; `.claude/skills/plz-*/**` does not overlap `.claude/agents/plz-a.md`.)

**Criteria.** Inside `Done when:`, each criterion starts with a line `- C<n> [<tag>] <text>`; lines starting with
two or more spaces continue it. `n` is unique within the brief. Tags:

| tag | verified by | rule |
|-----|-------------|------|
| `cmd` | `planzilla check`, no model | the text must start with one backticked span: that span (without backticks) is the command; text after it is commentary; pass = exit 0 |
| `review` | verifier (reads code, tests, files) | falsifiable statement about the tree |
| `smoke` | verifier (starts the app, calls an API) | names the command and the expected observation |
| `visual` | `plz-visual` (verifier role + browser tools, §14) | names the page/state and what must be seen |
| `human` | the human, in the batched round (§14); the verifier skips it | only if no other tag can check it |

The planner writes criteria that are each falsifiable and together cover the `Do:` (L4); the verifier judges
criteria only. The verifier model (Graph `<verify>`) is set by the hardest non-`cmd` criterion on the §4 scale:
haiku or `codex@low` to confirm an observable fact, sonnet or `codex@medium` for a well-specified review, opus,
fable or `codex@high` for judgement; `-` when all criteria are `cmd`. The verifier may run on a different provider than the
executor (§4); it sees only the brief's criteria (`brief --verify`, §9), so the model and provider that wrote the
code never colour the check.

## §7 Logs and evidence (runs/)

The log is the only record carried between attempts. Written only by the CLI: agents call `planzilla log`;
`check` and `resume` append their own lines. Entries are appended, never edited.

**Location.** L: `log/<id>.md`, created with the line `# <id> log` and a blank line. S/M: the `## Log` section
at the end of the plan file.

**Entry heading.** Each entry belongs to an attempt key: `brief` when the node is BRIEFING; `replan <r>` when it is
REPLAN; otherwise `try <n>`, with `n = t + 1` when the node is TODO or RETRY (an attempt about to start, e.g.
`check` on a check node) and `n = t` otherwise. Before writing, the CLI compares the last heading of the log
(L: the file; S/M: the whole `## Log` section) with the entry's key, ignoring the date; if they differ it first
appends a blank line and the heading:
- L: `## <key> · <today>`
- S/M: `### <id> <key> · <today>`

Readers also accept headings with a time (`## try 1 · 2026-10-01 14:03`) and any blank lines between lines.

**Entry lines.** `<kind>: <text>`, then zero or more `- <bullet>` lines. Kinds and writers:

| kind | written by | text |
|------|------------|------|
| `exec` | executor | `DONE · <tests line>` or `BLOCKED · <reason>`; bullets: what changed, choices made |
| `check` | `planzilla check` | `PASS <p>/<n>` or `FAIL C2,C4`; one bullet per failing criterion: `C2 exit <code>: <last non-blank output line, ≤ 120 chars>` |
| `verify` | verifier | `PASS` or `FAIL C2,C4`; one bullet per finding, prefixed with its criterion id |
| `plan` | planner | `BRIEFED`, `REPLANNED[ +N18,N19]` or `ASK D7`; bullets: cause, what the new brief changes |
| `human` | orchestrator | the human's answer; bullets: defects or rejected criteria |
| `resume` | `planzilla resume` | `rerun at try <t>; partial edits of this try may be in the tree` |
| `note` | anyone | free text |

**Reading rules.** The CLI always writes a kind line before any bullet. Readers accept, without judgement:
- a `- ` line before the first kind line of an entry (or an entry with no kind line at all): it is a bullet of an
  implicit `note:` line with empty text at the start of that entry; e.g. the `## replan 1` entry of
  `.plan/2026-10-01-planzilla-v1/log/N01.md` (planner bullets only) reads as `note:` plus three bullets;
- a line that is neither a heading, a `- ` line, nor `<kind>: <text>` with a kind above: a `note:` line with the
  whole line as text;
- `<text>` of `exec`, `check`, `verify` is taken verbatim after the first `: `; only its first word (`DONE`,
  `BLOCKED`, `PASS`, `FAIL`) and, for `FAIL`, the following comma-separated ids are interpreted.

No reader rejects a log; `lint` does not check log contents.

**Findings** of a node = the last `check: FAIL` or `verify: FAIL` line in its log (S/M: in its entries) plus its
bullets. **Last log line** = the last non-blank line of the node's log or entries. **Rerun marker** = a `resume:`
line after the last heading whose key is `try <t>`.

**Evidence.** L only: `check` writes `runs/<id>/check-try<n>.txt` (`n` as in the heading), overwriting it, with
per `[cmd]` criterion: `== C<k> <command>`, then `exit <code>`, then the combined stdout and stderr. Agents put
other evidence under `runs/<id>/` when their Write lists it. S/M plans have no `runs/`; `check`'s log bullets
are the only record.

## §8 Config

`.plan/config.md`, read by the CLI and the planner, never by executors or verifiers. Lines are blank, comments
(starting with `#`) or `key: value` with a key below; anything else, an unknown key or a repeated key is a parse
error naming the file and line. Missing file = all defaults. The first `plz-new-plan` run in a repo detects values
(pyproject.toml, package.json, Makefile, AGENTS.md/CLAUDE.md), proposes them in its question round and writes
the file. `providers` is an allowed delivery list, not a claim of installed binaries, login, quota or model
availability. `harness` records the configured client; actual callable tools decide dispatch (§14). A request
for an additional route is reconciled with plan policy before use. Do not silently rewrite repository config
to resolve a mismatch or an unavailable route. A Codex-only configuration can keep portable defaults, or pin
exact supported Sol IDs and efforts. A bare `codex@high` does not establish an exact model.

| key | values | default | used by |
|-----|--------|---------|---------|
| `verify` | shell command, full check for the repo | empty | planner → plan header `verify:`; the final check node's first criterion (M/L), an S exec node's last |
| `verify_fast` | shell command executors run before replying | `verify` | `brief` (last line, §9); an M/L exec node's last criterion |
| `commit` | `per-node` · `none` | `per-node` | planner → header `commit:`; CLI when the header lacks it |
| `push` | `per-node` · `none` (`yes`/`no` accepted as aliases) | `none` | planner → header `push:`; CLI when the header lacks it |
| `retention` | `keep` · `prune-logs` · `delete` · `branch-only` | `keep` | `commit` on the finishing commit (§10) |
| `visual_recipe` | one line: how to start the app and which URL to open | empty | `brief --verify` for nodes with `[visual]` |
| `models` | `planner=<m>, exec=<m>, verify=<m>` (any nonempty subset, no repeated roles); each `<m>` is a model token (§4) | `planner=opus, exec=sonnet, verify=sonnet` | role defaults, composed with plan models (§3) |
| `providers` | nonempty comma-separated subset of `claude`, `codex`, `copilot`, no repeats | `claude` | `lint` (rule `providers`, §9); allowed delivery routes for the planner/resolver |
| `harness` | `claude-code` · `codex` · `copilot`: configured agent harness | `claude-code` | `lint` (rule `visual`, §9); capability reconciliation (§14); never permission to infer native tools |
| `preauthorized` | `;`-separated actions agents may take without asking | empty | planner → Decisions |
| `always_review` | `yes` · `no` | `no` | planner: with `yes` every exec node gets at least one `[review]` criterion |
| `commit_trailer` | text; `\n` separates lines | empty | `commit` message (§10) |

A plan header value wins over the config for that plan. Engineering rules stay in AGENTS.md/CLAUDE.md, not here.

`models`, `providers` and `harness` limits (parse errors naming the file and line, whatever the key order):
- a `models` value that is not a model token is `bad models value '<value>': <token error>` (§4);
- empty models or unknown roles give `bad models value '<value>': expected 'planner=<m>, exec=<m>, verify=<m>' (any nonempty subset)`;
- repeated roles give `bad models value '<value>': repeated model role: <role>`;
- a `-` role default gives `bad models value '<value>': role default cannot be '-'`;
- `providers` empty, naming another provider or repeating one is
  `bad providers value '<value>': expected a comma-separated subset of claude, codex, copilot, no repeats`;
- every role default must have a syntactically compatible allowed route (§4), checked after all fields are
  parsed, regardless of config key order. An explicit route must be listed. Portable `opus` with
  `providers: codex` is valid; `claude::opus` with that list is disabled;
- a `harness` value outside the three choices is
  `bad harness value '<v>': expected one of claude-code, codex, copilot`.

Plan policy uses the same providers/models parsers. Pure effective-policy composition takes supplied config,
header and source location, returns a fresh provider/model policy, and checks all merged role defaults.
It performs no file, environment, clock or provider access. Header providers replace repo providers;
partial header models inherit other roles (§3). Explicit Graph selections win over role defaults for their
phase but cannot expand the effective provider list; Graph route restrictions are checked by `lint`.

## §9 CLI commands and output lines

`planzilla` and `plz` are the same program (`planzilla.cli:main`); vendored repos run `.planzilla/plz` (§11).
`planzilla --version` prints `planzilla <version>`; `--help` lists all commands. Each command lives in
`planzilla/commands/<name>.py` with `add_arguments(parser)` and `run(args) -> int`.

**Plan reference** `<plan>`: a path to an L directory or an S/M file under some `.plan/`, or a slug fragment
matched against the names in `./.plan/` (directories and `.md` files, not `config.md`); it must resolve to
exactly one plan. The repo root is the parent of that `.plan/`; commands run git and `[cmd]` criteria there.

**Exit codes**, for every command: `0` success · `1` negative result (`check` FAIL, `lint` problems) · `2` usage
or plan error (unknown plan or node, parse error, cycle, illegal transition, failed precondition, DRAFT plan) ·
`3` external failure (git, push, network, lock timeout). Errors print one line `error: <message>` to stderr and
nothing to stdout. Stubs print `not implemented: <name>` to stderr and exit 2.

**Writes and locking.** Commands that write plan files (`policy`, `set`, `resume`, `log`, `check`, `commit`) first take the
lock `<plan path>.lock` (a directory created with `os.mkdir` next to the plan file or plan directory), retrying
every 50 ms for 10 s, and remove it when done; a lock older than 60 s is stale and removed; timeout exits 3.
Files are replaced atomically (write a temp file, then `os.replace`).

| command | arguments | stdout (each line one line; `<…>` filled in) | exit |
|---------|-----------|----------------------------------------------|------|
| `install` | `[--target DIR]` (default cwd) `[--version vX]` `[--archive-url URL]` | `installed planzilla <version> into <target>: <a> added, <c> changed, <r> removed` | 0; 2 target missing; 3 download or extract failed (target unchanged) |
| `policy` | `<plan> [--harnesses LIST] [--providers LIST] [--models ROLES]` (at least one) | `policy updated: <plan name>` | 0; 2 invalid policy/Graph; 3 lock/write failure |
| `next` | `<plan>` | one line per action: `<id> <action> <model>`; nothing when no action | 0; 2 |
| `set` | `<plan> <id> [STATUS] [--note TEXT] [--add] [--title T] [--type exec\|check\|gate] [--deps D] [--model M]` | `<id> <STATUS> try <t> rp <r>`, plus ` · dispatch <agent> <model>` when STATUS is BRIEFING, RUNNING, VERIFYING or REPLAN | 0 (also when redirected); 2 |
| `resume` | `<plan>` | per in-flight node: `<id> <STATUS> try <t> rp <r> · rerun`; then per WAITING or BLOCKED node: `<id> <STATUS> try <t> rp <r> · held` | 0; 2 |
| `brief` | `<plan> <id> [--verify \| --ask]` | executor mode, verify mode or ask line (below) | 0; 2 |
| `log` | `<plan> <id> <kind> <text> [-b BULLET]...` | nothing | 0; 2 unknown kind |
| `check` | `<plan> <id>` | `<id> check PASS <p>/<n>` or `<id> check FAIL <C2,C4> (<p>/<n> passed)` | 0 PASS; 1 FAIL; 2 |
| `commit` | `<plan> <id>` | `<id> committed <sha7>[ · plan DONE · retention <value>][ · pushed \| · push failed: <reason>]` or `<id> commit skipped: commit none` | 0; 2 node not DONE; 3 git or push failed (commit kept) |
| `status` | `<plan>` | the §12 text | 0; 2 |
| `stats` | `<plan>` | the §12 line | 0; 2 |
| `lint` | `<plan>` | per problem: `<file>:<line>: <rule>: <message>`; when clean: `lint ok: <n> nodes, <w> waves` | 0 clean; 1 problems; 2 unreadable plan |
| `serve` | `<plan> [--port N]` (default 8765) | `serving <slug> on http://127.0.0.1:<port>/`, then blocks until Ctrl-C | 0; 3 port in use |
| `dispatch` | `<plan> <role> <line> --actual-harness H --facts FILE [--node ID] [--model TOKEN] [--allow-low] [--record FILE]` | the current role's one-line reply | 0; 2 invalid input/policy/state; 3 unavailable delivery/role failure |
| `run` | `<role> <model> <line>` | the agent's one-line reply | 0; 2 bad input; 3 CLI missing, not logged in, failed or empty reply |

Details:
- `next`: lines in Graph row order; `<action>` is `brief`, `exec`, `check`, `verify`, `replan` or `ask` (§5
  "ready"); `<model>`: exec → the Graph `<exec>`; verify → the Graph `<verify>` (effective `models` `verify` if `-`);
  brief and replan → effective `models` `planner`; check and ask → `-`. `ask` lines are printed only when no other
  line is. BLOCKED nodes never print a line. A cycle exits 2 with `error: cycle N03 -> N05 -> N03`.
- `set`: STATUS may be omitted only with structure options. `--add` appends a new row (`--title`, `--deps`,
  `--model` required, `--type` default `exec`, try 0, rp 0, TODO); `--title`, `--deps`, `--model` alone edit a
  node that is not DONE. Deps must exist and stay acyclic. `dispatch` agent: BRIEFING, REPLAN → `plz-planner`;
  RUNNING → `plz-executor`; VERIFYING → `plz-visual` if the node has a `[visual]` criterion, else `plz-verifier`;
  model as in `next`. During a run, `set` is the only writer of Graph rows (D8); the planner adds or edits rows
  through it.
- `policy`: replace each supplied existing policy header field (or insert it in canonical header order);
  omitted fields remain byte-identical. `--models` replaces the plan's role-override field as a whole;
  omitted roles inherit repository defaults individually. Values use the §3 parsers, including nonempty,
  duplicate-free lists. Under the plan lock, parse all proposed fields together, compose effective policy
  and validate every existing Graph token against it before any write. Update only policy fields and the
  `updated:` date atomically; preserve unrelated headers, Intent, Decisions, Graph, briefs and logs. Invalid
  values, empty intersections and incompatible inherited defaults/Graph routes exit 2 without writes.
  No options exits 2. No auth, model or quota probes occur. Example of a confirmed migration:
  `plz policy <plan> --harnesses codex --providers codex --models 'planner=gpt-6.1-sol@high, exec=gpt-6.1-sol@high, verify=gpt-6.1-sol@high'`.
- `next`, `set` and `resume` compose effective defaults before actionable output or state/log writes.
  With explicit plan policy, validate Graph restrictions too, including add/edit/retry/new nodes. Omitted
  plan policy preserves legacy Graph editing behavior; every capability-aware dispatch still resolves and
  enforces its request against effective providers. Rejected operations leave plan/log bytes unchanged.
- `dispatch`: `FILE` is a UTF-8 JSON array of §14 `Capability` records (nested `Model`/`Failure` objects;
  tuples become JSON arrays). Facts are supplied observed evidence, never auto-discovered or promoted from
  fixtures to proof of live access. The actual harness is required separately from repository `harness`.
  Excluded providers have no model/auth/quota probes. The command connects policy and resolution to
  `commands.run.run_selection`, retaining the selected exact model/effort/route without prefix reselection.
  CLI execution uses the referenced plan's repository as its working directory, including auth-status
  checks and role-file lookup; legacy direct `run` continues to use the caller's working directory.
  The shell has no native callback: absent native controls trigger pin-preserving proven CLI fallback or
  one focused handoff naming operation, constraint, evidence and alternatives (exit 3). External Copilot
  remains disabled. `--record FILE` writes an array of the full selection/handoff records as JSON, without
  changing plan state. Node-bearing input binds to that Graph row even without `--node`; an explicit node
  must agree. Node phases require BRIEFING/REPLAN, RUNNING or VERIFYING for planner, executor or verifier;
  conflicting `--model` cannot override Graph pins. Executors require a node. Before dispatching the next
  phase the orchestrator still performs `set`; `dispatch` never changes state. `--allow-low` is an explicit
  task permission. Visual work requires the host-native proven surface and never a text-only CLI.
- **Callable host adapter**: `planzilla.commands.dispatch.dispatch(plan_ref, Request, line, *,
  actual_harness, capabilities, adapters=(), node_id=None, reviewer=None, review_line=None,
  independence=None, review=False, initial_policy=None, record=None) -> int` is the supported native/CLI
  boundary. It loads existing plan policy, checks actual coordinator before capabilities, reconciles the
  observed callable schema, calls `resolve`/`resolve_pair`, records selections, then consumes the current
  phase selection. For deliberate independence pass both requests and lines on each invocation: resolve
  the pair together, launch only execution with `review=False`, then after checks and `set VERIFYING`
  resolve again and launch only the separate reviewer with `review=True`. No review runs ahead of state.
  Without a plan use `plan_ref=None` and a confirmed, effectively composed `initial_policy: Policy` for
  Outline/DRAFT; existing plans reject an initial-policy override. Planner-wide Revise/final review may
  omit a node and use effective role defaults. `record` receives each full immutable selection/handoff
  before invocation (both selections for a pair); it is a host-owned sink, not capability proof.
  `NativeAdapter(route, schema, invoke, model_field="model", effort_field="reasoning_effort",
  role_field="task_name", input_field="message", fixed={"fork_turns": "none"}, delivery_id=None)`
  describes one actually callable tool. `schema` maps real exposed field names to accepted-value tuples,
  or `None` for unrestricted string fields. The host supplies `invoke(fields) -> str`, which invokes the
  real tool and returns its completed reply; Python cannot manufacture that bridge. Codex requires the
  exact exposed `model`, `reasoning_effort`, `task_name`, `message`, `fork_turns="none"` controls; model
  IDs and efforts are intersected with accepted schema values. Other hosts supply their demonstrated
  field names/fixed controls explicitly, including Copilot profile/delegation precedence evidence (§14).
  A callback receives a separate `plz-<role>` invocation and prompt to read repo rules and its role file.
  Missing/unsupported fields disable only that concrete native delivery, retain evidence and all pins,
  and rerun resolution before any invocation. CLI selections use the existing shared runner; native
  selections never reach the shell. Completed replies keep the one-line protocol; wait/cancel and raw
  process classification remain outside this adapter. With no record sink, mismatch notices go to stderr.
- `brief` executor mode (default): the brief verbatim; then, if `t ≥ 2`, a blank line, `## Findings (try <t-1>)`
  and the findings (§7) verbatim; then, if the rerun marker is present, a blank line and
  `Rerun: this try was interrupted; the tree may hold its partial edits. Continue from them.`; then a blank line
  and `Verify: <verify_fast>`. `--verify` (cold verifier): the heading line, the `Write:` field and the
  `Done when:` field verbatim, plus `Visual recipe: <visual_recipe>` if the node has a `[visual]` criterion and
  the recipe is set; never findings, logs or the rerun notice. `--ask` prints one line: WAITING `ask: D7` →
  `<id> D7: <decision line without "- D7 ">`; WAITING `ask: C5,C6` → `<id> human C5: <text> · C6: <text>`;
  BLOCKED → `<id> blocked: <note without "blocked: ">`; gate → `<id> gate: <title> · <criteria texts joined by " · ">`;
  any other node exits 2.
- `log`: kinds of §7 except `check` and `resume`; writes per §7.
- `lint` rules (D12 plus parse errors), `<file>` relative to the repo root, `<line>` 1-based:
  `parse` (any §2-§6 parse error) · `tag` (a criterion without a §6 tag) · `cmd` (a `[cmd]` criterion whose text
  does not start with a backticked command) · `length` (a brief over 40 lines) · `deps` (a dep that is not a node) ·
  `cycle` (cycle in the Graph, reported on the first row of the cycle) · `overlap` (two nodes of the same wave with
  overlapping Write items, reported on the second node's `Write:` line, naming both items) · `providers` (a Graph
  exec or verify token incompatible with effective `providers`, reported on the node's row:
  `<id> model <token> needs <source> providers to list <required>`; source is `plan` when header providers
  exist, otherwise `config`, and required is the explicit route or `one of <compatible routes>`) ·
  `visual` (config `harness`, §8 and §14: on a
  `[visual]` criterion's line when the harness has no visual agent:
  `<id> [visual] needs a visual agent; harness <h> has none`; on the row line, for a node with a `[visual]`
  criterion whose verify model (Graph `<verify>`, else effective `models` `verify`) the harness does not run
  natively: `<id> verify <token> is not a model harness <h> runs natively`). A missing brief is not a problem
  (just-in-time briefing).
- `serve` binds 127.0.0.1 only and never writes.
- `run` runs one agent step on a model through the provider's CLI, from the current directory (the repo root); it
  reads no plan file and writes none. `<role>` is `planner`, `executor` or `verifier`; `<model>` is a model
  token (§4) whose name has a provider; `<line>` is the role's one-line input (§14), non-empty and without a
  line break. Any other input exits 2 with the reason. The prompt, sent on stdin, is
  `Follow .planzilla/roles/<role>.md: read it first; it is your whole role.`, then `Input: <line>`, then
  `Reply with exactly the one line that role names, nothing else.`, each on its own line. Before the call, the
  login check (`codex login status`, exit 0; `claude auth status`, exit 0 and stdout JSON with `loggedIn`
  true) must pass. argv per provider (`-m <name>` / `--model <name>` takes the name and is omitted for a bare
  `codex` / `claude` (§4); `@<effort>` adds the effort flag shown, and is omitted without it):
  - codex: `codex exec [-m <name>] [-c model_reasoning_effort="<effort>"] -s workspace-write -c
    sandbox_workspace_write.network_access=true -C <cwd> -o <reply file> -`; the reply is read from a temp
    file, removed afterwards.
  - claude: `claude -p [--model <name>] [--effort <effort>] --output-format text --no-session-persistence
    --tools <T> --allowedTools <T> --permission-mode dontAsk`; the reply is stdout. `<T>` per role: planner
    `Read,Grep,Glob,Write,Edit,Bash`; executor `Read,Grep,Glob,Edit,Write,Bash`; verifier `Read,Grep,Glob,Bash`.
  The reply is the last non-blank line of the output, stripped, printed alone to stdout (exit 0); an empty
  output is `error: <cli> gave an empty reply`. External failures exit 3, print exactly one `error: …`
  line to stderr and no reply to stdout. Diagnostics report observations, never inferred quota exhaustion,
  cancellation actor or termination cause:
  - Missing executable: `error: <cli> not found on PATH`. Other launch failures, including permission denial
    or a missing working directory: `error: <cli> <phase> launch failed[: <observed error detail>]`, where
    phase is `login check` or `execution`.
  - Nonzero child status: `error: <cli> exited <code>[: <detail>]`; negative subprocess return codes report
    `error: <cli> terminated by signal <positive signal number>[: <detail>]`. Login-check failures use
    `<cli> login check` in place of `<cli>`. Detail prefers the last non-blank stderr line, then stdout.
    A signal proves termination by that signal, not who sent it or why.
  - Failed status execution alone is not logout evidence. An explicit Codex `Not logged in` detail on an
    ordinary nonzero login-check exit appends `; codex is not logged in; run codex login` to its diagnostic.
    A successful Claude status operation with JSON `loggedIn: false` reports
    `error: claude is not logged in; run claude auth login`. Invalid/missing Claude authentication status
    reports `error: claude login check returned invalid authentication status[: <detail>]`.
    Recovery hints require established authentication failure; generic exits and signals give none.
  - Missing or unreadable Codex reply files: `error: codex reply read failed[: <observed error detail>]`.
    This differs from a successfully read but empty reply. Error detail is reduced to its last non-blank
    line. Per-role temporary reply directories are removed on success and failure.
  This lifecycle also applies to resolved CLI dispatch; supported argv, model/effort/route pins, role input
  and legacy direct-run selection remain unchanged. Billing goes to the plan or account the CLI is logged in to.
- `check`: runs each `[cmd]` criterion with `sh -c` from the repo root, in criterion order, all of them even after
  a failure, each with a 900 s timeout (timeout = fail, exit shown as `timeout`); writes the log entry and
  evidence (§7). It never changes the Graph. A node with no `[cmd]` criteria prints `<id> check PASS 0/0`.
- `commit`, `status`, `stats`, `serve`: §10 and §12.
- `install`: §11. `--version vX` downloads `https://github.com/IVIR3zaM/Planzilla/archive/refs/tags/vX.tar.gz`
  (or `--archive-url`) with urllib into a temp dir and installs from the extracted `src/planzilla/`; the
  version written is `__version__` read from that tree's `__init__.py`. Without `--version` the source is the
  running package.

## §10 Commit and retention

`commit <plan> <id>` makes exactly one commit on the current branch for a DONE node, carrying the node's work and
the plan state together; there are no status-only or retention-only commits (L6, D19).

1. Plan header `commit: none` (or config, if the header lacks it) → print `<id> commit skipped: commit none`,
   exit 0. Node not DONE → exit 2, nothing staged.
2. Stage (additions, changes and deletions; a path that matches nothing is skipped): every Write path of the
   node's brief (§6 globs), and the plan's files:
   - L: everything in the plan directory except `log/` and `runs/`, plus `log/<id>.md` and `runs/<id>/`;
   - S/M: the plan file.
   Nothing else is staged; other dirty files stay dirty and uncommitted.
3. Message: subject `<slug> <id>: <title>` (Graph title); if `commit_trailer` is set, a blank line and the trailer
   lines.
4. Push when the header `push:` (or config) is `per-node`: `git push -u origin HEAD`. A failed push keeps the
   commit and exits 3 with `· push failed: <first stderr line>`.

**Finishing commit.** When, at commit time, the plan status is DONE (every node DONE, written by `set`), the same
commit applies the retention policy (config `retention`) and the line adds `· plan DONE · retention <value>`:

| value | effect |
|-------|--------|
| `keep` (default) | nothing removed; records stay in the tree |
| `prune-logs` | L: `log/` and `runs/` of the plan are removed in this commit; S/M: the `## Log` section is removed from the file |
| `delete` | the whole plan (directory or file) is removed in this commit; history keeps it |
| `branch-only` | the records are kept on a side branch, not on the current one: the CLI first builds the node commit with the records kept (as `keep`) without moving HEAD (`git commit-tree` on the staged tree, parent = HEAD) and points local branch `plan/<slug>` at it; then it removes the plan from the index and makes the finishing commit on the current branch (as `delete`). Both commits carry the same node message (step 3) and are the same node's commit; the current branch gets exactly one commit and there is no retention-only commit. `<sha7>` is the current-branch commit. With push `per-node`, `git push origin plan/<slug>` follows the step-4 push |

## §11 Vendored layout and adapters

**Kit (package data, `src/planzilla/kit/`), final names:**

```
kit/roles/planner.md  kit/roles/executor.md  kit/roles/verifier.md  kit/roles/visual.md
kit/templates/plan-single.md   S/M plan file (header, Intent, Decisions, Graph, one brief, Log)
kit/templates/plan.md          L plan.md
kit/templates/intent.md        L intent.md
kit/templates/node.md          L brief
kit/templates/config.md        .plan/config.md with every §8 key and its default
kit/agents/claude/plz-planner.md  kit/agents/claude/plz-executor.md
kit/agents/claude/plz-verifier.md  kit/agents/claude/plz-visual.md  kit/agents/claude/plz-run.md
kit/skills/plz-new-plan/SKILL.md  kit/skills/plz-run-plan/SKILL.md
kit/AGENTS-block.md            text placed between the AGENTS.md markers
```

Role prompts are plain, harness-neutral files. A Claude Code adapter is a thin agent file with front matter
(`name`, `description`, `tools`, optional `model`) whose body says to follow `.planzilla/roles/<role>.md`;
`plz-visual` follows `roles/visual.md` (the verifier role plus browser tools). `plz-run` follows no role: it
runs `.planzilla/plz run <role> <model> <line>` (§9) in the background, waits for it and relays its one line. Skills use the Agent Skills
`SKILL.md` format (`name` equal to the directory name, `description`) and call the CLI as `.planzilla/plz`.

**Install targets in a consuming repo** (`install`, D14):

| target | source |
|--------|--------|
| `.planzilla/VERSION` | the version and `\n` |
| `.planzilla/plz` | Python launcher, mode 0755: `#!/usr/bin/env python3`, prepends its own `lib/` dir to `sys.path`, calls `planzilla.cli.main()` |
| `.planzilla/lib/planzilla/**` | a copy of the whole package (kit and web included), without `__pycache__/` and `*.pyc` |
| `.planzilla/roles/*.md` | `kit/roles/` |
| `.planzilla/templates/*` | `kit/templates/` |
| `.claude/agents/plz-*.md` | `kit/agents/claude/` |
| `.claude/skills/plz-*/**` | `kit/skills/` |
| `.agents/skills/plz-*/**` | `kit/skills/` (same bytes) |
| `AGENTS.md` | `kit/AGENTS-block.md` between the lines `<!-- planzilla:begin -->` and `<!-- planzilla:end -->` |

Rules: AGENTS.md missing → created holding only the marked block; present without markers → a blank line and
the block are appended; with markers → only the lines between them are replaced. Files are written only when
their bytes differ (a second install changes no byte). Files under `.planzilla/`, `.claude/agents/plz-*.md`,
`.claude/skills/plz-*/` and `.agents/skills/plz-*/` that the new kit does not ship are removed, then empty
directories. Install never writes `.plan/` and never edits or deletes any other path under `.claude/` or
`.agents/` (D25).

**Versions and upgrades.** `__version__` in `src/planzilla/__init__.py` is the one version. A release is the tag
`v<version>` on main, whose Release workflow publishes the GitHub release and the tap formula. Upgrading reruns
`planzilla install` (or `install --version vX`), which rewrites only changed files, removes files the kit dropped
and never writes `.plan/`; then commit and start a fresh agent session (skills and agents load at session start).

## §12 Status, stats and live-view data

`status`, `stats` and `serve` read files and `git log` only (no state file, D8) and never write. One pure
function builds the per-node view; git output and `now` are passed in.

**Per node:** `id`, `title`, `type`, `wave` (§4), `status`, `view` (the §5 live-view label: planning,
replanning, executing, verifying, done, blocked, plus todo, retry, waiting), `try`, `rp`, `note`, `last` (the
§7 last log line, cut to 80 characters with `…`, or `-`), `elapsed`.

**Elapsed** (seconds or unknown), from git log only: run `git log --format='%ct %s' -- <plan path>` in the repo
root. A node's commit is the newest whose subject starts with `<slug> <id>: `. start(node) = the newest commit
time among its deps' commits; for a node without deps, the oldest commit touching the plan path. end = its own
commit time when DONE, else `now`. elapsed = end - start; unknown when the node is TODO, when start is
unknown, or when it is DONE without a commit. Text form: `<h>h<mm>m` from one hour, `<m>m` from one minute, else
`<s>s`; unknown is `-`. Plan elapsed = (newest node commit time if DONE, else `now`) - oldest commit touching
the plan path.

**`status` text** (exact):

```
<title> · <plan status> · <d>/<n> done · <plan elapsed>
wave <w>
  <id> <view> · <title> · try <t> rp <r> · <elapsed> · <note or -> · <last>
```

One `wave <w>` line per wave in ascending order, its nodes in Graph row order.

**`stats` line** (exact): `nodes <n> · done <d> · tries <k> · replans <s> · blocked <b> · commits <c> · wall <elapsed>`
where tries = number of `try` entry headings in all logs, replans = sum of the rp cells, blocked = BLOCKED nodes,
commits = node commits found, wall = plan elapsed.

**Live view** (`serve`): `GET /` returns one self-contained HTML page (inline CSS and JS, no external URL,
light/dark via `prefers-color-scheme`, usable at 375 px) that polls `GET /state.json` every 2 s and groups nodes
by wave. Any other path returns 404. `/state.json` is rebuilt from files and git log on every request:

```json
{"plan": "<slug>", "title": "<title>", "status": "RUNNING", "tier": "L", "updated": "2026-10-01",
 "done": 2, "total": 17, "elapsed": 5400,
 "waves": [{"wave": 1, "nodes": [{"id": "N01", "title": "…", "type": "exec", "status": "DONE",
   "view": "done", "try": 1, "rp": 1, "note": "", "last": "verify: PASS", "elapsed": 720}]}]}
```

`elapsed` is an integer number of seconds or `null`.

## §13 Resume

A stop (usage limit, crash, closed session) is not a failure and spends no budget. All state is in the Graph and
logs, written before each dispatch (req 11), so the orchestrator always starts with `planzilla resume <plan>`.

- Same machine: the working tree holds the uncommitted edits of in-flight nodes.
- Another machine: check out the branch at its last pushed node commit. Work of nodes not yet committed is absent;
  their rows may say RUNNING or VERIFYING (committed with another node's commit) and they rerun.

`resume` (rows 29-32 of §5):
- RUNNING stays RUNNING, try kept: appends the `resume:` log line (§7), so `brief` adds the rerun notice (D18);
  partial edits stay in the tree.
- VERIFYING exec node with no uncommitted change under its Write paths (`git status --porcelain` on them is empty)
  becomes RUNNING, try kept, with the `resume:` line; otherwise it stays VERIFYING and the verifier reruns.
- BRIEFING and REPLAN stay; the planner reruns. Other statuses are untouched.
- Derives the plan status (§3), sets `updated:`, prints the §9 lines. On a DONE plan it prints nothing.

## §14 Orchestrator loop

The orchestrator never opens plan files, briefs, logs, diffs or source (L7). Its context holds only one-line CLI
outputs and one-line agent replies; between agents it passes `<plan>` and ids. It never commits except through
`planzilla commit`, so every commit is a node commit (L6).

**Dispatch lines and replies.**

| agent | dispatch line | replies |
|-------|---------------|---------|
| `plz-planner` | `Brief: <plan> · Node: <id>` · `Replan: <plan> · Node: <id>` · `Revise: <plan> · Node: <id> · D7: <answer>` | `BRIEFED <id>` · `REPLANNED <id>[ +N18,N19]` · `ASK <id>: D7` |
| `plz-executor` | `Plan: <plan> · Node: <id> · Try: <t>` | `DONE <id> \| tests: <n> passed` · `BLOCKED <id>: <reason>` |
| `plz-verifier` / `plz-visual` | `Plan: <plan> · Node: <id> · Try: <t>` | `PASS <id>` · `FAIL <id>: C2,C4` |
| `plz-run` | `Run: <role> <model> · <line>` (`<line>` is the named role's dispatch line) | the role's reply line, or `error: <message>` (§9) |

Agents read their input with `brief` (executor: default mode; verifier: `--verify`) and write their log entry
with `log` before replying. The planner runs `lint` after writing and edits Graph rows only through `set`.

**Capability resolution contract.** N03 supplies token parsing, pure policy composition and effective-policy
lint. N04 implements resolution from supplied capability facts; N08 propagates it through dispatch and the
kit. The following is their required contract, not a claim that parsing a token enables its execution.
Legacy `runs_natively`/visual checks remain conservative static lint checks: Claude's unqualified aliases
without effort are native there; Codex and Copilot have no statically asserted native or visual capability.
Legacy `plz run` supports Claude/Codex unqualified CLI tokens (§9); qualified/Copilot dispatch requires the
later resolver/runner integration. Do not send a qualified token to a legacy prefix-based runner.

Resolution receives data, never discovers tools or probes accounts itself. Apply optional plan `harnesses`
to the actual coordinator first and intersect delivery permissions with providers (§3), before defaults,
aliases or capability selection. Configured/actual mismatch cannot bypass the allowlist:

| supplied input | meaning |
|----------------|---------|
| policy and request | effective providers/role defaults, original token, role/phase, and any deliberate executor/reviewer independence requirement |
| actual harness | observed client and callable native tool schema, separately from configured `harness` |
| selection capabilities | each supported route/mode's exact model IDs, aliases/default resolution, supported efforts and enforceable model/effort controls, with evidence references |
| delivery facts | opaque nonsecret delivery and credential/quota identities; independently established separation, shared identity or unknown |
| availability facts | native callable support or demonstrated external entrypoint/reply usability; route-specific observed failures and their classification |
| visual facts | usable navigation and snapshot/image operations on the selected surface, with evidence; absent or unknown means unavailable |

The pure API is `resolver.resolve(policy, request, context, capabilities)` and
`resolver.resolve_pair(policy, executor, reviewer, context, capabilities, independence)`. `Policy` holds
effective providers, merged role defaults and optional harnesses. `effective_policy` can also receive
`actual_harness` to reject the coordinator before composing defaults; resolver entry points always check it.
`Request` keeps the original token (or `None` for a role default), role, low-effort permission and visual
requirement. `Context` separates actual and configured harness. Planner/replanner and replan use planner
defaults; executor/exec and verifier/verify use their respective defaults. Each selection requires a
separate role invocation, including a verifier sharing a route with its executor.

Each `Capability` describes one concrete route/mode/delivery, its supported `Model` records (exact ID,
family, resolved aliases and efforts), enforceable model/effort controls, and evidence references. Native
availability must be `callable_native` on the actual harness's route; CLI availability must be `external_reply`
demonstrating an entrypoint and usable reply. A disabled record, absent evidence, catalog, executable-only,
mock or unknown availability cannot enable delivery. Model/effort controls mean exposed enforceable fields
or flags, never prompt assertions. `default_id`, when supplied, is an evidenced exact resolution of a bare
CLI default into that capability's model records. A proven CLI default may omit a model control; explicit
model selection and native delivery still require it. Every selected explicit or mapped effort needs a
supported effort and an effort control. Low effort also requires the request's task-policy permission.
Visual booleans represent demonstrated navigation and snapshot/image operations on this delivery's surface;
both and nonempty visual evidence are required for a visual request.

`Failure` is an already classified, evidenced observation attached only to that concrete capability:
`missing_entrypoint`, `unsupported_selection`, `quota_exhausted`, `auth`, `permission`, or `unknown`.
The resolver does no diagnostic parsing; generic exits, signals, silence and HTTP 429 without quota semantics
must enter as `unknown`. Failed deliveries cannot be selected. Their classifications and evidence survive
fallback; authentication recovery remains explicit even when another delivery succeeds.

Opaque `delivery_id` and `quota_id` values are nonsecret canonical identities established by the caller.
`quota_evidence` must establish the quota identity/separation, rather than just label different routes.
`Independence(delivery=True)` requires different routes and different delivery identities;
`Independence(quota=True)` requires distinct known canonical quotas with evidence for each. Unknown or
shared quotas fail this requirement. Pair resolution searches the ordered candidate product so fallback
retains every pin and both independence requirements. Without independence requirements, separate cold
contexts may share a route; this supplies no claim of separate quotas.

Selections retain original request, resolved intent, family, exact ID, effort, actual harness, route, mode,
delivery/quota identity and evidence, pins, mismatch notices and classified failures. Unavailable results
retain the operation/request, failed constraint, evidence, mismatch and focused recovery/constraint-change
alternatives. Ordering prefers proven native selection on the actual harness, then effective provider order,
then supplied capability/model order. Identical inputs produce identical results without input mutation.

For identical supplied facts, selection and diagnostics are deterministic. Resolve both executor and
reviewer when independence constrains the pair. Output either a supported selection (original intent,
family, exact ID, effort, actual harness, delivery route, native/CLI mode, quota identity, evidence and
preserved pins), or an unavailable/unsupported outcome naming the failed constraint and focused handoff.
Keep family, exact ID, effort, harness, delivery and quota identity distinct. Model-name prefixes do not
select delivery; different route names alone do not prove separate quota identities.

Apply effective plan restrictions and explicit pins before choosing an available route. Prefer proven native
selection in the actual harness for portable intent. Apply these mappings only where the supplied capabilities
support the resulting tuple:

| portable intent | Claude Code native | Copilot native | active Codex native |
|-----------------|--------------------|----------------|---------------------|
| `opus` / judgement | supported Opus | supported Opus through Copilot | `gpt-6.1-sol@high` |
| `sonnet` / implementation | supported Sonnet | supported Sonnet through Copilot | `gpt-6.1-sol@medium` |
| `haiku` / mechanical | supported Haiku | supported Haiku through Copilot | supported Sol at low effort, when task policy permits |

These are intent mappings, not intelligence equivalences or claims of model availability. An explicit ID
remains exact; an explicit effort remains exact; a route qualifier remains fixed. For example,
`copilot::claude-sonnet-5@high` cannot become Codex Sol or Claude delivery. Unqualified exact
`claude-sonnet-5` can use either proven allowed compatible delivery while keeping that exact ID.
`codex::opus` retains its Codex route while resolving portable family intent. An effort-qualified alias
retains its pinned effort across any otherwise permitted mapping. Bare CLI defaults must be resolved and
checked; a prompt saying “use model X” or an unverified inherited default is insufficient exact selection.

Actual/configured mismatch is surfaced before dispatch. Use the actual exposed tool contract and effective
plan policy to reconcile it: a configured Claude harness never makes a Claude Agent tool callable from
Codex. If exact native selection is enforceable, use its real fields and a separate role invocation; otherwise
use a demonstrated supported CLI route preserving the tuple, or return a focused handoff. Planner-only DRAFT,
JIT briefing and replanning remain planner work; the orchestrator cannot author DRAFT to evade a model pin.

**Failures, fallback and review.** Missing executable/entrypoint, unsupported exact selection, concrete quota
exhaustion, authentication failure, permission denial and unknown/transient failure are separate outcomes.
Authentication failure gives recovery guidance; it is not quota evidence and does not trigger interactive
login. A generic exit, timeout, HTTP 429 without quota semantics or missing output cannot prove exhausted
quota. Never scan provider-wide quotas, infer termination cause from a signal alone, or rewrite config to
work around a failed route.

After a concrete route is unavailable (including observed Claude quota exhaustion), portable intent may
fall back to a proven allowed route only if every ID/effort/route pin and deliberate reviewer independence
survives. Exclude only the concrete unavailable route. Resolve the pair together rather than silently moving
both phases to the same delivery. Claude Opus execution with Copilot Opus review can preserve deliberately
distinct routes despite sharing a family, but requires evidence of usable routes and independent quotas.
Unknown quota independence cannot satisfy a distinct-quota requirement. Separate cold verifier contexts on
one route are allowed when policy allows them; they provide separate judgement contexts, not quota separation.
If no supported tuple preserves constraints, hand off once with the unavailable operation, evidence and
minimal alternatives (supply capability evidence, restore the route, or authorize a constraint change).

Native-only Copilot can be usable inside an active Copilot harness while its external executable is absent
or unusable from another harness. Keep external Copilot disabled without demonstrated reachability and reply
usability; a catalog or mock is insufficient. Browser/visual dispatch needs a usable surface, never just an
installed browser, login window or tool name. N02's evidence establishes neither external Copilot nor a
usable browser on the researched host, so both remain disabled there. Parsing/configuration support does
not change that evidence.

**Exact Codex-only plan policy.** A plan may restrict providers to `codex` and override planner/verifier
defaults to `gpt-6.1-sol@high` while repository planner remains `opus`. Its planner must author exact Graph
tokens too. For the copilot-cli-support D8 policy, the required tuple is `gpt-6.1-sol@high` for initial
Outline/DRAFT planning, JIT `Brief:`, `Replan:`, `Revise:`, every other planner/replanner, all executors except
N05/N07, every separate verifier and final review; N05/N07 execution uses `gpt-6.1-sol@medium`. Resume
preserves this policy before any subsequent action. No Claude/Copilot model, auth, login or quota calls are
allowed in that plan; controlled mocks exercise other routes. This describes policy support, without
migrating the running plan header, actual repository config or vendored files in N03.

Exact Codex native selection requires exposed `model` and `reasoning_effort` controls accepting those exact
values. On the researched host, `fork_turns: "none"` is required with these overrides; inherited/all context
cannot select them. If those controls are absent, a supported external route must preserve both model and
effort through actual flags (§9), or dispatch stops for evidence/replan. Availability is never inferred from
argv tests. Honor host permissions; never add approval/sandbox bypass flags.

`plz-visual` requires the proven visual surface and never goes through a text-only `plz run`. A supported
external dispatch uses the named role's one-line input and relays its final reply; an `error: …` line is a
crash. Retain a supported owned job handle and per-role temporary output/error/status. Wait within host
limits (at most five minutes per call, shorter where required); continue waiting while a quiet job is
pending. Silence is not a hang; wait-call limits introduce no automatic execution deadline. Cancel only
on explicit stop/cancel or demonstrated need, target only the owned job through supported host controls,
and never kill by broad process matching. Retain output, error and observed completion status until reply
extraction or cancellation is confirmed, then clean up only that job's temporary directory. Never delete
live-job evidence; retain the handle and evidence while cancellation is unconfirmed. Do not introduce
streaming logs or a process supervisor. An interruption does not consume a node retry; resume uses
existing plan state through `resume` before continuing. Preserve pending/completed/failed/cancellation
observations without inventing a cause. A line no route can dispatch stops with
`<id>: cannot dispatch <agent> <m>` plus the focused constraint handoff. A batch may mix proven native and CLI
routes. Executable presence, catalog entries and controlled mocks never prove live reachability or quota.

**Loop.**

1. `planzilla resume <plan>`; remember the `held` ids.
2. `planzilla next <plan>`. No line and nothing held: done (the last `commit` line said `plan DONE`); report.
   No line but held BLOCKED ids, or only `ask` lines: go to 5.
3. For each line, in one batch (agents dispatched in parallel in one message):
   - `brief`: `set <id> BRIEFING`, dispatch `plz-planner` `Brief:`.
   - `exec`: `set <id> RUNNING`, dispatch `plz-executor` with the try from the set line.
   - `check`: `check <plan> <id>`, then route as in 4.
   - `verify`: `set <id> VERIFYING`, dispatch the agent named in the set line.
   - `replan`: `set <id> REPLAN`, dispatch `plz-planner` `Replan:`.
4. Route each reply when it arrives (every `set` before any dispatch that depends on it):
   - executor `DONE`: `check <plan> <id>`; PASS → `set <id> VERIFYING`; FAIL → `set <id> RETRY --note "fail <ids>"`.
   - executor `BLOCKED`: `set <id> REPLAN --note "blocked: <reason>"`.
   - verifier `PASS`: `set <id> DONE`. `FAIL`: `set <id> RETRY --note "fail <ids>"`.
   - planner `BRIEFED` or `REPLANNED`: `set <id> TODO`. `ASK`: `set <id> WAITING --note "ask: D7"`.
   - Whenever a `set` line says `DONE`: `commit <plan> <id>`; exit 3 stops the run. A line saying BLOCKED or
     WAITING adds the id to `held`.
   - Crash or malformed reply: re-dispatch once with the same `set <id> <same status>`; if it recurs, stop and
     tell the user.
   When the batch is routed, go to 2.
5. Human round, only when nothing can run and nothing is in flight: for each `ask` line and held id,
   `brief <plan> <id> --ask`; ask all of them in one round (recommended answer first); then:
   - `ask: D7` → `set <id> REPLAN`, dispatch `plz-planner` `Revise: … · D7: <answer>`; its reply routes as in 4.
   - `ask: C5` → confirmed: `set <id> DONE`, `commit`; rejected: `log <plan> <id> human "FAIL C5" -b "<why>"`,
     `set <id> RETRY --note "fail C5"`.
   - gate → approved: `set <id> DONE`, `commit`; defects: `log … human` with the defects, `set <id> REPLAN --note "gate: <short>"`.
   - BLOCKED → new brief: `set <id> REPLAN`, dispatch `Replan:`; skip: `set <id> DONE --note "skipped: <why>"`,
     `commit`; stop: end the run.
   Go to 2.

Per node the CLI calls are therefore: (`set BRIEFING`) · `set RUNNING` · `check` · `set VERIFYING` · `set DONE` ·
`commit`, plus `set RETRY`/`set REPLAN`/`set TODO` on failures and replans. Pausing needs no call: the plan already
holds the state; say `Paused at <ids>; /plz-run-plan <slug> resumes.`
