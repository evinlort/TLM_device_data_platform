# Next Codex Session

## Activation condition

Step 5 may start only after Step 4.5 is committed, pushed, successful in the
Pull Request workflow, and the published test-results artifact has been
downloaded and inspected. Before any Step 5 change, verify that the actual
branch, HEAD, remote, clean working tree, Pull Request, latest required CI
result, artifact listing, and downloaded artifact agree with
`docs/ci/CI_STATE.md`. If Step 4.5 changes are still uncommitted, its remote
check is pending or failed, or its artifact has not been inspected, finish or
investigate Step 4.5 instead of starting Step 5.

## Step

Step 5 — Add duplicate, offline, and reconnect scenarios

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `src/tlm_device_data_platform/simulation.py`
- `src/tlm_device_data_platform/telemetry_fixture.py`
- `tests/test_simulation.py`
- `tests/test_telemetry_fixture.py`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/test.txt`

Do not read unrelated future files unless the current step requires them.

## Goal

Add deterministic, hardware-independent scenarios that prove logical
duplicate idempotency, retention in the test queue while transport is
unavailable, and ordered replay after reconnect including a
correctness-scale buffered burst.

## Current verified starting point

- `ScriptedTransport` provides deterministic delivery outcomes over opaque
  `bytes` and records attempts.
- `TemporaryFileQueue` provides test-only FIFO persistence across instances.
- `TelemetryFixtureEnvelope` is an explicitly test-only contract with
  `message_id`, `stream_id`, and `sequence_no`; none of its fields or values
  are Product requirements.
- Pull Request CI runs the locked Python 3.11 environment and publishes JUnit
  XML plus a readable pytest log as one artifact.
- No production retry loop, acknowledgement protocol, offline retention
  guarantee, queue capacity, overflow policy, API, database, or Supabase
  implementation exists.

## Allowed scope

- The smallest provider-independent test orchestration needed to compose the
  existing transport, queue, and fixture boundaries.
- Explicitly test-only duplicate, unavailable-transport, reconnect, replay,
  and buffered-burst fixtures.
- Deterministic tests for the Step 5 acceptance criteria.
- CI handoff updates and validation required by this step.

## Out of scope

- Product retry timing, backoff, acknowledgement, retention duration, buffer
  size, overflow, or data-loss policy.
- Step 6 out-of-order current-state, new-stream restart, late-data, or
  clock-skew semantics.
- API, HTTP, Storage Adapter, Supabase, PostgreSQL, Docker, production
  credentials, authorization, deployment, branch protection, caching, lint,
  type checking, or coverage thresholds.
- Changing test artifact publication except where a Step 5 validation exposes
  a defect in the already completed Step 4.5 flow.

## Required investigation

- Reconfirm repository, Pull Request, CI, and artifact state before changes.
- Determine the minimum orchestration boundary that can express Step 5
  behavior without turning test fixtures into Product requirements.
- Define what logical acceptance means inside the test scenario without
  inventing a production storage or acknowledgement contract.
- Keep the buffered burst a deterministic correctness fixture, not a scale,
  performance, capacity, or SLO claim.
- Preserve opaque serialized messages at the existing provider-independent
  transport and queue boundaries.

## Validation

Run the existing locked install, `pip check`, and full pytest suite. Prove each
new scenario deterministically, repeat the relevant suite to detect accidental
time/order dependence, confirm installed-package imports, scan for forbidden
hardware/production dependencies, confirm the workflow still creates both
test-result files, and run `git diff --check`. After approved commit and push,
verify the updated Pull Request workflow and inspect its published artifact.

## Stop condition

After Step 5 implementation, validation, state update, approved commit/push,
successful Pull Request workflow verification, and artifact inspection. Do
not start Step 6 in the same session.
