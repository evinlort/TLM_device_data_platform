# Next Codex Session

## Activation condition

The planned CI sequence through Step 12 is complete. Start a new session only
to verify the final Step 12 persistent handoff commit after it has been
explicitly approved, committed, and pushed, or when the user explicitly
authorizes new work.

Before any action, verify the actual branch, exact local and remote HEAD, clean
working tree, Pull Request, exact-commit workflow run, both jobs, both artifacts,
complete branch-protection read-back, required check/provider bindings, and
repository rulesets against `docs/ci/CI_STATE.md`.

## Step

Post-Step 12 — Verify the final handoff and stop

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`
7. `docs/ci/FLOW_EXPLANATIONS.md`

Read only additional GitHub workflow, artifact, Pull Request, and repository
setting sources needed for final handoff verification.

## Current completed state

- Step 12 status is `DONE`.
- `main` is protected by the explicitly approved classic configuration
  `PROTECTION v1.1`.
- Required contexts are `Python 3.11` and `Local Supabase integration`, both
  bound to GitHub Actions App `15368`, with `strict = true`.
- Pull Request #1 remains open and unmerged. Its merge state is blocked by one
  old unresolved, outdated review conversation; the branch is not behind and
  both required checks are successful.
- Repository rulesets are empty.
- Documentation commit `0a71ad4cc852ba9c0699a1153f8e10d3ec6b0103`
  passed workflow run #25 and both artifact contracts were independently
  verified.

## Goal

Verify that the final Step 12 handoff commit itself is present locally,
remotely, and at the Pull Request head; that its two jobs and artifacts pass the
existing contracts; and that `PROTECTION v1.1` remains unchanged. Report the
result and stop without creating another handoff commit.

## Required approach

- Match local HEAD, remote-tracking branch, and Pull Request head exactly.
- Inspect the exact-commit Pull Request workflow run and every main/post job
  step.
- Download both artifacts, compare GitHub and independently computed SHA-256
  digests, inspect exact non-empty contents, and verify pgTAP/JUnit/pytest
  totals.
- Read back the full protection and confirm every `PROTECTION v1.1` field.
- Reconfirm both required contexts are bound to GitHub Actions App `15368` and
  repository rulesets remain empty.
- Confirm Pull Request #1 remains open and unmerged, then stop.

## Out of scope and safety limits

- Do not create another handoff commit merely to record this verification.
- Do not resolve or dismiss the existing review conversation without separate
  explicit authorization.
- Do not merge or close Pull Request #1.
- Do not change branch protection, add a ruleset, rename checks, alter workflow
  commands, or add a coverage threshold.
- Do not deploy, link, or mutate a remote Supabase project.
- Do not begin another CI or Product step without explicit user direction.

## Stop condition

After verifying the final handoff commit and unchanged protection, report that
the planned CI sequence through Step 12 is complete and wait for user direction.
