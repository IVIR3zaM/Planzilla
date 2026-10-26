# GitHub Copilot CLI evidence

This file records what Planzilla may rely on when it runs GitHub Copilot CLI, either as the harness a person
works in or as an external delivery route that `plz run` and `plz dispatch` launch. It is the source the external
Copilot runner is built from, and `src/planzilla/runner.py` (`build_argv`, `copilot_entry`, `copilot_logged_out`,
`login_hint`) and `src/planzilla/commands/run.py` (the `PATH` lookup and the call) now implement it; FORMAT §9
(`run`) states the resulting argv and exit codes. Delivery is the external CLI only, with no visual agent. The
runner never installs, updates or logs in to the CLI: it uses the `gh copilot --` route only when `gh` already
holds its downloaded CLI, since `gh copilot` would otherwise download one (see `## Entrypoint`).

Evidence was gathered on 2026-10-26 on macOS (darwin, arm64) with GitHub Copilot CLI 1.0.103 and gh 2.103.2.
Each fact is marked:

- `live-verified`: observed on this host, through `--version`, `--help`, a `copilot help <topic>` page, or one of
  the three prompt calls in `## Live calls`.
- `documentation-only`: read in an official page (cited by URL) and not exercised here.

Non-prompt commands used (no prompt sent, no AI credits spent): `copilot --version`, `gh copilot -- --version`,
`copilot --help`, `gh copilot --help`, `copilot login --help`, `copilot version --help`, `copilot config --help`,
`copilot help permissions`, `copilot help environment`, `copilot help billing`, `copilot help config`, and
`copilot config model` (read only). Nothing was installed, no login was made, no Copilot setting was changed, and
no token was printed.

Docs cited (all fetched 2026-10-26):

- [cmd-ref] https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
- [prog-ref] https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference
- [prog-howto] https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically
- [tools] https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools
- [agents] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli
- [instr] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions
- [skills] https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills
- [auth] https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli
- [auth-fix] https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/troubleshoot-copilot-cli-auth
- [install] https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli
- [gh-manual] https://cli.github.com/manual/gh_copilot (the GitHub CLI manual page for `gh copilot`; same text as
  `gh copilot --help`)

## Harness

Copilot CLI as the client a person runs Planzilla inside.

- Custom agents are Markdown files with an `.agent.md` extension; project agents live in `.github/agents/`, user
  agents in `~/.copilot/agents/`, and a user agent wins over a project agent with the same ID. The ID is the file
  name without `.agent.md`. `documentation-only` [agents], [cmd-ref] "Custom agent locations".
- Lookup order when IDs clash: `~/.copilot/agents/`, then `.github/agents/` from the working directory up to the
  Git root, then `.claude/agents/`, then `--add-dir` roots, plugins, and organization agents. A user-level
  `plz-executor.agent.md` therefore shadows the installed profile. `documentation-only` [cmd-ref].
- Profile frontmatter fields that matter here: `description` (required), `tools` (default `["*"]`; any `*` grants
  every tool), `model`, `models`, `modelPolicy` (`"preferred"` default, `"required"` locks dispatch to an authored
  model), `reasoningEffort`, and `include-custom-instructions` (default `false`; a custom agent run as a subagent
  gets no `AGENTS.md`, `CLAUDE.md` or `copilot-instructions.md` unless it is `true`). `documentation-only` [cmd-ref].
- Planzilla's `src/planzilla/kit/agents/copilot/plz-{planner,executor,verifier}.agent.md` set
  `include-custom-instructions: true`, pin no model, and give the verifier no `edit` tool. `live-verified` (files
  in this repo).
- A profile can be started directly with `--agent <agent>`; its `model` outranks `--model`. Help line:
  `--agent <agent>  Specify a custom agent to use`. `live-verified` (help); precedence `documentation-only`
  [prog-ref] "Model precedence".
- Repository instructions loaded by default: `.github/copilot-instructions.md`, `AGENTS.md`, and `CLAUDE.md`, plus
  `@path` includes inside them; `--no-custom-instructions` turns this off. `documentation-only` [instr]; flag
  `live-verified` (help: `--no-custom-instructions  Disable loading of custom instructions from AGENTS.md and
  related files`).
- Project skills are found in `.github/skills`, `.claude/skills` or `.agents/skills`; personal skills in
  `~/.copilot/skills` or `~/.agents/skills`. Planzilla's shared `.agents/skills/` is therefore discovered.
  `documentation-only` [skills].

## Dispatch from the skills

The `plz-run-plan` and `plz-new-plan` skills share one `## Dispatch contract` (FORMAT §14). After the allowlist
check (plan `harnesses`, effective `providers`), each set line's agent and model `<m>` go by the harness the
orchestrator actually runs in (`<role>` is planner, executor or verifier):

- Claude Code, `<m>` is `opus`, `sonnet`, `haiku` or `fable` without `@<effort>`: dispatch the agent natively.
- Claude Code, any other `<m>` (`copilot::<id>` too): dispatch `plz-run` with `Run: <role> <m> · <line>`.
- Codex or Copilot: run `plz run <role> <m> '<line>'` as a shell job. Inside Copilot CLI as the harness, every
  role therefore runs as a shell job.
- `plz-visual` never goes through `plz run`: native in Claude Code with a native `<m>`; anywhere else the run
  stops with `<id>: cannot dispatch plz-visual <m>`. Copilot has no visual agent (see `## Limits`).

Copilot as a delivery route, from any host: `plz run <role> copilot::<model> '<line>'` with an exact Copilot
model id. Its auth check is that call itself (see `## Auth`): a logged-out CLI gives
`error: copilot is not logged in; run copilot login`, and the person logs in.

Advanced, optional: `plz run` exits 3 for a qualified portable token such as `copilot::opus` (see `## Effort`).
Resolve it with `plz dispatch <plan> <role> '<line>' --actual-harness <h> --facts <file> --node <id>`, run as a
shell job, where `<file>` is a copy of `.planzilla/templates/capabilities.json` with each placeholder replaced by
evidence you observed and `"enabled": true` only on routes you have demonstrated. The shipped copilot record
names example model ids only; check each id against your account (see `## Models`).

## Entrypoint

- Lookup for the external route: use `copilot` when it is on `PATH`; otherwise use `gh copilot --` followed by the
  same arguments, but only when `gh` is on `PATH` and its downloaded CLI already exists at
  `$XDG_DATA_HOME/gh/copilot/copilot` (default `~/.local/share/gh/copilot/copilot`); with neither, exit 3. The
  `--` stops `gh` from parsing Copilot flags. Help line: "To prevent `gh` from interpreting flags intended for
  Copilot, use `--` before Copilot flags and args." `live-verified` (`gh copilot --help`).
- `gh copilot` runs the Copilot CLI found on `PATH` when one is installed. When none is installed, it downloads
  the CLI to `~/.local/share/gh/copilot` and runs it. Planzilla must never trigger that download, so it checks for
  the downloaded copy first and treats its absence as "no Copilot CLI". `gh` labels running Copilot through `gh`
  as preview and subject to change. `documentation-only` [gh-manual]; this host was not tested without the CLI.
- On this host, `copilot` is on `PATH`, unlike the plan's context, which said it was not. It is a symlink
  `~/.local/bin/copilot -> ~/.local/share/gh/copilot/copilot`, so it is the copy that `gh` downloaded.
  `copilot --version` and `gh copilot -- --version` both print `GitHub Copilot CLI 1.0.103.` `live-verified`.
- Other documented installs (npm `@github/copilot`, Homebrew cask `copilot-cli`, WinGet, install script) all
  provide a `copilot` executable. `documentation-only` [install].
- `-C <directory>  Change working directory before doing anything else` sets the session directory. That
  directory is also the root that path checks allow (see `## Tools`). `live-verified` (help).
- Auto-update: by default the CLI may download newer versions and run them.
  `--no-auto-update  Disable downloading CLI updates automatically` stops this. All three live calls used it.
  `live-verified` (help, `copilot help environment`).

## Prompt

- Headless prompt: `-p, --prompt <text>  Execute a prompt in non-interactive mode (exits after completion)`.
  `live-verified` (help, live calls 1 to 3).
- A prompt may also be piped on stdin (`echo "..." | copilot`). Piped input is ignored when `-p` is given.
  `documentation-only` [prog-howto].
- `-s, --silent  Output only the agent response (no stats), useful for scripting with -p`. Flag
  `live-verified` (help, live call 1 parsed it); its output shape is `documentation-only` [prog-ref]: "Suppress
  stats and decoration, outputting only the agent's response."
- `--no-ask-user  Disable the ask_user tool (agent works autonomously without asking questions)`; the docs
  recommend it for scripts. `live-verified` (help, live calls 1 to 3) and [prog-howto].
- `--output-format <format>`: `text` (default) or `json` (JSONL, one JSON object per line). `live-verified`
  (help); not used in a live call.
- Recommended headless shape:
  `copilot -p <prompt> -s --no-ask-user --no-auto-update [--model <id>] [--reasoning-effort <level>] <tool flags>`.
  Built from the help lines above and [prog-howto] ("Use `-s` (silent) when capturing output", "Use
  `--no-ask-user`", "Set a model explicitly with `--model`").

## Models

- `--model <model>  Set the AI model to use (use 'auto' to let Copilot pick automatically)`. `live-verified`
  (help).
- Model precedence, highest first: the custom agent's `model`, `--model`, the `COPILOT_MODEL` environment
  variable, `model` in `~/.copilot/settings.json`, then the CLI default. `documentation-only` [prog-ref].
- Ids the live calls observed:
  - `auto` answered (live call 3, exit 0). `auto` is also the effective default on this account: live call 2 set
    no `--model` and the error named `Model "auto"`. `live-verified`.
  - `claude-haiku-4.5` was rejected on this account: `Error: Model "claude-haiku-4.5" from --model flag is not
    available.`, exit 1 (live call 1). Being named by docs or help does not make a model available; which models
    work depends on the account's plan and policy. `live-verified`.
- Ids named by `copilot help config` under the `model` setting: `claude-sonnet-5.5`, `claude-sonnet-5`,
  `claude-fable-5.1`, `claude-fable-5`, `claude-opus-5.5`, `claude-opus-5`, `claude-opus-4.8`,
  `claude-opus-4.8-fast`, `claude-sonnet-4.6`, `claude-haiku-5.5`, `claude-haiku-4.5`, `gpt-6.1-sol`, `gpt-6-sol`,
  `gpt-6-luna`, `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`,
  `gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5-mini`, `mai-code-1.1-flash`, `gemini-4-argon`, `gemini-3.8-flash`,
  `gemini-3.7-flash`, `grok-4.7`, `grok-4.6`, `grok-4.5`, `kimi-k3`. These names were read from help; except for
  `claude-haiku-4.5` (rejected above), whether this account can use them is not verified. The docs list a smaller
  table with `claude-sonnet-5.5` marked as the default. `documentation-only` [cmd-ref] "Supported models".
- In text mode without `-s`, the stats block on stderr has no model line (live call 3), although [prog-ref] says
  the model is shown when `-s` is not used. The model that `auto` resolved to is therefore not observable from a
  text reply. `live-verified`.

Smoke model: auto

## Effort

- `--reasoning-effort <level>  Set the reasoning effort level [possible values: none, minimal, low, medium, high,
  xhigh, max]`. `live-verified` (help).
- The docs list `--effort=LEVEL` and `--reasoning-effort=LEVEL` with the values `low`, `medium`, `high`, `xhigh`,
  `max`; `max` is the highest tier for Anthropic models. `documentation-only` [cmd-ref]. `none` and `minimal`
  appear only in the 1.0.103 help.
- Planzilla's copilot effort list is the flag's own: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`.
  The flag parser accepts all of them; whether a given model accepts one is up to that model.
- The CLI validates effort against the model before any request is sent: `Error: Model "auto" does not support
  reasoning effort configuration (requested: "low").`, exit 1, empty stdout (live call 2). `live-verified`.
  So `auto` must be called without an effort, and a pinned effort needs an exact model id that supports it.
  Planzilla therefore exits 3 before any subprocess for an effort on a bare `copilot` (its default is `auto`), and
  never passes `--reasoning-effort` without an exact `--model`. Qualified portable aliases (`copilot::opus`) exit
  3 too: a Copilot model id is needed, resolved by `plz dispatch` or named by the caller.
- A profile can set `reasoningEffort`, and settings can set `effortLevel`. `documentation-only` [cmd-ref],
  [prog-ref].

## Auth

- No status subcommand: the 1.0.103 command list (`app`, `login`, `help`, `init`, `config`, `update`, `version`,
  `workflow`, `sessions`, `memories`, `plugin`, `mcp`, `skill`, `instruction`, `lsp`, `sandbox`, `completion`)
  has no auth status, and `copilot login --help` offers only `--host`, `--device-code`, `--web-flow` and
  `--with-token`. `live-verified` (help). `copilot version` makes a network request to check for updates, so it is
  not an auth check either. `live-verified` (`copilot version --help`).
- `gh auth status` checks only the lowest-priority credential source (the `gh` token fallback), so it cannot
  answer whether Copilot is logged in. `documentation-only` [auth] (credential order: `COPILOT_GITHUB_TOKEN`,
  `GH_TOKEN`, `GITHUB_TOKEN`, OAuth token in the system keychain, then `gh auth token`).
- Auth check, therefore: the prompt call itself.
  - Logged in: the call runs; live call 3 exited 0 and printed the reply. `live-verified`.
  - Logged out: the CLI prints `Error: No authentication information found` and then `Copilot can be authenticated
    with GitHub using an OAuth Token or a Fine-Grained Personal Access Token`. `documentation-only` [auth-fix].
    The stream and exit code are not documented; live calls 1 and 2 show that CLI errors go to stderr with exit 1.
    So the runner should treat a nonzero exit whose stderr contains `No authentication information found` as
    logged out, and print the login hint `copilot login` (or `gh copilot -- login` on the `gh` route). Other
    documented auth failures: `401 Unauthorized` (token revoked), `403 Forbidden` or a policy denial (license or
    org policy). `documentation-only` [auth-fix].
- Login (`copilot login`, OAuth browser or device flow) is a person's step. The runner never runs it.
  `live-verified` (`copilot login --help`).

## Tools

How tool flags work (help lines and `copilot help permissions`, `live-verified`; semantics `documentation-only`
[tools], [cmd-ref] "Tool availability values", "Tool permission patterns"):

- `--available-tools [<tools>...]  Only these tools will be available to the model` and
  `--excluded-tools [<tools>...]` decide which tools the model can see. When both are given, `--available-tools`
  wins.
- `--allow-tool [<tools>...]` and `--deny-tool [<tools>...]` approve or deny without a prompt. Patterns have the
  form `kind(argument)` with kinds `shell`, `write`, `read`, `url`, `memory` and MCP server names. Deny rules beat
  allow rules, even `--allow-all-tools`. Several values go in one quoted, comma-separated argument.
- Tool names: `bash`, `read_bash`, `write_bash`, `stop_bash`, `list_bash` (shell); `view`, `create`, `edit`,
  `apply_patch` (files); `glob`, `grep`; `task`, `list_agents`, `read_agent`, `write_agent` (subagents); `skill`,
  `web_fetch`, `ask_user`.
- `write` covers file tools but not shell. Help: "To allow all shell redirections, set --allow-all-tools." Without
  that flag, shell redirections are not auto-approved.
- Paths: by default file access is limited to the working directory and its subdirectories plus the system temp
  directory. `--allow-all-paths  Disable file path verification and allow access to any path`.
- `--allow-all-tools` is described in help as "required for non-interactive mode". The docs instead run `-p` with
  only `--allow-tool`, for example `copilot -p "..." -s --allow-tool='shell(npm:*), write' --no-ask-user`
  [prog-howto]. The live calls needed no tool, so it is not verified here whether per-tool flags alone let a
  headless role use its tools. `documentation-only`.
- `--allow-all`, `--yolo` and `--allow-all-urls` add path and URL bypasses; Planzilla never uses them.
- `--disable-builtin-mcps  Disable all built-in MCP servers (currently: github-mcp-server, githubiq)` removes the
  GitHub API tools that no role needs. `live-verified` (help).

Least-privilege set per role (the `tools` argv part after the common flags). It uses per-tool flags and never
`--allow-all-paths`, `--allow-all-tools`, `--allow-all`, `--yolo` or `--allow-url`:

| role | flags |
| --- | --- |
| planner | `--available-tools=bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep,create,edit,apply_patch` `--allow-tool=read,write,shell` `--deny-tool=shell(git push)` `--disable-builtin-mcps` |
| executor | `--available-tools=bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep,create,edit,apply_patch` `--allow-tool=read,write,shell` `--deny-tool=shell(git push),shell(git commit)` `--disable-builtin-mcps` |
| verifier | `--available-tools=bash,read_bash,write_bash,stop_bash,list_bash,view,glob,grep` `--allow-tool=read,shell` `--deny-tool=write,shell(git push),shell(git commit)` `--disable-builtin-mcps` |

- The verifier gets no file-writing tool (`create`, `edit` and `apply_patch` are hidden) and a `write` deny. Like
  the Claude verifier (`Read,Grep,Glob,Bash`), it keeps shell so it can run the Verify command and `.planzilla/plz
  log`.
- These sets mirror `_CLAUDE_TOOLS` in `src/planzilla/runner.py`. The git denials follow the role rule "never
  commit, stage, push" for executors, and "never push" for every role.
- `documentation-only`: assembled from the cited semantics and not run with tools on this host. If the first live
  role run shows that per-tool flags cannot run a headless role, the fallback is `--allow-all-tools` plus the same
  `--available-tools` and `--deny-tool` lists. Denials still apply under it.

## Reply

- stdout carries only the agent's reply text. Live call 3 (no `-s`) printed `PLZ-OK` plus a trailing blank line on
  stdout. `live-verified`.
- stderr carries the stats block even without `-s`: blank lines, then `Changes`, `AI Credits <n> (<seconds>s)`,
  `Tokens ...`, and `Resume copilot --resume=<session-id>` (live call 3). CLI errors also go to stderr as
  `Error: ...` (live calls 1 and 2). `live-verified`. With `-s` the stats are suppressed; error and status
  diagnostics may still appear on stderr. `documentation-only` [prog-ref], [cmd-ref].
- Capture rule: take the last non-blank line of stdout (the same rule as `last_line` in `runner.py`). On failure,
  report the last non-blank stderr line.
- Exit codes: `0` when the prompt completed (live call 3); `1` for an unavailable model and for an effort the model
  does not support (live calls 1 and 2). `live-verified`. The docs give exit codes only for `copilot workflow run`
  (`0`, `1`, `2`, `130` on SIGINT or SIGTERM); prompt-mode codes are not documented. `documentation-only`
  [prog-ref] "Workflow exit codes".
- Failures as the runner prints them, through `plz run` and `plz dispatch` alike: exit 3, one `error: ...` line on
  stderr, nothing on stdout, never a handoff (a handoff is only a selection outcome): no entrypoint
  (`copilot not found on PATH (nor a Copilot CLI already downloaded by gh)`), logged out (`copilot is not logged in;
  run copilot login`, or `gh copilot -- login`), nonzero exit (`copilot exited <code>[: <last stderr line>]`), empty
  reply (`copilot gave an empty reply`).
- `--output-format json` gives JSONL on stdout for machine parsing. `documentation-only` [prog-ref].

## Limits

- No visual agent: the tool list has no browser, screenshot or page-inspection tool (only `web_fetch`, which
  Planzilla's role sets exclude). `--attachment` only attaches an image or document to the initial prompt.
  Planzilla ships no Copilot visual profile. Visual nodes must not be routed to Copilot. `documentation-only`
  [cmd-ref] "Tool availability values"; `live-verified` (help `--attachment`, kit contents).
- Each prompt-mode call saves a resumable session (the `Resume` line in live call 3). No help flag turns this off;
  `--session-id` only chooses the id. `live-verified` (help, live call 3).
- `auto` reports no resolved model id in text mode and accepts no effort (see `## Models`, `## Effort`).
  `live-verified`.
- Model availability depends on the account (live call 1). A pinned id must be checked against the account, not
  against docs or help lists. `live-verified`.
- Each call spends AI credits (live call 3 reported `AI Credits 0.25`). `--max-ai-credits <credits>` sets a soft
  limit per response. `live-verified` (help, live call 3).
- Org or enterprise policy can block Copilot CLI or the allow-all flags
  (`permissions.disableBypassPermissionsMode`). `documentation-only` [install], [cmd-ref].
- The `gh copilot --` route is preview and downloads the CLI when `gh` has none, so Planzilla uses it only when
  the downloaded copy already exists (see `## Entrypoint`). `documentation-only` [gh-manual].
- Whether per-tool flags are enough for a headless role is not proven here (see `## Tools`).
  `documentation-only`.

## Live calls

Each call ran from a fresh `mktemp -d` directory outside the repo, with stdout and stderr captured to separate
files. The session id is replaced by `<session-id>`.

1. argv: `copilot -p 'Reply with exactly the one line PLZ-OK and nothing else.' -s --model claude-haiku-4.5
   --no-ask-user --no-auto-update`. Exit code `1`. stdout empty; stderr one line:
   `Error: Model "claude-haiku-4.5" from --model flag is not available.`
2. argv: `copilot -p 'Reply with exactly the one line PLZ-OK and nothing else.' --reasoning-effort low
   --no-ask-user --no-auto-update`. Exit code `1`. stdout empty; stderr one line:
   `Error: Model "auto" does not support reasoning effort configuration (requested: "low").`
3. argv: `copilot -p 'Reply with exactly the one line PLZ-OK and nothing else.' --model auto --no-ask-user
   --no-auto-update`. Exit code `0`. stdout `PLZ-OK` and a newline (8 bytes); stderr is the stats block (blank
   lines, `Changes +0 -0`, `AI Credits 0.25 (9s)`, `Tokens ↑ 27.9k (9.0k cached, 18.9k written) • ↓ 28 (18
   reasoning)`, `Resume copilot --resume=<session-id>`).
