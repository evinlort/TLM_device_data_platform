# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`.
- Starting HEAD for Step 8:
  `11a96b308aa26a067cd2aeb995662f06f9c35471`.
- Step 8 implementation commit:
  `ef051ddeb7264ddbc392ba80c894d0d8027a46ae`.
- The commit containing this file finalizes the Step 8 handoff; use
  `git rev-parse HEAD` for its exact SHA without creating a self-referential
  state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: public `evinlort/TLM_device_data_platform` with `main` as
  the default branch. Public visibility is intentional.
- Pull Request: [#1 — Add Python validation and pull request CI](https://github.com/evinlort/TLM_device_data_platform/pull/1)
  is open, mergeable, and points from `ci/github-actions-foundation` to `main`.
- Working tree: expected to be clean after the approved final Step 8 handoff
  commit.

## Current milestone

- Step: Step 8 — Define the Supabase schema bootstrap strategy.
- Status: DONE.
- Completion blockers: none.

## Verified starting state

- Local branch, HEAD, remote-tracking branch, and Pull Request head all equal
  `11a96b308aa26a067cd2aeb995662f06f9c35471`.
- Required workflow `CI` run #16, ID `36747992035`, completed successfully for
  that final Step 7 handoff commit. Every `Python 3.11` job step completed with
  conclusion `success`.
- Its artifact `pytest-results-python-3.11`, ID `11112439370`, was downloaded
  and inspected. GitHub and the downloaded ZIP both report SHA-256
  `92a56afc6382c97df635277829ba29234d32c844dce03f84f71d7a4d9344b69c`.
- The ZIP passed integrity checking and contains exactly non-empty
  `pytest.xml` (`3481` bytes) and `pytest.log` (`961` bytes). The log reports
  `22 passed`; parsed JUnit totals are `22` tests, `0` failures, `0` errors,
  and `0` skipped.
- This newer final-handoff run supplements the Step 7 implementation run #15
  already recorded in history; both are successful and their artifacts were
  inspected.

## Implemented in Step 8

- Added project-scoped Node tooling metadata with exact Supabase CLI
  `2.118.0`, Node.js `>=20`, and a generated npm lock file.
- Added `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md` defining:
  - ordered SQL migrations as the future Git source of truth;
  - separate authorized-remote and approved-greenfield bootstrap paths;
  - explicit review of generated `config.toml` and baseline SQL;
  - credential and generated-state boundaries;
  - disposable local rebuild expectations for Step 9;
  - remote mutation commands that require separate authorization;
  - the prohibition on automated production `db reset --linked`.
- Added `CI-DEC-012` to preserve the migration-backed bootstrap decision.
- Added `node_modules/` and generated `test-results/` to `.gitignore`.

## Current database state

- Repository inspection found no Supabase configuration, migrations,
  declarative schema, seed, database tests, database client, or other SQL
  schema source.
- No remote Supabase schema source was explicitly authorized for Step 8.
- No `supabase/config.toml` or migration was created because current
  `supabase init` output includes a PostgreSQL major version and many local
  Auth/API/Storage defaults that are not verified project facts.
- No Supabase login, project link, schema pull, database reset, database push,
  migration repair, Docker service, or local/remote database operation was
  performed.
- `TemporaryDirectoryStorage` remains a filesystem CI adapter and is not a
  database, schema prototype, or Supabase emulator.

## Tool and strategy facts

- Official Supabase guidance verified on 2026-09-30 recommends a
  project-scoped npm dependency pinned for the team and requires Node.js 20 or
  later for npm/npx use.
- GitHub's official `supabase/cli` latest-stable endpoint reported release
  `v2.118.0`, published 2026-09-25; it was not a prerelease.
- Official guidance says `supabase init` creates `supabase/config.toml`, local
  development requires a Docker-compatible runtime, migrations live under
  `supabase/migrations/`, and `db reset` rebuilds a local database from them.
- `db pull` requires a linked project or explicit database URL and a Docker
  daemon for its shadow database. Current guidance shows it may offer to update
  remote migration history, so even discovery needs explicit target approval.
- Official team guidance is to make schema changes through local migrations
  after bootstrap rather than direct changes to a shared remote database.

## Validation

- Local Node: `v22.23.2`; npm: `10.9.8`.
- Clean `npm ci`: PASS (`9` packages installed, `0` vulnerabilities reported).
- `npx supabase --version`: PASS (`2.118.0`).
- `npm ls --depth=0`: PASS; the only direct package is
  `supabase@2.118.0`.
- JSON/lock assertions: PASS; package is private, Node baseline is `>=20`, and
  manifest plus lock both resolve exact CLI version `2.118.0`.
- Locked Python reinstall: PASS.
- `.venv/bin/python -m pip check`: PASS
  (`No broken requirements found`).
- Workflow-equivalent full pytest with real loopback HTTP: PASS (`22 passed`),
  with non-empty JUnit XML and readable log.
- JUnit parse: PASS (`22` tests, `0` failures, `0` errors, `0` skipped).
- Installed-package import from `/tmp`: PASS; `local_integration.py` resolves
  from `.venv/lib/python3.11/site-packages`.
- Repository scan confirms no `supabase/` directory, remote credential,
  production URL, secret reference, connection string, `pull_request_target`,
  or new required-CI production dependency.
- Existing workflow still creates, validates, and uploads both pytest result
  files with always-run behavior.
- `git diff --check` plus untracked-file whitespace validation: PASS.

Remote Step 8 validation:

- Commit: `ef051ddeb7264ddbc392ba80c894d0d8027a46ae`.
- Workflow: `CI`, run ID `36760536805`, run number `17`, conclusion
  `success`.
- Job: `Python 3.11`; checkout, Python setup, locked install, `pip check`,
  pytest, result validation, artifact upload, and all post steps completed with
  conclusion `success`.
- Artifact: `pytest-results-python-3.11`, ID `11118133887`, `1494` archive
  bytes, not expired when inspected.
- GitHub digest and downloaded ZIP SHA-256 both equal
  `44b67a55d353dcb32250aabc9ff15bd59edcf3665ed5b5ae92578d0fb03364ee`.
- ZIP integrity: PASS; it contains exactly `pytest.xml` (`3481` bytes) and
  `pytest.log` (`961` bytes), both non-empty.
- Downloaded JUnit XML: `22` tests, `0` failures, `0` errors, `0` skipped.
- Downloaded pytest log: PASS; final summary is `22 passed in 0.19s`.

## Required CI

- Pull Request workflow: `.github/workflows/ci.yml`.
- Required Python job: `CI / Python 3.11`.
- Local Python reproduction:
  - `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Supabase CLI tool reproduction:
  - `npm ci`
  - `npx supabase --version`
- Required CI still uses no physical hardware, Docker, secret, credential,
  production service, Supabase project, or PostgreSQL instance.

## Product decisions still OPEN

- Product telemetry envelope, field names, schema versions, field semantics,
  and rates per `system_type`.
- Authoritative database schema source and, if remote, exact authorized project,
  environment, schema scope, and PostgreSQL major version.
- Production tables, columns, identifiers, constraints, transactions,
  retention, and conflict-resolution policy.
- Production history, current-state, stream identity, reboot, ordering,
  late-data, timestamp trust, and idempotency policy.
- Credential implementation and provisioning details.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Production acknowledgement, retry, reconnect, buffer, overflow, and data-loss
  policies.
- Command authority, SLO, production scale, and cost.

## Files changed in Step 8

- `.gitignore`
- `package.json`
- `package-lock.json`
- `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`

No Python source, test, dependency, or GitHub Actions workflow file changed.

## Next step

- Step: Step 9 — Add a reproducible local database and confirmed database
  tests.
- Activation requires Step 8 to be committed, pushed, remotely successful, and
  artifact-inspected, plus an explicitly authorized existing schema source or
  approved greenfield schema requirements.
- If the schema-source prerequisite is absent, the next session must stop and
  request it rather than invent tables, roles, RLS, or tests.

Use `docs/ci/BOOTSTRAP_PROMPT.md` for the next session. Do not start Step 9 in
this session.
