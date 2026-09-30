# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Step 7 implementation commit:
  `922ea764909e60ce9de828d557298d66a32e09b6`.
- The commit containing this file finalizes the Step 7 handoff; use
  `git rev-parse HEAD` for its exact SHA without creating a self-referential
  state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. The user confirmed on 2026-09-30 that public visibility
  is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main`.
- GitHub Actions
  [CI #15](https://github.com/evinlort/TLM_device_data_platform/actions/runs/36746384665)
  completed successfully for the Step 7 implementation commit. Its
  `Python 3.11` job completed locked installation, dependency checking,
  pytest, result-file validation, and artifact upload successfully.
- The Step 7 artifact `pytest-results-python-3.11`, ID `11111973801`, was
  downloaded and inspected. Its GitHub digest and downloaded ZIP SHA-256 both
  equal
  `b15231921bf2d820d9965715ca678c283f370d565563d0afc8cc0e34ad696d70`.
- Working tree: expected to be clean after the approved final Step 7 handoff
  commit.

## Current milestone

- Step: Step 7 — Establish the local API/storage integration boundary.
- Status: DONE.
- Completion blockers: none.

## Verified facts

- `StorageAdapter` is a structural, provider-independent boundary whose only
  operation stores opaque `bytes`.
- `OpaqueTelemetryAPI` is a minimal WSGI application that passes an HTTP
  request body to the configured `StorageAdapter` without parsing telemetry or
  importing any Supabase/database implementation.
- `TemporaryDirectoryStorage` is explicitly a local CI implementation. Its
  ordered file names and durability properties are test configuration, not a
  production schema or persistence guarantee.
- The configured test route `/test-fixture-telemetry` and HTTP `204` outcome
  are test integration choices, not a production URL or acknowledgement
  contract.
- The full deterministic scenario crosses the existing queue and `Transport`
  boundaries, a real `127.0.0.1` HTTP socket, the WSGI API, and a temporary
  filesystem boundary, then reopens storage and verifies the exact bytes.
- A separate scenario sends non-JSON bytes containing `NUL` and `0xff` and
  proves that API/storage preserve them unchanged rather than interpreting the
  test fixture contract.
- No runtime or test dependency was added. The HTTP server/client and WSGI
  boundary use the Python standard library.
- `.github/workflows/ci.yml`, `pyproject.toml`, and `requirements/test.txt` did
  not require changes.
- No physical hardware, production service, Docker, credential, secret,
  Supabase, PostgreSQL, schema, migration, or external network dependency is
  used by required CI.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 7.

## Implemented in Step 7

- Added `src/tlm_device_data_platform/local_integration.py` with:
  - the provider-independent `StorageAdapter` protocol;
  - the opaque WSGI `OpaqueTelemetryAPI` boundary;
  - the deterministic local `TemporaryDirectoryStorage` implementation.
- Added `tests/test_local_integration.py` with:
  - an end-to-end queued fixture flow over real loopback HTTP into storage;
  - exact persisted-byte and reopened-storage verification;
  - an opaque non-fixture binary-message scenario.
- Existing `simulation.py` and `telemetry_fixture.py` contracts were reused
  without adding provider details or promoting fixture fields to production
  semantics.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Targeted Step 7 suite: PASS (`2 passed`).
- Workflow-equivalent full pytest command: PASS (`22 passed`), returning
  status `0` and creating both non-empty result files.
- JUnit XML parse: PASS (`22` tests, `0` failures, `0` errors, `0` skipped).
- Step 7 integration suite repeated five times: PASS (`2 passed` each time).
- Installed-package import from `/tmp`: PASS; `local_integration.py` resolves
  from `.venv/lib/python3.11/site-packages`, not the source tree.
- Forbidden production dependency, credential, hardware, random-input, and
  uncontrolled-time scan: PASS.
- Existing artifact contract: PASS; the workflow still creates and uploads
  both `test-results/pytest.xml` and `test-results/pytest.log` with always-run
  validation and upload behavior.
- `git diff --check` and untracked-file whitespace/newline validation: PASS.

The first locked reinstall attempt ran inside the restricted Codex sandbox and
could not resolve PyPI. The approved network-enabled retry rebuilt and
installed the wheel successfully. A sandboxed full test run then reported
`PermissionError` only for creation of a loopback TCP socket (`20 passed`, `2`
failed); the same full command outside that socket restriction passed all `22`
tests. The targeted loopback suite also passed once and then five repeated
runs outside the socket-restricted sandbox. No external host was contacted by
the tests.

Remote Step 7 validation:

- Workflow: `CI`, run ID `36746384665`, run number `15`.
- Commit: `922ea764909e60ce9de828d557298d66a32e09b6`.
- Job: `Python 3.11`; every job step completed with conclusion `success`.
- Artifact: `pytest-results-python-3.11`, ID `11111973801`, `1487` archive
  bytes, not expired when inspected.
- The GitHub-reported and downloaded ZIP SHA-256 both equal
  `b15231921bf2d820d9965715ca678c283f370d565563d0afc8cc0e34ad696d70`.
- The downloaded ZIP passed archive integrity validation and contained exactly
  the expected non-empty `pytest.xml` (`3481` bytes) and `pytest.log` (`961`
  bytes).
- Downloaded JUnit XML: `22` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; it contains the `22 passed` summary.

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
  delivery scenarios, four ordering scenarios, and two local HTTP/storage
  integration scenarios; `22` tests total.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.
- `TemporaryDirectoryStorage` is a filesystem CI adapter and is not a
  database, schema prototype, or Supabase emulator.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Production API URL, HTTP contract, acknowledgement and error semantics.
- Production Storage Adapter implementation, database schema, transactions,
  retention, and conflict-resolution policy.
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

## Files changed in Step 7

- `src/tlm_device_data_platform/local_integration.py`
- `tests/test_local_integration.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

`.github/workflows/ci.yml`, `pyproject.toml`, and `requirements/test.txt` did
not require changes.

## Next step

- Step: Step 8 — Define the Supabase schema bootstrap strategy.
- Step 7 is committed, pushed, successful in the Pull Request workflow, and
  its published artifact has been downloaded and inspected.
- Step 8 must start in a new Codex session.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for that new session. Do not start Step 8 in
this session.
