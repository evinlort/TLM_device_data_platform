# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Starting HEAD for Step 9:
  `632643d755c3758d334281994feae305ec9c6855`.
- Step 9 implementation commit:
  `2e46cd6baf5dc013a64b3c0fdde54e34acb11f01`.
- The commit containing this file finalizes the Step 9 handoff; use
  `git rev-parse HEAD` for its exact SHA without creating a self-referential
  state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. Public visibility is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open, mergeable, and points from `ci/github-actions-foundation` to `main`.
- Working tree: contains only the reviewed, uncommitted final Step 9 handoff
  update after remote validation.

## Current milestone

- Step: Step 9 — Add reproducible local database and database tests.
- Status: DONE.
- Completion blockers: none.

## Verified starting state

- Local branch, starting HEAD, remote-tracking branch, and Pull Request head all
  equal `632643d755c3758d334281994feae305ec9c6855`.
- Required workflow `CI` run #18, ID `36761100821`, completed successfully for
  that final Step 8 handoff commit. Every `Python 3.11` job step completed with
  conclusion `success`.
- Its artifact `pytest-results-python-3.11`, ID `11118621855`, is not expired;
  GitHub reports digest
  `sha256:13f8f2e62dc02e6b3065dd5e804b67a53821385ce6a7f4cfab6bd1974e19db00`.
- The artifact was downloaded and inspected. It contains exactly non-empty
  `pytest.xml` and `pytest.log`; the log reports `22 passed`, and parsed JUnit
  totals are `22` tests, `0` failures, `0` errors, and `0` skipped.

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

## Validation

- Local Node: `v22.23.2`; npm: `10.9.8`.
- Clean `npm ci`: PASS (`9` packages installed, `0` vulnerabilities reported).
- `npx supabase --version`: PASS (`2.118.0`).
- `npm ls --depth=0`: PASS; the only direct package is
  `supabase@2.118.0`.
- `supabase/config.toml` parse and required-value assertions: PASS.
- Locked Python reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Workflow-equivalent full pytest with real loopback HTTP: PASS (`22 passed`),
  with non-empty JUnit XML and readable log.
- JUnit parse: PASS (`22` tests, `0` failures, `0` errors, `0` skipped).
- Installed-package import from `/tmp`: PASS; `local_integration.py` resolves
  from `.venv/lib/python3.11/site-packages`.
- Native disposable PostgreSQL `17.9` fallback independently applied the
  migration and confirmed both column definitions, identity mode, RLS, zero
  policies, role privileges, exact bytes, empty bytes, and duplicates.
- A disposable rootless Docker daemon then allowed the locked Supabase CLI to
  start its local stack without system Docker access.
- Official Supabase cycle 1: `db reset --local` PASS; migration applied;
  `supabase test db` PASS (`1` file, `18` tests).
- Live local catalog: PostgreSQL `17.6`, RLS enabled, `0` policies,
  `anon` SELECT denied, `authenticated` INSERT denied, `service_role` INSERT
  granted and SELECT denied.
- Official Supabase cycle 2: clean reset and database test PASS again
  (`18/18`).
- `supabase stop --no-backup`: PASS; no local Supabase containers remained.
- The temporary rootless Docker daemon and its multi-gigabyte `/tmp` data were
  removed without modifying host Docker configuration.
- Secret/identifier scan: PASS; no remote project reference, URL, connection
  string, credential, token, or password appears in the Step 9 source changes.
- Final `git diff --check` and untracked-file whitespace validation after the
  persistent handoff update: PASS.

## Remote Step 9 validation

- Commit: `2e46cd6baf5dc013a64b3c0fdde54e34acb11f01`.
- Local HEAD, remote-tracking branch, and Pull Request head matched that commit
  after push.
- Pull Request #1 remained open, non-draft, and mergeable.
- Workflow: `CI`, run ID `36777217649`, run number `19`, conclusion `success`.
- Job: `Python 3.11`, ID `110098037814`; checkout, Python setup, locked install,
  `pip check`, pytest, result validation, artifact upload, and all post steps
  completed with conclusion `success`.
- Artifact: `pytest-results-python-3.11`, ID `11125259470`, `1489` archive
  bytes, not expired when inspected. GitHub reports digest
  `sha256:6d67301a53cd2005040400c5268eb28049d442ee3a6d9d8d9bef9c0b7e36793b`.
- The downloaded artifact contains exactly two non-empty files:
  `pytest.xml` (`3481` bytes) and `pytest.log` (`961` bytes).
- Downloaded JUnit XML: `22` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; final summary is `22 passed in 0.22s`.
- This unchanged workflow does not yet exercise Supabase. The database job is
  intentionally deferred to Step 10; Step 9's two official local Supabase
  cycles remain the database-specific validation evidence.

## Required CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local Python reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Local database reproduction after `npm ci`:
  - `npx supabase start`
  - `npx supabase db reset --local`
  - `npx supabase test db`
  - `npx supabase stop --no-backup`
- The current required workflow is intentionally unchanged and still uses no
  physical hardware, Docker, secret, credential, production service, Supabase
  project, or PostgreSQL instance. Step 10 will add the disposable local
  database/integration job.

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

## Files changed in Step 9

- `.gitignore`
- `supabase/.gitignore`
- `supabase/config.toml`
- `supabase/migrations/20260930233000_create_ingest_messages.sql`
- `supabase/tests/ingest_messages.test.sql`
- `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

No Python source, Python test, Python dependency, npm dependency, or GitHub
Actions workflow file changed.

## Next step

- Step: Step 10 — Add the local integration CI job.
- Activation requires the reviewed Step 9 changes to be committed and pushed,
  the updated Pull Request workflow to succeed, and its published test-results
  artifact to be downloaded and inspected.
- Step 10 must run only disposable local infrastructure on a clean runner and
  must not link to or depend on any remote Supabase project.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for the next session. Do not start Step 10 in
this session.
