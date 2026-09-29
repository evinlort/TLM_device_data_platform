# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`
- HEAD: the commit containing this file completes Step 0; use
  `git rev-parse HEAD` to obtain its exact SHA without creating a
  self-referential state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- GitHub CLI: version 2.86.0-112-gc30647b78 is authenticated to `github.com`
  as active account `evinlort` using HTTPS for Git operations.
- Working tree before the final Step 0 state update: clean.

## Current milestone

- Step: Step 0 — Repository audit and CI state bootstrap
- Status: DONE
- Completion blockers: none.

## Verified facts

- The repository initially contains only
  `TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`.
- `.agents/` and `.codex/` exist but contain no files.
- No `AGENTS.md` or `AGENT.md` existed before Step 0.
- No Python package, dependency file, lock file, tests, pytest configuration,
  lint/type-check configuration, API, simulator, Docker configuration,
  Supabase files, GitHub Actions workflow, or prior handoff exists.
- Local Python reports 3.11.9. This is an environment observation, not the
  selected project version or a product requirement.
- Local `pytest --version` fails because the `pytest` module is not installed.
- Local Docker reports 29.7.2.
- Local Supabase CLI is not installed.
- GitHub CLI authentication is configured and verified for account `evinlort`.
- GitHub repository `evinlort/TLM_device_data_platform` exists and is private.
- `main` was initialized from the reviewed Step 0 root commit and is the
  default branch. Ongoing work remains on `ci/github-actions-foundation`.

## Implemented

- Step 0 coordination/state files and the unchanged master prompt are stored
  in Git and published to the private GitHub repository.
- No application, CI workflow, simulator, or database implementation exists.

## Validation

Commands executed during the audit:

- `git status --short --branch`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git remote -v`
- `rg --files -uu`
- `find . -maxdepth 4 -type d -print`
- `find . -maxdepth 4 -type f -printf '%p\t%k KB\n'`
- `git ls-files --stage`
- `git branch --all --verbose`
- `python --version`
- `python3 --version`
- `pytest --version`
- `docker --version`
- `supabase --version`
- `gh --version`
- `gh auth status`
- `gh repo view evinlort/TLM_device_data_platform --json nameWithOwner,url,isPrivate,defaultBranchRef`
- `gh repo create evinlort/TLM_device_data_platform --private --source=. --remote=origin`
- `git push -u origin ci/github-actions-foundation`
- `git push origin e7d049db9e89eab661539c3dbd79fa58f193ae9c:refs/heads/main`
- `gh repo edit evinlort/TLM_device_data_platform --default-branch main`
- `git ls-remote --heads origin`
- `git diff --cached --check -- AGENTS.md docs/ci`

Results:

- Repository inventory and absence claims above are verified.
- The initial `git rev-parse HEAD` failed as expected for an unborn branch;
  the reviewed root commit was then created successfully.
- Whitespace validation passes for all Step 0 coordination files.
- A global staged whitespace check reports the original master prompt's
  intentional two-space Markdown line breaks; the source document is kept
  unchanged.
- GitHub CLI authentication, private repository creation, remote branch
  publication, and default-branch verification pass.
- No tests or workflows can be executed yet.

## Current CI

- Workflows: none.
- Tests: none.

## Current simulator state

- No simulator exists.
- No physical device is available or required for planned PR CI.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Credential implementation and provisioning details.
- Product telemetry fields and rates per `system_type`.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Retention, offline buffer limits, command authority, SLO, scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Technical blockers

- None for Step 1.

## Files changed in the current step

- `AGENTS.md`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/BOOTSTRAP_PROMPT.md`
- `docs/ci/DECISIONS.md`
- `TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`

The existing master prompt is intentionally unchanged and is included in Git
so a fresh checkout retains the process source.

## Next step

- Step: Step 1 — Establish the Python validation baseline
- Goal: create the smallest reproducible Python package/test baseline without
  inventing product behavior.
- Expected files: exact files must be confirmed during Step 1 after official
  tooling review; likely project metadata, a minimal package boundary, and
  deterministic tests.
- Validation required: clean-environment installation plus the established
  test/lint commands.

Step 1 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`.
