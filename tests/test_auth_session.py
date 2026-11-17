from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from jazira_agri.auth import (
    create_session_token,
    hash_password,
    validate_api_key,
    verify_password,
    verify_session_token,
)
from jazira_agri.core.configuration import get_settings


class AuthenticationTests(unittest.TestCase):
    def test_signed_session_round_trip_and_tamper_rejection(self):
        token = create_session_token("farmer", "s" * 40)
        self.assertEqual(verify_session_token(token, "s" * 40)["sub"], "farmer")
        self.assertIsNone(verify_session_token(token + "x", "s" * 40))
        self.assertIsNone(verify_session_token(token, "x" * 40))

    def test_salted_password_hash_verifies_and_rejects_wrong_password(self):
        encoded = hash_password("correct-horse-battery")
        self.assertTrue(verify_password("correct-horse-battery", encoded))
        self.assertFalse(verify_password("incorrect-password", encoded))
        self.assertFalse(verify_password("x", "invalid"))

    def test_api_key_comparison_rejects_empty_or_wrong_key(self):
        self.assertTrue(validate_api_key("secret", "secret"))
        self.assertFalse(validate_api_key("wrong", "secret"))
        self.assertFalse(validate_api_key("secret", ""))

    def test_settings_redact_all_secrets(self):
        with patch.dict(os.environ, {
            "JAZIRA_USERNAME": "farmer", "JAZIRA_PASSWORD": "private",
            "JAZIRA_PASSWORD_HASH": "hash-private", "API_KEY": "key",
            "SECRET_KEY": "secret" * 8, "DB_PASSWORD": "db-private",
            "DATABASE_URL": "postgres://private",
        }, clear=False):
            get_settings.cache_clear()
            values = get_settings().as_dict()
            self.assertNotIn("private", str(values))
            self.assertEqual(values["password"], "***hidden***")
            self.assertEqual(values["password_hash"], "***hidden***")
        get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
