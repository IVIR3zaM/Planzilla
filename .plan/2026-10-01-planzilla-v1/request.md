# Request: build Planzilla v1

Consolidated from a design conversation (the owner's requirements, the agreed design and the owner's amendments).
Not verbatim: the conversation was long; everything the planner needs is here.

## What Planzilla is

An open-source (Apache-2.0) toolkit for graph-engineered, AI-assisted coding: a request becomes a task graph of
nodes; a thin orchestrator dispatches fresh executor and verifier agents per node, commits each verified node,
retries on findings, replans broken briefs, and resumes from files after any stop (usage limits included).
Repo: https://github.com/IVIR3zaM/Planzilla (this repo).

## Prior art to learn from (read excerpts only, never whole files)

No local-machine paths: this plan must run in a cloud session that has only this repo and the network.

- Global version (directory plans, Decisions, logs): bootstrap copies in this repo, `.claude/skills/new-plan/`
  (SKILL.md, templates/), `.claude/skills/run-plan/SKILL.md`, `.claude/agents/{planner,executor,verifier}.md`.
  They run this plan. Planzilla's own kit uses `plz-*` names and never edits or deletes them.
- Repo version (single-file plans, Findings inline, visual gates): https://github.com/IVIR3zaM/Sonar, branch `main`.
  Fetch files from `https://raw.githubusercontent.com/IVIR3zaM/Sonar/main/<path>`:
  `.claude/skills/new-plan/SKILL.md`, `.claude/skills/new-plan/template.md`, `.claude/skills/run-plan/SKILL.md`,
  `.claude/agents/{planner,executor,verifier}.md`, `CLAUDE.md` (sections "Graph workflow", "Token discipline"),
  and finished plans under `.plan/` (read heads only).
- A large real run of the global version: https://github.com/IVIR3zaM/Arboretum, final state at commit `25de39f`
  (not on any branch). Plan: `https://raw.githubusercontent.com/IVIR3zaM/Arboretum/25de39f/.plan/2026-09-27-credentials-practice-cloud-build/plan.md`;
  briefs and logs: same prefix + `nodes/N23.md`, `log/N17.md` etc.; the run's commits:
  `https://api.github.com/repos/IVIR3zaM/Arboretum/commits?sha=25de39f&per_page=60`.

## Lessons from those runs (design must address each)

- L1 Briefs bloated across replans (Arboretum N17/N23 ≈ 11 KB, carrying "History" sections). Replans rewrite a clean
  brief; history lives only in the log; briefs capped (~40 lines) or split.
- L2 All briefs written up front went stale (4 fix nodes added mid-run). Large plans brief just-in-time.
- L3 Most human stops were environment problems found hours in (permission refusals, `claude -p` auth in cloud,
  handoffs). A preflight node checks tools, auth, network, permissions first.
- L4 Verifier failed nodes on "Do" prose: criteria didn't cover the brief. Every criterion is falsifiable and the
  set covers the Do; the verifier judges criteria only.
- L5 Sonar's orchestrator did visual checks itself, filling its context with screenshots. Visual checks go to a
  subagent with browser tools.
- L6 Arboretum made ~27 status-only commits. No status-only commits: plan state rides in each node's commit.
- L7 Orchestrator re-read a 15 KB plan.md (19 long Decisions). The orchestrator must not read plan files at all.
- L8 Global and project skills/agents with the same names shadow each other (personal skills beat project skills,
  project agents beat user agents). Unique, prefixed names; no global copies needed.
- Works well, keep: per-node commits, cold verifier, verify script per plan, `runs/<node>/` evidence folder,
  pre-authorizing actions as Decisions, one-line agent replies, retry/replan budgets (2 tries, 2 replans).

## Requirements

1. One source of truth in its own versioned repo; usable on any machine and in cloud sessions because consuming
   repos vendor a pinned copy (skills, role prompts, adapters, script) into the repo and commit it. Upgrades by
   re-installing a newer version. No dependence on `~/.claude`.
2. Cross-harness where possible: role prompts are plain files (`roles/planner.md`, `executor.md`, `verifier.md`);
   per-harness adapters are thin (for Claude Code: `.claude/agents/plz-executor.md` etc. that say "follow
   roles/executor.md" and set tool limits; skills in Agent Skills `SKILL.md` format). README explains setup for
   Claude Code and at least the other common harnesses that read AGENTS.md / SKILL.md.
3. A CLI (`planzilla`, short alias optional) holding the state machine so agents never parse plan files. Python 3,
   standard library only. Commands (names may be refined): `install [--version]`, `next` (ready wave with models),
   `set <node> <status>` (validated transitions, try counter), `brief <node>` (brief + last findings on retry),
   `log <node> …`, `check <node>` (runs `[cmd]` criteria, no model), `commit <node>` (stages Write paths + plan,
   commits, pushes if configured), `status` (text), `serve` (live local web page), `stats`.
4. Installable by Homebrew (owner's tap) as well as `uvx`/`pipx` from git. GitHub Actions: CI (tests, lint) on push
   and PR; release on tag (GitHub release with artifacts; Homebrew formula updated).
5. Three tiers, chosen by new-plan before anything else (after clarifying intent, see 6), never preassigned to repos:
   - S: one executor context, no real decisions → single-file plan with 1–2 nodes; plan, execute, verify in the
     current thread as orchestrator with subagents.
   - M: ~2–10 nodes, clear scope → single file (Sonar-like), the whole plan and all briefs written in one planner call;
     the orchestrator only calls the planner again on BLOCKED/replan.
   - L: larger, multi-session or multi-environment, or needs evidence artifacts → directory; outline the whole graph,
     brief nodes just-in-time when they become ready.
   - Tiers only escalate (S→M on BLOCKED; M→L only via replan if the graph outgrows it).
6. First stage of new-plan = clarification: turn a vague request into a concrete one by surfacing missing parts and
   hidden assumptions, and agree them with the user before any graph is drawn. Output: `intent.md` (L) or an
   `## Intent` section (S/M): goal, in/out of scope, constraints, definition of done. The raw prompt is never stored.
7. Human in the loop minimal: all questions (clarification, decisions, verification doubts, pre-authorizations,
   project config) asked in the new-plan phase in as few rounds as possible; mid-run questions batched and only when
   nothing else can run; an S plan with no open questions just runs.
8. Per-repo rules: `.plan/config.md` (or similar), read only by planner/orchestrator: verify and verify_fast commands,
   commit/push policy, retention, visual-check recipe, default models, pre-authorized actions, always_review.
   Missing → the first new-plan detects values from the repo (pyproject, package.json, Makefile, CLAUDE.md/AGENTS.md)
   and proposes them in the same question round. Engineering rules stay in CLAUDE.md/AGENTS.md.
9. Verification planned per criterion with a method tag: `[cmd]` (run by `check`, no model), `[review]`,
   `[visual]` (browser-capable subagent), `[smoke]` (start app / call API), `[human]` only if unavoidable. Verifier
   model chosen per node by the hardest criterion (haiku can confirm a command; opus for judgement). Doubt about how
   to verify → ask during planning. Verifier stays cold (no logs) and reports failures only.
10. Records kept in the repo and never deleted by default; a repo's config can override retention
    (`keep` | `prune-logs` | `delete` | `branch-only`), applied when a plan finishes.
11. Resumable after any stop, including usage limits, on the same machine (working tree) or another (last pushed
    node commit; in-flight nodes rerun). Every state change is written before the dispatch that depends on it.
12. Token-aware everywhere: orchestrator context near-empty (only one-line CLI outputs and agent replies), agents
    exchange paths/ids not contents, one-line replies, briefs cite file:line and never paste code, `verify_fast` for
    executors and full `verify` for the check node.
13. Live view: `serve` shows the graph by wave with each node's status (planning, replanning, executing, verifying,
    done, blocked), try/replan counts, last log line, elapsed; works off files + git log; `status` prints the same as
    text for cloud sessions.
14. Apache-2.0 LICENSE and a good README: what it is, install (brew, uvx/pipx, vendoring into a repo), usage in
    Claude Code and other harnesses, the tiers, config, verification tags, resuming, the live view.

## Running this plan

Runs in a Claude Code cloud session on https://github.com/IVIR3zaM/Planzilla (or locally from this repo) with the
bootstrap run-plan skill and agents in `.claude/`. No `~/.claude` and no sibling checkouts exist there. The session
needs Python 3, git, network to PyPI and GitHub (raw and api), and push access to its own branch: every verified node
is committed and pushed so another session can resume. Once Planzilla can install itself, it may vendor itself into
this repo (dogfooding) — the planner decides whether that belongs in v1.
