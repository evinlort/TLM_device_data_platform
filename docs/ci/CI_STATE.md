# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Step 5 implementation commit:
  `f89366151dc7b913feb6d77bef776b960a575a88`.
- The commit containing this file finalizes the Step 5 handoff; use
  `git rev-parse HEAD` for its exact SHA without creating a self-referential
  state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. The repository changed from the previously recorded
  private visibility; the user confirmed on 2026-09-30 that public visibility
  is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main`.
- GitHub Actions
  [CI #11](https://github.com/evinlort/TLM_device_data_platform/actions/runs/36721698288)
  completed successfully for the Step 5 implementation commit. Its
  `Python 3.11` job completed locked installation, dependency checking,
  pytest, result-file validation, and artifact upload successfully.
- Step 5 artifact `pytest-results-python-3.11`, ID `11098952143`, was
  downloaded and inspected. Its GitHub digest and the downloaded ZIP SHA-256
  both equal
  `f5eb6b10322b29f799f64eb94cf6eb64cc759f7cae3684533b56325e671f738c`.
- Working tree: expected to be clean after the approved final Step 5 handoff
  commit.

## Current milestone

- Step: Step 5 — Add duplicate, offline, and reconnect scenarios.
- Status: DONE.
- Completion blockers: none.

## Verified facts

- `Transport` and `DurableQueue` continue to carry opaque serialized `bytes`.
- `flush_test_queue()` is explicitly test-only deterministic orchestration.
  One call attempts FIFO messages until the queue is empty or the configured
  transport returns `False`.
- A configured `True` removes only the matching queue head in the test flow.
  A configured `False` stops the explicit flush and leaves that message and
  all later messages queued.
- Reconnect is modeled by constructing a new `ScriptedTransport` and calling
  `flush_test_queue()` again; there is no automatic retry loop, timer,
  backoff, wait, or reconnect implementation.
- Logical duplicate acceptance is defined only inside the Step 5 fixture
  scenario as keeping the first parsed envelope for each fixture
  `message_id`. It is not a production storage or acknowledgement contract.
- The buffered burst contains `64` fixture messages only to exercise ordered
  correctness over more than a trivial sequence. It is not a capacity,
  performance, scale, overflow, retention, or SLO claim.
- No runtime or test dependency was added, and `.github/workflows/ci.yml` did
  not require a change.
- No physical hardware, wall-clock wait, random input, network service,
  credential, API, database, Supabase, PostgreSQL, or Docker dependency is
  used by the new scenarios.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 5.

## Implemented in Step 5

- `flush_test_queue()` in `simulation.py` composes the existing queue and
  transport protocols without interpreting message contents.
- A duplicate fixture retry scenario proves two delivery attempts with the
  same fixture `message_id` produce one logical fixture acceptance.
- An unavailable-transport scenario proves the failed queue head and the next
  message remain in the temporary durable test queue across instances.
- A reconnect scenario proves persisted messages replay in FIFO sequence
  order `1, 2, 3` and leave the queue empty after configured success.
- A `64`-message correctness burst proves exact byte-for-byte FIFO replay and
  sequence order after an explicit offline/reconnect transition.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Workflow-equivalent full pytest command: PASS (`16 passed`), returning
  status `0` and creating both non-empty result files.
- JUnit XML parse: PASS (`16` tests, `0` failures, `0` errors, `0` skipped).
- Step 5 scenario suite repeated five times: PASS (`4 passed` each time).
- Installed-package import from `/tmp`: PASS; `flush_test_queue` resolves from
  `.venv/lib/python3.11/site-packages`, not the source tree.
- Forbidden hardware/production dependency scan: PASS.
- Existing artifact contract: PASS; the workflow still creates and uploads
  both `test-results/pytest.xml` and `test-results/pytest.log` with always-run
  validation and upload behavior.
- `git diff --check`: PASS.

The first locked reinstall attempt ran in the restricted sandbox and could not
resolve the pinned PEP 517 build dependency. The identical command succeeded
after explicit network approval; dependency versions and the installation
contract were not changed.

Remote Step 5 validation:

- Workflow: `CI`, run ID `36721698288`, run number `11`.
- Commit: `f89366151dc7b913feb6d77bef776b960a575a88`.
- Job: `Python 3.11`; every job step completed with conclusion `success`.
- Artifact: `pytest-results-python-3.11`, ID `11098952143`, `1254` archive
  bytes, not expired when inspected.
- GitHub-reported and downloaded ZIP SHA-256 both equal
  `f5eb6b10322b29f799f64eb94cf6eb64cc759f7cae3684533b56325e671f738c`.
- The downloaded ZIP passed archive integrity validation and contained exactly
  the expected non-empty `pytest.xml` (`2642` bytes) and `pytest.log` (`801`
  bytes).
- Downloaded JUnit XML: `16` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; it contains the `16 passed` summary.

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
  simulator-boundary tests, seven telemetry-fixture contract cases, and four
  Step 5 delivery scenarios; `16` tests total.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Credential implementation and provisioning details.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Production duplicate key, idempotency, acknowledgement, retry, reconnect,
  retention, offline guarantee, buffer capacity, overflow, and data-loss
  policies.
- Command authority, SLO, production scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Files changed in Step 5

- `src/tlm_device_data_platform/simulation.py`
- `tests/test_delivery_scenarios.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

`.github/workflows/ci.yml`, `pyproject.toml`, and `requirements/test.txt` did
not require changes.

## Next step

- Step: Step 6 — Add ordering, stream, and late-data scenarios.
- Step 5 is committed, pushed, successful in the Pull Request workflow, and
  its published artifact has been downloaded and inspected.
- Step 6 must start in a new Codex session.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for that new session. Do not start Step 6 in
this session.
