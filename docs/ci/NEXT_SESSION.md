# Next Codex Session

## Activation condition

Step 11 may start only after the final Step 10 persistent handoff update is
committed and pushed, both Pull Request jobs succeed on that exact final handoff
commit, and every published required result artifact is downloaded and
inspected. Verify the actual branch, HEAD, remote, clean working tree, Pull
Request, job details, artifact listings, digests, and downloaded contents
against `docs/ci/CI_STATE.md` before any change. The implementation evidence
recorded there belongs to run #21; the next session must independently validate
the later run created by the final handoff commit.

The local integration job must remain independent of physical hardware, remote
Supabase projects, credentials, and production services. Do not treat a local
fixture, generated local key, or artifact retention setting as a Product
requirement.

## Step

Step 11 — Measure, document, and prepare branch protection

## Read first

1. `AGENTS.md`
2. `docs/ci/CI_STATE.md`
3. `docs/ci/CI_PLAN.md`
4. `docs/ci/NEXT_SESSION.md`
5. `docs/ci/DECISIONS.md`
6. `docs/ci/FLOW_EXPLANATIONS.md`

Read only additional source, test, workflow, and documentation files relevant
to Step 11.

## Goal

Measure the existing test coverage before proposing any threshold, document in
Russian how to reproduce and extend the Python, simulator, local API/storage,
and local Supabase checks and how to diagnose CI failures, and confirm the
stable Pull Request check names needed for a later branch-protection proposal.

## Required approach

- Measure coverage from the repository's actual full Python suite before
  proposing a coverage policy; do not invent an arbitrary threshold.
- Document exact local reproduction for both required jobs and their artifacts.
- Explain simulator fixtures, local HTTP/storage integration, migrations,
  pgTAP extension, failure handling, and the open Product decisions.
- Confirm the final check names from successful Pull Request runs.
- Keep documentation and measurement changes separate from product behavior.

## Out of scope and safety limits

- Do not enable or modify branch protection without explicit user approval.
- Do not merge or close the Pull Request.
- Do not deploy or link to any remote Supabase project.
- Do not add physical-hardware, production-service, secret, or credential
  dependencies.
- Do not invent telemetry, authorization, retention, scale, SLO, or coverage
  requirements.
- Do not begin any work beyond Step 11.

## Validation

At minimum:

- reproducible coverage measurement with its exact command and result;
- documentation command and path accuracy;
- workflow and stable check-name verification against the successful remote
  Step 10 run;
- locked Python and npm dependency checks where affected;
- full pytest and local Supabase/database checks where affected;
- secret, remote-identifier, generated-state, and whitespace scans.

After approved commit and push, verify every updated Pull Request job and
download and inspect every required result artifact.

## Stop condition

Stop after Step 11 implementation, validation, persistent handoff update,
approved commit/push, successful Pull Request workflow verification, and
artifact inspection. Do not enable branch protection or merge the Pull Request
without separate explicit approval.
