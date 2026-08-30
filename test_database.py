"""Tests for PostgreSQL connection and diagnostic helpers."""

import unittest
from unittest.mock import Mock
from unittest.mock import patch

from database import connect_database, sanitize_database_error


class DatabaseTest(unittest.TestCase):
    @patch("database.importlib.import_module")
    def test_connect_database_uses_database_parameter_for_name(self, import_module):
        connect = Mock()
        import_module.return_value.connect = connect
        connect_database("index")
        connect.assert_called_once_with(database="index")

    @patch("database.importlib.import_module")
    def test_connect_database_uses_dsn_for_uri(self, import_module):
        connect = Mock()
        import_module.return_value.connect = connect
        uri = "postgresql://api_user:secret@127.0.0.1:5432/index"
        connect_database(uri)
        connect.assert_called_once_with(uri)

    def test_sanitize_database_error_redacts_uri_password(self):
        error = RuntimeError(
            'database "postgresql://api_user:secret@127.0.0.1:5432/index" does not exist'
        )
        message = sanitize_database_error(error)
        self.assertNotIn("secret", message)
        self.assertIn("postgresql://api_user:***@127.0.0.1:5432/index", message)

    def test_sanitize_database_error_redacts_keyword_password(self):
        message = sanitize_database_error(RuntimeError("password='secret value' host=db"))
        self.assertEqual(message, "password=*** host=db")


if __name__ == "__main__":
    unittest.main()
