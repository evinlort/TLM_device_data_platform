# Next Codex Session

## Activation condition

Step 9 may start only after Step 8 is committed, pushed, successful in the Pull
Request workflow, and the published test-results artifact has been downloaded
and inspected. Verify the actual branch, HEAD, remote, clean working tree, Pull
Request, latest required CI result, artifact listing, and downloaded artifact
against `docs/ci/CI_STATE.md` before any change.

Step 9 also requires one of these inputs:

1. explicit user authorization identifying an existing Supabase project and
   environment whose schema may be inspected and captured; or
2. confirmed greenfield schema requirements sufficient to author the first
   migration without inventing Product semantics.

If neither input exists, stop and request the missing source-of-truth decision.
Do not create placeholder production tables, roles, RLS policies, or database
tests.

## Step

Step 9 — Add a reproducible local database and confirmed database tests

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`
7. `docs/ci/FLOW_EXPLANATIONS.md`

Additional files relevant to this step:

- `package.json`
- `package-lock.json`
- `.github/workflows/ci.yml`
- `src/tlm_device_data_platform/local_integration.py`
- `tests/test_local_integration.py`

Inspect any Supabase/schema files that exist at the start of the session. Do
not read unrelated future files unless the current step requires them.

## Goal

Establish a version-controlled Supabase/PostgreSQL configuration and real
baseline migration from an authorized source, then prove that a disposable
local database can be rebuilt from Git and run only database tests supported by
confirmed requirements.

## Required approach

- Follow `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md`.
- Use the exact project-scoped Supabase CLI version already locked in npm.
- For a remote source, identify and re-confirm the exact project, environment,
  schema scope, PostgreSQL major version, and allowed commands before linking
  or pulling.
- Explain the target and effect before every remote command.
- Keep credentials, passwords, connection strings, `.temp` state, and remote
  identifiers out of commits and artifacts unless a non-secret identifier is
  explicitly approved for version control.
- Review generated configuration and SQL before local application.
- Use only disposable local services for rebuild and tests.

## Out of scope and safety limits

- Never run `supabase db reset --linked` against production.
- Do not run `db push`, `migration repair`, accept a remote-history update, or
  perform any other remote mutation without separate explicit authorization.
- Do not invent tables, columns, roles, grants, RLS, authorization, retention,
  idempotency, ordering, conflict-resolution, or seed semantics.
- Do not add the Step 10 integration CI job in this session.
- Do not deploy, merge the Pull Request, configure branch protection, or add
  unrelated caching, lint, typing, coverage, scale, or SLO policy.

## Validation

Validate every file introduced by the authorized schema source. At minimum:

- clean `npm ci` and exact CLI version;
- local stack startup without production secrets;
- clean local rebuild from version-controlled migrations;
- confirmed database tests, if requirements exist;
- reliable local cleanup;
- locked Python reinstall, `pip check`, and full pytest suite;
- installed-package import where relevant;
- preservation of the pytest artifact contract;
- scan for secrets, production dependencies, and untracked generated state;
- `git diff --check` and untracked-file whitespace validation.

After approved commit and push, verify the updated Pull Request workflow and
inspect its published artifact.

## Stop condition

Stop after Step 9 implementation, validation, persistent handoff update,
approved commit/push, successful Pull Request workflow verification, and
artifact inspection. Do not start Step 10 in the same session.
