"""Unit tests for security, secret scrubbing, and command approval guard."""

import unittest
from devpilot.core.security import redact_secrets, is_safe_startup_command, sanitize_project_name


class TestSecurity(unittest.TestCase):
    def test_redact_api_keys(self):
        sample = "export API_KEY=AIzaSyDxyz1234567890abcdef"
        redacted = redact_secrets(sample)
        self.assertNotIn("AIzaSyDxyz1234567890abcdef", redacted)
        self.assertIn("API_KEY", redacted)

    def test_redact_tokens_and_passwords(self):
        sample = "connect(password=SuperSecretPassword123, auth_token=ghp_ABC1234567890XYZ)"
        redacted = redact_secrets(sample)
        self.assertNotIn("SuperSecretPassword123", redacted)
        self.assertNotIn("ghp_ABC1234567890XYZ", redacted)

    def test_is_safe_startup_command(self):
        # Safe commands
        safe1, _ = is_safe_startup_command("npm run dev")
        self.assertTrue(safe1)

        safe2, _ = is_safe_startup_command("python -m uvicorn main:app --reload")
        self.assertTrue(safe2)

        safe3, _ = is_safe_startup_command("flutter run -d chrome")
        self.assertTrue(safe3)

        # Dangerous commands
        danger1, reason1 = is_safe_startup_command("rm -rf /")
        self.assertFalse(danger1)
        self.assertIn("Recursive deletion", reason1)

        danger2, reason2 = is_safe_startup_command("git push --force origin main")
        self.assertFalse(danger2)
        self.assertIn("Force push", reason2)

        danger3, reason3 = is_safe_startup_command("del /f /q C:\\Windows")
        self.assertFalse(danger3)
        self.assertIn("System drive deletion", reason3)

    def test_sanitize_project_name(self):
        clean = sanitize_project_name("My<App>:Test*Folder?")
        self.assertEqual(clean, "My_App__Test_Folder_")


if __name__ == "__main__":
    unittest.main()
