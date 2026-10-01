# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Starting HEAD for Step 10 and current committed HEAD:
  `581d389c9b5072f80cb5eb2409b32a3716e09627`.
- Step 9 implementation commit:
  `2e46cd6baf5dc013a64b3c0fdde54e34acb11f01`.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. Public visibility is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open, mergeable, and points from `ci/github-actions-foundation` to `main`.
- Starting branch, remote-tracking branch, and Pull Request head all matched the
  current committed HEAD before Step 10 changes.
- Working tree: contains only the reviewed, uncommitted Step 10 workflow and
  persistent handoff changes listed below.

## Current milestone

- Step: Step 10 — Add the local integration CI job.
- Status: READY_FOR_COMMIT.
- Completion blocker: explicit user approval to commit and push, followed by
  remote validation of both Pull Request jobs and both result artifacts.

## Verified starting state

- Local branch, starting HEAD, remote-tracking branch, and Pull Request head all
  equal `581d389c9b5072f80cb5eb2409b32a3716e09627`; the working tree was clean.
- Pull Request #1 was open, non-draft, mergeable, and targeted `main`.
- Required workflow `CI` run #20, ID `36777531943`, completed successfully for
  that final Step 9 handoff commit. Every `Python 3.11` job step completed with
  conclusion `success`.
- Its artifact `pytest-results-python-3.11`, ID `11126805181`, is not expired;
  GitHub reports digest
  `sha256:79a3bde2c877a4da19d3fa6ef2e2f8dbffebd517636807b370184f2c3139148b`.
- The artifact was downloaded and inspected. It contains exactly non-empty
  `pytest.xml` (`3481` bytes) and `pytest.log` (`961` bytes); the log reports
  `22 passed`, and parsed JUnit totals are `22` tests, `0` failures, `0` errors,
  and `0` skipped.

## Authorized source and remote discovery

- The user identified one exact Supabase project as a development environment,
  confirmed it is not production, authorized read-only MCP inspection of only
  the `public` schema, and authorized PostgreSQL major-version discovery.
- PostgreSQL version discovery returned `17.6`; local configuration therefore
  uses major version `17`.
- Initial inspection found no Auth users, Storage buckets or objects, Vault
  secrets, Edge Functions, or development branches. The application URL was
  not connected to an app, site, or device according to the user.
- The user manually removed seven obsolete functions and then removed the
  remaining `rls_auto_enable()` function together with its dependent
  `ensure_rls` event trigger.
- Under separate explicit authorization, obsolete remote migration-history
  entries were marked reverted with the locked CLI. No schema deployment,
  `db push`, data write, project setting change, or other remote mutation was
  performed.
- Final read-only inspection found zero `public` relations, functions,
  policies, custom types, and migration-history entries. Six remaining event
  triggers are platform-owned Supabase infrastructure (`supabase_admin` with
  functions in `extensions`) and were intentionally retained.
- The remote project remains empty and is not the runtime dependency or
  deployment target of this Step 9 implementation.
- The project reference, organization identifier, credentials, connection
  strings, and generated link state are not stored in version-controlled files.

## Approved greenfield requirement

The user explicitly approved `PROPOSAL v1`:

- table `public.ingest_messages`;
- columns `id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY` and
  `body bytea NOT NULL`;
- backend-only access with RLS enabled and no policies;
- duplicate and empty `bytea` values are allowed;
- all richer Product semantics are deferred.

The implementation interprets backend-only narrowly: `anon` and
`authenticated` receive no privileges, while `service_role` receives only
`INSERT` on the table and `USAGE` on its identity sequence. The identity value
does not define Product ordering, and `body` remains opaque.

## Implemented in Step 9

- Added a locked-CLI-generated `supabase/config.toml` reviewed for local use:
  PostgreSQL major version `17`, migrations enabled, seed disabled, and
  `api.auto_expose_new_tables = false` so grants remain explicit.
- Added `supabase/migrations/20260930233000_create_ingest_messages.sql` as the
  first version-controlled database migration.
- The migration creates only the approved table, documents its opaque boundary,
  enables RLS, revokes inherited application-role access, and grants only the
  approved backend insert path.
- Added `supabase/tests/ingest_messages.test.sql`, an 18-assertion transactional
  pgTAP test for the approved schema, RLS/policy state, privileges, exact opaque
  byte round-trip, empty bytes, and duplicates.
- Added generated Supabase state exclusions in root and Supabase-local
  `.gitignore` files.
- Added `CI-DEC-013` to preserve the approved minimal ingress decision and its
  explicit non-decisions.
- No seed, remote link, remote deployment, API adapter implementation, Python
  product behavior, or GitHub Actions database job was added.

## Implemented in Step 10

- Kept the existing `CI / Python 3.11` job and its artifact contract unchanged.
- Added a separate `CI / Local Supabase integration` job in
  `.github/workflows/ci.yml`.
- Pinned the job to `ubuntu-24.04`, Node.js `22.23.2`, Python `3.11`, a
  30-minute timeout, and `actions/setup-node` v7.0.0 at verified full commit SHA
  `820762786026740c76f36085b0efc47a31fe5020`.
- The job performs locked npm and Python installs, verifies Supabase CLI
  `2.118.0`, starts only local Supabase, rebuilds the database from migrations,
  runs the existing 18-assertion pgTAP suite, and runs the complete 22-test
  Python suite including the real loopback HTTP/storage integration scenarios.
- `supabase start` stdout is suppressed so local URLs and generated local keys
  are not retained in logs or artifacts.
- `supabase stop --no-backup` uses `always()` and runs before result validation
  and artifact upload.
- A separate `local-integration-results` artifact contains only
  `database-tests.log`, `pytest.xml`, and `pytest.log` under the already ignored
  `test-results/local-integration/` path.
- Added `CI-DEC-014` for the separate disposable job and the intentional
  deferral of any provider-specific Python database adapter.
- No schema, migration, database test, Python source/test/dependency, npm
  dependency, remote Supabase state, or Product behavior changed.

## Step 10 local validation

- Official Supabase guidance was rechecked on `2026-10-01`: project-scoped CLI,
  exact version, Node.js 20 or later, a Docker-compatible runtime, committed
  migrations, and clean local `db reset` remain the documented model.
- Official GitHub runner-image data identifies `ubuntu-24.04` as the current
  `ubuntu-latest` image and includes Docker; the explicit label avoids a gradual
  `-latest` migration during this CI step.
- `actions/setup-node` release v7.0.0 and verified full commit SHA
  `820762786026740c76f36085b0efc47a31fe5020`: PASS.
- Workflow YAML parse, expected job structure, and all action full-SHA pins:
  PASS.
- Clean `npm ci`: PASS (`9` packages installed); `npm ls --depth=0`: only
  `supabase@2.118.0`.
- Supabase CLI exact version assertion: PASS (`2.118.0`).
- Locked Python reinstall and `.venv/bin/python -m pip check`: PASS.
- Official disposable local Supabase startup and clean `db reset --local`:
  PASS; the committed migration applied.
- `supabase test db`: PASS (`1` file, `18` tests, `Result: PASS`).
- Full pytest while local Supabase was running: PASS (`22 passed`); JUnit totals
  are `22` tests, `0` failures, `0` errors, and `0` skipped.
- Installed-package import from `/tmp`: PASS; the package resolves from
  `.venv/lib/python3.11/site-packages`.
- Result-file contract: PASS; the three local integration files exist, are
  non-empty, and contain the expected pgTAP and pytest totals.
- Failure-path cleanup simulation: PASS; after an intentional non-zero command,
  `supabase stop --no-backup` left zero Supabase containers.
- The disposable rootless Docker daemon, containers, runtime directory, and
  multi-gigabyte `/tmp` data were removed; host Docker configuration was not
  changed.
- Step 10 implementation scan found no remote project identifier, hosted URL,
  connection string, password, token, secret, or credential.
- Final documentation/status consistency, action-pin structure,
  generated-state, secret, whitespace, and diff checks: PASS.

## Remote activation validation

- Commit: `581d389c9b5072f80cb5eb2409b32a3716e09627`.
- Local HEAD, remote-tracking branch, and Pull Request head matched that commit.
- Pull Request #1 was open, non-draft, and mergeable.
- Workflow: `CI`, run ID `36777531943`, run number `20`, conclusion `success`.
- Job: `Python 3.11`, ID `110099109099`; checkout, Python setup, locked install,
  `pip check`, pytest, result validation, artifact upload, and all post steps
  completed with conclusion `success`.
- Artifact: `pytest-results-python-3.11`, ID `11126805181`, `1489` archive
  bytes, not expired when inspected. GitHub reports digest
  `sha256:79a3bde2c877a4da19d3fa6ef2e2f8dbffebd517636807b370184f2c3139148b`.
- The downloaded artifact contains exactly two non-empty files:
  `pytest.xml` (`3481` bytes) and `pytest.log` (`961` bytes).
- Downloaded JUnit XML: `22` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; final summary is `22 passed in 0.61s`.
- This run proves the exact Step 10 starting commit and existing Python artifact
  contract. Remote validation of the new local integration job is pending commit
  approval and push.

## Required CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Proposed new required database/integration job after remote validation:
  `CI / Local Supabase integration`.
- Local Python reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Local database reproduction after `npm ci`:
  - `npx --no-install supabase start`
  - `npx --no-install supabase db reset --local`
  - `npx --no-install supabase test db`
  - `npx --no-install supabase stop --no-backup`
- Both jobs require no physical hardware, GitHub secret, remote Supabase project,
  hosted PostgreSQL instance, or production service. The local integration job
  uses only Docker-backed disposable services on its clean GitHub runner.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Production tables and columns beyond the approved opaque ingress boundary.
- Production identifiers, transactions, retention, and conflict resolution.
- Production history, current-state, stream identity, reboot, ordering,
  late-data, timestamp trust, and idempotency policy.
- Credential implementation and provisioning details.
- Group/session role and authorization semantics.
- Any authorization path beyond backend-only `service_role` insertion into
  `public.ingest_messages`, including read access and API exposure.
- Production acknowledgement, retry, reconnect, buffer, overflow, and data-loss
  policies.
- Command authority, SLO, production scale, and cost.

## Files changed in Step 10

- `.github/workflows/ci.yml`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

No Python source, Python test, Python dependency, npm dependency, Supabase
configuration, migration, or database test changed.

## Next step

- Step: Step 11 — Measure, document, and prepare branch protection.
- Activation requires the reviewed Step 10 changes to be committed and pushed,
  both Pull Request jobs to succeed on the exact commit, and both published
  result artifacts to be downloaded and inspected.
- Do not enable branch protection or merge the Pull Request without separate
  explicit user approval.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for the next session. Do not start Step 11 in
this session.
