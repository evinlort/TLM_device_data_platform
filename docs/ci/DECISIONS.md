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
