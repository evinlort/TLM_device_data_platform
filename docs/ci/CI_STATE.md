# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Step 4.5 implementation commit:
  `a4604c7a5ca43fa9f6d65ce27be1a622d28435fe`.
- The commit containing this file finalizes the Step 4.5 handoff; use
  `git rev-parse HEAD` for its exact SHA without creating a self-referential
  state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open from `ci/github-actions-foundation` to `main` and is mergeable.
- GitHub Actions run
  [CI #9](https://github.com/evinlort/TLM_device_data_platform/actions/runs/36708553100)
  completed successfully for the Step 4.5 implementation commit.
- Artifact `pytest-results-python-3.11`, ID `11093152151`, was downloaded and
  inspected successfully from that run.
- Working tree: expected to be clean after the approved final Step 4.5 handoff
  commit.

## Current milestone

- Step: Step 4.5 — Publish test result artifacts.
- Status: DONE.
- Completion blockers: none.

## Verified facts

- Python 3.11 remains the minimum supported project version for the initial
  baseline.
- The current official `actions/upload-artifact` release is `v7.0.1`; its tag
  resolves upstream to full commit SHA
  `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`.
- The test step creates `test-results/pytest.xml` and
  `test-results/pytest.log` while keeping readable pytest output in the job
  log.
- The shell captures `${PIPESTATUS[0]}` and exits with that value, so `tee`
  does not replace pytest's exit status.
- An `always()` validation step checks that both expected files exist and are
  non-empty, reporting a GitHub error annotation for each missing file.
- An `always()` upload step uses the official action at the verified full SHA,
  includes both files, and also sets `if-no-files-found: error`.
- No `retention-days` input is set, so GitHub uses the repository-default
  artifact retention. This is CI artifact retention, not a Product telemetry
  retention decision.
- No project dependency, product behavior, test case, secret, hardware,
  production service, Supabase, database, or Docker dependency was added.
- `docs/ci/FLOW_EXPLANATIONS.md` contains detailed Russian explanations for
  Steps 1 through 4.5.

## Implemented in Step 4.5

- Pytest JUnit XML generation and readable output capture in
  `.github/workflows/ci.yml`.
- Explicit preservation of the pytest process status across the `tee`
  pipeline.
- Always-run validation of both expected non-empty result files.
- Always-run upload of artifact `pytest-results-python-3.11` with the official
  full-SHA-pinned `actions/upload-artifact@v7.0.1`.
- Repository-default artifact retention with no product retention inference.

## Validation

Local environment:

- Python: `3.11.9`.
- Locked project reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Workflow-equivalent pytest command: PASS (`12 passed`), returning status
  `0` and creating both non-empty result files.
- JUnit XML parse: PASS (`12` tests, `0` failures, `0` errors).
- Human-readable pytest log inspection: PASS; it contains the XML report path
  and the `12 passed` summary.
- Workflow YAML parse and contract assertions: PASS, including three full-SHA
  action pins, two `always()` conditions, both result paths,
  `if-no-files-found: error`, and absence of retention override, secrets, and
  `pull_request_target`.
- Failing pytest invocation: PASS; pytest status `4` survived the logging
  pipeline and both failure-run files were non-empty.
- Missing-result validation: PASS; both absent paths emitted explicit error
  annotations and the validation returned status `1`.

The locally installed `gh` command again could not start because its Snap
launcher rejected the local AppArmor state. Pull Request and workflow state
were therefore verified through the authenticated GitHub connector; this did
not require a repository or workflow workaround.

Remote validation:

- Workflow: `CI`, run ID `36708553100`, run number `9`.
- Commit: `a4604c7a5ca43fa9f6d65ce27be1a622d28435fe`.
- Job: `Python 3.11`.
- Conclusion: SUCCESS.
- Checkout, Python setup, locked installation, dependency consistency, pytest,
  result-file validation, and artifact upload all completed successfully.
- Artifact: `pytest-results-python-3.11`, ID `11093152151`, `1113` archive
  bytes, not expired when inspected.
- GitHub-reported and downloaded ZIP SHA-256 both equal
  `f2aa0cf4a9aaabe41d6f4308f9b2fe28fc9c308e8010b744ee3838bbf087639e`.
- The downloaded ZIP passed archive integrity validation and contained exactly
  the expected non-empty `pytest.xml` (`2117` bytes) and `pytest.log` (`721`
  bytes).
- Downloaded JUnit XML: `12` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; it records the runner XML path and `12 passed`.

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

## Files changed in Step 4.5

- `.github/workflows/ci.yml`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

`docs/ci/DECISIONS.md` did not require a change because Step 4.5 implements
the already planned artifact behavior without making a new durable Product or
architecture decision.

## Next step

- Step: Step 5 — Add duplicate, offline, and reconnect scenarios.
- Step 4.5 is committed, pushed, successful in the Pull Request workflow, and
  its published artifact has been downloaded and inspected.
- Step 5 must not infer product retry, retention, capacity, or overflow policy
  beyond explicitly test-only deterministic scenarios.

Step 5 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`. Do not start it in this session.
