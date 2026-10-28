# Local Infrastructure Validation

**Last verified:** 26 October 2026
**Scope:** Local PostgreSQL setup and configuration helper

## Test environment

| Component | Version / configuration |
| --- | --- |
| Platform | macOS, Apple Silicon, Docker Desktop |
| Docker | 29.6.1 |
| Docker Compose | 5.3.0 |
| PostgreSQL | 17.11, from `postgres:17-bookworm` |
| Database / application user | `pricelumi` / `pricelumi_app` |
| Application schema | `app` |

## Results

| Check | Result |
| --- | --- |
| Compose configuration and shell script syntax | Passed |
| Empty-volume startup and automatic account creation | Passed |
| Database health check | Passed |
| Password-authenticated connection from the host | Passed |
| Connection from another container through `db:5432` | Passed |
| Incorrect password rejected | Passed |
| Application role cannot create roles or databases | Passed |
| Application role cannot create tables in `public` | Passed |
| Application read/write in `app` schema | Passed |
| Data retained after database restart | Passed |
| Temporary test resources removed | Passed |
| Setup-helper safety tests | 5 passed |

The setup-helper tests cover existing credential preservation, private password
creation without printed values, occupied ports, Docker failure and symbolic-link
rejection. Docker detection is mocked in these unit tests. A separate run of the
setup command confirmed Docker detection and preservation of the existing `.env`.

The database checks ran in a separate temporary Compose project with an empty
volume and generated credentials. The existing development database was not
restarted or modified during the isolated test.

## Reproduce

Run from the repository root with Docker Desktop running. The isolated database
test also requires Python 3 and the PostgreSQL client `psql` on the host.

```sh
docker compose config --quiet
python3 -B -m unittest discover -s infra/scripts -p test_setup_local.py -v
python3 infra/scripts/check-fresh-start.py
```

Compose validation requires a local `.env`; create it using the README instructions.
The isolated test removes its own containers, network and volume when it finishes.
If forcibly terminated, its temporary resources may require manual cleanup.

To test the normal development database instead:

```sh
sh infra/scripts/check-db.sh
```

This command briefly restarts that database and removes its temporary test table
after a successful run.

## Limitations

Backend integration, migrations, shared sample data, Redis, CI, staging and backup
recovery are not validated. The setup has not yet been verified on another
developer's machine. These checks do not establish production readiness.
