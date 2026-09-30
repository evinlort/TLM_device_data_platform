# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- HEAD: the commit containing this file completes Step 2; use
  `git rev-parse HEAD` to obtain its exact SHA without creating a
  self-referential state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main` and is mergeable.
- Working tree: expected to be clean after the approved final Step 2 handoff
  commit.

## Current milestone

- Step: Step 2 — Add the Python GitHub Actions foundation.
- Status: DONE.
- Completion blockers: none.

## Verified facts

- Python 3.11 remains the minimum supported project version for the initial
  baseline.
- The Step 1 locked installation and mandatory checks pass in a newly created
  isolated `.venv` using Python 3.11.9 and pip 24.0.
- The package imports from the installed wheel in `site-packages`, not from
  the source tree.
- GitHub documents explicit least-privilege workflow permissions and
  full-length commit SHA action pins as security practices.
- The official action releases and upstream tag SHAs used by the workflow are:
  - `actions/checkout@v7.0.1`:
    `3d3c42e5aac5ba805825da76410c181273ba90b1`.
  - `actions/setup-python@v7.0.0`:
    `5fda3b95a4ea91299a34e894583c3862153e4b97`.
- Repository Actions are enabled with all actions allowed.
- GitHub Actions workflow run
  [CI #1](https://github.com/evinlort/TLM_device_data_platform/actions/runs/36674668467)
  completed successfully for implementation commit
  `72380506cbae287db8858a55e041fd4186054f1a`.
- The `Python 3.11` job and every configured step completed successfully.

## Implemented

- One Pull Request workflow at `.github/workflows/ci.yml`.
- Workflow-level `contents: read` permission.
- Per-PR concurrency with cancellation of superseded runs.
- One `ubuntu-latest` Python 3.11 job with a 10-minute timeout.
- Full-SHA pins for `actions/checkout` and `actions/setup-python`.
- Checkout credential persistence disabled.
- The exact Step 1 install, dependency-consistency, and pytest commands.
- No `pull_request_target`, secret, production service, hardware, Docker,
  Supabase, cache, test split, coverage threshold, lint, or type-check layer.

## Validation

Local commands executed:

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

Local results:

- Clean isolated installation: PASS.
- Dependency consistency: PASS (`No broken requirements found`).
- Tests: PASS (`1 passed`).
- Installed-package boundary: PASS.
- YAML syntax: PASS.
- Workflow security/semantics assertions: PASS.
- Whitespace validation: PASS.

Remote result:

- Workflow: `CI`, run ID `36674668467`, run number `1`.
- Job: `Python 3.11`.
- Conclusion: SUCCESS.
- Successful configured steps: checkout, Python setup, locked installation,
  dependency consistency, and pytest.

## Current CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local reproduction:
  - `python3 -m venv .venv`
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
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

- None for Step 3.

## Files changed in the completed step

- `.github/workflows/ci.yml`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`

## Next step

- Step: Step 3 — Define deterministic simulator boundaries.
- Goal: define the smallest fake sensor, clock, transport, and temporary
  durable queue boundaries and prove deterministic behavior with unit tests.
- Do not invent product telemetry, timing, capacity, credential, or
  authorization requirements.
- Required CI must remain independent of physical hardware and production
  services.

Step 3 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`.
