# Homebrew release pipeline
status: RUNNING
created: 2026-10-01 · updated: 2026-10-01
goal: pushing a vX.Y.Z tag tests, releases and publishes a brew-tested planzilla formula to IVIR3zaM/homebrew-tap
verify: uv run ruff check . && uv run ruff format --check . && uv run pytest -q
commit: per-node
push: per-node
budgets: 2 tries per brief · 2 replans per node
tier: M

## Intent

Goal: Make a tag push the whole release path for Planzilla: the repo's tests and lint pass, a GitHub release
carries the sdist and wheel, and a formula that has really been installed, tested and audited by Homebrew on
macOS lands in the tap IVIR3zaM/homebrew-tap, so `brew install IVIR3zaM/tap/planzilla` works. Then cut v0.1.0.

In scope: a stdlib launcher formula (package in libexec, `planzilla` and `plz` wrappers on python@3.13) in
release/planzilla.rb.tmpl, with release/render_formula.py (URL and SHA256 only) and its tests to match; one
Release workflow with a test/build job, a macOS brew job used as a dry run on pushes and PRs touching the
release files and as the required gate on tags, and a tags-only publish job; a one-line README install edit;
opening the PR into main once the workflow is pushed, so the dry run also runs on the PR; and the first
release, v0.1.0, after a human gate.

Out of scope: editing the tap repo from this session (it is read-only here; only the workflow writes to it), the
tap README, PyPI or any other package manager, bumping the version (it stays 0.1.0), and any pre-authorization
in .plan/config.md.

Constraints: AGENTS.md rules: strict TDD for code in release/, stdlib only at runtime, ruff, type hints, Write
paths only, no commits by agents. Workflow YAML cannot run here, so its local criteria are parse and grep checks
and its macOS behaviour is proven by the branch's push and PR dry-run runs on GitHub (N06). GitHub is driven
through `gh api` REST only. The PR is merged and v0.1.0 tagged only after the human's gate: by the human, or by
the run on the human's go-ahead given at that gate. The tap is written only by the publish job with the
HOMEBREW_TAP_TOKEN secret, after the brew job passes. Decisions D1-D9.

Definition of done: verify passes; the Release dry runs for the branch push and for the PR, macOS brew job
included, are green on GitHub; after the human gate the PR is merged, tag v0.1.0 points at the merged main
commit, the v0.1.0 Release run succeeded, the GitHub release v0.1.0 holds the sdist and wheel, and
Formula/planzilla.rb in the tap points at v0.1.0's sdist url with its sha256.

## Decisions

- D1 The formula drops virtualenv_install_with_resources: install copies src/planzilla (with kit/) into libexec and writes bin/planzilla and bin/plz wrappers that exec python@3.13 `-m planzilla` with libexec on PYTHONPATH (the idea of .planzilla/plz); keeps `depends_on "python@3.13"`, license, desc, homepage and `test do` on `planzilla --version`; no `version` line (derived from the url) | confirmed
- D2 render_formula.py takes only URL and SHA256 (`render(url, sha256)`, CLI `render_formula.py URL SHA256`); the VERSION argument is dropped and the version comes from the url | confirmed
- D3 One workflow, .github/workflows/release.yml (name Release), jobs `build` (ubuntu: uv sync, ruff check, ruff format --check, pytest, tag = v__version__ on tags, uv build, upload dist) → `brew` (macos-latest, local tap, install --build-from-source, brew test, brew audit --strict) → `publish` (tags only); triggers: tags v*, plus branch pushes and pull_requests touching release/** or the workflow file | confirmed
- D4 The brew gate installs the locally built sdist (file:// url, the same bytes later uploaded) before any release exists; publish then creates the release, downloads the uploaded sdist back, fails unless its sha256 equals the gated one, renders the formula with the release download url and pushes it to the tap | confirmed
- D5 The release's own tests and lint run once on Python 3.13 inside the build job; ci.yml keeps the 3.10-3.13 matrix on every push | confirmed
- D6 README: only the Homebrew comment line of the Install section changes, to say the formula uses python@3.13 (both `planzilla` and `plz` are already stated) | confirmed
- D7 Work branch is claude/tender-davinci-ej9m0c; each node's commit is pushed (config push per-node), so the dry run runs on the push of N03's commit, and N06 checks that run and the PR's run | confirmed
- D8 After N03's commit is pushed, N05 opens the PR from claude/tender-davinci-ej9m0c into main through `gh api` REST, so the Release dry run also runs on the PR. At gate N07 the human either merges the PR and pushes tag v0.1.0 themselves, or tells the orchestrator in chat to do it; approving N07 is that go-ahead, and only then N08 merges the PR (if still open, once its checks are green) and pushes tag v0.1.0 (if absent). Nothing is pre-authorized in .plan/config.md | confirmed
- D9 N07 human gate: the human adds the HOMEBREW_TAP_TOKEN secret (Contents read/write on IVIR3zaM/homebrew-tap); the PR is merged and tag v0.1.0 pushed from the merged main commit (by the human, or by N08 on the human's go-ahead, D8); publish pushes Formula/planzilla.rb straight to the tap's default branch as github-actions[bot], as release.yml:47-59 does | confirmed

## Graph

| id | title | type | deps | model | try | rp | status | note |
|----|-------|------|------|-------|-----|----|--------|------|
| N01 | preflight | check | - | -/- | 1 | 0 | DONE | |
| N02 | stdlib launcher formula | exec | N01 | sonnet/sonnet | 0 | 0 | TODO | |
| N03 | release workflow with brew gate | exec | N02 | opus/opus | 0 | 0 | TODO | |
| N04 | README install line | exec | N02 | haiku/haiku | 0 | 0 | TODO | |
| N05 | open PR into main | exec | N03 | sonnet/haiku | 0 | 0 | TODO | |
| N06 | dry runs green on GitHub | check | N05 | -/sonnet | 0 | 0 | TODO | |
| N07 | tap secret and release go-ahead | gate | N04,N06 | -/- | 0 | 0 | TODO | |
| N08 | merge PR and tag v0.1.0 | exec | N07 | sonnet/- | 0 | 0 | TODO | |
| N09 | plan acceptance | check | N08 | -/sonnet | 0 | 0 | TODO | |

## N01 preflight
Do: Confirm the starting point: verify passes on the untouched tree; gh is authenticated with push rights on
IVIR3zaM/Planzilla and can read Actions runs, releases and pull requests over REST; git can push the work
branch and tag v0.1.0 does not exist yet; the tap and GitHub release downloads are reachable read-only; ruby and
PyYAML exist for the local formula and YAML checks.
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `gh api repos/IVIR3zaM/Planzilla --jq .permissions.push | grep -qx true`
- C3 [cmd] `gh api 'repos/IVIR3zaM/Planzilla/actions/runs?per_page=1' --jq .total_count | grep -qE '^[0-9]+$' && gh api repos/IVIR3zaM/Planzilla/releases --jq length && gh api 'repos/IVIR3zaM/Planzilla/pulls?state=all&head=IVIR3zaM:claude/tender-davinci-ej9m0c' --jq length`
- C4 [cmd] `test "$(git branch --show-current)" = claude/tender-davinci-ej9m0c && git push --dry-run origin HEAD`
- C5 [cmd] `git ls-remote https://github.com/IVIR3zaM/homebrew-tap HEAD | grep -q HEAD && curl -fsS -o /dev/null https://raw.githubusercontent.com/IVIR3zaM/homebrew-tap/HEAD/Formula/cairn.rb`
- C6 [cmd] `curl -fsS -o /dev/null https://github.com/IVIR3zaM/Planzilla/releases`
- C7 [cmd] `ruby --version && python3 -c "import yaml"`
- C8 [cmd] `test -z "$(git ls-remote origin refs/tags/v0.1.0)"`

## N02 stdlib launcher formula
Do: Rewrite the Homebrew formula template as a stdlib launcher and make render_formula.py match, test first.
The install copies the sdist's src/planzilla package (kit/ included) into libexec and writes two executables,
bin/planzilla and bin/plz, that exec python@3.13's interpreter with `-m planzilla` and pass all arguments
through, with libexec on PYTHONPATH; no virtualenv, pip or resources. Drop the `version` line and the
Virtualenv include; keep desc, homepage, url, sha256, license, `depends_on "python@3.13"` and the
`test do` on `planzilla --version`. render() and main() take only URL and SHA256.
Context: D1 formula shape (above); D2 `render(url, sha256)`, CLI `render_formula.py URL SHA256`, exit 2 with a
usage line on a wrong argument count or a sha that is not 64 hex chars, sha lowercased. Current template
release/planzilla.rb.tmpl:1-20, renderer release/render_formula.py:13-29, tests tests/test_render_formula.py:19-51;
launcher idea .planzilla/plz:1-12; src/planzilla/__main__.py exists so `-m planzilla` runs the CLI.
Read: `release/planzilla.rb.tmpl`, `release/render_formula.py`, `tests/test_render_formula.py`, `.planzilla/plz`
Write: `release/planzilla.rb.tmpl`, `release/render_formula.py`, `tests/test_render_formula.py`
Test first: tests assert the rendered formula has url and sha256 once each, no placeholder, no `version` line,
no virtualenv, `depends_on "python@3.13"`, libexec install, wrappers for both planzilla and plz using
`-m planzilla`, and a `test do` on `--version`; main takes two args; see them fail before editing release/.
Done when:
- C1 [cmd] `uv run pytest -q tests/test_render_formula.py`
- C2 [cmd] `python3 release/render_formula.py https://github.com/IVIR3zaM/Planzilla/releases/download/v0.1.0/planzilla-0.1.0.tar.gz "$(python3 -c 'print("a"*64)')" | ruby -c`
- C3 [cmd] `! grep -niE 'virtualenv|^ *version "|@VERSION@' release/planzilla.rb.tmpl && grep -q 'depends_on "python@3.13"' release/planzilla.rb.tmpl && grep -q 'libexec' release/planzilla.rb.tmpl`
- C4 [cmd] `python3 release/render_formula.py 1.2.3 u "$(python3 -c 'print("a"*64)')"; test $? -eq 2`
- C5 [review] The template's install puts src/planzilla under libexec and creates bin/planzilla and bin/plz
  that run python@3.13 (via the dependency's opt path) with `-m planzilla "$@"` and libexec on PYTHONPATH;
  nothing in it needs pip, hatchling or network; render_formula.py has type hints and stdlib imports only.
- C6 [cmd] `uv run pytest -q`

## N03 release workflow with brew gate
Do: Rewrite .github/workflows/release.yml (keep `name: Release`) into three jobs with these exact ids and no
`name:` keys. `build` (ubuntu-latest, uv on Python 3.13): uv sync, ruff check, ruff format --check, pytest; on
tag refs only, fail unless the tag is v + planzilla.__version__; uv build; upload dist/ as an artifact.
`brew` (macos-latest, needs build): download dist, render the formula with release/render_formula.py using the
sdist's file:// url and its sha256, put it in a throwaway local tap made with `brew tap-new` (never the real
tap), then `brew install --build-from-source`, `brew test` and `brew audit --strict` on it. `publish` (needs
brew, runs only for refs/tags/v*): create the GitHub release with the dist sdist and wheel, download the
uploaded sdist back and fail unless its sha256 equals the dist one, render with
https://github.com/IVIR3zaM/Planzilla/releases/download/<tag>/planzilla-<version>.tar.gz and push
Formula/planzilla.rb to IVIR3zaM/homebrew-tap with HOMEBREW_TAP_TOKEN (fail clearly if the secret is empty).
Context: D2 CLI is `render_formula.py URL SHA256`. D3 single workflow; triggers: push tags v*, push branches
'**' with paths release/** and .github/workflows/release.yml (GitHub ignores paths for tag pushes), and
pull_request with the same paths. D4 gate on the local sdist before any release exists. D5 tests/lint once on
3.13 here. D9 tap push as release.yml:47-59 (bot identity, no-op when unchanged). Workflow-level permissions
`contents: read`; only publish gets `contents: write`; the token appears only in publish. Current file
.github/workflows/release.yml:1-59; ci.yml:18-25 shows the uv steps.
Read: `.github/workflows/release.yml`, `.github/workflows/ci.yml`, `release/render_formula.py`, `release/planzilla.rb.tmpl`
Write: `.github/workflows/release.yml`
Test first: -
Done when:
- C1 [cmd] `python3 -c "import yaml; j=yaml.safe_load(open('.github/workflows/release.yml'))['jobs']; assert sorted(j)==['brew','build','publish']; assert j['brew']['runs-on']=='macos-latest' and 'build' in str(j['brew']['needs']); assert 'brew' in str(j['publish']['needs']) and 'refs/tags/v' in j['publish']['if']"`
- C2 [cmd] `python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/release.yml')); o=d[True]; p={'release/**','.github/workflows/release.yml'}; assert d['name']=='Release' and o['push']['tags']==['v*'] and 'branches' in o['push'] and p<=set(o['push']['paths']) and p<=set(o['pull_request']['paths'])"`
- C3 [cmd] `f=.github/workflows/release.yml; grep -q 'brew audit --strict' $f && grep -q 'brew test' $f && grep -q -- '--build-from-source' $f && grep -q 'brew tap-new' $f && grep -q 'ruff format --check' $f && grep -q 'pytest' $f && grep -q 'render_formula.py' $f`
- C4 [review] The file does what Do says, in that order: the tag/version check and every tap or release write
  happen only on tags; publish cannot start unless brew succeeded; the brew job installs, tests and audits the
  rendered formula, not a hand-written one; HOMEBREW_TAP_TOKEN and `contents: write` appear only in publish;
  the published formula uses the release url and the sha256 checked against the uploaded asset.
- C5 [cmd] `uv run pytest -q`

## N04 README install line
Do: In the README Install section, change only the Homebrew comment line so it says the formula installs
planzilla with python@3.13; keep the three install commands and the rest of the file unchanged.
Context: D6 one-line edit. README.md:23-38 is the Install section; README.md:25 already says every method gives
both `planzilla` and `plz`; the formula (release/planzilla.rb.tmpl) depends on python@3.13.
Read: `README.md`, `release/planzilla.rb.tmpl`
Write: `README.md`
Test first: -
Done when:
- C1 [cmd] `grep -qF 'brew install IVIR3zaM/tap/planzilla' README.md && sed -n 23,40p README.md | grep -q 'python@3.13'`
- C2 [cmd] `test "$(git diff --numstat -- README.md | cut -f1,2)" = "$(printf '1\t1')"`
- C3 [cmd] `uv run pytest -q`

## N05 open PR into main
Do: Open one pull request in IVIR3zaM/Planzilla from claude/tender-davinci-ej9m0c into main, not a draft,
through `gh api` REST (POST repos/IVIR3zaM/Planzilla/pulls), unless one is already open; reuse an open one.
Title: `Homebrew release pipeline`. Body: a short summary of the four changes (stdlib launcher formula and
renderer, Release workflow with build, macOS brew gate and tags-only publish, README install line), a line
saying merging and tagging v0.1.0 wait for the human gate, and any PR footer your session instructions require.
Change no files; do not merge, tag, push, or touch the tap or any secret.
Context: D8 the PR is opened now so the Release dry run also runs on it; merging waits for gate N07. N03's
commit is already pushed (push per-node). D3: release.yml triggers on pull_request with paths release/** and
.github/workflows/release.yml, so opening the PR starts a Release run. GraphQL is blocked, so `gh pr create`
fails; use `gh api` with `-f head=claude/tender-davinci-ej9m0c -f base=main`.
Write: -
Test first: -
Done when:
- C1 [cmd] `test "$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=open&base=main&head=IVIR3zaM:claude/tender-davinci-ej9m0c' --jq length)" = 1`
- C2 [cmd] `for i in $(seq 18); do n=$(gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=pull_request&branch=claude/tender-davinci-ej9m0c' --jq '[.workflow_runs[]|select(.name=="Release")]|length'); [ "$n" -ge 1 ] && break; sleep 10; done; [ "$n" -ge 1 ]`
  waits up to 3 minutes for the PR's Release run to appear.
- C3 [review] The open PR (`gh api 'repos/IVIR3zaM/Planzilla/pulls?state=open&base=main&head=IVIR3zaM:claude/tender-davinci-ej9m0c'`)
  is not a draft, its title is `Homebrew release pipeline`, and its body summarises the four changes and
  says merging and tagging v0.1.0 wait for the human gate.
- C4 [cmd] `uv run pytest -q`

## N06 dry runs green on GitHub
Do: Confirm on GitHub that the Release dry runs completed green: the push run for the N03 commit (the last
commit touching release/ or the workflow) and the latest pull_request run of the PR. In both, build and brew
succeeded and publish was skipped; in the push run every brew step succeeded. C1 and C4 each wait up to 14 minutes.
Context: D3 job ids build, brew, publish; D4 brew gates on the local sdist; D7 branch
claude/tender-davinci-ej9m0c, pushed per node; D8 the PR was opened by N05. Use only `gh api` REST.
Done when:
- C1 [cmd] `sha=$(git log -1 --format=%H -- release .github/workflows/release.yml); for i in $(seq 84); do s=$(gh api "repos/IVIR3zaM/Planzilla/actions/runs?head_sha=$sha&event=push" --jq '[.workflow_runs[]|select(.name=="Release")][0]|.status+" "+(.conclusion//"")'); [ "${s%% *}" = completed ] && break; sleep 10; done; test "$s" = "completed success"`
- C2 [cmd] `sha=$(git log -1 --format=%H -- release .github/workflows/release.yml); id=$(gh api "repos/IVIR3zaM/Planzilla/actions/runs?head_sha=$sha&event=push" --jq '[.workflow_runs[]|select(.name=="Release")][0].id'); gh api repos/IVIR3zaM/Planzilla/actions/runs/$id/jobs --jq '[.jobs[]|.name+"="+.conclusion]|sort|join(" ")' | grep -qx 'brew=success build=success publish=skipped'`
- C3 [cmd] `sha=$(git log -1 --format=%H -- release .github/workflows/release.yml); id=$(gh api "repos/IVIR3zaM/Planzilla/actions/runs?head_sha=$sha&event=push" --jq '[.workflow_runs[]|select(.name=="Release")][0].id'); test "$(gh api repos/IVIR3zaM/Planzilla/actions/runs/$id/jobs --jq '[.jobs[]|select(.name=="brew")|.steps[].conclusion]|unique|join(" ")')" = success`
- C4 [cmd] `for i in $(seq 84); do r=$(gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=pull_request&branch=claude/tender-davinci-ej9m0c' --jq '[.workflow_runs[]|select(.name=="Release")][0]|"\(.id) \(.status) \(.conclusion)"'); [ "$(echo "$r" | cut -d' ' -f2)" = completed ] && break; sleep 10; done; test "${r#* }" = "completed success" && gh api repos/IVIR3zaM/Planzilla/actions/runs/${r%% *}/jobs --jq '[.jobs[]|.name+"="+.conclusion]|sort|join(" ")' | grep -qx 'brew=success build=success publish=skipped'`
- C5 [review] The push run's brew job log (`gh api repos/IVIR3zaM/Planzilla/actions/jobs/<job id>/logs`) shows
  the formula installed from a file:// url, `brew test` running `planzilla --version` with 0.1.0, and
  `brew audit --strict` reporting no problems.

## N07 tap secret and release go-ahead
Do: The human takes the outward-facing release decision no agent may take alone: add the tap token secret,
then either merge the PR into main and push tag v0.1.0 from the merged main commit themselves, or approve this
gate as the go-ahead for N08 to merge the PR and push tag v0.1.0 now. Approving means the release may be cut.
Context: D8 approving this gate is the human's chat go-ahead; nothing is pre-authorized in config. D9
HOMEBREW_TAP_TOKEN is a token with Contents read/write on IVIR3zaM/homebrew-tap only; the version is already
0.1.0 (src/planzilla/__init__.py:3), so the tag must be v0.1.0 or the build job fails.
Done when:
- C1 [human] Repository secret HOMEBREW_TAP_TOKEN exists in IVIR3zaM/Planzilla and can push to IVIR3zaM/homebrew-tap.
- C2 [human] The PR's CI and Release (dry run) checks are green, and the human has either merged it and pushed
  tag v0.1.0 from the merged main commit, or tells the orchestrator to have N08 merge it and push v0.1.0 now.

## N08 merge PR and tag v0.1.0
Do: Finish whatever of the release cut is still missing, on the human's go-ahead given at gate N07. If the PR
from claude/tender-davinci-ej9m0c into main is still open: wait up to 15 minutes for every check run on its
head commit to complete; merge it through REST (`gh api -X PUT repos/IVIR3zaM/Planzilla/pulls/<n>/merge -f
merge_method=merge`) only if all are success or skipped, otherwise reply BLOCKED. Then, if tag v0.1.0 is absent
on origin, fetch origin main, tag v0.1.0 at the PR's merge commit and `git push origin v0.1.0`; if it exists at
another commit, reply BLOCKED. Never move, delete or force-push a tag or branch; change no files; never touch the
tap, secrets or the GitHub release (the tag's Release run does those).
Context: D8 approving N07 is the go-ahead; skip each step the human already did. D9 the tag must point at the
merged main commit; version 0.1.0 at src/planzilla/__init__.py:3. GraphQL is blocked, so `gh pr merge` fails;
use `gh api` REST only.
Write: -
Test first: -
Done when:
- C1 [cmd] `test "$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=closed&base=main&head=IVIR3zaM:claude/tender-davinci-ej9m0c' --jq '[.[]|select(.merged_at!=null)]|length')" = 1`
- C2 [cmd] `h=$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=closed&base=main&head=IVIR3zaM:claude/tender-davinci-ej9m0c' --jq '[.[]|select(.merged_at!=null)][0].head.sha'); gh api "repos/IVIR3zaM/Planzilla/commits/$h/check-runs?per_page=100" --jq '[.check_runs[].conclusion]|unique|join(" ")' | grep -qxE '(skipped )?success'`
- C3 [cmd] `m=$(gh api 'repos/IVIR3zaM/Planzilla/pulls?state=closed&base=main&head=IVIR3zaM:claude/tender-davinci-ej9m0c' --jq '[.[]|select(.merged_at!=null)][0].merge_commit_sha'); test -n "$m" && test "$(git ls-remote origin refs/tags/v0.1.0 'refs/tags/v0.1.0^{}' | tail -1 | cut -f1)" = "$m"`
- C4 [cmd] `for i in $(seq 12); do n=$(gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=push&branch=v0.1.0' --jq '[.workflow_runs[]|select(.name=="Release")]|length'); [ "$n" -ge 1 ] && break; sleep 10; done; [ "$n" -ge 1 ]`
- C5 [cmd] `uv run pytest -q`

## N09 plan acceptance
Do: Check the whole plan: verify passes, the PR's last dry run and the v0.1.0 Release run are green with all
three jobs, the release has the sdist and wheel, and the tap formula points at v0.1.0's sdist with its sha256.
C3 waits up to 14 minutes for the v0.1.0 Release run to finish.
Context: D3 job ids build, brew, publish; D4 published url
https://github.com/IVIR3zaM/Planzilla/releases/download/v0.1.0/planzilla-0.1.0.tar.gz; D6 README line. REST only.
Done when:
- C1 [cmd] `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- C2 [cmd] `gh api "repos/IVIR3zaM/Planzilla/actions/runs?event=pull_request&branch=claude/tender-davinci-ej9m0c" --jq '[.workflow_runs[]|select(.name=="Release")][0].conclusion' | grep -qx success`
- C3 [cmd] `for i in $(seq 84); do r=$(gh api 'repos/IVIR3zaM/Planzilla/actions/runs?event=push&branch=v0.1.0' --jq '[.workflow_runs[]|select(.name=="Release")][0]|"\(.id) \(.status) \(.conclusion)"'); [ "$(echo "$r" | cut -d' ' -f2)" = completed ] && break; sleep 10; done; test "${r#* }" = "completed success" && gh api repos/IVIR3zaM/Planzilla/actions/runs/${r%% *}/jobs --jq '[.jobs[]|.name+"="+.conclusion]|sort|join(" ")' | grep -qx 'brew=success build=success publish=success'`
- C4 [cmd] `gh api repos/IVIR3zaM/Planzilla/releases/tags/v0.1.0 --jq '[.assets[].name]|sort|join(" ")' | grep -qx 'planzilla-0.1.0-py3-none-any.whl planzilla-0.1.0.tar.gz'`
- C5 [cmd] `f=$(curl -fsSL https://raw.githubusercontent.com/IVIR3zaM/homebrew-tap/HEAD/Formula/planzilla.rb) && s=$(curl -fsSL https://github.com/IVIR3zaM/Planzilla/releases/download/v0.1.0/planzilla-0.1.0.tar.gz | sha256sum | cut -d' ' -f1) && echo "$f" | grep -qF 'url "https://github.com/IVIR3zaM/Planzilla/releases/download/v0.1.0/planzilla-0.1.0.tar.gz"' && echo "$f" | grep -qF "sha256 \"$s\""`
- C6 [review] README.md Install section matches the shipped formula: `brew install IVIR3zaM/tap/planzilla`
  gives `planzilla` and `plz` on python@3.13, and the uvx and pipx lines are unchanged.

## Log

### N01 try 1 · 2026-10-01
check: PASS 8/8
