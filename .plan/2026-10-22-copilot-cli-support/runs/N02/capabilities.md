# N02 capability report

Observed 2026-10-22. Scope: research artifacts only. No product, kit, repo configuration, authentication or permanent host installation change was made. No Claude/Copilot model, login/status or quota request was invoked. Test subprocesses use mocks; they do not establish provider access.

## Evidence and bounded conclusion

Labels: **documented** = fetched official documentation or exposed tool contract; **demonstrated** = locally observed operation; **mocked** = controlled synthetic process result; **unavailable** = prerequisite missing here; **inconclusive** = evidence insufficient. Recommendations below are proposed implementation policy, not claims of live execution.

Mandatory Copilot harness conventions are **documented**: instruction discovery, Agent Skills, custom profiles, delegation and explicit model/effort controls have concrete official references below. This is enough to specify installation and guarded native dispatch. It does not certify that this host can execute Copilot. No mandatory research question remains blocking; if later implementation requires an exact operation absent from its actual tool schema, it must report BLOCKED/replan rather than infer it.

Conditional external Copilot provider execution is **unavailable and disabled**: `command -v copilot` returned 1; `copilot --version` exited 127. Conditional Copilot browser verification is **inconclusive and disabled**: no usable Copilot browser surface was demonstrated. Handoff guidance: install/authenticate Copilot separately when authorized, then demonstrate a harmless headless reply and a browser navigate/snapshot interaction before enabling those capabilities. Until then report the unsupported operation, or route the role to an already suitable supported route; a required visual criterion needs planner replan or explicit human handoff.

This executor did not dispatch extra model agents. The session exposes exact Codex native selection controls; native execution itself and this executor's selected parent model/effort were not introspected.

## Reproduction and local observations

Run from the repository root. Supporting files are confined to this N02 directory.

| Command or tool observation | Result | Class |
|---|---|---|
| `command -v codex`; `codex --version` | Found under the existing Node v22.21.1 installation; `codex-cli 0.163.0`, exit 0. Warning: unable to create PATH aliases, operation not permitted; version/help still exited 0. | demonstrated installation/help only |
| `command -v claude`; `claude --version` | `/opt/homebrew/bin/claude`; `2.1.89 (Claude Code)`, exit 0 | demonstrated installation only |
| `command -v copilot`; `copilot --version` | No PATH entry, exit 1; shell command not found, exit 127 | unavailable external CLI |
| `codex exec --help`; `codex --help` | Model, config override, sandbox, working directory, stdin and final-message output flags exposed | demonstrated help; see `codex-help.txt` |
| `claude --help` | Print, model, effort, output format, tools, permission mode, no-session-persistence flags exposed | demonstrated help; see `claude-help.txt` |
| Session `collaboration.spawn_agent` declaration | Exact model and effort fields, subject to fresh-context fork restriction | documented local tool contract; `native-tool-metadata.json` |
| `uv run python .plan/2026-10-22-copilot-cli-support/runs/N02/probe.py > .plan/2026-10-22-copilot-cli-support/runs/N02/probe-results.json` | Six exact Sol role/effort dispatches return 0 under mocks; five failure fixtures return 3; benign child pending/cancel observed | mocked provider behavior; demonstrated local process only |
| `uv run pytest -q tests/test_runner.py tests/commands/test_run.py tests/commands/test_install.py` | 108 passed in 2.60s, exit 0 | demonstrated tests, mocked provider IO |

The probe patches PATH resolution, the command's entire provider-call boundary and temporary reply location. Its recorded login argv is a fixture, never an executed authentication command. It exercises planner/executor/verifier with `gpt-6.1-sol@medium` and `@high`, retaining `-m gpt-6.1-sol` and the exact TOML effort argument. The current resolver maps `opus` and `claude-opus-5.5` to `claude`, and `gpt-6.1-sol` to `codex`; it cannot represent delivery collisions.

No environment dump, credential file, personal CLI config, auth cache, session history or provider-wide quota probe was read. Existing repo config was deliberately not opened by this executor; the configured planner=opus problem comes from the brief, not independent inspection.

## Harness matrix

All remote-source observations below were fetched on 2026-10-22. Documentation versions may exceed installed versions.

| Capability | Claude Code | Codex | GitHub Copilot CLI |
|---|---|---|---|
| Instructions | `CLAUDE.md`, `.claude/CLAUDE.md`, user `~/.claude/CLAUDE.md`; hierarchy and imports. Current docs add version-gated AGENTS support; local 2.1.89 predates it. | `AGENTS.override.md` before `AGENTS.md` at each applicable directory; global and repo-to-CWD hierarchy. | `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `.github/copilot-instructions.md`; path rules use `.github/instructions/**/*.instructions.md` with `applyTo`. |
| Skills | Project/user `.claude/skills/<name>/SKILL.md`; YAML metadata and Markdown instructions. | Project `.agents/skills/<name>/SKILL.md`, scanning CWD toward root; user `~/.agents/skills`; name/description metadata. | Project `.github/skills`, `.claude/skills`, `.agents/skills`; user `~/.copilot/skills`, `~/.agents/skills`; SKILL.md requires YAML name/description. |
| Custom agents | `.claude/agents/*.md`, `~/.claude/agents/*.md`; YAML name/description plus body; tools/model/effort optional. | Current docs: `.codex/agents/*.toml`, `~/.codex/agents/*.toml`; required name/description/developer_instructions; model/model_reasoning_effort optional. | `.github/agents/*.agent.md`, personal `~/.copilot/agents`; YAML description required, name/model/tools optional, Markdown body. See guarded contract below. |
| Native exact delegate selection | Model aliases/full IDs documented; local delegate tool not exposed in this Codex session, so not demonstrated. Version-gate effort. | Actual session contract below supplies exact model and effort; no live delegate launched. | Delegation documented; this session exposes no Copilot native task tool. Require actual native schema matching the requested tuple. |
| Headless and reply | `claude -p --model … --effort … --output-format text`; stdout final reply; JSON/stream-json also documented. Installed help agrees on those flags. | `codex exec -m … -c 'model_reasoning_effort="high"' -o <reply> -`; stdin prompt, final message file; JSONL is progress rather than final reply text. | Documented `copilot -p <prompt> -s --model <id> --agent <id>`; silent mode removes decoration. No local binary: external route disabled. |
| Permissions/auth prerequisites | Authenticated direct subscription, Console/API or supported cloud provider; tools and permission mode scoped explicitly. No authentication observed. | Configured authenticated route, network and sandbox permissions; session native children inherit constraints. CLI login status not checked. | Copilot entitlement, organization CLI policy if applicable, trusted working directory, explicit tool/path/URL permissions. No authentication observed. |
| Browser | Chrome integration documented with extension/browser/direct account prerequisites. Not exercised. | Session computer-use tool exists, but no usable surface was tested; do not infer a product-wide absence or a CLI browser connection. | Browser tooling documented; no Copilot process or usable surface demonstrated. Disabled here. |

Sources by matrix row, with precise sections:

- Instructions: [Anthropic, Choose where to put CLAUDE.md files / AGENTS.md](https://code.claude.com/docs/en/memory#claudemd-files); [OpenAI, How Codex discovers guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md); [GitHub, Types of custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions#types-of-custom-instructions).
- Skills: [Anthropic, Choose where skills load / Frontmatter reference](https://code.claude.com/docs/en/skills); [OpenAI, Where Codex loads local skills / Create a skill](https://learn.chatgpt.com/docs/build-skills); [GitHub, Creating and adding a skill](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills#creating-and-adding-a-skill).
- Agent schemas: [Anthropic, Frontmatter reference / Choose a model / Choose an effort level](https://code.claude.com/docs/en/sub-agents); [OpenAI, Custom agents / Custom agent file schema](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents); [GitHub, YAML frontmatter properties](https://docs.github.com/en/copilot/reference/custom-agents-configuration#yaml-frontmatter-properties).
- Agent paths and invocation: [GitHub, Creating a custom agent / Using a custom agent](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli); [GitHub, Use custom agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/invoke-custom-agents#use-custom-agents). Delegation is discretionary; a natural-language mention alone does not prove a separate invocation.
- Headless/replies/permissions: [Anthropic, Basic usage / Get structured output / Auto-approve tools](https://code.claude.com/docs/en/headless); [OpenAI, codex exec](https://learn.chatgpt.com/docs/developer-commands?surface=cli); [GitHub, Command line options / Model precedence](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference).
- Auth: [Anthropic, Log in to Claude Code](https://code.claude.com/docs/en/authentication#log-in-to-claude-code); [OpenAI, Sign in with an API key](https://learn.chatgpt.com/docs/auth#sign-in-with-an-api-key); [GitHub, Installation / Starting the CLI for the first time](https://docs.github.com/en/copilot/get-started/cli-quickstart). GitHub documents npm `@github/copilot` (Node >=22) and Homebrew `--cask copilot-cli`; neither was installed here.
- Browser: [Anthropic, Prerequisites](https://code.claude.com/docs/en/chrome#prerequisites); GitHub CLI command reference below, Built-in MCP servers. A browser opening for login is not evidence of automation or visual verification.

## Copilot native contract and version caveats

**Documented**, not locally executed: CLI-specific reference lists `task` delegation; `model`/`models`, `reasoningEffort`, `modelPolicy: required`, and `include-custom-instructions: true`. Without the latter, custom subagents omit repo instructions. Unsupported requested settings can fall back; required model policy guards authored model selection. Auto session selection can override agent model intent. Personal agent IDs can shadow project profiles. Require explicit selection and evidence of effective settings.

The command reference documents effort flags `--effort`/`--reasoning-effort` (model-dependent low/medium/high/xhigh/max), IDs `claude-opus-5.5` and `gpt-6.1-sol`, and built-in Playwright automation. These are catalog facts, not account availability or usable-browser proof. Source: [GitHub CLI command reference, Command-line options / Supported models / Custom agents reference / Built-in MCP servers](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference).

Proposed installer profile requirements: use a stable plz role ID, required description, an explicit role-file instruction, and the repository-instruction opt-in; keep tool scope role-appropriate. Avoid copying Claude's tool names as though they were Copilot tool names. Planner can author DRAFT; executor implements one brief; verifier reads evidence and judges independently. Do not hard-code a profile model that silently defeats the selected per-role model. Validate model/effort support in the actual harness before native selection; if exact selection cannot be established, return unsupported/handoff. Do not silently accept a session default after a pinned request.

The general GitHub agent schema omits some CLI-specific fields; use the CLI-specific reference for these additions, rather than assuming all Copilot clients share one schema. The programmatic page describes custom-agent model precedence over `--model`, whereas CLI delegation documents per-call resolution. Treat session startup versus delegation as separate operations; local behavior remains untested. Do not rely on a CLI flag overriding a profile without checking the target version.

Anthropic's current subagent page documents per-invocation effort only from v2.1.292; installed v2.1.89 cannot establish that feature. Its help demonstrates session `--effort` only. AGENTS auto-discovery requires v2.1.277; a direct role prompt must explicitly ensure repo rules are read on this installed version. No upgrade or import was made.

## Family, delivery and availability

Proposed resolver record (conceptual fields; no new public token grammar selected here):

`intent/portability · family · exact_id · effort · actual_harness · delivery_route · quota_identity · availability_evidence · pin_constraints`

A model vendor is not its delivery route. An Opus family delivered by Claude Code uses a different route from Opus through Copilot. GPT through Codex and GPT through Copilot can use the identical ID `gpt-6.1-sol` and still have different delivery/quota identities. GitHub lists both OpenAI and Anthropic families in its model catalog: [Supported models, Supported AI models / Model availability](https://docs.github.com/en/copilot/reference/ai-models/supported-models). That catalog cannot establish a particular account's entitlement. OpenAI API-key billing also differs from ChatGPT plan credits even within Codex; do not infer independent budgets from a CLI name alone ([OpenAI authentication, API key sign-in](https://learn.chatgpt.com/docs/auth#sign-in-with-an-api-key)).

Use opaque, nonsecret route/credential-source identities; never persist tokens or account identifiers as evidence. If independence cannot be established, mark it unknown. Native-only Copilot means an active Copilot harness can delegate internally even if `copilot` is absent or unusable from some other harness's shell. It does not make an external Copilot provider reachable. Conversely, an installed executable proves neither native delegation nor a usable headless route.

Proposed portable mappings, based on this brief's policy and fetched model guidance:

| Intent | Claude Code harness | Copilot harness | Active Codex harness |
|---|---|---|---|
| ordinary opus / judgement | Native Opus family, exact supported alias/ID resolved locally | Native Opus family via Copilot, locally supported exact ID | Sol family, current evidenced target `gpt-6.1-sol@high` |
| ordinary sonnet / specified implementation | Native Sonnet family | Native Sonnet family | `gpt-6.1-sol@medium` when Sol is the supported target |
| ordinary haiku / mechanical | Native Haiku family | Native Haiku family | Supported Sol at low effort if the task policy permits; no substitution during this D8 plan |
| explicit model, route or effort | Preserve all explicit constraints | Preserve all explicit constraints | Preserve all explicit constraints |

These are workload recommendations, not claims of equivalent model intelligence or identical effort semantics. OpenAI describes Sol for demanding planning/tool/validation work and high versus medium effort tradeoffs ([Subagents, Choosing models and reasoning](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning)). D8 supersedes generic alias choices for this plan. Cross-harness full Claude IDs remain pinned Claude requests; a name beginning `claude-` must not become Codex merely because Codex is active. Portable ordinary family intent must be distinguishable from that explicit pin in the later contract.

## Deterministic fallback and independent review

Proposed decision procedure: first apply plan-scoped pins, then explicit request constraints, then portable intent against actual harness capabilities and supported routes. Record the chosen tuple and evidence. A known missing binary, an unsupported exact tuple, quota exhaustion, authentication failure and an unknown transient failure are distinct conditions.

| Concrete case | Required result |
|---|---|
| Portable opus under active Codex with a supported exact Sol native route | Select Sol/high directly; do not infer a Claude route from the alias spelling. |
| Portable opus first attempted through Claude, executable missing or explicit usage/quota exhaustion observed | Remove only that concrete unavailable delivery route; fallback to proven active-Codex Sol if constraints and review independence survive. No blanket quota scan. |
| Synthetic `rate_limit_error: usage limit reached` versus synthetic failed login | First is quota evidence for the attempted route only; second is auth failure, not proof of exhausted quota. Current probe outputs differ; no live failure was observed. Auth failure should give recovery/handoff guidance, not label quota or start interactive login. |
| Qualified Claude route or explicit Claude ID/effort with no working route | Keep pinned; unsupported/BLOCKED or ask for a constraint change. Do not replace with Sol. |
| Claude Opus executor + Copilot Opus reviewer with established distinct delivery/quota routes | Same-family cross-route review preserves route independence; it is not model-family diversity. Both routes must actually work. Disabled on this host because Copilot external access is missing. |
| Executor and verifier on the same Codex route | Separate cold verifier invocation provides independent judgement context, not independent delivery/quota. Allowed for this plan by D8; cannot satisfy an unrelated explicit cross-route requirement. |
| A fallback would put executor and reviewer on one route when separate routes were deliberate | Resolve the pair together; choose a supported distinct reviewer route, or ask/replan if none preserves constraints. Never silently collapse independence. |
| Generic exit 1, timeout-looking silence, HTTP 429 without quota semantics, or failed permission check | Preserve observed failure and classify inconclusive/transient/permission as supported by evidence. Do not call all of them quota exhaustion or probe every provider. |
| No suitable supported tuple preserves pins and independence | Ask once with the concrete unavailable operation and minimal constraint alternatives; do not rewrite config automatically. |

A successful auth status or help/catalog entry would still not prove quota or live model execution. This research intentionally ran neither. Existing failure helpers report text, not typed quota/auth classifications; the fixture strings above are controlled inputs rather than vendor-stable parsers.

## Exact Codex selection and D8 propagation

**Documented local contract:** `collaboration.spawn_agent` actually exposes `model`, `reasoning_effort`, `fork_turns`, `task_name`, `message`. Model options include exactly `gpt-6.1-sol`; effort options include medium and high. Overrides are accepted only with `fork_turns: "none"`; the default/all fork inherits parent settings and cannot accept overrides. See `native-tool-metadata.json`. This is concrete exposed selection control, not merely a prompt naming a desired model. No native delegate execution is claimed.

For an orchestrator authorized to dispatch, select a fresh context with the exact model and effort and the usual role wrapper plus exact one-line input. A request containing only the string “use Sol high” without these fields is not proof of selected settings. A custom agent definition can carry its own overrides in current Codex documentation; if such a definition is used, verify precedence and resulting tuple. This session's tool contract, rather than another client's schema, governs the call.

| Dispatch phase | D8 exact model/effort |
|---|---|
| Initial planner / Outline / DRAFT authoring | `gpt-6.1-sol`, high |
| Every JIT `Brief:`, replan `Replan:` and decision `Revise:` | `gpt-6.1-sol`, high |
| N05 and N07 executor | `gpt-6.1-sol`, medium |
| All other executors, including N02 | `gpt-6.1-sol`, high |
| Every verifier and planner/replanner | `gpt-6.1-sol`, high; fresh separate invocation |

These are required dispatch settings, not attestation of how a previous invocation was launched. This executor cannot retroactively prove its parent's selection. The six mocked role/effort paths show the current external builder retains both parameters.

Fallback mechanism if a future host lacks the exact native fields: the existing runner builder produces `codex exec -m gpt-6.1-sol -c 'model_reasoning_effort="high"' -s workspace-write -c sandbox_workspace_write.network_access=true -C <repo> -o <reply> -`; medium changes only the effort value. Installed help validates the CLI flags and official reference documents overrides/final-message files. The probe validates argv construction and reply extraction, **not live CLI model access**. If native selection is unproven and that CLI route has not been demonstrated reachable, stop for evidence/replan; do not call a mocked route live-validated. Never add approval/sandbox bypass flags. This host has approval policy never; denied operations remain denied.

Current gaps identified from permitted code/spec reads:

- FORMAT §4 and `providers.py:18` derive delivery from model-name prefix, conflating family and route. `runs_natively` declares nothing native for Codex even though this host exposes an exact native tool.
- FORMAT §8, `config.py:10` and the brief's configured planner=opus case can send initial/JIT/replan planning to Claude under active Codex. The plan's D8 decision currently lives in brief context; there is no scoped policy field among `config.py:11-27`. Apply it before every planner dispatch, not only Graph execution. Do not inspect or rewrite config to solve this research node.
- FORMAT §14 and kit run-skill lines 63-71 route from configured harness, not a validated actual tool capability. An actual/configured mismatch must be surfaced and reconciled through plan-scoped resolution; a Claude profile/tool name is not callable merely because config names Claude.
- `runner.py:39` and `commands/run.py:34` support only Claude/Codex external calls. `commands/install.py:34-37,94-110` installs Claude agent wrappers and shared skills, with no explicit Copilot profile contract. The installed shared skill paths are already documented Copilot discovery paths, but that does not prove profile semantics. Current GitHub CLI documentation also lists `.claude/agents` as a compatibility discovery location; discovery of existing wrappers does not establish exact models, permissions or instruction inheritance.
- `kit/roles/planner.md:5,10,16` assigns planner-only DRAFT authoring and JIT/replan work. Preserve this boundary in every harness; orchestrators resolve and dispatch, rather than authoring DRAFT to evade planner model selection.

## Wait, cancel and failure evidence

**Demonstrated local process only:** the probe starts a benign Python child, observes its ready line and `poll() is None`, deliberately calls `terminate()`, then observes return code -15. The cause is known because the probe sent termination. This says nothing about provider cancellation or other unexpected terminations.

**Mocked runner failures:** failed login -> `error: codex is not logged in; run codex login`; quota fixture -> `error: codex exited 1: rate_limit_error: usage limit reached (synthetic fixture)`; negative rc -> `error: codex exited -15`; missing output -> `error: codex gave an empty reply`; failed spawn boundary -> `error: codex not found on PATH`. All return external-failure exit 3. No cancellation actor or termination cause can be recovered from a bare negative rc.

**Documented/code-observed:** `commands/run.py:20-31` blocks in captured `subprocess.run`, with no streaming/timeout/cancel interface. It maps every caught OSError to “not found”, which may conceal permission or launch errors. The adapter `kit/agents/claude/plz-run.md:15-21` polls an rc file, returns PENDING while absent and removes files on completion. Missing rc is pending/unknown, not a hang diagnosis. This observation is source inspection; no long-running provider was started.

**Available tool contracts:** exec-command sessions can yield a session_id and be polled with write_stdin; a functions.exec cell_id is a different handle. Native wait_agent waits for mailbox activity; interrupt_agent interrupts a turn and leaves the agent addressable. Neither implies process-tree teardown. Actual tool waits in this session included a running pytest session followed by successful completion (108 tests); no timeout or unexpected signal occurred.

Proposed bounded runner/kit behavior: preserve a job's last observed state, separate pending/completed/failed/cancel-requested/confirmed-cancelled, and report only observed status/rc/error. Poll in host-supported intervals (this host caps blocking communication intervals at 60 seconds; the kit's five-minute maximum is not a required wait length). On explicit cancellation use only the supported handle and report whether cancellation was confirmed. Do not invent “hung”, quota, sandbox kill, or user cancellation from silence/negative rc alone. No generic supervisor is proposed.

## Downstream work and disabled capabilities

| Later work area | Evidence-driven requirement |
|---|---|
| Contract/spec | Separate intent, family, exact model, effort, delivery/quota route and actual harness; define pinning, independence, capability evidence and plan-scoped D8 precedence. Settle token spelling there; this report introduces no grammar. |
| Resolver/policy | Resolve ordinary family aliases against actual harness; preserve qualified pins, pairwise reviewer independence, concrete route failures and scoped planner/JIT/replan overrides. Never provider-wide quota-probe. |
| Installer | Add Copilot profiles using its actual schema and repo-instruction opt-in; preserve role boundaries and idempotent ownership. Use documented shared skill discovery rather than speculative global config edits. |
| Runner | Keep IO in command modules; exact argv/effort/final-reply handling, bounded diagnostics and conditional external enablement; controlled tests before implementation. Copilot external capability stays disabled without a demonstrated entrypoint. |
| Kit/orchestration | Dispatch only through exposed native controls or demonstrated external routes; handle configured/actual mismatch and D8 on every planner/exec/review action; retain separate verifier invocation. |
| Browser/visual | Require usable navigate/snapshot evidence on the selected harness surface; metadata, an installed browser, login flow or mocked screenshot cannot enable visual verification. Currently disabled. |

Do not block mandatory installer/contract work merely because optional live evidence is absent. Do block/replan any later mandatory behavior that would require guessed native fields, unsupported pinned settings, unavailable required independent routes, or a visual operation without a usable surface.

## Verification

Research artifacts have no test-first implementation requirement per the brief. The existing controlled tests and probe were used without product changes. Final repository checks and exact totals are recorded in `verification.txt`.

