# Next Codex Session

## Activation condition

Step 4 may start only after Step 3 is committed, pushed, and successful in the
Pull Request workflow. Before any Step 4 change, verify that the actual branch,
HEAD, remote, clean working tree, Pull Request, and latest required CI result
agree with `docs/ci/CI_STATE.md`. If Step 3 changes are still uncommitted or its
remote check is pending or failed, finish or investigate Step 3 instead of
starting Step 4.

## Step

Step 4 — Add normal telemetry and contract scenarios

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `pyproject.toml`
- `src/tlm_device_data_platform/simulation.py`
- `tests/test_simulation.py`
- `.github/workflows/ci.yml`

Do not read unrelated future files unless the current step requires them.

## Goal

Add the smallest test-only telemetry contract needed to validate an accepted
envelope, ordered test messages with `sequence_no` 1, 2, and 3, controlled
malformed-envelope rejection, and controlled unsupported test schema-version
rejection. Do not convert test fixtures into product requirements.

## Current verified starting point

- Step 3 defines provider-independent sensor, clock, transport, and durable
  queue protocols.
- Deterministic test implementations control readings, time, delivery results,
  and temporary queue state.
- Messages at transport and queue boundaries are opaque `bytes`; no product
  telemetry fields or envelope have been defined.
- Python 3.11, the locked pytest environment, and Pull Request workflow are
  established.
- Product telemetry fields, rates, credentials, retention, buffer limits, and
  authorization semantics remain open decisions.

## Allowed scope

- An explicitly labeled test fixture/test configuration telemetry envelope.
- Deterministic serialization and validation sufficient for Step 4 tests.
- Ordered normal test messages with `sequence_no` 1, 2, and 3.
- Controlled errors for malformed test envelopes and unsupported test schema
  versions.
- Unit tests and CI handoff updates required by this step.

## Out of scope

- Treating fixture field names, values, or schema versions as confirmed
  product requirements.
- Duplicate-idempotency, unavailable transport, durable replay, reconnect, or
  buffered-burst behavior from Step 5.
- Out-of-order current-state, stream restart, late-data, or clock-skew behavior
  from Step 6.
- API, HTTP, Supabase, PostgreSQL, Docker, production credentials,
  authorization, retention guarantees, capacity limits, or remote commands.
- Hardware-in-the-Loop, deployment, coverage thresholds, caching, lint, or
  type-check additions.

## Required investigation

- Reconfirm repository, Pull Request, and CI state before changes.
- Reuse the Step 3 boundaries without broadening their provider-independent
  contracts unnecessarily.
- Separate fixture schema choices visibly from confirmed product semantics.
- Do not infer acceptance, authorization, storage, retry, or current-state
  behavior beyond the Step 4 goal.

## Validation

Recreate or reuse the isolated environment and run:

- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`

Also verify deterministic repeatability, installed-package imports, controlled
error behavior, no production-service or hardware dependency, and
`git diff --check`. After approved commit and push, verify the updated Pull
Request workflow.

## Stop condition

After Step 4 implementation, validation, state update, approved commit/push,
and successful Pull Request workflow verification. Do not start Step 5 in the
same session.
