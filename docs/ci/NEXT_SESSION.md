# Next Codex Session

## Activation condition

Step 2 implementation and local validation are complete but uncommitted.
Continue only after verifying the actual branch, HEAD, remote, working tree,
and diff against `docs/ci/CI_STATE.md`. Investigate any mismatch before
changing files.

## Step

Continue Step 2 — approve, publish, and remotely validate the Python GitHub
Actions foundation.

This is completion work for Step 2, not permission to begin Step 3.

## Current verified starting point

- Branch: `ci/github-actions-foundation`.
- Base HEAD: the approved Step 1 commit.
- `.github/workflows/ci.yml` is implemented locally and remains uncommitted.
- Clean Python 3.11 installation, `pip check`, and pytest pass.
- Workflow YAML syntax and explicit security/semantics assertions pass.
- The action release tags and full upstream SHAs are verified.
- No remote Pull Request ref exists yet.
- Commit and push require explicit user approval.

## Goal

Complete Step 2 by reviewing the prepared diff, obtaining explicit approval,
committing and pushing it, opening a Pull Request to `main`, and confirming an
actual successful `CI / Python 3.11` GitHub Actions check.

## Required sequence

1. Read `AGENTS.md`, `docs/ci/CI_STATE.md`, `docs/ci/CI_PLAN.md`, this file,
   and `docs/ci/DECISIONS.md`.
2. Verify `git status`, branch, HEAD, remote, and the complete diff.
3. Re-run local validation if the implementation or environment changed.
4. Show the user the validation results and diff summary.
5. Obtain explicit approval before commit or push.
6. Commit and push the Step 2 changes.
7. Open a Pull Request from `ci/github-actions-foundation` to `main` using a
   concise English title and body that describe only Steps 1 and 2.
8. Verify the resulting `CI / Python 3.11` check and inspect failure logs if
   it is not green.
9. After the remote check is green, update the persistent handoff:
   - mark Step 2 DONE in `docs/ci/CI_PLAN.md`;
   - record the verified GitHub run in `docs/ci/CI_STATE.md`;
   - rewrite this file for Step 3;
   - update `docs/ci/DECISIONS.md` only if a durable decision was made.
10. Commit and push the final handoff only under explicit user authorization.
11. Stop without implementing Step 3.

## Validation already completed locally

- `python3 -m venv .venv`
- `.venv/bin/python -m pip install --constraint requirements/test.txt '.[test]'`
- `.venv/bin/python -m pip check`
- `.venv/bin/python -m pytest`
- Installed-package path verification from outside the repository root.
- YAML parsing and explicit workflow semantics/security assertions.
- `git diff --check`.
- Official action tag resolution using `git ls-remote`.

Expected local result: dependency consistency passes and pytest reports
`1 passed`.

## Stop condition

Stop after the GitHub Actions check is green, Step 2 is recorded as DONE, and
the approved final handoff is pushed. Do not start Step 3.
