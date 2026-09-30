# Next Codex Session

## Activation condition

Step 6 may start only after Step 5 is committed, pushed, successful in the
Pull Request workflow, and the published test-results artifact has been
downloaded and inspected. Before any Step 6 change, verify that the actual
branch, HEAD, remote, clean working tree, Pull Request, latest required CI
result, artifact listing, and downloaded artifact agree with
`docs/ci/CI_STATE.md`. If Step 5 changes are still uncommitted, its remote
check is pending or failed, or its artifact has not been inspected, finish or
investigate Step 5 instead of starting Step 6.

## Step

Step 6 — Add ordering, stream, and late-data scenarios

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
- `tests/test_delivery_scenarios.py`
- `tests/test_simulation.py`
- `tests/test_telemetry_fixture.py`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/test.txt`

Do not read unrelated future files unless the current step requires them.

## Goal

Add deterministic, hardware-independent test scenarios proving that
out-of-order and late fixture telemetry remains in test history without
rolling back a newer test current-state projection, that a new fixture
`stream_id` permits a test sequence restart, and that controlled device-clock
skew does not act as an authorization or trust proof.

## Current verified starting point

- `TelemetryFixtureEnvelope` provides explicitly test-only `message_id`,
  `stream_id`, `sequence_no`, and `recorded_at` fields; none is a confirmed
  Product contract.
- `flush_test_queue()` explicitly replays opaque queued `bytes` in FIFO order
  until the configured test transport becomes unavailable.
- Step 5 proves fixture-only duplicate acceptance, offline queue persistence,
  ordered reconnect replay, and a `64`-message correctness burst.
- No production history store, current-state projection, ordering policy,
  reboot protocol, trusted clock, API, database, or Supabase implementation
  exists.

## Allowed scope

- The smallest provider-independent, explicitly test-only orchestration needed
  to represent fixture history and a fixture current-state projection.
- Deterministic out-of-order, new-stream restart, late-data, and clock-skew
  fixtures required by the Step 6 acceptance criteria.
- CI handoff updates and validation required by this step.

## Out of scope

- Confirming production ordering, history, current-state, stream identity,
  reboot, timestamp trust, authorization, or conflict-resolution policy.
- API, HTTP, Storage Adapter, Supabase, PostgreSQL, Docker, production
  credentials, authorization, deployment, branch protection, caching, lint,
  type checking, or coverage thresholds.
- Product retry timing, acknowledgement, retention duration, buffer capacity,
  overflow, data-loss policy, performance, scale, or SLO claims.
- Step 7 API/storage integration implementation.
- Changing test artifact publication except where Step 6 validation exposes a
  defect in the completed flow.

## Required investigation

- Reconfirm repository, Pull Request, CI, and artifact state before changes.
- Define the minimum test-only history/current-state model without presenting
  it as a production persistence or conflict-resolution contract.
- Keep sequence comparisons scoped to the explicit fixture stream being
  tested, and prove a new fixture stream can restart its sequence.
- Separate fixture observation time/order from `recorded_at` so controlled
  device-clock skew cannot become an authorization or trust decision.
- Preserve opaque serialized messages at existing transport and queue
  boundaries.

## Validation

Run the existing locked install, `pip check`, and full pytest suite. Prove each
new scenario deterministically, repeat the relevant suite to detect accidental
time/order dependence, confirm installed-package imports, scan for forbidden
hardware/production dependencies, confirm the workflow still creates both
test-result files, and run `git diff --check`. After approved commit and push,
verify the updated Pull Request workflow and inspect its published artifact.

## Stop condition

After Step 6 implementation, validation, state update, approved commit/push,
successful Pull Request workflow verification, and artifact inspection. Do not
start Step 7 in the same session.
