# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Verified starting HEAD for Step 6:
  `4fc720d2db00c5f852e800b06b2d4a8615be0f97`.
- Remote branch `origin/ci/github-actions-foundation` resolved to the same SHA
  before Step 6 changes.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. The user confirmed on 2026-09-30 that public visibility
  is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main`.
- GitHub Actions
  [CI #12](https://github.com/evinlort/TLM_device_data_platform/actions/runs/36723266684)
  completed successfully for the verified starting HEAD. Its `Python 3.11`
  job completed locked installation, dependency checking, pytest, result-file
  validation, and artifact upload successfully.
- Prerequisite artifact `pytest-results-python-3.11`, ID `11101041556`, was
  downloaded and inspected before Step 6. Its GitHub digest and downloaded
  ZIP SHA-256 both equal
  `ab5529354c9de7eca236a3d091a351610219994a178c6f739f1814bcf5c08231`.
- Working tree: contains the reviewed and locally validated Step 6 changes;
  they are not committed or pushed pending explicit user approval.

## Current milestone

- Step: Step 6 — Add ordering, stream, and late-data scenarios.
- Status: READY_FOR_COMMIT.
- Completion blockers: explicit commit/push approval, then successful Pull
  Request workflow verification and inspection of the Step 6 artifact.

## Verified facts

- `TelemetryFixtureProjection` is explicitly deterministic test-only
  orchestration, not a production persistence or conflict-resolution model.
- Every parsed fixture observation is retained in immutable-view history with
  a deterministic `observation_no` and separately supplied `observed_at`.
- `recorded_at` remains untrusted fixture data and never activates a stream or
  decides `current_state`.
- Sequence comparison applies only to the stream explicitly activated by the
  test harness. A higher sequence in an inactive stream stays in history and
  cannot replace the active stream's current state.
- Explicit `activate_test_stream()` resets only the fixture current-state
  projection, so the newly selected stream may begin at sequence `1` while
  prior observations remain in history.
- Existing `Transport` and `DurableQueue` boundaries still carry opaque
  serialized `bytes`; no fixture parsing was added to those boundaries.
- No runtime or test dependency was added, and `.github/workflows/ci.yml` did
  not require a change.
- No physical hardware, wall-clock wait, random input, network service,
  credential, API, database, Supabase, PostgreSQL, or Docker dependency is
  used by the new scenarios.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 6.

## Implemented in Step 6

- `ObservedTelemetryFixture` records fixture arrival order, controlled
  observation time, and the parsed envelope without conflating observation
  time with device-provided `recorded_at`.
- `TelemetryFixtureProjection` keeps complete test history and updates
  `current_state` only for a higher sequence in the explicitly active test
  stream.
- An out-of-order scenario ingests fixture sequence `1, 3, 2`, retains that
  exact history, and proves current state remains sequence `3`.
- A reboot scenario explicitly switches fixture streams and proves the new
  stream can restart at sequence `1` without deleting earlier history.
- A late-data scenario proves a later observation from the inactive pre-reboot
  stream remains in history and cannot replace the post-reboot current state.
- A controlled clock-skew scenario proves past and far-future `recorded_at`
  values neither choose current state nor activate another fixture stream.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Workflow-equivalent full pytest command: PASS (`20 passed`), returning
  status `0` and creating both non-empty result files.
- JUnit XML parse: PASS (`20` tests, `0` failures, `0` errors, `0` skipped).
- Step 6 scenario suite repeated five times: PASS (`4 passed` each time).
- Installed-package import from `/tmp`: PASS;
  `TelemetryFixtureProjection` resolves from
  `.venv/lib/python3.11/site-packages`, not the source tree.
- Forbidden hardware/production dependency and uncontrolled-time scan: PASS.
- Existing artifact contract: PASS; the workflow still creates and uploads
  both `test-results/pytest.xml` and `test-results/pytest.log` with always-run
  validation and upload behavior.
- `git diff --check`: PASS.

The first targeted Step 6 test run used the previously installed Step 5 wheel
and failed collection because the new projection class was intentionally not
importable from the source tree. Reinstalling the current project with the
locked command rebuilt the wheel; the targeted and full suites then passed.
No import-path workaround or dependency change was made.

Remote Step 6 validation:

- PENDING until the user approves commit and push.
- The Step 6 Pull Request run must complete successfully and its published
  `pytest-results-python-3.11` artifact must be downloaded and inspected before
  Step 6 can be marked DONE.

## Current CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- CI test results:
  - `test-results/pytest.xml` — machine-readable JUnit XML;
  - `test-results/pytest.log` — human-readable pytest output;
  - artifact name: `pytest-results-python-3.11`.
- Current suite: one installed-package boundary test, four deterministic
  simulator-boundary tests, seven telemetry-fixture contract cases, four
  Step 5 delivery scenarios, and four Step 6 ordering scenarios; `20` tests
  total.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Production history, current-state, stream identity, reboot, ordering,
  late-data, timestamp trust, and conflict-resolution policy.
- Credential implementation and provisioning details.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Production duplicate key, idempotency, acknowledgement, retry, reconnect,
  retention, offline guarantee, buffer capacity, overflow, and data-loss
  policies.
- Command authority, SLO, production scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Files changed in Step 6

- `src/tlm_device_data_platform/telemetry_fixture.py`
- `tests/test_ordering_scenarios.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

`.github/workflows/ci.yml`, `pyproject.toml`, and `requirements/test.txt` did
not require changes.

## Next step

- Step: Step 7 — Establish the local API/storage integration boundary.
- Step 7 is not activated while Step 6 is `READY_FOR_COMMIT`.
- After approved commit/push, successful Pull Request CI, artifact download
  and inspection, and a final Step 6 handoff update, Step 7 must start in a
  new Codex session.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for that new session. Do not start Step 7 in
this session.
