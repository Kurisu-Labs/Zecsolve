# Contributing

Our workflow is: choose a task → publish its branch → implement and push progress → open a final PR → review and merge → delete the merged branch.

## Before starting a task

Check remote branches and open pull requests before choosing work:

```sh
git fetch --prune origin
git branch -r
gh pr list --state open
```

An active branch can represent work that has no PR yet. Check its recent commits and coordinate with its contributor if the scope overlaps. A branch name signals work in progress; it does not lock files or prevent conflicts.

Use one branch per task, named for the kind of change and the actual work: `feat/recipient-normalization`, `fix/credential-expiry`, or `docs/contribution-workflow`. The same convention applies to people and coding agents; do not use an agent name such as `codex/` as the prefix.

From a clean checkout, update `main`, create the branch, and **push it before editing or coding**:

```sh
git switch main
git pull --ff-only origin main
git switch -c feat/recipient-normalization
git push -u origin feat/recipient-normalization
```

Replace the example name with your task. If you have uncommitted work, preserve it on its existing branch before switching. Do not reset or overwrite another contributor's work.

## During implementation

Keep working on the same branch and push meaningful progress regularly so teammates can inspect it. Use English commit messages and stage only files belonging to the task:

```sh
git add <changed-files>
git commit -m "feat: add recipient address normalization"
git push
```

Keep unrelated changes on separate branches. Coordinate changes to shared API contracts, migrations, and modules before editing them. Never commit secrets, `.env`, build output, or private customer evidence.

Make each commit the smallest coherent, reviewable change, including its related tests. For example, a feature branch may contain separate commits for its contract, decoder, CLI, adapter, integration coverage, and documentation. Commit and push each completed increment during implementation instead of collecting all work into one final commit. There is no fixed commit count, and a tiny change does not need artificial splitting.

## When the task is complete

Review your diff and run the relevant checks. For application changes, run `make test` and `make lint`. Also run `make test-db` against a disposable database for model, migration, or allocation changes, and regenerate the verifier schema with `make schema` when its contract changes. For documentation-only changes, check the content, links, and `git diff --check`; CI still runs on the PR.

Push the final changes, then open a PR targeting `main`. Include what changed, why, validation results, and any remaining limitations. Do not open a PR merely to announce that implementation has started; the published branch provides that visibility.

```sh
git push
gh pr create --base main
```

## Review, merge, and cleanup

Maintainers check the final diff, CI, and mergeability. Ready PRs can be merged directly after that review. Resolve any conflicts on the feature branch, rerun affected checks, and push the resolution before merging. Do not push changes directly to `main` or bypass required checks.

Use **Create a merge commit** (or `gh pr merge --merge`) rather than squash merging, so the branch's incremental commits remain visible in history.

Once the PR is confirmed merged and the branch contains no unmerged work, delete its remote branch using GitHub's **Delete branch** button. Then update your local checkout and remove your local feature branch:

```sh
git switch main
git pull --ff-only origin main
git branch -d feat/recipient-normalization
git fetch --prune origin
```

Deleting a merged branch preserves the PR and the commits integrated into `main`. If Git refuses the local deletion, inspect the remaining commits before taking any further action.
