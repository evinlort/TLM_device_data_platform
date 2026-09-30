# Next Codex Session

## Activation condition

Step 4.5 may start only after Step 4 is committed, pushed, and successful in
the Pull Request workflow. Before any Step 4.5 change, verify that the actual
branch, HEAD, remote, clean working tree, Pull Request, and latest required CI
result agree with `docs/ci/CI_STATE.md`. If Step 4 changes are still
uncommitted or its remote check is pending or failed, finish or investigate
Step 4 instead of starting Step 4.5.

## Step

Step 4.5 — Publish test result artifacts

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/test.txt`
- `tests/`

Do not read unrelated future files unless the current step requires them.

## Goal

Make the Pull Request workflow retain both a machine-readable JUnit XML report
and a human-readable pytest log while preserving pytest's real exit status.
Upload both files even when tests fail, and fail clearly if the expected files
are absent.

## Current verified starting point

- The Pull Request workflow has one `Python 3.11` job that installs the locked
  test environment, runs `pip check`, and runs pytest.
- The local and CI test command is `python -m pytest`.
- The suite is deterministic and requires no physical hardware, production
  service, secret, database, or Docker.
- No result file or artifact upload currently exists.
- Product data retention remains an open decision and is unrelated to CI test
  artifact retention.

## Allowed scope

- Pytest options or shell flow needed to create JUnit XML and a readable log
  without hiding the pytest exit code.
- An official `actions/upload-artifact` action pinned to a verified full
  commit SHA.
- An upload step that runs after test failure and validates the expected files
  exist.
- Local workflow-contract checks, CI handoff updates, and remote artifact
  verification required by this step.

## Out of scope

- Changing product data retention requirements.
- Duplicate-idempotency, offline queue, reconnect, replay, or buffered-burst
  behavior from Step 5.
- New test semantics unrelated to artifact generation.
- API, HTTP, Supabase, PostgreSQL, Docker, production credentials,
  authorization, deployment, branch protection, caching, lint, type checking,
  or coverage thresholds.

## Required investigation

- Reconfirm repository, Pull Request, and CI state before changes.
- Verify the current official `actions/upload-artifact` release and resolve its
  release tag to a full upstream commit SHA.
- Choose a shell/test invocation that records readable output and returns the
  original pytest status rather than the status of a logging command.
- Ensure upload is attempted after pytest failure and missing expected files
  produce a clear workflow failure.
- Use repository-default artifact retention; do not infer product retention.

## Validation

Run the existing locked install, `pip check`, and pytest checks. Also validate
the workflow syntax and semantics, pytest exit-code preservation, creation of
both expected result files, upload conditions, full-SHA action pin, absence of
secrets/production dependencies, and `git diff --check`. After approved commit
and push, verify the updated Pull Request workflow and download/inspect the
published artifact.

## Stop condition

After Step 4.5 implementation, validation, state update, approved commit/push,
successful Pull Request workflow verification, and artifact inspection. Do
not start Step 5 in the same session.
