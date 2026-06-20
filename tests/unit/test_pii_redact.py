"""Unit tests for cherenkov/security/redact.py — PII redaction engine."""

import unittest
from cherenkov.security.redact import redact, redact_dict, is_clean


class TestRedactEmail(unittest.TestCase):
    def test_plain_email(self):
        out = redact("Contact me at alice@example.com please")
        self.assertNotIn("alice@example.com", out)
        self.assertIn("[REDACTED:email]", out)

    def test_subdomain_email(self):
        out = redact("user@mail.corp.org is valid")
        self.assertNotIn("user@mail.corp.org", out)

    def test_no_false_positive_on_normal_text(self):
        self.assertEqual(redact("Hello World"), "Hello World")


class TestRedactPhone(unittest.TestCase):
    def test_dashed_phone(self):
        out = redact("Call 555-867-5309 now")
        self.assertNotIn("555-867-5309", out)

    def test_dotted_phone(self):
        out = redact("555.867.5309")
        self.assertNotIn("555.867.5309", out)


class TestRedactSSN(unittest.TestCase):
    def test_ssn_dashes(self):
        out = redact("SSN: 123-45-6789")
        self.assertNotIn("123-45-6789", out)
        self.assertIn("[REDACTED:ssn]", out)

    def test_ssn_spaces(self):
        out = redact("SSN 123 45 6789")
        self.assertNotIn("123 45 6789", out)


class TestRedactAPIKey(unittest.TestCase):
    def test_openai_sk_key(self):
        out = redact("key=sk-abcdefghijklmnopqrstuvwxyz1234567890ab")
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", out)

    def test_aws_access_key(self):
        out = redact("AKIAIOSFODNN7EXAMPLE")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out)
        self.assertIn("[REDACTED:aws_access_key]", out)

    def test_bearer_token(self):
        out = redact("Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9")
        self.assertNotIn("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9", out)
        self.assertIn("[REDACTED:bearer_token]", out)


class TestRedactCreditCard(unittest.TestCase):
    def test_visa_card(self):
        out = redact("Card: 4111111111111111 expires soon")
        self.assertNotIn("4111111111111111", out)

    def test_amex_card(self):
        out = redact("Amex: 378282246310005")
        self.assertNotIn("378282246310005", out)


class TestRedactDict(unittest.TestCase):
    def test_sensitive_key_value_masked(self):
        data = {"username": "alice", "password": "s3cr3t!"}
        out = redact_dict(data)
        self.assertEqual(out["username"], "alice")
        self.assertEqual(out["password"], "[REDACTED:sensitive_field]")

    def test_nested_dict(self):
        data = {"user": {"email": "alice@example.com", "age": 30}}
        out = redact_dict(data)
        self.assertNotIn("alice@example.com", out["user"]["email"])
        self.assertEqual(out["user"]["age"], 30)

    def test_list_values(self):
        data = {"logs": ["user alice@example.com logged in", "normal event"]}
        out = redact_dict(data)
        self.assertNotIn("alice@example.com", out["logs"][0])

    def test_api_key_in_headers(self):
        data = {"headers": {"Authorization": "Bearer tok_abc123xyz987654321"}}
        out = redact_dict(data)
        self.assertNotIn("tok_abc123xyz987654321", str(out))

    def test_non_string_scalars_unchanged(self):
        data = {"count": 42, "active": True, "ratio": 3.14, "nul": None}
        out = redact_dict(data)
        self.assertEqual(out["count"], 42)
        self.assertEqual(out["active"], True)
        self.assertIsNone(out["nul"])

    def test_empty_dict(self):
        self.assertEqual(redact_dict({}), {})

    def test_secret_key_name(self):
        data = {"api_key": "supersecretvalue12345"}
        out = redact_dict(data)
        self.assertEqual(out["api_key"], "[REDACTED:sensitive_field]")


class TestIsClean(unittest.TestCase):
    def test_clean_text(self):
        self.assertTrue(is_clean("The server responded with 200 OK"))

    def test_dirty_text(self):
        self.assertFalse(is_clean("User: admin@corp.com"))

    def test_empty_string(self):
        self.assertTrue(is_clean(""))


class TestLabelPiiFlag(unittest.TestCase):
    def test_no_label_mode(self):
        out = redact("admin@corp.com", label_pii=False)
        self.assertNotIn("admin@corp.com", out)
        self.assertEqual(out, "[REDACTED]")

    def test_label_mode(self):
        out = redact("admin@corp.com", label_pii=True)
        self.assertIn("[REDACTED:email]", out)


if __name__ == "__main__":
    unittest.main()
