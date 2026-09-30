# Next Codex Session

## Activation condition

Step 2 is complete. Before starting Step 3, verify that the actual branch,
HEAD, remote, clean working tree, Pull Request, and latest required CI result
agree with `docs/ci/CI_STATE.md`. Stop and investigate any mismatch.

## Step

Step 3 — Define deterministic simulator boundaries

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
- `.github/workflows/ci.yml`

Do not read unrelated future files unless the current step requires them.

## Goal

Define the smallest provider-independent boundaries for a deterministic fake
sensor, controllable clock, transport, and temporary durable queue. Prove their
deterministic behavior with unit tests without defining product telemetry,
timing, capacity, credential, or authorization requirements.

## Current verified starting point

- The project currently contains only the package boundary and one
  installed-package test; no application or simulator abstractions exist.
- Python 3.11 and the locked pytest environment are established.
- Pull Request workflow `CI / Python 3.11` reproduces the mandatory Python
  checks and has a successful GitHub run.
- No physical hardware, API, database, Docker, Supabase, secrets, or production
  service is available or required.
- Product telemetry fields, rates, retention, buffer limits, and command
  authority remain open decisions.

## Allowed scope

- Minimal interfaces or protocols for fake sensor, clock, transport, and
  temporary durable queue boundaries.
- Deterministic in-memory or temporary-filesystem test implementations.
- Explicitly labeled test fixtures and test configuration.
- Unit tests that prove deterministic control of time, readings, delivery
  success/failure, queue persistence behavior, and ordering only to the extent
  needed to validate the boundaries.
- Dependency and CI handoff updates required by this step.

## Out of scope

- Product telemetry envelope or field definitions; those belong to Step 4.
- Duplicate, reconnect, replay, late-data, reboot, or stream semantics from
  Steps 5 and 6.
- API implementation, HTTP integration, Supabase, PostgreSQL, Docker, or
  schema work.
- Production credentials, authorization roles, retention guarantees, buffer
  limits, sampling/reporting rates, or remote-command behavior.
- Hardware-in-the-Loop, deployment, coverage thresholds, caching, lint, or
  type-check additions.

## Required investigation

- Reconfirm repository, Pull Request, and CI state before changes.
- Inspect the current minimal package and test structure.
- Choose the smallest boundaries that support later deterministic scenarios
  without prematurely implementing those scenarios.
- Keep temporary values explicitly named as test fixtures or test
  configuration, never as product defaults or requirements.

## Validation

Recreate or reuse the isolated environment and run:

- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`

Also verify deterministic repeatability, installed-package imports, no
production-service or hardware dependency, and `git diff --check`. After
approved commit and push, verify the updated Pull Request workflow.

Expected result: boundary tests pass repeatedly with no wall-clock timing,
network, hardware, Docker, Supabase, secret, or production dependency.

## Stop condition

After Step 3 implementation, validation, state update, approved commit/push,
and successful Pull Request workflow verification. Do not start Step 4 in the
same session.
