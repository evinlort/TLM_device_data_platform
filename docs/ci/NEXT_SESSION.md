# Next Codex Session

## Activation condition

Step 0 is complete. Before starting Step 1, verify that the actual branch,
HEAD, remote, and working tree agree with `docs/ci/CI_STATE.md`. Stop and
investigate any mismatch.

## Step

Step 1 — Establish the Python validation baseline

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`

Additional files relevant to this step:

- `TLM GitHub CI — Codex Master Prompt (пошаговая работа между сессиями).md`

Do not read unrelated future files unless the current step requires them.

## Goal

Establish the smallest reproducible Python package and test baseline suitable
for the currently empty repository. Select tooling deliberately, add at least
one deterministic and meaningful validation target, and document exact local
commands without inventing product behavior.

## Current verified starting point

- The repository had no application code, project metadata, dependencies,
  tests, workflows, simulator, or database files at the Step 0 audit.
- Local Python 3.11.9 is only an environment observation; no supported project
  version has been selected.
- Local `pytest` is currently not importable.
- No physical hardware is available or required.

## Allowed scope

- Python project metadata and dependency declarations.
- Minimal `src/` package foundation only where necessary for a meaningful
  validation target.
- Deterministic unit tests and test configuration.
- Minimal lint/format configuration only after checking that no established
  repository tool exists.
- CI state/handoff updates required by the step-end protocol.

## Out of scope

- GitHub Actions workflow implementation; that is Step 2.
- Device simulator behavior.
- API implementation.
- Supabase configuration, migrations, seed data, or database tests.
- Product credential, role, telemetry-field, retention, or rate decisions.
- Deployment and Hardware-in-the-Loop.

## Required investigation

- Reconfirm repository and Git state before changes.
- Check current official Python packaging and pytest guidance relevant to the
  chosen baseline.
- Do not treat the locally installed Python version as an automatic project
  requirement.

## Validation

Establish and execute exact commands for:

- dependency installation in a clean isolated environment;
- deterministic tests;
- lint/format validation if such tooling is added.

Expected result: every mandatory command passes without network, Docker,
Supabase, secrets, or physical hardware after dependencies are installed.

## Stop condition

After implementation, validation, state update, approved commit, and push.
Do not start Step 2 in this session.
