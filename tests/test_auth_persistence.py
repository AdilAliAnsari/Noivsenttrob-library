import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import Auth
import Dp
import config


class AuthPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_auth.db")
        self.addCleanup(self.tmp_dir.cleanup)

        self.patch_db_path = mock.patch.object(Dp, "DB_PATH", self.db_path)
        self.patch_config_db = mock.patch.object(config, "DB_PATH", self.db_path)
        self.patch_db_path.start()
        self.patch_config_db.start()
        self.addCleanup(self.patch_db_path.stop)
        self.addCleanup(self.patch_config_db.stop)

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_user_creates_users_table_and_persists_profile(self):
        user = Auth._save_user("google", "123", "Alice Example", "alice@example.com", "https://img.test/alice")

        self.assertEqual(user["id"], "google:123")
        self.assertEqual(user["provider"], "google")

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id, provider, name, email, avatar_url FROM users WHERE id = ?",
                ("google:123",),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], "google")
        self.assertEqual(row[2], "Alice Example")
        self.assertEqual(row[3], "alice@example.com")


if __name__ == "__main__":
    unittest.main()
