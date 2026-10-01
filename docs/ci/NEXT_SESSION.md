# Next Codex Session

## Activation condition

Continue Step 12 only after its current documentation-only handoff is committed
and pushed with explicit user approval. Before any further change, verify the
actual branch, exact local and remote HEAD, clean working tree, Pull Request,
workflow run, both jobs, both artifacts, complete branch-protection read-back,
required check/provider bindings, and repository rulesets against
`docs/ci/CI_STATE.md`.

If the documentation commit has not been approved, committed, and pushed,
remain in Step 12 and request only that approval. Do not alter the already
verified protection configuration while waiting.

## Step

Step 12 — Finalize and remotely verify the approved branch-protection handoff

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`
7. `docs/ci/FLOW_EXPLANATIONS.md`

Read only additional GitHub workflow, artifact, Pull Request, and repository
setting sources relevant to this final Step 12 verification.

## Current verified protection

`main` uses classic branch protection with approved configuration
`PROTECTION v1.1`:

- `strict = true`;
- required `Python 3.11` from GitHub Actions App `15368`;
- required `Local Supabase integration` from GitHub Actions App `15368`;
- Pull Request reviews enabled with zero required approvals;
- stale-review dismissal, code-owner review, and last-push approval disabled;
- administrator enforcement enabled, without push restrictions or bypass
  allowances;
- conversation resolution required;
- signed commits and linear history disabled;
- force pushes and deletion disabled;
- branch-creation blocking, branch lock, and fork syncing disabled.

Repository rulesets are empty. Pull Request #1 remains open and unmerged. Its
merge state is blocked by one old unresolved, outdated review conversation;
the branch is not behind and both required checks are successful.

## Goal

After the documentation-only Step 12 commit is pushed, prove that the exact
commit passes both jobs and preserves both artifact contracts, and reconfirm
that every protection field and required check/provider binding still matches
`PROTECTION v1.1`. Then prepare the final persistent Step 12 handoff.

## Required approach

- Match local HEAD, remote-tracking branch, and Pull Request head exactly.
- Inspect the exact-commit Pull Request workflow run and every main/post job
  step.
- Download both published artifacts, compare GitHub and independently computed
  SHA-256 digests, inspect exact non-empty contents, and verify pgTAP/JUnit/
  pytest totals.
- Read back full protection plus required checks, Pull Request reviews, signed
  commits, branch protected state, and repository rulesets.
- Reconfirm both required contexts are bound to GitHub Actions App `15368`.
- Confirm the Pull Request remains open and unmerged; explain any merge-state
  blocker without changing it.
- Update the final Step 12 persistent handoff and request separate approval for
  any resulting documentation-only commit/push.

## Out of scope and safety limits

- Do not resolve or dismiss the existing review conversation without separate
  explicit authorization.
- Do not merge or close Pull Request #1.
- Do not change `PROTECTION v1.1`, add a ruleset, rename checks, alter workflow
  commands, or add a coverage threshold.
- Do not deploy, link, or mutate a remote Supabase project.
- Do not change Product source, schema, migrations, tests, telemetry,
  authorization, retention, SLO, scale, or other Product requirements.
- No later CI implementation step is currently authorized.

## Stop condition

Stop after exact remote verification and the final Step 12 persistent handoff.
If no new work is explicitly authorized, record that the planned CI sequence
through Step 12 is complete and wait for user direction.
