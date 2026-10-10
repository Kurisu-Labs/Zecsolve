# Contribution workflow

- Before starting, fetch remote branches and inspect open PRs for overlapping work. Coordinate overlapping scope with the contributor already working on it.
- Start from an up-to-date `main` and create one branch named for the work, using a type such as `feat/`, `fix/`, or `docs/` and a descriptive task name. Do not use an agent-name prefix such as `codex/`.
- Push the branch to the remote before implementation so teammates can see that the task is in progress.
- Commit and push progress regularly on that same branch. Keep unrelated work on separate branches.
- Keep each commit focused on the smallest coherent change, with its related tests. Commit and push completed increments during implementation; do not bundle the entire branch into one final commit or force an arbitrary commit count.
- Open a pull request only when the task is complete and the relevant checks pass. Include the scope and validation results.
- Do not push directly to `main`; integrate changes through a pull request.
- Review the final diff and CI, resolve conflicts on the feature branch, and merge when ready. Delete the branch after confirming all its commits are merged.
- Use merge commits rather than squash merging so the incremental commit history remains visible.
- Write all Git commit messages in English.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the team workflow and commands.
