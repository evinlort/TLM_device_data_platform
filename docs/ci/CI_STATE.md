# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Base HEAD before the uncommitted Step 3 work:
  `67ddea716aa48956b717bf1004084fa393208a47`.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main` and is mergeable.
- The current remote HEAD check `CI / Python 3.11` is successful.
- Working tree: contains the completed, locally validated, uncommitted Step 3
  implementation and handoff updates pending explicit commit approval.

## Current milestone

- Step: Step 3 — Define deterministic simulator boundaries.
- Status: READY_FOR_COMMIT.
- Remaining completion gates: explicit commit/push approval and a successful
  Pull Request workflow for the pushed Step 3 HEAD.

## Verified facts

- Python 3.11 remains the minimum supported project version for the initial
  baseline.
- The existing locked install, `pip check`, and pytest flow remains valid.
- The simulator boundaries use no physical hardware, wall clock, network,
  Docker, Supabase, secret, or production service.
- Sensor readings stay generic and transport/queue messages stay opaque
  `bytes`; no product telemetry envelope or field has been defined.
- Test readings, time, delivery outcomes, messages, and paths are explicitly
  test fixtures or test configuration.
- The temporary queue persists FIFO content across new queue instances using
  a file under pytest's temporary directory. It defines no production
  durability, retention, capacity, retry, or replay guarantee.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 3.

## Implemented in Step 3

- Provider-independent `Sensor`, `Clock`, `Transport`, and `DurableQueue`
  protocols in `src/tlm_device_data_platform/simulation.py`.
- Deterministic `SequenceSensor`, `ManualClock`, and `ScriptedTransport` test
  implementations.
- `TemporaryFileQueue`, a temporary-filesystem FIFO test implementation with
  replacement-based file updates.
- Unit tests for configured reading order and exhaustion, manually controlled
  time, scripted delivery failure/success and attempt capture, plus queue FIFO
  persistence across instances.
- No runtime or test dependency was added.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- `.venv/bin/python -m pytest -q`, repeated five times: PASS each time
  (`5 passed`).
- Installed-package import from `/tmp`: PASS; `simulation.py` resolved from
  `.venv/lib/python3.11/site-packages`.
- Forbidden external-dependency scan across `src` and `tests`: PASS; no wall
  clock, sleep, network client, Supabase, PostgreSQL, Docker, or secret use.
- `git diff --check`: PASS before handoff updates and must be rerun on the
  final diff.

The first reinstall attempt inside the restricted sandbox could not download
the pinned PEP 517 build dependency. The same locked command succeeded after
network access was explicitly approved; this was an environment access issue,
not a package or test failure.

Remote validation for the pushed Step 3 HEAD is pending commit approval.

## Current CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Current suite: one installed-package boundary test and four deterministic
  simulator-boundary tests.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Credential implementation and provisioning details.
- Product telemetry fields and rates per `system_type`.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Retention, offline buffer limits, command authority, SLO, scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Files changed in Step 3

- `src/tlm_device_data_platform/simulation.py`
- `tests/test_simulation.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

## Next step

- Step: Step 4 — Add normal telemetry and contract scenarios.
- Activation requires Step 3 to be committed, pushed, and successful in the
  Pull Request workflow.
- Step 4 must define only a confirmed or explicitly test-only telemetry
  envelope and controlled malformed/version rejection behavior.

Step 4 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`. Do not start it while Step 3 completion gates
remain open.
