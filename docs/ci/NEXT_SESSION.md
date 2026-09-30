# Next Codex Session

## Activation condition

Step 10 may start only after Step 9 is committed, pushed, successful in the
Pull Request workflow, and the published Python test-results artifact has been
downloaded and inspected. Verify the actual branch, HEAD, remote, clean working
tree, Pull Request, latest required CI result, artifact listing, and downloaded
artifact against `docs/ci/CI_STATE.md` before any change.

The Step 9 migration and database test must be present in the verified remote
commit. Do not substitute the authorized development project for local CI and
do not deploy the migration remotely as part of activation.

## Step

Step 10 — Add the local integration CI job

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`
7. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `.github/workflows/ci.yml`
- `package.json`
- `package-lock.json`
- `supabase/config.toml`
- `supabase/migrations/20260930233000_create_ingest_messages.sql`
- `supabase/tests/ingest_messages.test.sql`
- `src/tlm_device_data_platform/local_integration.py`
- `tests/test_local_integration.py`

Do not read or change unrelated future files unless this step requires them.

## Goal

Add one reproducible GitHub-hosted Pull Request job that starts only disposable
local Supabase/PostgreSQL infrastructure, rebuilds the approved migration from
Git, runs the database tests, exercises the existing provider-independent local
integration boundary where justified, and always cleans up. It must require no
physical hardware, production service, remote Supabase project, or secret.

## Required approach

- Use the exact project-scoped Supabase CLI version and npm lock already in the
  repository.
- Verify current GitHub-hosted runner and Supabase CLI requirements before
  choosing runner setup or commands.
- Keep the existing `CI / Python 3.11` check stable unless a reviewed workflow
  reason requires a change.
- Add a separate, clearly named local integration/database job with an explicit
  timeout.
- Start Supabase locally without `supabase link`, remote credentials, or remote
  identifiers.
- Rebuild from `supabase/migrations/` and run `supabase test db`.
- Connect the existing local API/storage integration flow to the approved
  ingress table only if the smallest adapter and test can preserve opaque bytes
  without inventing API, acknowledgement, transaction, or Product semantics.
- Make cleanup execute reliably after success or failure and preserve useful
  failure logs/artifacts without exposing credentials.
- Reproduce the workflow locally as far as the environment allows.

## Out of scope and safety limits

- No `supabase link`, `db pull`, `db push`, `migration repair`, linked reset,
  remote SQL, or any other remote Supabase access or mutation.
- Do not add production secrets, project references, database passwords, or
  connection strings to GitHub Actions, Git, logs, or artifacts.
- Do not invent richer tables, fields, constraints, policies, seed data,
  telemetry parsing, identity, retention, ordering, idempotency, or authorization
  semantics.
- Do not make required CI depend on the authorized development project.
- Do not begin Step 11, deploy, merge the Pull Request, configure branch
  protection, or add unrelated caching, lint, typing, coverage, scale, or SLO
  policy.

## Validation

At minimum:

- workflow syntax and full-SHA action pin validation;
- clean locked npm installation and exact Supabase CLI version;
- clean local Supabase startup and migration rebuild;
- `supabase test db` with all 18 current assertions passing;
- any added adapter/integration test over real local boundaries;
- reliable always-run cleanup on the tested path;
- locked Python reinstall, `pip check`, and full pytest suite;
- installed-package import where relevant;
- preservation of the existing Python pytest artifact contract;
- scan for secrets, remote identifiers, production dependencies, and untracked
  generated state;
- `git diff --check` and untracked-file whitespace validation.

After approved commit and push, verify every updated Pull Request job and
download and inspect every required result artifact.

## Stop condition

Stop after Step 10 implementation, validation, persistent handoff update,
approved commit/push, successful Pull Request workflow verification, and
artifact inspection. Do not start Step 11 in the same session.
