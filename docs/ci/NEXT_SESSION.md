# Next Codex Session

## Activation condition

Step 12 may start only after the final Step 11 persistent handoff update is
committed and pushed, both Pull Request jobs succeed on that exact final
handoff commit, and every published required result artifact is downloaded and
inspected. Verify the actual branch, HEAD, remote, clean working tree, Pull
Request, job details, artifact listings, digests, downloaded contents, current
`main` protection, and repository rulesets against `docs/ci/CI_STATE.md` before
any change.

The two candidate required checks must still appear as context `Python 3.11`
and context `Local Supabase integration`, both produced by GitHub Actions App
`15368`. Do not infer protection settings from their successful history.

## Step

Step 12 — Apply explicitly approved branch protection

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/TESTING_AND_BRANCH_PROTECTION.md`
7. `docs/ci/FLOW_EXPLANATIONS.md`

Read only additional workflow and GitHub repository-setting sources relevant
to Step 12.

## Goal

Obtain explicit user approval for one exact branch-protection configuration,
apply only that approved configuration to `main`, and verify the read-back
state and required check/provider identities.

## Decisions required before mutation

Ask the user to decide every setting that the selected GitHub API or ruleset
operation will write, including at minimum:

- whether branches must be up to date before merging (`strict`);
- the exact required checks and provider binding;
- Pull Request approval count and stale/last-push behavior;
- administrator enforcement and bypass behavior;
- conversation resolution, signed commits, and linear history;
- force-push and branch-deletion behavior.

Do not supply a write request with invented defaults. A minimal proposal may
name the two verified CI checks, but every field sent to GitHub requires
explicit user approval.

## Required approach

- Reconfirm successful check identities on the final Step 11 handoff commit.
- Reconfirm existing branch protection and rulesets before mutation.
- Prefer provider-bound required checks using GitHub Actions App `15368` where
  the chosen interface supports `app_id`.
- Apply exactly one reviewed configuration after explicit approval.
- Read back the effective configuration and compare every changed field with
  the approved proposal.
- Keep branch governance separate from coverage policy and Product behavior.

## Out of scope and safety limits

- Do not merge or close Pull Request #1.
- Do not change workflow job names or CI commands merely to configure
  protection.
- Do not add a coverage threshold or required coverage check.
- Do not deploy, link, or mutate any remote Supabase project.
- Do not change Product source, database schema, migrations, tests, telemetry,
  authorization, retention, SLO, or scale requirements.
- Do not begin work beyond Step 12.

## Validation

At minimum:

- exact local/remote branch and Pull Request head consistency;
- both Pull Request jobs and every expected artifact verified on the final
  Step 11 handoff commit;
- pre-change protection/ruleset read-back;
- approved request payload or UI choices reviewed field by field;
- post-change protection/ruleset read-back matching the approval;
- required check context and GitHub Actions provider identity verification;
- repository documentation consistency, secret scan, and whitespace check.

## Stop condition

Stop after Step 12 protection configuration, verification, persistent handoff
update, and any separately approved documentation commit/push. Do not merge or
close Pull Request #1 without a later, separate explicit approval.
