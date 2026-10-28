# shopagent
Shop Agent

# Local development

PostgreSQL 17 for local development. Backend integration and Redis are not included yet.

## Requirements

- Docker Desktop, installed and running
- Python 3

Open a terminal in the `pricelumi` repository root. Run all commands below there.

## 1. Create your local settings

```sh
python3 infra/scripts/setup-local.py
```

This creates `.env` with two random passwords. If `.env` already exists, it is left unchanged.

If port 5432 is busy on a new setup, use:

```sh
python3 infra/scripts/setup-local.py --port 5433
```

If `.env` already exists, change `POSTGRES_PORT` in that file instead.

## 2. Start the database

```sh
docker compose up -d --wait db
docker compose ps
```

Wait for the database to show `healthy`. The first startup creates the database,
application account and `app` schema automatically.

## 3. Connect your backend

| Setting | Value |
| --- | --- |
| Database | `pricelumi` |
| User | `pricelumi_app` |
| Password | `APP_DB_PASSWORD` from your own `.env` |
| Host when backend runs on your computer | `localhost` |
| Port when backend runs on your computer | `POSTGRES_PORT` from your `.env` |
| Address inside the same Compose network | `db:5432` |
| Schema | `app` |

The default host port is 5432. If you selected 5433, use `localhost:5433`.
Backend integration and its environment variable names are pending.
The backend will need these credentials configured; creating `.env` here does not
configure the backend automatically.

## Passwords

Each developer runs their own local database with their own generated passwords.

- `APP_DB_PASSWORD` is for the backend's `pricelumi_app` account.
- `POSTGRES_PASSWORD` is for the `postgres` administrator account. Do not use it in the backend.
- Keep `.env` private. It is excluded from Git. Share `.env.example` instead.
- Running setup again does not replace existing passwords.
- After the database has been initialized, editing a password in `.env` alone does
  not change the password stored in PostgreSQL. Database password changes must
  also be applied in PostgreSQL.

## Check the connection

```sh
docker compose exec db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB"'
```

At the SQL prompt, run:

```sql
SELECT current_database(), current_user;
```

Expected: `pricelumi` and `pricelumi_app`. Type `\q` to exit.

## Stop and restart

```sh
docker compose stop db
docker compose up -d --wait db
```

Data is kept between restarts. Do not run `docker compose down -v` unless you intend
to delete the local database data.

## Troubleshooting

- **Docker unavailable:** open Docker Desktop and wait for it to start.
- **Port already in use:** change `POSTGRES_PORT` in `.env`, then run the start command again.
- **Login fails:** check that the backend uses `APP_DB_PASSWORD` from your `.env`.
  If passwords were changed after initialization, check that PostgreSQL and `.env`
  use matching values.
- **Startup fails:** run `docker compose logs --tail=50 db`. Remove any sensitive
  information before sharing logs. Do not delete your volume to troubleshoot.

## Optional checks

| Command | What it does |
| --- | --- |
| `sh infra/scripts/check-db.sh` | Checks read/write and persistence; briefly restarts your database |
| `python3 infra/scripts/check-fresh-start.py` | Tests a separate empty database and removes it afterward; also requires `psql` on your computer |
| `python3 -B -m unittest discover -s infra/scripts -p test_setup_local.py -v` | Tests the setup helper without starting database services |

See [Validation results](docs/infra-validation.md) for completed checks and limitations.

See [Infrastructure CI](docs/ci.md) for automated checks and troubleshooting.
