"""Safety checks run in temporary folders; no Docker services are changed."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("setup_local", Path(__file__).with_name("setup-local.py"))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupSafetyTests(unittest.TestCase):
    def test_existing_credentials_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "require_docker"):
            folder = Path(directory)
            original = b"APP_DB_PASSWORD=existing-secret\nPOSTGRES_PORT=5433\n"
            (folder / ".env").write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertFalse(setup.prepare(folder, 5432))
            self.assertEqual((folder / ".env").read_bytes(), original)
            self.assertNotIn("existing-secret", output.getvalue())

    def test_new_credentials_private_and_not_printed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "require_docker"):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            folder = Path(directory)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertTrue(setup.prepare(folder, port))
            target = folder / ".env"
            values = dict(line.split("=", 1) for line in target.read_text().splitlines())
            self.assertEqual(values["POSTGRES_PORT"], str(port))
            self.assertNotEqual(values["POSTGRES_PASSWORD"], values["APP_DB_PASSWORD"])
            for key in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD"):
                self.assertEqual(len(values[key]), 48)
                self.assertNotIn(values[key], output.getvalue())
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_busy_port_does_not_create_env(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "require_docker"), socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            folder = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                setup.prepare(folder, occupied.getsockname()[1])
            self.assertFalse((folder / ".env").exists())

    def test_docker_failure_does_not_create_env(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "require_docker", side_effect=RuntimeError("Docker unavailable")):
            folder = Path(directory)
            with self.assertRaises(RuntimeError):
                setup.prepare(folder, 5432)
            self.assertFalse((folder / ".env").exists())

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, "require_docker"):
            folder = Path(directory)
            target = folder / "private"
            target.write_text("unchanged")
            (folder / ".env").symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "symbolic link"):
                setup.prepare(folder, 5432)
            self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
