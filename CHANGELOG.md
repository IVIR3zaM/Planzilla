# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-27

### Added

- Copilot CLI is a delivery route: `plz run <role> copilot::<model> '<line>'` hands a planner, executor or verifier
  role to Copilot CLI headlessly, and `plz dispatch` can choose it. Planzilla never installs or logs in to the CLI.
- `plz install` writes Copilot CLI agent profiles for the planner, executor and verifier under `.github/agents/`.
- `docs/COPILOT.md` records the Copilot CLI flags, models, authentication and entrypoint behavior that Planzilla
  relies on, with the evidence behind each fact.
- Portable `opus`, `sonnet` and `haiku` intent can be resolved to an exact Copilot model through `plz dispatch`.
- An example capabilities facts file ships with the kit to show the `--facts` format.
- `CHANGELOG.md`, kept in Keep a Changelog format, and a repository rule to update it with every user-visible
  change.

### Changed

- The `plz-new-plan` and `plz-run-plan` skills are rewritten to be shorter and easier to read, with one simple
  rule for dispatching each role.
- The README describes Copilot CLI support both as a harness and as a delivery route.
- `docs/FORMAT.md` §11 lists the Copilot profiles that `plz install` writes, and the README release steps
  include the changelog.
- Review independence is anchored to a completed execution, and the first dispatch of a plan is limited to the
  planner.

### Fixed

- An explicit `low` effort pin is honored instead of being replaced by a portable mapping.
- The `--facts` help of `plz dispatch` describes the file it expects correctly.
- Failures of the external runner report clearer diagnostics, including a hint when Copilot CLI is logged out.

## [0.2.0] - 2026-10-20

### Added

- Codex delivery: models can name a provider route (`codex::<model>`), and a repository config `providers` key
  lists the allowed routes.
- `plz run` launches a role on an external provider CLI, with a `plz-run` adapter agent for Claude Code.
- A `harness` config key names the client in use, and `plz lint` checks the new `providers` and `harness` keys.
- Bare provider tokens such as `codex` or `claude` select that provider's default model.

### Changed

- The planner role and both skills cover provider and model choice.
- `docs/FORMAT.md` and the README describe model tokens, providers and harnesses.

### Removed

- The bootstrap new-plan and run-plan kit used before Planzilla could plan itself.

## [0.1.0] - 2026-10-01

### Added

- First release of Planzilla, a plan-and-run workflow for coding agents driven by the `plz` command line.
- Plans with a state machine, waves of parallel nodes and per-node briefs, with commands to move a plan along:
  `status`, `stats`, `lint`, `next`, `resume`, `set`, `brief`, `log`, `check` and `commit`.
- `plz serve`, a live view of a running plan.
- Planner, executor and verifier roles, and the `plz-new-plan` and `plz-run-plan` skills, installed into a repo
  with `planzilla install`.
- A Homebrew release pipeline for installing the tool.

[Unreleased]: https://github.com/IVIR3zaM/Planzilla/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/IVIR3zaM/Planzilla/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/IVIR3zaM/Planzilla/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/IVIR3zaM/Planzilla/releases/tag/v0.1.0
