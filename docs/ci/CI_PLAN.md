# TLM CI Plan

## Goal

Build reproducible GitHub Pull Request validation for TLM without physical
hardware or production Supabase. The finished CI must exercise deterministic
unit tests, software device simulation, local API/database boundaries, and a
version-controlled local Supabase/PostgreSQL schema where applicable.

## Non-goals

- Production or staging deployment.
- Required Hardware-in-the-Loop checks.
- Product credential, role, telemetry-field, retention, or remote-command
  decisions that Product Management has not confirmed.
- Direct device coupling to Supabase implementation details.
- Premature CI caching, test splitting, or arbitrary coverage thresholds.

## Verified starting point

The Step 0 audit found a new repository containing only the CI master prompt.
There is no committed history, remote, Python project, test suite, API,
simulator, Supabase configuration, or GitHub Actions workflow.

## Milestones

### Step 0 — Repository audit and CI state bootstrap

Status: DONE

Acceptance criteria:

- Audit Git, Python, tests, Supabase, GitHub Actions, and repository guidance.
- Create a small, non-duplicative persistent state and handoff layout.
- Point `AGENTS.md` to the stable bootstrap prompt and exact next-step file.
- Validate the coordination files.
- Commit and push the Step 0 baseline after explicit user approval.

Dependencies: none.

### Step 1 — Establish the Python validation baseline

Status: DONE

Acceptance criteria:

- Confirm the supported Python version and dependency-management approach.
- Add the smallest reproducible Python package/test configuration suitable for
  this empty repository.
- Add at least one deterministic, meaningful validation target without
  inventing product behavior.
- Establish exact local install and test commands and verify them from a clean
  environment.

Dependencies: Step 0.

### Step 2 — Add the Python GitHub Actions foundation

Status: DONE

Acceptance criteria:

- Verify current official GitHub Actions and supported Python setup guidance.
- Add one minimal workflow with Pull Request validation, `contents: read`,
  concurrency cancellation, job timeout, and verified full-SHA action pins.
- Run the same mandatory Python checks established in Step 1.
- Do not use secrets, production services, or `pull_request_target`.

Dependencies: Step 1.

### Step 3 — Define deterministic simulator boundaries

Status: DONE

Acceptance criteria:

- Define boundaries for fake sensor, clock, transport, and temporary durable
  queue using existing project abstractions if any exist by then.
- Keep test data explicitly marked as test data.
- Prove deterministic behavior with unit tests.

Dependencies: Step 1.

### Step 4 — Add normal telemetry and contract scenarios

Status: DONE

Acceptance criteria:

- Validate the accepted telemetry envelope with test-only payload data.
- Simulate ordered messages with `sequence_no` 1, 2, and 3.
- Reject malformed envelopes and unsupported test schema versions in a
  controlled way.

Dependencies: Step 3.

### Step 4.5 — Publish test result artifacts

Status: DONE

Acceptance criteria:

- Produce a machine-readable JUnit XML report and a human-readable pytest log
  without masking the pytest exit status.
- Upload both files after the test step with the official
  `actions/upload-artifact` action pinned to a verified full commit SHA.
- Attempt the upload even when pytest fails, and fail clearly when the
  expected result files are absent.
- Verify that the artifact is available from the completed Pull Request run.
- Use the repository's default artifact retention and do not turn artifact
  retention into a product data-retention requirement.

Dependencies: Step 4.

### Step 5 — Add duplicate, offline, and reconnect scenarios

Status: DONE

Acceptance criteria:

- Prove duplicate `message_id` retry is logically idempotent.
- Prove unavailable transport retains messages in a durable test queue.
- Prove deterministic replay after reconnect, including a correctness-scale
  buffered burst.

Dependencies: Step 4.5.

### Step 6 — Add ordering, stream, and late-data scenarios

Status: DONE

Acceptance criteria:

- Prove out-of-order history ingestion does not roll back `current_state`.
- Prove a new `stream_id` permits sequence restart after reboot.
- Prove late telemetry remains in history and cannot replace newer state.
- Include deterministic clock-skew coverage without treating device time as an
  authorization proof.

Dependencies: Step 5.

### Step 7 — Establish the local API/storage integration boundary

Status: DONE

Acceptance criteria:

- Use the repository's actual API and Storage Adapter abstractions, or define
  the minimum provider-independent boundary if they still do not exist.
- Exercise real local HTTP and storage boundaries where possible.
- Keep device code independent of Supabase internals.

Dependencies: Steps 4-6 and relevant application architecture.

### Step 8 — Define the Supabase schema bootstrap strategy

Status: READY_FOR_COMMIT

Acceptance criteria:

- Inspect any repository and remote schema sources that exist at that time.
- Verify current official Supabase CLI guidance.
- Explain migration/bootstrap strategy before schema pull or implementation.
- Perform no destructive operation against production.

Implementation summary:

- Repository inspection found no schema/configuration source and no authorized
  remote schema source.
- Stable Supabase CLI `2.118.0` is pinned as a project-scoped development tool
  with Node.js 20 or later and a committed npm lock file.
- `docs/ci/SUPABASE_SCHEMA_BOOTSTRAP.md` defines migrations as the future
  source of truth, the authorized remote/greenfield bootstrap paths, local
  rebuild contract, credential boundaries, and prohibited remote mutations.
- No `supabase/config.toml`, migration, seed, table, role, RLS policy, remote
  link, schema pull, Docker service, or database operation was created without
  a verified schema source.

Dependencies: Step 7 and user approval for any remote schema access.

### Step 9 — Add reproducible local database and database tests

Status: NOT_STARTED

Acceptance criteria:

- Rebuild the local database from version-controlled files on a clean setup.
- Add database tests only for confirmed requirements.
- Record authorization cases blocked by unresolved Product decisions rather
  than inventing policies.

Dependencies: committed and remotely verified Step 8, plus an explicitly
authorized existing schema source or confirmed greenfield schema requirements.

### Step 10 — Add the local integration CI job

Status: NOT_STARTED

Acceptance criteria:

- Start pinned local test infrastructure on a clean GitHub-hosted runner.
- Rebuild and test the database, launch the local API, and run simulator tests
  over real local boundaries.
- Add timeout and reliable cleanup without production secrets.

Dependencies: Steps 2, 7, and 9.

### Step 11 — Measure, document, and prepare branch protection

Status: NOT_STARTED

Acceptance criteria:

- Measure coverage before proposing any threshold.
- Document local reproduction, simulator use, local Supabase, test extension,
  open Product decisions, and CI failure handling in Russian.
- Confirm stable check names before proposing required status checks.
- Do not enable branch protection or merge a Pull Request without explicit
  user approval.

Dependencies: stable completion of earlier CI steps.

## Dependency order

`Step 0 -> Step 1 -> Step 2`

`Step 1 -> Step 3 -> Step 4 -> Step 4.5 -> Step 5 -> Step 6 -> Step 7`

`Step 7 -> Step 8 -> Step 9 -> Step 10 -> Step 11`

The plan is a living document. Steps may be split when later repository facts
show that a step is too large, but verified history must not be rewritten.

## Open Product Manager decisions affecting CI

The following do not block the initial Python/tooling foundation but can block
specific future tests:

- Final device provisioning and credential technology.
- Final telemetry schema for each `system_type`.
- Participant roles, persistent learning groups, and final decision authority.
- Meaning of `device_assignments` for group sessions.
- RLS versus Application API authorization responsibilities.
- Sampling/reporting rates, retention, offline retention guarantee, and buffer
  overflow policy.
- Remote-command and AI authority.
- Wix identity model and company roles.
- SLO, production fleet size, and infrastructure cost limits.

Temporary test values must be labeled TEST FIXTURE or TEST CONFIGURATION and
must not be treated as product requirements.
