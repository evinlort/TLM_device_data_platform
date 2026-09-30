# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Base HEAD before the uncommitted Step 4 work:
  `959d08eef602d4ceaaad53e601f622262d5b9764`.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main` and is mergeable.
- The current remote HEAD check `CI / Python 3.11` is successful.
- Working tree: contains the completed, locally validated, uncommitted Step 4
  implementation and handoff updates pending explicit commit approval.

## Current milestone

- Step: Step 4 — Add normal telemetry and contract scenarios.
- Status: READY_FOR_COMMIT.
- Remaining completion gates: explicit commit/push approval and a successful
  Pull Request workflow for the pushed Step 4 HEAD.

## Verified facts

- Python 3.11 remains the minimum supported project version for the initial
  baseline.
- The existing locked install, `pip check`, and pytest flow remains valid.
- `telemetry_fixture.py` is an explicitly test-only contract. Its field names,
  schema version, values, and validation rules are not product requirements.
- Fixture serialization is deterministic UTF-8 JSON with stable key ordering,
  compact separators, and rejection of non-finite JSON numbers.
- The fixture parser distinguishes malformed envelopes from unsupported
  fixture schema versions with controlled exception types.
- Ordered fixture messages with `sequence_no` 1, 2, and 3 pass through the
  existing opaque-`bytes` `ScriptedTransport` boundary without changing that
  provider-independent protocol.
- No acceptance, authorization, storage, retry, idempotency, current-state, or
  production schema behavior was added.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 4.

## Implemented in Step 4

- `TelemetryFixtureEnvelope`, fixture schema-version constant, deterministic
  serializer, and strict parser in
  `src/tlm_device_data_platform/telemetry_fixture.py`.
- Controlled `MalformedTelemetryFixtureError` and
  `UnsupportedFixtureSchemaVersionError` failure modes.
- A normal ordered transport scenario using fixture `sequence_no` values 1,
  2, and 3.
- Unit coverage for deterministic round trips, malformed JSON/object/field
  shapes, invalid field types, and unsupported fixture versions.
- No runtime or test dependency was added.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- `.venv/bin/python -m pytest -q`, repeated five times: PASS each time
  (`12 passed`).
- Installed-package import from `/tmp`: PASS; `telemetry_fixture.py` resolved
  from `.venv/lib/python3.11/site-packages`.
- Controlled malformed/version rejection: PASS through dedicated tests.
- Forbidden external-dependency scan across `src` and `tests`: PASS; no wall
  clock, sleep, network client, Supabase, PostgreSQL, Docker, secret, or
  physical-device use.
- `git diff --check`: PASS on the final prepared diff.

The first pytest invocation correctly exposed that the isolated environment
still contained the previously installed Step 3 wheel, so the new module was
not yet present in `site-packages`. The first locked reinstall attempt inside
the restricted sandbox then could not download the pinned PEP 517 build
dependency. The same locked command succeeded after network access was
explicitly approved; the full suite then passed. These were installed-package
and environment-access conditions, not source defects.

Remote validation for the pushed Step 4 HEAD is pending commit approval.

## Current CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Current suite: one installed-package boundary test, four deterministic
  simulator-boundary tests, and seven telemetry-fixture contract cases.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Credential implementation and provisioning details.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Retention, offline buffer limits, command authority, SLO, scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Files changed in Step 4

- `src/tlm_device_data_platform/telemetry_fixture.py`
- `tests/test_telemetry_fixture.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

## Next step

- Step: Step 4.5 — Publish test result artifacts.
- Activation requires Step 4 to be committed, pushed, and successful in the
  Pull Request workflow.
- Step 4.5 must preserve the pytest exit status while producing and uploading
  machine-readable and human-readable test results.

Step 4.5 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`. Do not start it while Step 4 completion gates
remain open.
