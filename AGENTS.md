# Repository Instructions

For TLM CI work:

- Communicate with the user in Russian. Keep source code, identifiers, commands,
  filenames, branch names, commit messages, YAML, SQL, code comments, and
  docstrings in English.
- Work on one logical CI step per Codex session. Do not begin the next step in
  the same session.
- Do not invent Product Manager decisions. Mark temporary test values as test
  fixtures or test configuration, not product requirements.
- Required CI must not depend on physical hardware or production Supabase.
- Validate each step and update the persistent handoff before completion.
- After completing and validating each step, but before requesting commit
  approval, append a complete Russian-language explanation to
  `docs/ci/FLOW_EXPLANATIONS.md`. Explain why the step was needed, what
  changed, how the resulting flow works and solves the goal, what happened
  during implementation, how problems were resolved, what validation proves,
  and what remains intentionally out of scope.
- Commit and push only after explicit user approval.

Persistent CI coordination files:

- Plan: `docs/ci/CI_PLAN.md`
- Current verified state: `docs/ci/CI_STATE.md`
- Exact next step: `docs/ci/NEXT_SESSION.md`
- Durable decisions: `docs/ci/DECISIONS.md`
- New-session prompt: `docs/ci/BOOTSTRAP_PROMPT.md`
- Detailed Russian step explanations: `docs/ci/FLOW_EXPLANATIONS.md`

Before the next CI step, open `docs/ci/BOOTSTRAP_PROMPT.md` and use its
contents as the prompt for a new Codex session. The concrete task for that
session is defined only in `docs/ci/NEXT_SESSION.md`.
