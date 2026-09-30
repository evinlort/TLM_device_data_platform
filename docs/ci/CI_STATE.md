# TLM CI Current State

## Repository

- Branch: `ci/github-actions-foundation`
- HEAD: the commit containing this file completes Step 1; use
  `git rev-parse HEAD` to obtain its exact SHA without creating a
  self-referential state update.
- Remote: `origin` is
  `https://github.com/evinlort/TLM_device_data_platform.git`.
- GitHub repository: private `evinlort/TLM_device_data_platform` with `main`
  as the default branch.
- Working tree: expected to be clean after the approved Step 1 commit.

## Current milestone

- Step: Step 1 — Establish the Python validation baseline
- Status: DONE
- Completion blockers: none.

## Verified facts

- Python 3.11 is the minimum supported project version for the initial
  baseline. Upstream security support continues through October 2027.
- Local validation used Python 3.11.9 and pip 24.0 in a newly created isolated
  virtual environment.
- The project uses `pyproject.toml`, a `src/` layout, setuptools 84.0.0 as the
  pinned build backend, and pytest 9.1.1.
- `requirements/test.txt` locks the resolved Python 3.11 test environment.
- Package version `0.0.0` is a non-release bootstrap placeholder, not a
  product release or versioning requirement.
- No lint or type-check dependency is established yet.

## Implemented

- A buildable `tlm-device-data-platform` distribution with the import package
  `tlm_device_data_platform`.
- Strict pytest configuration with `importlib` import mode and `tests/` as the
  explicit test path.
- One deterministic test proving the normally installed package is
  importable.
- Git ignores for virtual environments, Python caches, test caches, build
  output, and package metadata output.

## Validation

Canonical clean-environment commands established by Step 1:

- `python3 -m venv .venv`
- `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`

Additional commands executed during Step 1:

- `python3 --version`
- `python3 -m pip --version`
- `python3 -m venv /tmp/tlm-step1-locked.u0nmpr/venv`
- `/tmp/tlm-step1-locked.u0nmpr/venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
- `/tmp/tlm-step1-locked.u0nmpr/venv/bin/python -m pip check`
- `/tmp/tlm-step1-locked.u0nmpr/venv/bin/python -m pytest`
- Installed-package path verification from outside the repository root
- `git diff --check`

Results:

- Clean isolated installation built and installed the wheel successfully.
- The import package resolved from the clean environment's `site-packages`,
  not from the source tree.
- Dependency consistency: PASS (`No broken requirements found`).
- Tests: PASS (`1 passed`).
- Mandatory post-install checks required no network, Docker, Supabase,
  secrets, or physical hardware.

## Current CI

- Workflows: none.
- Mandatory local checks:
  - `.venv/bin/python -m pip check`
  - `.venv/bin/python -m pytest`
- Tests: one deterministic installed-package boundary test.

## Current simulator state

- No simulator exists.
- No physical device is available or required for planned PR CI.

## Current database state

- No version-controlled schema or Supabase configuration exists.
- No local or remote database operation has been performed.

## Product decisions still OPEN

- Credential implementation and provisioning details.
- Product telemetry fields and rates per `system_type`.
- Group/session role and authorization semantics.
- RLS versus Application API authorization split.
- Retention, offline buffer limits, command authority, SLO, scale, and cost.

See `docs/ci/CI_PLAN.md` for the fuller list and affected future milestones.

## Technical blockers

- None for Step 2.

## Files changed in the last completed step

- `.gitignore`
- `pyproject.toml`
- `requirements/test.txt`
- `src/tlm_device_data_platform/__init__.py`
- `tests/test_package.py`
- `docs/ci/CI_PLAN.md`
- `docs/ci/CI_STATE.md`
- `docs/ci/NEXT_SESSION.md`
- `docs/ci/DECISIONS.md`

## Next step

- Step: Step 2 — Add the Python GitHub Actions foundation
- Goal: run the established clean install and mandatory Python checks in one
  minimal, hardened Pull Request workflow.
- Expected files: `.github/workflows/ci.yml` plus CI state/handoff updates.
- Validation required: local baseline checks, workflow syntax/security review,
  verified action SHAs, and an actual GitHub Actions run when safely
  triggerable after approval.

Step 2 must start in a new Codex session using
`docs/ci/BOOTSTRAP_PROMPT.md`.
