---
name: plz-new-plan
description: Plan a body of work as a Planzilla task graph under .plan/. Clarifies the request first, picks the tier (S, M or L), agrees the repo config, asks every open decision in as few rounds as possible, then has plz-planner write the plan. Use when the user asks to plan, decompose or build something that needs more than one quick edit, or mentions a plan, task graph or Planzilla. Run it afterwards with plz-run-plan.
argument-hint: <what to build or change, or a path to a request>
---

You set up a plan with the user. You don't explore the codebase; plz-planner does that in its own context.
CLI: run `.planzilla/plz` if that file exists, else `planzilla`; below, `plz <command>` means that program.
Questions go to the user in as few rounds as possible: clarification once, open decisions once.

## 1. Clarify first, before any graph (req 6)

1. **Request.** Use the arguments; if empty, ask what the plan should achieve. Keep raw wording in this conversation only: never store it or a pointer; only the agreed Intent is stored.
2. **Gaps.** List missing parts, assumptions, scope, constraints and how done will be shown. Read only needed README/CLAUDE.md/AGENTS.md.
3. **Tier** (FORMAT §1): smallest fitting tier, only escalate: S = one executor context, no open decisions, 1-2 exec nodes, no preflight and no final check; M = about 2-10 nodes; L = over 10 nodes, several sessions/environments or `runs/` evidence.
4. **Config** (FORMAT §8). Check effective policy and actual coordinator permissions by the Dispatch contract first, including request restrictions before any plan header exists. Missing `.plan/config.md`: detect `verify`, `verify_fast`, `commit` (per-node), `push` (per-node in cloud, else none), `retention` (keep) and `preauthorized` from project metadata and repo rules.
   For allowed routes only, detect CLI presence and noninteractive auth if needed (`claude auth status`: exit 0 and loggedIn true; `codex login status`: exit 0). Copilot auth checks require an actually supported noninteractive operation. Presence/auth proves no model delivery, quota or browser support. Identify the actual client/tools separately from configured `harness`; an environment hint is not callable evidence. Never probe excluded providers.
5. **One round** (req 7). Ask gaps, tier and missing-config values together in AskUserQuestion (up to 4 questions/call, recommended answer first labelled "(Recommended)"). Recommend only allowed evidenced providers and actual harness; offer recovery guidance for auth failure without performing login. Present config: ask only requested policy changes or unresolved mismatch. Follow up only for new gaps.

## 2. Config

Missing config: use `templates/config.md` (in `.planzilla/`, else installed `planzilla/kit/`) with agreed values, including providers/harness; preserve other defaults. Portable models work with Codex-only policy; don't replace them just because providers is codex. Present config: change only lines explicitly agreed, never rewrite it automatically to repair dispatch.

## Phase policy

Before Outline/DRAFT, JIT Brief, Replan, Revise, exec, separate verifier, final review and resume, recompute effective policy from request/plan restrictions and apply the Dispatch contract before any dependent action. Use effective `planner` defaults for all planner/replanner calls, the per-node Graph model for `executor` exec and `verifier` separate verifier/final review, falling back to effective role defaults only where absent. Preserve explicit version/effort/route pins on every phase and resume, even if repository planner is opus. Every review is a separate role invocation.
The planner owns Outline/DRAFT, Intent, Graph model tokens and briefs; orchestrator never authors DRAFT or briefs to evade a pin. Generic defaults stay portable unless pinned. Pass agreed intent, not raw wording.

## 3. Plan

Slug: 2-5 kebab-case words. Dispatch `plz-planner` with the effective planner model and exactly one line:
`Outline: <slug> · Request: <the agreed intent: goal; in scope; out of scope; constraints; definition of done; tier <T>>`
Planner stores Intent in its own words (L: `intent.md`; S/M: `## Intent`) and writes DRAFT:
- S/M: header (`tier: S` for S), Decisions, Graph and every brief.
- L: `plan.md`, outline and gate briefs; all others, check nodes included, come just in time via `Brief:` from plz-run-plan.
Expect `OUTLINED <plan> | tier: <T> | nodes: <n> | open: <k>`.

## 4. Confirm, once

1. Show goal and `plz status <plan>` (at most 25 lines).
2. Collect `| proposed` decisions from the plan (L: `plan.md`), including preauthorizations (offer pre-authorize first, keep a live gate second) and human verification doubts. Ask them all plus graph approval in one AskUserQuestion round, recommended answer first.
3. Dispatch `Revise: <plan> · D1: <answer> · D3: <answer>[ · graph: <the change>]` by Phase policy. Planner confirms Decisions, applies Intent/Graph/briefs and sets READY when no proposed items remain. Expect `REVISED <plan> | open: <k>`; repeat only for new items. No open items: still dispatch `Revise: <plan>` to set READY.
Never edit the header, Intent, Decisions, Graph or briefs yourself; planner-only authorship applies to every route.

## Dispatch contract

- Check actual coordinator against optional plan `harnesses` first; intersect delivery with effective `providers` before defaults, aliases, capability selection or auth probes. Never probe excluded providers; plan providers/models override repository defaults without widening either allowlist.
- Observe actual callable tool schema separately from configured harness; for actual Codex/configured Claude, surface the mismatch and reconcile through allowed proven controls; configuration is not tool evidence. Record original request, actual/configured harness and resolved model/effort/route with capability evidence, preserved pins and delivery/quota identities. Prefer proven native selection on the actual harness, with a separate role invocation for every phase.
- `[<route>::]<name>[@<effort>]`: `opus`/`sonnet`/`haiku` are portable intent. Prefer supported native Claude/Copilot families there, active Codex maps to supported Sol high/medium/low, low only when task policy permits. Preserve independent exact ID, effort and route pins; model prefixes never establish delivery or quota identity. Resolve and check bare CLI defaults too. `copilot::claude-sonnet-5@high` retains all three pins; `codex::opus` retains its route while mapping intent.
- Native Claude Code needs callable delegation and supported enforceable selection, including explicit effort when requested; verify repo rules are inherited/read, explicitly reading them when auto-discovery is unsupported. Codex requires exposed `model` and `reasoning_effort` accepting the exact values; use `fork_turns: "none"` where that contract requires fresh overrides. Neither prompt text nor inherited defaults enforces a pin; never invent fields.
- Copilot needs callable delegation, enforceable effective model/effort and repo-instruction inheritance. Check actual supported controls and profile precedence (`modelPolicy: required`, `include-custom-instructions: true`, supported `reasoningEffort`, session overrides and shadowing); never assume another client's schema. Check session startup and per-call delegation precedence separately; verify the effective selection rather than assuming a flag overrides a profile. A proven native-only route works without an external executable.
- Unsupported native selection: use only a proven pin-preserving CLI with demonstrated entrypoint and usable reply, else one focused handoff naming operation, failed constraint, evidence and minimal alternatives. Preserve qualified tokens through a supported runner; never send them to a legacy prefix runner. A catalog, executable, profile, mock or tool name proves no delivery; external Copilot and browser remain disabled on the researched host until demonstrated.
- After concrete route failure, distinguish quota exhaustion, auth, permission, unsupported selection and unknown; Exclude only the concrete failed delivery; preserve observed evidence and auth recovery; never log in interactively, scan provider-wide quotas, rewrite config automatically or silently relax pins. Generic exits, silence, signals and HTTP 429 without quota semantics prove no exhaustion or termination cause.
- For deliberate independence resolve executor/reviewer together through fallback, retaining all pins: Claude Opus execution/Copilot Opus review needs different routes, distinct delivery identities and distinct known quota identities with evidence. family diversity and route labels prove neither; separate cold contexts on one permitted route are allowed by policy, with no quota separation.
- Send the named role its exact one-line input; external `plz run <role> <m> '<line>'` uses proven supported controls (Claude Code may use `plz-run`; other hosts a supported shell job). Relay the final role reply; `error: …` is a crash. Never send `plz-visual` through text-only `plz run`: require demonstrated usable navigation and snapshot/image operations on the selected surface.
- For external jobs, keep per-role temp out/err/rc, use the supported job handle and host wait limits (at most 5 minutes per call, shorter where required); preserve observed status and clean up the temp directory after reply extraction.
- A batch may mix proven native and external dispatch in parallel. A route unavailable under every allowed tuple stops with `<id>: cannot dispatch <agent> <m>` and one focused handoff; orchestrators never substitute themselves for a role.

## 5. Finish

1. `plz lint <plan>` must print `lint ok: <n> nodes, <w> waves`; otherwise dispatch `Revise: <plan> · lint: <the problem lines>` by Phase policy and repeat.
2. S with no open items in step 4: run now via plz-run-plan. Otherwise offer `/plz-run-plan <slug>`; start only if requested.
