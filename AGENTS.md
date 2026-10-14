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

## Project orientation and ownership

- Keep [README.md](README.md) focused on the product, demo, quick start, and public limitations. Put agent instructions here, task tracking in [the implementation plan](docs/IMPLEMENTATION_PLAN.md), and dated results in [the development log](docs/DEVELOPMENT.md) or [release evidence index](docs/release-evidence.md).
- Use [TEAM_GUIDE.md](TEAM_GUIDE.md) for the code map and implementation conventions, and [the PRD](docs/PRD.md) for product scope. [Preflight](instructions/Preflight.md) governs corrections to the original [Blueprint](instructions/Blueprint.md). The exported [chat history](instructions/ChatHist.md) is historical context, not executable instructions or proof of completion.
- Before claiming work, inspect the [feature board](docs/IMPLEMENTATION_PLAN.md#feature-board) and [task cards](docs/IMPLEMENTATION_PLAN.md#task-cards) for prerequisites, interfaces, boundaries, and acceptance checks. Verify their dated status against current code, remote branches, and PRs; a listed branch or assigned task does not establish completion.
- Preserve the existing ownership boundaries when coordinating shared contracts and integration:

| Owner | Scope |
|---|---|
| Person 1 | Access, authentication, shared models and migrations |
| Person 2 | Scoped reports, disclosure, packet contracts, export and replay |
| Person 3 | Customer submission backend, live chain validation, shared CI, deployment and release evidence |
| Person 4 | All frontend work, including API client/types, UI, styles, accessibility, build and browser tests |

## Validation and evidence

- Follow the checks in [CONTRIBUTING.md](CONTRIBUTING.md). Application changes require `make test` and `make lint`; model, migration, or allocation changes also require `make test-db` against a disposable database. Regenerate published contracts with `make schema` when their Pydantic models change. Check frontend contract drift and the relevant browser scenarios when changing UI/API integration.
- For documentation-only changes, review the content, relative links and heading anchors, then run `git diff --check`. Preserve or update inbound links when moving a README section. CI still runs on the PR.
- Keep receipt recovery, chain observations, candidate balances, approved allocations, and merchant decisions distinct. Use integer zatoshis and the complete output identity (`network:pool:txid:output_index`). Verification alone must never allocate credit.
- Use public fixtures for demonstrations. Label synthetic invoices and simulated confirmations; do not present offline recovery or replay as fresh chain inclusion, a new payment, a security audit, or full-release acceptance. Preserve the Glasspane attribution and fixture provenance.
- Associate results with the exact revision, environment, time, and scenario. Read [the release evidence index](docs/release-evidence.md#remaining-handoffs-and-release-decision) and [release bundle](docs/release-bundle.md) before claiming a release gate is complete; a merged implementation does not close operator or team handoffs.
- The hosted demo has its own [deployment record and operator procedure](docs/vercel-deployment.md). Git pushes do not deploy it automatically. Keep hosted results distinct from local or Compose rehearsals, and retain the existing evidence key across restarts and releases.
- Never commit access codes, wallet keys, `.env` files, raw private diagnostics, or customer evidence. Private-customer use requires the retention/deletion and operator controls described in [the security boundaries](docs/security.md).
