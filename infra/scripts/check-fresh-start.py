"""Test an isolated database and remove its resources. Requires Docker and psql."""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import uuid


def main():
    source = Path(__file__).resolve().parents[2]
    psql = shutil.which("psql")
    if not psql:
        raise SystemExit("Install the PostgreSQL client (psql) before running this check.")
    project = "pricelumi-check-" + uuid.uuid4().hex[:12]
    password = secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="pricelumi-check-") as directory:
        folder = Path(directory)
        shutil.copy2(source / "compose.yaml", folder / "compose.yaml")
        shutil.copytree(source / "infra" / "postgres", folder / "infra" / "postgres")
        config = folder / ".env"
        config.write_text(
            "POSTGRES_DB=pricelumi\nPOSTGRES_PORT=0\n"
            f"POSTGRES_PASSWORD={secrets.token_hex(24)}\nAPP_DB_PASSWORD={password}\n"
        )
        config.chmod(0o600)
        # Explicit test values prevent inherited shell variables overriding .env.
        env = os.environ.copy()
        for key in ("POSTGRES_DB", "POSTGRES_PORT", "POSTGRES_PASSWORD", "APP_DB_PASSWORD",
                    "COMPOSE_FILE", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES"):
            env.pop(key, None)
        base = ["docker", "compose", "--project-directory", str(folder),
                "--env-file", str(config), "-f", str(folder / "compose.yaml"), "-p", project]

        def compose(*args):
            return subprocess.run(base + list(args), env=env, text=True,
                                  capture_output=True, check=True)

        try:
            compose("up", "-d", "--wait", "--wait-timeout", "90", "db")
            print("PASS: empty-volume startup and health check", flush=True)
            address = compose("port", "db", "5432").stdout.strip()
            if not address.startswith("127.0.0.1:"):
                raise AssertionError("Database is not published exclusively on loopback")
            port = address.rsplit(":", 1)[1]
            client_env = os.environ.copy()
            client_env.update(PGPASSWORD=password, PGCONNECT_TIMEOUT="5", PGSSLMODE="disable")
            client = [psql, "-X", "-w", "-h", "127.0.0.1", "-p", port,
                      "-U", "pricelumi_app", "-d", "pricelumi", "-v", "ON_ERROR_STOP=1", "-At"]

            def query(sql, wrong_password=False):
                credentials = client_env.copy()
                if wrong_password:
                    credentials["PGPASSWORD"] = secrets.token_hex(24)
                return subprocess.run(client + ["-c", sql], env=credentials,
                                      text=True, capture_output=True)

            def expect(sql, value):
                result = query(sql)
                if result.returncode or result.stdout.strip() != value:
                    raise AssertionError(f"Unexpected result for check: {sql}\n{result.stderr}")

            expect("SELECT current_database() || '|' || current_user;", "pricelumi|pricelumi_app")
            expect("SHOW search_path;", "app")
            print("PASS: automatic app account and host-to-Docker password login", flush=True)
            rejected = query("SELECT 1;", wrong_password=True)
            if rejected.returncode == 0 or "password authentication failed" not in rejected.stderr:
                raise AssertionError("Wrong password did not produce the expected authentication rejection")
            print("PASS: incorrect password rejected", flush=True)
            expect("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user;", "f|f|f")
            for sql in ("CREATE ROLE forbidden_test_role;", "CREATE DATABASE forbidden_test_db;",
                        "CREATE TABLE public.forbidden_test_table (id integer);"):
                result = query(sql)
                if result.returncode == 0 or "permission denied" not in result.stderr:
                    raise AssertionError(f"Expected permission denial: {sql}")
            print("PASS: cannot create roles, databases or public-schema tables", flush=True)
            result = query("CREATE TABLE app.persistence_check (id integer PRIMARY KEY); INSERT INTO app.persistence_check VALUES (1);")
            if result.returncode:
                raise AssertionError("Application table creation/write failed")
            expect("SELECT id FROM app.persistence_check;", "1")
            result = compose("run", "--rm", "--no-deps", "db", "sh", "-c",
                             'PGPASSWORD="$APP_DB_PASSWORD" psql -X -w -h db -U "$APP_DB_USER" -d "$POSTGRES_DB" -Atc "SELECT 1"')
            if result.stdout.strip() != "1":
                raise AssertionError("Compose-network connection failed")
            print("PASS: separate container connects using db:5432", flush=True)
            compose("restart", "db")
            compose("up", "-d", "--wait", "--wait-timeout", "90", "db")
            # Docker may assign a different ephemeral host port after restart.
            address = compose("port", "db", "5432").stdout.strip()
            client[client.index("-p") + 1] = address.rsplit(":", 1)[1]
            expect("SELECT id FROM app.persistence_check;", "1")
            print("PASS: application data survives restart", flush=True)
            print("Test project: " + project, flush=True)
        except subprocess.CalledProcessError as error:
            print(error.stderr, flush=True)
            logs = compose("logs", "--tail=30", "db").stdout
            print(logs.replace(password, "[redacted]"), flush=True)
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans")
            print("Temporary test containers, network and volume removed.", flush=True)


if __name__ == "__main__":
    main()
