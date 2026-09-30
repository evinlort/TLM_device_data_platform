# Next Codex Session

## Activation condition

Step 1 is complete. Before starting Step 2, verify that the actual branch,
HEAD, remote, and clean working tree agree with `docs/ci/CI_STATE.md`. Stop and
investigate any mismatch.

## Step

Step 2 — Add the Python GitHub Actions foundation

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`

Additional files relevant to this step:

- `pyproject.toml`
- `requirements/test.txt`
- `src/tlm_device_data_platform/__init__.py`
- `tests/test_package.py`

Do not read unrelated future files unless the current step requires them.

## Goal

Add one minimal GitHub Actions workflow that installs the locked Python 3.11
test environment and runs the mandatory checks established in Step 1 on Pull
Requests. Harden the workflow without adding unrelated CI layers.

## Current verified starting point

- Python 3.11 is the minimum supported baseline and remains supported upstream
  through October 2027.
- A clean isolated installation with the locked test constraints succeeds.
- `.venv/bin/python -m pip check` passes.
- `.venv/bin/python -m pytest` passes with `1 passed`.
- No GitHub Actions workflow exists.
- No physical hardware, Docker, Supabase, secrets, or network access is needed
  after dependency installation.

## Allowed scope

- One workflow under `.github/workflows/`.
- Pull Request validation and optional safe manual/main-branch triggers if
  justified by current repository policy.
- Python 3.11 setup and the exact Step 1 install/check commands.
- Minimum `contents: read` permissions, concurrency cancellation, and a job
  timeout.
- Full-commit-SHA pins verified against the official upstream repositories.
- CI state/handoff updates required by the step-end protocol.

## Out of scope

- Device simulator behavior or tests.
- API implementation.
- Supabase, PostgreSQL, Docker, or integration jobs.
- Dependency caching or test splitting.
- Coverage thresholds, lint/type-check additions, and deployment.
- Secrets, `pull_request_target`, branch protection, or required-check changes.

## Required investigation

- Reconfirm repository and Git state before changes.
- Check current official GitHub Actions workflow syntax and security guidance.
- Verify the current supported `actions/checkout` and `actions/setup-python`
  releases and resolve their release tags to full upstream commit SHAs.
- Inspect current repository settings only as needed to choose safe triggers.
- Do not copy mutable action tags into the final workflow.

## Validation

Recreate or reuse an isolated environment and run:

- `python3 -m venv .venv`
- `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`

Also validate the workflow syntax and semantics, confirm `contents: read`,
concurrency cancellation, timeout, safe event context, and verified full-SHA
pins. After approved commit and push, verify the workflow in GitHub when the
configured trigger can be exercised safely.

Expected result: the local checks remain green and the minimal workflow is
ready to provide the same mandatory validation on a clean GitHub-hosted
runner without secrets, production services, or physical hardware.

## Stop condition

After implementation, validation, state update, approved commit, and push.
Do not start Step 3 in this session.
