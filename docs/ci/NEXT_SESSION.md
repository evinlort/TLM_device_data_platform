# Next Codex Session

## Activation condition

Step 8 may start only after Step 7 is committed, pushed, successful in the
Pull Request workflow, and the published test-results artifact has been
downloaded and inspected. Before any Step 8 change, verify that the actual
branch, HEAD, remote, clean working tree, Pull Request, latest required CI
result, artifact listing, and downloaded artifact agree with
`docs/ci/CI_STATE.md`. If Step 7 changes are still uncommitted, its remote
check is pending or failed, or its artifact has not been inspected, finish or
investigate Step 7 instead of starting Step 8.

## Step

Step 8 — Define the Supabase schema bootstrap strategy

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `src/tlm_device_data_platform/local_integration.py`
- `tests/test_local_integration.py`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/test.txt`

Inspect any Supabase/schema/configuration files that exist at the start of the
session. Do not read unrelated future files unless the current step requires
them.

## Goal

Determine and document a safe, reproducible strategy for establishing a
version-controlled local Supabase/PostgreSQL schema from the repository and
any explicitly authorized schema source, without destructive production
operations or invented Product authorization/data semantics.

## Current verified starting point

- Required CI has a provider-independent `StorageAdapter`, an opaque WSGI API,
  and deterministic real-loopback/local-filesystem integration coverage.
- Device-facing `Transport` and API/storage boundaries contain no Supabase
  URLs, credentials, tables, or schema details.
- No Supabase configuration, migration, PostgreSQL schema, database test, CLI
  dependency, or local database job exists.
- Product telemetry, identity, authorization, RLS, retention, idempotency,
  ordering, and persistence semantics remain open.

## Allowed scope

- Inspect repository schema/configuration sources and any remote source the
  user explicitly authorizes.
- Verify current official Supabase CLI and local-development guidance.
- Explain and record the migration/bootstrap strategy before any schema pull
  or implementation.
- Add only the minimal non-destructive bootstrap configuration justified by
  verified facts and the exact Step 8 strategy.
- CI handoff updates and validation required by this step.

## Out of scope

- Destructive production or remote database operations.
- Inventing tables, columns, credentials, roles, RLS, authorization, retention,
  idempotency, ordering, or conflict-resolution rules.
- Step 9 local database rebuild/tests and Step 10 integration CI job.
- Production deployment, branch protection, caching, lint, type checking,
  coverage thresholds, performance, scale, or SLO claims.

## Required investigation

- Reconfirm repository, Pull Request, CI, and artifact state before changes.
- Determine whether any repository or explicitly authorized remote schema
  source exists at that time.
- Verify current official Supabase CLI installation, initialization, local
  development, migration, schema pull, and safety guidance.
- Explain the proposed source of truth and bootstrap/rebuild flow before
  running any schema command.
- Stop for explicit user authorization before accessing a remote schema or
  performing any operation whose target or destructive effect is unclear.

## Validation

Validate every configuration or documentation change that Step 8 actually
introduces. Preserve the locked Python checks and full pytest suite, confirm
that required CI still has no production service or secret dependency, verify
installed-package imports where relevant, confirm the test-result artifact
contract, and run `git diff --check`. After approved commit and push, verify
the updated Pull Request workflow and inspect its published artifact.

## Stop condition

After Step 8 strategy/configuration, validation, state update, approved
commit/push, successful Pull Request workflow verification, and artifact
inspection. Do not start Step 9 in the same session.
