# TLM CI Decisions

## CI-DEC-001 — Hardware-independent required CI

Status: ACCEPTED

Decision:

Required Pull Request validation uses deterministic software tests and must not
depend on a physical TLM device. Hardware-in-the-Loop may be added later as a
separate optional job.

Reason:

No physical TLM device is available for CI, and required checks must be
reproducible on a clean runner.

Consequences:

- Unit tests use deterministic fakes at external boundaries.
- Integration tests use a software device simulator and local services.
- Hardware-in-the-Loop is not a required check in the current milestone.

Source:

`TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`

## CI-DEC-002 — Provider-independent device boundary

Status: ACCEPTED

Decision:

The physical device and simulator target the TLM Device Protocol and TLM
Device API. They do not depend on Supabase project URLs, table names,
PostgREST, Edge Function implementation details, service-role credentials, or
database schema.

Reason:

Supabase is the current backend/storage provider, not part of the device
contract.

Consequences:

- Future simulator tests must exercise a provider-independent API boundary.
- Supabase-specific logic stays behind the Storage Adapter.
- Privileged Supabase credentials must not appear on devices, in browsers, or
  in test fixtures.

Source:

`TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`

## CI-DEC-003 — Git-backed cross-session state

Status: ACCEPTED

Decision:

Use `docs/ci/CI_PLAN.md`, `docs/ci/CI_STATE.md`,
`docs/ci/NEXT_SESSION.md`, `docs/ci/BOOTSTRAP_PROMPT.md`, and
`docs/ci/DECISIONS.md` as the compact persistent CI handoff. `AGENTS.md`
contains only stable repository-wide instructions and pointers.

Reason:

The repository had no existing planning or handoff convention. Every Codex
session must be replaceable without chat history, and a fresh checkout must
contain enough information to continue safely.

Consequences:

- One logical step is executed per session.
- The exact next step is stored only in `NEXT_SESSION.md`.
- The bootstrap prompt stays generic and must not contain stale branch or
  commit identifiers.
- State and implementation changes are committed together after approval.

Source:

`TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`

## CI-DEC-004 — Initial default branch bootstrap

Status: ACCEPTED

Decision:

Initialize remote `main` from the reviewed Step 0 root commit and use it as the
GitHub default branch. Keep ongoing CI implementation work on
`ci/github-actions-foundation` until changes are explicitly approved for
merge.

Reason:

The new GitHub repository had no branches. Its first feature-branch push was
temporarily selected as the default branch, while the agreed workflow requires
a stable `main` base and feature-branch development.

Consequences:

- The approved Step 0 bootstrap is the initial `main` baseline.
- New implementation commits are not made directly on `main`.
- Pull Requests can target a stable default branch.

Source:

Step 0 repository initialization and the Git workflow requirements in
`TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`.

## CI-DEC-005 — Initial Python validation baseline

Status: ACCEPTED

Decision:

Use Python 3.11 as the minimum supported Python version for the initial CI
baseline. Define the project with `pyproject.toml`, a `src/` package layout,
and a setuptools build backend. Use pinned pytest 9.1.1 with strict
configuration and `importlib` import mode. Lock the resolved Python 3.11 test
dependencies in `requirements/test.txt`.

Reason:

Python 3.11 remains supported upstream through October 2027 and is available
for local verification. The PyPA and pytest documentation recommend
`pyproject.toml`, isolated virtual environments, installed-package testing,
the `src/` layout, and `importlib` import mode for new projects. Pinning the
test environment makes the same baseline installable on a clean runner.

Consequences:

- Step 2 must install with
  `python -m pip install --constraint requirements/test.txt '.[test]'` and run
  `python -m pytest`.
- Dependency updates must keep `pyproject.toml` and `requirements/test.txt`
  consistent and must be revalidated in a clean environment.
- The package version `0.0.0` is a non-release bootstrap placeholder. This
  step makes no product release or versioning decision.
- Additional supported Python versions and lint/type-check tools require
  separate verified changes; they are not implied by this baseline.

Source:

Step 1 official Python Packaging User Guide, pytest documentation, and Python
version-support review.

## CI-DEC-006 — Detailed Russian step explanations

Status: ACCEPTED

Decision:

After every completed and validated CI step, append a standalone,
Russian-language explanation to `docs/ci/FLOW_EXPLANATIONS.md` before
requesting approval to commit. Each explanation covers the reason for the
step, the starting point, the implemented changes, the end-to-end flow, how
the changes solve the stated goal, implementation events and problem
resolution, validation and its meaning, and intentionally excluded scope.

Reason:

The compact plan and state files optimize safe cross-session continuation but
do not provide enough teaching context for a reader to understand the complete
technical flow and the reasoning behind it.

Consequences:

- `CI_STATE.md` remains the compact source of current verified state.
- `FLOW_EXPLANATIONS.md` is append-only step history and explanation, not a
  replacement for the plan, state, next-session handoff, or durable decisions.
- A step is not ready for commit approval until its explanation has been
  appended and checked against the implementation and validation evidence.
- Explanations use Russian prose while preserving English source identifiers,
  commands, filenames, and configuration keys.

Source:

Direct user instruction after Step 2.

## CI-DEC-007 — Opaque deterministic simulator boundaries

Status: ACCEPTED

Decision:

Define simulator dependencies as four structural Python protocols: generic
sensor readings, a controllable clock, transport of opaque serialized `bytes`,
and a FIFO durable queue of the same opaque messages. Keep deterministic fake
implementations in project code for CI use. Use a temporary-file queue only to
prove persistence across instances; do not treat it as production storage.

Reason:

Later CI scenarios need replaceable hardware, time, delivery, and buffering
boundaries now, while the product telemetry schema, transport provider,
retention, capacity, retry, and authorization semantics are still undecided.
Opaque and minimal contracts permit deterministic tests without silently
deciding those product questions.

Consequences:

- Product telemetry fields remain outside the Step 3 interfaces.
- Tests configure readings, time, outcomes, messages, and temporary paths
  explicitly.
- Future scenarios may compose these protocols but must not interpret the
  temporary file implementation as a production durability guarantee.
- Retry, acknowledgement, replay, duplicate, reconnect, and overflow policies
  require their own later steps or confirmed Product decisions.

Source:

Step 3 simulator-boundary implementation and the existing
`CI-DEC-001`/`CI-DEC-002` constraints.

## CI-DEC-008 — Explicitly test-only telemetry fixture contract

Status: ACCEPTED

Decision:

Use a versioned JSON envelope only as a deterministic CI fixture contract.
The fixture contains `schema_version`, `message_id`, `stream_id`,
`sequence_no`, `recorded_at`, and `payload`, and fixture schema version `1` is
the only supported test version. Serialize it deterministically to UTF-8
`bytes`, validate its exact test shape, and report malformed data separately
from unsupported fixture versions. Do not change the provider-independent
transport boundary, which continues to carry opaque `bytes`.

Reason:

Step 4 needs stable normal, malformed, and version-rejection scenarios while
Product Management has not confirmed the production telemetry envelope or its
field semantics. An unmistakably fixture-specific contract permits meaningful
CI coverage without presenting temporary test choices as product decisions.

Consequences:

- Every field name, value, type rule, and schema version in
  `telemetry_fixture.py` remains test configuration rather than a production
  requirement.
- A future production contract requires separate confirmed requirements; it
  must not silently adopt this fixture schema.
- Later deterministic CI scenarios may compose the fixture fields, but doing
  so does not define production acceptance, authorization, storage, retry,
  idempotency, ordering, or current-state policy.
- No JSON, schema, or validation concern leaks into the existing `Transport`
  or `DurableQueue` protocols.

Source:

Step 4 telemetry-fixture implementation and the open Product decisions
recorded in `CI_PLAN.md`.

## CI-DEC-009 — Explicit test-only queued-delivery orchestration

Status: ACCEPTED

Decision:

Use `flush_test_queue()` only as deterministic CI orchestration over the
existing opaque `DurableQueue` and `Transport` boundaries. One explicit call
attempts queued messages in FIFO order, removes a message only after the
configured transport returns `True`, and stops at the first configured
`False` while leaving that message queued. Tests model reconnect with a new
transport and another explicit call. For the duplicate fixture scenario only,
logical acceptance means retaining the first parsed fixture envelope for each
fixture `message_id`.

Reason:

Step 5 must prove duplicate, unavailable-transport, reconnect, and replay
behavior without inventing product retry timing, acknowledgement, storage,
retention, capacity, or overflow semantics. Keeping orchestration explicit and
fixture-named makes the test flow deterministic while preserving the existing
provider-independent opaque-message boundary.

Consequences:

- `flush_test_queue()` is not a production retry loop or acknowledgement
  protocol and performs no automatic retry, waiting, backoff, or reconnect.
- The fixture `message_id` acceptance rule proves only logical idempotency in
  the Step 5 test; it does not define a production unique key, database
  constraint, storage result, or transport acknowledgement.
- `TEST_CORRECTNESS_BURST_SIZE = 64` is test configuration for ordered replay,
  not a product buffer size, capacity, performance target, scale claim, or
  SLO.
- Production offline guarantees and delivery policy remain open Product
  decisions.

Source:

Step 5 deterministic delivery-scenario implementation and the existing
`CI-DEC-001`, `CI-DEC-002`, `CI-DEC-007`, and `CI-DEC-008` constraints.
