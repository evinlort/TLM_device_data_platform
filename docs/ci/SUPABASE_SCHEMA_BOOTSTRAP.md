# Supabase Schema Bootstrap Strategy

## Scope

This document defines how the repository will obtain and maintain a
version-controlled local Supabase/PostgreSQL schema. It does not define any
product table, column, role, RLS policy, retention rule, identity rule, or
telemetry semantic.

The repository inspection performed on 2026-09-30 found no Supabase project
configuration, SQL migration, declarative schema, seed, database test, database
client, or authorized remote schema source. The existing
`TemporaryDirectoryStorage` is a local filesystem test adapter and is not a
schema prototype.

## Toolchain

The repository pins stable Supabase CLI `2.118.0` as an exact npm development
dependency. The official CLI guidance recommends a project-scoped dependency,
an exact shared version, and Node.js 20 or later. The canonical commands are:

```bash
npm ci
npx supabase --version
```

`package-lock.json` is the tool dependency lock. `node_modules/` is local
generated state and is not version-controlled. A future CLI upgrade is a
reviewed dependency change and must revalidate generated configuration,
migrations, and local rebuild commands.

Verified official references:

- <https://supabase.com/docs/guides/local-development/cli/getting-started>
- <https://supabase.com/docs/guides/local-development/cli-workflows>
- <https://supabase.com/docs/guides/deployment/database-migrations>
- <https://supabase.com/docs/reference/cli/supabase-db-schema-declarative>
- <https://github.com/supabase/cli/releases/tag/v2.118.0>

## Source of truth

Once an authorized schema source exists, the source of truth will be the
ordered SQL files in `supabase/migrations/`. `supabase/config.toml` will define
only the reproducible local stack configuration. Optional `supabase/seed.sql`
and `supabase/tests/` will contain test data and database tests, not production
data or unconfirmed authorization requirements.

No empty or invented baseline migration is created in Step 8. A migration is
valid only when it comes from one of these reviewed sources:

1. an explicitly authorized existing remote schema captured as a baseline; or
2. a Product-approved greenfield schema expressed as reviewed SQL.

After the baseline is accepted, schema changes must be made through new local
migration files and reviewed in Git. Direct remote Dashboard, SQL Editor, or
Table Editor changes bypass migration history and are not the normal workflow.

## Bootstrap from an existing remote project

Remote access requires a separate explicit authorization that identifies the
exact Supabase project and environment. Before any command runs, record the
project reference, confirm whether the target is production, confirm the
schemas to capture, and determine the remote PostgreSQL major version. Keep
access tokens, database passwords, generated `.temp` state, and connection
strings out of Git and CI artifacts.

The authorized bootstrap flow is:

1. Install the locked CLI with `npm ci` and verify version `2.118.0`.
2. Run `npx supabase init` locally.
3. Review the generated `supabase/config.toml`; set the local project ID and
   PostgreSQL major version from verified facts, and label all other retained
   values as local test configuration.
4. Authenticate and link only to the explicitly named project.
5. Run `npx supabase db pull` with the approved schema scope. The command needs
   a Docker-compatible runtime for its shadow database. Current CLI guidance
   shows that it may offer to update remote migration history, so the prompt
   must not be accepted without separate authorization.
6. Review the generated baseline SQL for schemas, extensions, ownership,
   grants, functions, triggers, policies, and unsupported or omitted objects.
   Do not infer missing Product semantics.
7. Disconnect remote credentials and validate the baseline only against the
   local stack on a clean setup.
8. Commit the reviewed configuration and migration only after the local rebuild
   and database tests pass and the user approves the commit.

`supabase db push`, `supabase migration repair`, and any accepted remote-history
update mutate remote state. They are not part of schema discovery and require
separate authorization. `supabase db reset --linked` is prohibited for
production and must never be automated.

## Bootstrap for a greenfield schema

If no existing remote schema is authoritative, wait for confirmed Product and
architecture requirements. Then initialize the local project, create a named
migration with `npx supabase migration new <description>`, author only the
approved SQL, and prove a clean rebuild locally. Test-only seed values must be
clearly marked and must not become product defaults.

## Local rebuild contract

After a baseline exists, Step 9 must prove on a clean local environment:

```text
npm ci
  -> pinned Supabase CLI is available
  -> local Supabase starts without production credentials
  -> local database is reset from supabase/migrations
  -> test-only seed data is applied when present
  -> confirmed database tests run
  -> existing Python checks remain green
  -> local services stop reliably
```

The exact `supabase start`, `supabase db reset`, and `supabase test db` commands
will be recorded only after `config.toml` and a real baseline migration exist
and have been validated. Required Pull Request CI must use local disposable
services and must not link to or depend on production Supabase.

## Current blocker for database implementation

Step 8 establishes the tool and decision process, but there is still no
authorized schema source. Step 9 database rebuild/tests cannot define tables,
roles, RLS, or assertions until either an existing remote schema is explicitly
authorized for capture or a greenfield schema is approved. This is a Product
and source-of-truth input requirement, not a reason to invent a temporary
production model.
