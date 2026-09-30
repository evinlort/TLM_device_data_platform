# TLM CI Codex Session Bootstrap Prompt

Continue the TLM GitHub CI project.

This is a NEW Codex session. Do not assume access to previous chat or session
context.

Before making any changes:

1. Read `AGENTS.md` or `AGENT.md`, whichever exists and is authoritative for
   this repository.
2. Read `docs/ci/CI_STATE.md`.
3. Read `docs/ci/CI_PLAN.md`.
4. Read `docs/ci/NEXT_SESSION.md`.
5. Read `docs/ci/DECISIONS.md` only as needed for the current step.
6. Read `docs/ci/FLOW_EXPLANATIONS.md` for the completed-step context and
   required explanation format.
7. Verify:
   - `git status`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git remote -v`
8. Compare the actual Git state with `docs/ci/CI_STATE.md`.
9. If state differs, stop and investigate before changing files.
10. Execute ONLY the step defined in `docs/ci/NEXT_SESSION.md`.
11. Read only additional source or architecture files relevant to that step.
12. Do not start the following step in this session.

Communication rules:

- Explain everything to the user in Russian.
- Keep source code, code comments, commands, filenames, branch names, commit
  messages, YAML, SQL, and identifiers in English.
- Work one logical step at a time.
- If the user must execute a shell command, give one command at a time.
- Never invent Product Manager decisions.
- No physical device is available; required CI must use deterministic
  fakes/mocks/software simulation.
- Validate the step before marking it DONE.
- Update persistent CI state before finishing.
- Commit and push the completed step only after explicit user approval.

At the end of this session:

- append the completed step's full Russian-language explanation to
  `docs/ci/FLOW_EXPLANATIONS.md`, including purpose, implementation flow,
  encountered problems and resolutions, validation meaning, and excluded
  scope;
- update `docs/ci/CI_PLAN.md`;
- update `docs/ci/CI_STATE.md`;
- rewrite `docs/ci/NEXT_SESSION.md` for the following step;
- update `docs/ci/DECISIONS.md` only if a durable decision was made;
- verify this bootstrap prompt still matches the workflow;
- verify `AGENTS.md` or `AGENT.md` still points to this file;
- show validation results and diff summary;
- obtain approval, then commit and push;
- stop.

Do not execute the next step in this session.
