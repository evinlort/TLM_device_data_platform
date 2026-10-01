# Repository Instructions

## Current work: laboratory device ingestion v1

- Communicate in Russian. Keep code, identifiers, commands, filenames, SQL,
  YAML, comments, docstrings, branch names and commit messages in English.
- Read `README.md`, `docs/device_ingestion/PROTOCOL_V1.md`,
  `docs/device_ingestion/IMPLEMENTATION.md`, and
  `docs/device_ingestion/STAND_SETUP.md` before changing ingestion code.
- The user explicitly authorized sequential implementation of all three
  ingestion stages and committing each change. This authorization does not
  authorize automatic merge of the new implementation PR, branch deletion,
  or changes to branch protection.
- Read actual Git refs, the current PR, and exact-commit CI results before
  making state claims. Historical validation SHAs in documentation are not
  assertions about the current checkout HEAD.
- Keep changes in a feature branch and validate each logical change.
- Required CI uses software input and disposable local Supabase only. Do not
  weaken assertions, replace real HTTP/database integration with mocks, or
  silently skip database tests to obtain green checks.
- Do not invent sensor readings, real sensor drivers, school/student roles,
  device authorization, current-state semantics, retention or scale guarantees.
- Real deployment requires an explicitly identified development target and
  appropriate credentials. Never run remote reset, publish secrets, or treat
  a software demo as hardware validation.
- Preserve the existing migration history and old CI fixture contract.
- Record implementation reasoning and validation in the ingestion handoff.

## Historical CI foundation

The planned CI sequence through Step 12 is complete and PR #1 was merged.
The following files preserve its history, not the current product backlog:

- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/DECISIONS.md`
- `docs/ci/FLOW_EXPLANATIONS.md`
- `docs/ci/BOOTSTRAP_PROMPT.md`

`docs/ci/NEXT_SESSION.md` points to the current ingestion handoff.
Future CI-only work normally uses one logical step per session unless the user
explicitly authorizes a sequential multi-step implementation. Commit and push
require user authorization; never infer permission to merge or delete branches.
