# Infrastructure CI

The workflow in `.github/workflows/infrastructure.yml` runs on pull requests to
any base branch, pushes to `main` and `feature/W1-22-ci`, and manual runs once the workflow
is available on the default branch. It uses GitHub-hosted Ubuntu 24.04 runners.

| Check | Coverage |
| --- | --- |
| Infrastructure checks | Setup-helper safety tests, Compose configuration and shell script syntax |
| PostgreSQL integration | Empty-volume startup, health, host/container connections, rejected passwords, role permissions and data persistence after restart |
| Secret scanning | Gitleaks 8.30.1 checks committed history reachable from HEAD for recognized secret patterns |
| Workflow validation | actionlint 1.7.12 checks workflow syntax, expressions and job references |

The database test creates a separate Compose project with random credentials and
removes its containers, network and volume afterward. No repository secrets or
developer `.env` files are needed. `.env.example` is used only to validate Compose
syntax; its placeholder passwords are not used to start a database.

The workflow has read-only repository permissions. Checkout is pinned to a commit
and does not persist Git credentials. Time limits bound each job, and a newer run
on the same branch or PR cancels the older run. A forcibly interrupted database
test may not finish cleanup; its GitHub-hosted runner is discarded after the job.

## Reproduce a failure locally

From the repository root, with Python 3, Docker Compose and the `psql` client:

```sh
python3 -B -m unittest discover -s infra/scripts -p test_setup_local.py -v
docker compose --env-file .env.example config --quiet
sh -n infra/scripts/check-db.sh
python3 -u infra/scripts/check-fresh-start.py
```

Open the failed check on the pull request and expand the failing step to see its
output. Fix the cause and push the correction to the same branch. GitHub runs the
checks again. Fork PRs may need a maintainer to approve the workflow run.

## Secret scanning and workflow validation

Both tools are downloaded from their official GitHub releases at fixed versions.
The workflow verifies each archive against a pinned SHA-256 checksum before running
it. No additional repository permissions or application secrets are required.

Secret scanning fetches full history and scans commits reachable from the checked-out
HEAD, including credentials removed in later commits. It does not scan uncommitted
files or guarantee detection of every password. Findings fail the job, with secret
values fully redacted. No scan report is uploaded as an artifact.

If a real secret is reported, revoke or rotate it with its owner and coordinate
history cleanup with Sonali. Deleting the latest copy alone does not remove it from
history. Review suspected false positives before adding any narrowly scoped exception.
Do not paste a secret into PR comments or logs.

To run these tools locally after installing the versions above from their official
releases:

```sh
gitleaks git --redact=100 --no-banner --log-opts="HEAD" .
actionlint -color -shellcheck=""
```

Commit intended changes before the history scan; it does not inspect the working
tree. actionlint reads the current workflow files. The optional ShellCheck integration
is disabled for consistent local/CI results; shell syntax still has its separate
check. This is workflow validation, not a security audit of every shell command.

Local verification on 27 October 2026 found no secret patterns in committed history
and no workflow validation errors. Temporary negative tests confirmed that a synthetic
token fails scanning without exposing its value, and an invalid job dependency fails
workflow validation. The test files were removed and were never added to this project.
The original infrastructure and database jobs previously passed on the fork.

## Pending work

- Verify the expanded workflow on GitHub and the PR-side run in the integration repository.
- Add backend tests/lint and frontend build/lint after their files and commands arrive.
- Confirm required-check names with Sonali before she configures merge rules.
- Add dependency and container scanning separately; these checks do not scan vulnerabilities.

W1-22 remains in progress until the agreed application checks are also implemented
and verified on a pull request.
