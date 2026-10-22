# Working on this repo

Read first, every session, in this order:

1. `docs/decision-log.md` - every decision, what was rejected, why. These are constraints.
2. `docs/SESSION.md` - where the last session stopped.
3. `docs/flow.md` - how the pipeline fits together.

Rules:

- Tests are frozen. Never edit a test to make code pass; fix the code.
  New behavior gets new tests.
- Build -> test -> push. `python3 -m unittest discover -s tests` must be
  green before every commit.
- Stdlib-only core. Optional integrations load lazily and fail with a
  clear message when missing.
- No secrets in the repo. Keys come from the environment.
- One feature per session. Update `docs/SESSION.md` and the decision log
  when you stop.
