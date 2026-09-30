# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- HEAD: the approved Step 1 commit; use `git rev-parse HEAD` for the exact SHA.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Working tree: contains the locally implemented Step 2 workflow and handoff
  updates awaiting explicit commit/push approval.

## Current milestone

- Step: Step 2 — Add the Python GitHub Actions foundation.
- Status: IN_PROGRESS.
- Completed locally: workflow implementation, clean Python validation,
  workflow syntax review, workflow security/semantics review, and official
  action release/SHA verification.
- Remaining: obtain approval, commit and push, open a Pull Request, verify the
  actual GitHub Actions run, then record the final Step 2 state.

## Verified facts

- Python 3.11 remains the minimum supported project version for the initial
  baseline.
- The Step 1 locked installation and mandatory checks still pass in a newly
  created isolated `.venv` using Python 3.11.9 and pip 24.0.
- The package imports from the installed wheel in `site-packages`, not from
  the source tree.
- GitHub documents explicit least-privilege workflow permissions and
  full-length commit SHA action pins as security practices.
- The current official releases selected for this workflow were verified
  directly against their upstream Git repositories:
  - `actions/checkout@v7.0.1` resolves to
    `3d3c42e5aac5ba805825da76410c181273ba90b1`.
  - `actions/setup-python@v7.0.0` resolves to
    `5fda3b95a4ea91299a34e894583c3862153e4b97`.
- No Pull Request ref currently exists in the remote repository, so opening a
  Pull Request is required to exercise the PR-only workflow after push.

## Implemented locally

- One workflow at `.github/workflows/ci.yml`.
- Pull Request is the only trigger; there is no `pull_request_target`, secret,
  production service, hardware, Docker, or Supabase dependency.
- Workflow-level `contents: read` permission.
- Per-PR concurrency with cancellation of superseded runs.
- One `ubuntu-latest` Python 3.11 job with a 10-minute timeout.
- Full-SHA pins for `actions/checkout` and `actions/setup-python`.
- Checkout credential persistence disabled.
- The exact Step 1 install, dependency-consistency, and pytest commands.

## Local validation

Commands executed:

- `python3 -m venv .venv`
- `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`
- Installed-package path verification from outside the repository root.
- Ruby/Psych YAML parse of `.github/workflows/ci.yml`.
- Explicit assertions for the trigger, permissions, concurrency cancellation,
  timeout, full-SHA pins, mandatory commands, and absence of unsafe event or
  secret references.
- `git diff --check`
- `git ls-remote` verification of the two official action release tags.

Results:

- Clean isolated installation: PASS.
- Dependency consistency: PASS (`No broken requirements found`).
- Tests: PASS (`1 passed`).
- Installed-package boundary: PASS.
- YAML syntax: PASS.
- Workflow security/semantics assertions: PASS.
- Whitespace validation: PASS.
- Actual GitHub Actions run: PENDING approved push and Pull Request creation.

## Current CI

- Local mandatory checks:
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Pull Request workflow: implemented and locally validated, not yet committed
  or exercised on GitHub.
- Tests: one deterministic installed-package boundary test.

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

- None. Completion is waiting only for explicit repository-write approval and
  the resulting remote workflow run.

## Files changed in the current step

- `.github/workflows/ci.yml`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`

## Exact continuation

- Review the current diff and local validation evidence.
- Obtain explicit approval before commit or push.
- Commit and push the Step 2 implementation.
- Open a Pull Request to `main` from `ci/github-actions-foundation`.
- Verify the actual `CI / Python 3.11` GitHub Actions check.
- If green, mark Step 2 DONE and prepare Step 3 in the persistent handoff.
- Do not implement Step 3 in this session.
