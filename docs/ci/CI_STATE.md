# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Starting committed HEAD for Step 12 and current committed HEAD:
  `9f74490a0f415aaaf23a202c5bd0665a432f8b1a`.
- Final Step 11 handoff commit:
  `9f74490a0f415aaaf23a202c5bd0665a432f8b1a`.
- Step 11 implementation commit:
  `55e8a18e7988445fffb4411a3648d4cdd6a629ae`.
- Final Step 10 handoff commit:
  `5c11432939c3efe17f8189d09e64042e03d60822`.
- Step 10 implementation commit:
  `08b10d5eb0c450251fe23e3618a6d93ac7ac4aaa`.
- Step 9 implementation commit:
  `2e46cd6baf5dc013a64b3c0fdde54e34acb11f01`.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. Public visibility is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open, non-draft, technically mergeable, and points from
  `ci/github-actions-foundation` to `main`. Its merge-state status is `blocked`
  because the approved conversation-resolution rule exposes one old unresolved
  and now outdated review thread.
- Local HEAD, remote-tracking branch, and Pull Request head all match
  `9f74490a0f415aaaf23a202c5bd0665a432f8b1a`.
- Working tree: contains only the uncommitted Step 12 persistent handoff and
  documentation update.

## Current milestone

- Step: Step 12 — Apply explicitly approved branch protection.
- Status: READY_FOR_COMMIT.
- Completion blocker: none for the repository setting. The approved protection
  is active and verified; the documentation-only Step 12 handoff still requires
  separate explicit approval before commit/push and subsequent remote CI and
  artifact verification.

## Step 12 verified starting state

- Final Step 11 handoff commit, local HEAD, remote-tracking branch, and Pull
  Request head all matched
  `9f74490a0f415aaaf23a202c5bd0665a432f8b1a`; the working tree was clean.
- Pull Request #1 was open, non-draft, mergeable, and targeted `main`.
- Workflow `CI`, run #24, ID `36902702860`, completed successfully for that
  exact commit.
- Job `Python 3.11`, ID `110505497845`, and all of its main/post steps completed
  successfully. Job `Local Supabase integration`, ID `110505497485`, and all
  setup, database, test, cleanup, artifact, and post steps also completed
  successfully.
- Check runs `Python 3.11` and `Local Supabase integration` both completed with
  conclusion `success` and were produced by GitHub Actions App `15368`.
  Third-party `Sourcery review` belonged to App `48477`, was skipped, and was
  excluded from the approved required-check set.
- Artifact `pytest-results-python-3.11`, ID `11182775775`, archive size `1491`
  bytes, had matching GitHub and independently computed SHA-256
  `7eb19c484e34d09155a04dc6f740ff57b88ed47904b9ed79b9bfc5d105e91801`.
  It contained exactly non-empty `pytest.xml` (`3481` bytes) and `pytest.log`
  (`961` bytes); JUnit reported `22` tests with zero failures, errors, or
  skipped tests, and pytest reported `22 passed in 0.30s`.
- Artifact `local-integration-results`, ID `11181977994`, archive size `2242`
  bytes, had matching GitHub and independently computed SHA-256
  `472d0315c32090fbcc55a49409cdcbf4486745b9ccb01fc2ba89186b124072b5`.
  It contained exactly non-empty `database-tests.log` (`1395` bytes),
  `pytest.xml` (`3481` bytes), and `pytest.log` (`979` bytes); pgTAP reported
  one file, `18` tests, and `Result: PASS`, while JUnit reported `22` tests with
  zero failures, errors, or skipped tests and pytest reported
  `22 passed in 0.44s`.
- Artifact scans found no hosted Supabase endpoint, PostgreSQL connection URL,
  JWT-like value, token, password, secret, or service-role key. The disposable
  download directory was removed after inspection.
- Pre-change read-back returned `404 Branch not protected` for `main` and an
  empty repository-ruleset list.

## Step 11 verified starting state

- Local branch, starting HEAD, remote-tracking branch, and Pull Request head all
  equal `5c11432939c3efe17f8189d09e64042e03d60822`; the working tree was clean.
- Pull Request #1 was open, non-draft, mergeable, and targeted `main`.
- Required workflow `CI` run #22, ID `36874430650`, completed successfully for
  that exact final Step 10 handoff commit.
- Job `Python 3.11`, ID `110410104000`, and every main/post step completed with
  conclusion `success`.
- Job `Local Supabase integration`, ID `110410104398`, and every main/post step
  completed with conclusion `success`, including local cleanup.
- Artifact `pytest-results-python-3.11`, ID `11168572267`, was downloaded and
  inspected. Its independent SHA-256 equals GitHub's digest
  `sha256:9cd599649d7e0666aaf185832d2937d8f8eb3dd5c46031728df2bd38aca6e39b`.
  It contains exactly non-empty `pytest.xml` (`3481` bytes) and `pytest.log`
  (`961` bytes); JUnit totals are `22` tests, `0` failures, `0` errors, and `0`
  skipped, and the log reports `22 passed in 0.20s`.
- Artifact `local-integration-results`, ID `11168014395`, was downloaded and
  inspected. Its independent SHA-256 equals GitHub's digest
  `sha256:f6005522d6c62b966f11a40a33d6735deb2e3e21fd4239e937451f4bdc923e64`.
  It contains exactly non-empty `database-tests.log` (`1395` bytes),
  `pytest.xml` (`3481` bytes), and `pytest.log` (`979` bytes). The database log
  reports `Files=1, Tests=18` and `Result: PASS`; JUnit totals are `22` tests,
  `0` failures, `0` errors, and `0` skipped; pytest reports `22 passed in
  0.30s`.

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

## Implemented in Step 11

- Added exact `coverage.py` `7.16.1` to the locked Python test environment in
  both `pyproject.toml` and `requirements/test.txt`.
- Configured statement and branch measurement for the installed
  `tlm_device_data_platform` package. No `fail_under`, coverage artifact, new CI
  command, or required coverage check was added.
- The complete 22-test suite measures `88%` combined coverage: `253`
  statements with `22` missed and `56` branches with `15` partial.
- Added `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`, a Russian guide for exact
  local reproduction, artifact contracts, coverage, simulator fixtures, real
  loopback HTTP/storage tests, local Supabase and pgTAP, safe test extension,
  failure diagnosis, open Product decisions, and future branch protection.
- Added `CI-DEC-015` to preserve the measured coverage baseline without
  converting it into an arbitrary policy threshold.
- Confirmed across successful runs #21 and #22 that the check contexts are
  `Python 3.11` and `Local Supabase integration`; both are produced by GitHub
  Actions App `15368`. Their Pull Request display names are respectively
  `CI / Python 3.11` and `CI / Local Supabase integration`.
- Read-only GitHub API inspection returned `404 Branch not protected` for
  `main` protection and an empty repository-ruleset list. No repository
  setting, branch protection, Pull Request state, or remote Supabase state was
  changed.
- No workflow, Product source, Python test, npm dependency, Supabase
  configuration, migration, database test, or schema changed.

## Step 11 local validation

- Exact locked install in a fresh virtual environment: PASS; installed
  `coverage==7.16.1`, `pytest==9.1.1`, and the pinned transitive set, followed
  by a successful `pip check`.
- Full clean-environment coverage run: PASS (`22 passed`); `coverage report`
  reproduced the `88%` total and exact statement/branch counts recorded above.
- Existing-environment standard Python artifact reproduction: PASS (`22`
  tests, `0` failures, `0` errors, `0` skipped); exactly non-empty
  `test-results/pytest.xml` and `test-results/pytest.log` were produced.
- Clean `npm ci`: PASS (`9` packages); `npm ls --depth=0` listed only
  `supabase@2.118.0`, and the exact CLI assertion returned `2.118.0`.
- A clean disposable local Supabase start and `db reset --local`: PASS; the
  committed migration applied.
- `supabase test db`: PASS (`1` file, `18` tests, `Result: PASS`).
- Full pytest while local Supabase was running: PASS (`22` tests, `0`
  failures, `0` errors, `0` skipped).
- Local integration result contract: PASS; exactly non-empty
  `database-tests.log`, `pytest.xml`, and `pytest.log` contain the expected
  pgTAP and pytest totals.
- `supabase stop --no-backup`: PASS; the isolated Docker daemon reported zero
  remaining containers and was then stopped and removed with its disposable
  runtime data. Host Docker configuration was not changed.
- The first isolated rootless Docker attempt used the `vfs` driver and was
  abandoned after registry-rate and temporary disk-quota failures. Its daemon
  and UID-mapped storage were removed. A fresh `overlay2` daemon completed the
  exact validation after transient registry retries; no failed attempt was
  counted as validation evidence.
- The ordinary sandbox disallowed loopback socket creation and dependency
  download. The same commands were repeated unchanged with only the required
  loopback/network capabilities; both then passed.
- Dependency/configuration assertions, documented-path checks, artifact
  parsing, secret and hosted-endpoint scans, generated-state checks,
  whitespace checks, and confirmation that workflow/source/tests/package lock/
  Supabase files are unchanged: PASS.

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

## Step 10 starting-state remote validation

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
- This run proved the exact Step 10 starting commit and existing Python artifact
  contract before the implementation changed the workflow.

## Remote Step 10 validation

- Implementation commit:
  `08b10d5eb0c450251fe23e3618a6d93ac7ac4aaa`.
- Local HEAD, remote-tracking branch, and Pull Request head matched that exact
  commit. Pull Request #1 remained open, non-draft, mergeable, and targeted
  `main`.
- Workflow: `CI`, run ID `36871919192`, run number `21`, conclusion `success`.
- Existing job: `Python 3.11`, ID `110401569886`, duration `11s`. Checkout,
  Python setup, locked install, `pip check`, pytest, result validation, artifact
  upload, and all post steps completed with conclusion `success`.
- New job: `Local Supabase integration`, ID `110401569122`, duration `2m31s`.
  Checkout, Node and Python setup, locked installs, exact CLI assertion, local
  Supabase start, database reset, pgTAP, full pytest, unconditional cleanup,
  result validation, artifact upload, and all post steps completed with
  conclusion `success`.
- Artifact `pytest-results-python-3.11`, ID `11168265241`, contained exactly
  non-empty `pytest.log` (`961` bytes) and `pytest.xml` (`3481` bytes). Its
  archive size was `1488` bytes; GitHub and an independent streamed download
  both reported
  `sha256:5d7feafde9d9f3dbbb641b6be15c4985080bfeb02653e692207dc378eee1ca91`.
- The existing-job JUnit totals were `22` tests, `0` failures, `0` errors, and
  `0` skipped; its log ended with `22 passed in 0.21s`.
- Artifact `local-integration-results`, ID `11167561341`, contained exactly
  non-empty `database-tests.log` (`1395` bytes), `pytest.log` (`979` bytes),
  and `pytest.xml` (`3481` bytes). Its archive size was `2236` bytes; GitHub and
  an independent streamed download both reported
  `sha256:f52c7b1f8fa38275ae7afc4d6267c6f2c8a8a0b3476eefd2e17d5adddc1793bc`.
- The integration JUnit totals were `22` tests, `0` failures, `0` errors, and
  `0` skipped; its pytest log ended with `22 passed in 0.19s`. The database log
  reported `Files=1, Tests=18` and `Result: PASS`.
- Artifact and complete new-job log scans found no hosted project URL, database
  URL, project reference, generated local connection URL, key, password, token,
  or secret. The database log's notice that CLI `2.119.0` exists does not change
  the intentional project lock at `2.118.0`.
- Successful `Cleanup local Supabase` and every subsequent step prove that the
  clean hosted runner completed the disposable lifecycle and preserved both
  required result contracts without a remote Supabase dependency.

## Remote Step 11 validation

- Implementation commit:
  `55e8a18e7988445fffb4411a3648d4cdd6a629ae`, message
  `ci: document testing and coverage baseline`.
- Local HEAD, remote-tracking branch, and Pull Request head matched that exact
  commit. Pull Request #1 remained open, non-draft, mergeable, and targeted
  `main`.
- Workflow: `CI`, run ID `36890182877`, run number `23`, conclusion `success`.
- Job `Python 3.11`, ID `110463533621`, duration `19s`: every setup, locked
  install, dependency check, pytest, result validation, artifact upload, post,
  and completion step concluded `success`.
- Job `Local Supabase integration`, ID `110463533001`, duration `2m41s`: every
  Node/Python setup, locked install, exact CLI check, local startup, database
  reset, pgTAP, Python flow, unconditional cleanup, result validation,
  artifact upload, post, and completion step concluded `success`.
- Exact-commit check runs reconfirmed contexts `Python 3.11` and
  `Local Supabase integration`, both completed successfully and both produced
  by GitHub Actions App `15368`. Third-party `Sourcery review` was skipped and
  remains outside required CI.
- Artifact `pytest-results-python-3.11`, ID `11176261987`, archive size `1494`
  bytes, was not expired. GitHub metadata and the independently downloaded ZIP
  both reported
  `sha256:4d969634cf135ac9c623fe0e68d5e6e9cf48f28a3b1dcf1762f9fab6663d0acd`.
  It contained exactly non-empty `pytest.xml` (`3481` bytes) and `pytest.log`
  (`961` bytes); JUnit totals were `22` tests, `0` failures, `0` errors, and
  `0` skipped, and the log ended with `22 passed in 0.26s`.
- Artifact `local-integration-results`, ID `11175808418`, archive size `2230`
  bytes, was not expired. GitHub metadata and the independently downloaded ZIP
  both reported
  `sha256:3eb50ab646a7bdac7a39dab8d71525b3a00aa8ea9d0bf7aa5bead15b68d2a6d0`.
  It contained exactly non-empty `database-tests.log` (`1362` bytes),
  `pytest.xml` (`3481` bytes), and `pytest.log` (`979` bytes). The database log
  reported `Files=1, Tests=18` and `Result: PASS`; JUnit totals were `22`
  tests, `0` failures, `0` errors, and `0` skipped; pytest ended with
  `22 passed in 0.35s`.
- Downloaded artifact scans found no hosted database URL, generated local
  endpoint, token, key, or credential. The disposable download directory was
  removed after inspection.
- Final read-only checks still returned `404 Branch not protected` for `main`
  and an empty repository-ruleset list. No GitHub repository setting or Pull
  Request state changed during Step 11.
- GitHub emitted an informational annotation that `ubuntu-latest` will begin
  migrating to Ubuntu 26 on `2026-10-19`. The current exact run was successful;
  changing the existing Python job runner was outside Step 11.

## Step 12 protection application and validation

- The user explicitly approved `PROTECTION v1`, including every field in the
  proposed classic branch-protection request. GitHub rejected the first request
  with HTTP `422` because its active schema treats `contexts` and `checks` as
  mutually exclusive even when `contexts` is an empty array. Read-back proved
  that the rejected request created no protection or ruleset.
- The user then explicitly approved `PROTECTION v1.1`, whose only structural
  change was omitting the empty `contexts` member while preserving the exact
  provider-bound `checks` and every other setting.
- One successful `PUT` created classic branch protection for `main` with:
  - `strict = true`;
  - required check `Python 3.11` from GitHub Actions App `15368`;
  - required check `Local Supabase integration` from GitHub Actions App
    `15368`;
  - Pull Request reviews enabled with zero required approvals,
    `dismiss_stale_reviews = false`, `require_code_owner_reviews = false`, and
    `require_last_push_approval = false`;
  - administrator enforcement enabled and no push restrictions or bypass list;
  - conversation resolution required;
  - signed commits and linear history not required;
  - force pushes and branch deletion disallowed;
  - branch creation blocking, branch locking, and fork syncing disabled.
- Independent full and subresource read-backs matched every approved field.
  `main` now reports `protected = true`; required-signature read-back reports
  `enabled = false`; repository rulesets remain empty.
- Pull Request #1 remains open, non-draft, and technically mergeable. It is not
  merged or closed. GitHub now reports merge-state `blocked`: the branch is not
  behind `main` and both required checks are successful, but one old review
  conversation from commit `72380506cbae287db8858a55e041fd4186054f1a`
  remains unresolved and is now outdated. This is the intended observable
  effect of `required_conversation_resolution = true`; the thread was not
  resolved because doing so was not part of the approved mutation.
- No workflow, CI command, coverage policy, Product source, test, dependency,
  Supabase file, database schema, remote Supabase state, Pull Request content,
  or repository ruleset changed.
- Added `CI-DEC-016` and updated the testing/protection guide and persistent
  handoff to record the approved governance contract and exact read-back.

## Required CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python check: context `Python 3.11`, displayed as
  `CI / Python 3.11`, produced by GitHub Actions App `15368`.
- Required database/integration check: context
  `Local Supabase integration`, displayed as
  `CI / Local Supabase integration`, produced by GitHub Actions App `15368`.
- Both checks are enforced by classic branch protection on `main`, with
  `strict = true` and explicit provider binding to App `15368`. Repository
  rulesets remain absent.
- Detailed reproduction and diagnosis guide:
  `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`.
- Local Python reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Local coverage measurement after the same locked install:
  - `.venv/bin/python -m coverage erase`
  - `.venv/bin/python -m coverage run -m pytest`
  - `.venv/bin/python -m coverage report`
- Local database reproduction after `npm ci`:
  - `npx --no-install supabase start`
  - `npx --no-install supabase db reset --local`
  - `npx --no-install supabase test db`
  - `npx --no-install supabase stop --no-backup`
- Both jobs require no physical hardware, GitHub secret, remote Supabase project,
  hosted PostgreSQL instance, or production service. The local integration job
  uses only Docker-backed disposable services on its clean GitHub runner.
- Coverage is measured locally at `88%` but has no threshold and is not a
  required check.

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

## Files changed in Step 12

- `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

The only non-file change is the explicitly approved classic branch-protection
configuration for `main`. No workflow, Python source/test/dependency, npm
dependency, package lock, Supabase configuration, migration, database test,
schema, Product behavior, remote Supabase state, Pull Request content, or
repository ruleset changed.

## Files changed in Step 11

- `.gitignore`
- `pyproject.toml`
- `requirements/test.txt`
- `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

No workflow, Python source, Python test, npm dependency, package lock,
Supabase configuration, migration, database test, schema, or Product behavior
changed.

## Next step

- Step: finish Step 12 remote verification after the documentation-only handoff
  commit is explicitly approved, committed, and pushed.
- Verify the exact pushed commit, both Pull Request jobs and both published
  artifacts, and confirm that the complete `PROTECTION v1.1` read-back remains
  unchanged.
- Then prepare the final Step 12 handoff. No later CI implementation step is
  currently authorized.
- Do not resolve review conversations, merge or close Pull Request #1, change
  protection, add a coverage threshold, or begin Product work without separate
  explicit direction.

Use `docs/ci/BOOTSTRAP_PROMPT.md` if a new session is needed. Do not start a new
logical CI step in this session.
