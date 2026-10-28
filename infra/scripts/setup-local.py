"""Prepare local configuration without starting Docker services or replacing .env."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess


def require_docker():
    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed. Install and open Docker Desktop first.")
    for command, message in (
        (["docker", "compose", "version"], "Docker Compose is unavailable."),
        (["docker", "info"], "Docker is not reachable. Open Docker Desktop and wait for it to start."),
    ):
        result = subprocess.run(command, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(message)


def prepare(folder, port):
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port between 1024 and 65535.")
    require_docker()
    target = folder / ".env"
    if target.is_symlink():
        raise RuntimeError(".env is a symbolic link. Review it manually; no changes made.")
    if target.exists():
        if not target.is_file():
            raise RuntimeError(".env exists but is not a regular file; no changes made.")
        print("Existing .env preserved. Passwords and port were not changed.")
        print("Existing settings were not validated. Use docker compose config --quiet to check required values.")
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(
                f"Local port {port} is unavailable. Retry with --port followed by another port, such as 5433."
            ) from error
    content = (
        f"POSTGRES_DB=pricelumi\nPOSTGRES_PORT={port}\n"
        f"POSTGRES_PASSWORD={secrets.token_hex(24)}\n"
        f"APP_DB_PASSWORD={secrets.token_hex(24)}\n"
    )
    # Exclusive creation prevents overwriting a file created concurrently.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
    print(f"Created local .env for port {port}; password values are hidden.")
    print("Keep .env private. Port availability was checked but is not reserved.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5432, help="Local host port for a NEW .env (default: 5432)")
    args = parser.parse_args()
    try:
        prepare(Path(__file__).resolve().parents[2], args.port)
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        if isinstance(error, subprocess.TimeoutExpired):
            parser.exit(1, "Docker did not respond within 30 seconds. Check Docker Desktop and retry.\n")
        parser.exit(1, f"Setup stopped: {error}\n")
    print("Next, from the pricelumi repository root: docker compose up -d --wait db")


if __name__ == "__main__":
    main()
