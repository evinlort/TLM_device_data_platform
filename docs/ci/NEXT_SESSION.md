# Next Codex Session

## Activation condition

Step 7 may start only after Step 6 is committed, pushed, successful in the
Pull Request workflow, and the published test-results artifact has been
downloaded and inspected. Before any Step 7 change, verify that the actual
branch, HEAD, remote, clean working tree, Pull Request, latest required CI
result, artifact listing, and downloaded artifact agree with
`docs/ci/CI_STATE.md`. If Step 6 changes are still uncommitted, its remote
check is pending or failed, or its artifact has not been inspected, finish or
investigate Step 6 instead of starting Step 7.

## Step

Step 7 — Establish the local API/storage integration boundary

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `src/tlm_device_data_platform/simulation.py`
- `src/tlm_device_data_platform/telemetry_fixture.py`
- `tests/test_delivery_scenarios.py`
- `tests/test_ordering_scenarios.py`
- `tests/test_simulation.py`
- `tests/test_telemetry_fixture.py`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `requirements/test.txt`

Do not read unrelated future files unless the current step requires them.

## Goal

Establish and test the smallest provider-independent local API and storage
integration boundary that can accept opaque device telemetry through a real
local HTTP boundary where practical, while keeping device-facing code
independent of Supabase and avoiding unconfirmed Product semantics.

## Current verified starting point

- Required CI has deterministic package, simulator, telemetry-fixture,
  delivery, ordering, stream, late-data, and clock-skew coverage.
- `Transport` and `DurableQueue` carry opaque serialized `bytes` and have no
  Supabase knowledge.
- `TelemetryFixtureProjection` is explicitly test-only orchestration and is
  not a production storage adapter or conflict-resolution policy.
- No API framework, HTTP server/client dependency, Storage Adapter, database,
  Supabase configuration, or version-controlled schema exists.
- Product telemetry, authentication, authorization, storage, idempotency,
  ordering, and acknowledgement semantics remain open.

## Allowed scope

- Inspect the existing architecture and define the minimum provider-independent
  API and Storage Adapter abstractions needed by this step.
- Add deterministic local integration tests using real local HTTP and local
  storage boundaries where possible without production services.
- Add only dependencies that are necessary, pinned, and reproducibly
  validated for this boundary.
- CI handoff updates and validation required by this step.

## Out of scope

- Supabase schema, migrations, CLI bootstrap, PostgreSQL, production or remote
  database access, and Step 8 implementation.
- Production credentials, identity, roles, authorization, RLS policy, device
  provisioning, or secrets.
- Confirming a production telemetry envelope, acknowledgement, idempotency,
  ordering, retention, conflict-resolution, or error-response contract.
- Deployment, branch protection, caching, lint, type checking, coverage
  thresholds, performance, scale, or SLO claims.

## Required investigation

- Reconfirm repository, Pull Request, CI, and artifact state before changes.
- Determine whether any actual API or Storage Adapter abstraction exists; if
  none exists, introduce only the minimum provider-independent boundary.
- Keep Supabase-specific URLs, tables, credentials, and schema details out of
  the device-facing contract.
- Prefer a real loopback HTTP boundary and deterministic temporary local
  storage without requiring network services, Docker, secrets, or production
  infrastructure.
- Keep fixture-only fields and outcomes clearly separated from Product
  requirements.

## Validation

Run the locked install, `pip check`, and full pytest suite. Exercise the local
HTTP/storage integration deterministically, repeat the relevant suite, confirm
installed-package imports, scan for forbidden production dependencies and
credentials, confirm the workflow still creates both test-result files, and
run `git diff --check`. After approved commit and push, verify the updated Pull
Request workflow and inspect its published artifact.

## Stop condition

After Step 7 implementation, validation, state update, approved commit/push,
successful Pull Request workflow verification, and artifact inspection. Do not
start Step 8 in the same session.
