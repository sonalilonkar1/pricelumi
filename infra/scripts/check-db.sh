#!/bin/sh
# Restarts the local development database.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
query() {
  docker compose exec -T db sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -X -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At'
}
docker compose up -d --wait db
printf '%s\n' 'SELECT current_database(), current_user;' \
  'SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;' | query
table="infra_check_$(date +%s)_$$"
printf 'CREATE TABLE app.%s (id integer PRIMARY KEY); INSERT INTO app.%s VALUES (1);\n' "$table" "$table" | query
docker compose restart db
docker compose up -d --wait db
result=$(printf 'SELECT id FROM app.%s;\n' "$table" | query)
if [ "$result" != "1" ]; then
  echo 'FAIL: persistence check did not return the expected row.' >&2
  exit 1
fi
printf 'DROP TABLE app.%s;\n' "$table" | query
echo 'PASS: application login, table write/read, and persistence after restart.'
