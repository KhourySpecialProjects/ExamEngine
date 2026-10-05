# ExamEngine hard rules

Full workflow: `AGENTS.md` → "Development workflow".

- Branches in use: feature branches → `develop` → `staging`. `main`/`master` are not in use.
  GitHub defaults to `main`: always pass `--base develop` or `--base staging` to `gh pr create`.
- Discuss and agree on a fix with the user, then create the Linear issue, then cut a feature
  branch from `origin/develop` named with the issue's `gitBranchName`. Never commit to `develop`
  or `staging` directly.
- No CI runs on PRs into `develop`/`staging`: run backend pytest, frontend vitest + tsc, and a
  smoke test yourself before saying work is done.
- Never put local dataset specifics (dataset names, CRNs, rooms, IDs, counts) in PRs, comments,
  issues or committed files.
- Never commit local edits to `docker-compose.override.yml`.
- Promote `develop` → `staging` only when the user asks, after the data-safety check and the
  two-axis code review; merge with `--match-head-commit`.
- Read `.session-notes.md` at the start of every session. Update it without being asked after
  each merge or promotion and when the user wraps up. Never commit it.
