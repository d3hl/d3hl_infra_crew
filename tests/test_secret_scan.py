import unittest

from d3hl_infra_crew.secret_scan import find_plaintext_secrets


class SecretScanTests(unittest.TestCase):
    def test_flags_high_confidence_token(self):
        self.assertTrue(find_plaintext_secrets("api_key = sk-abcdefghijklmnopqrstuvwxyz0123"))

    def test_flags_private_key_block(self):
        self.assertTrue(find_plaintext_secrets("-----BEGIN OPENSSH PRIVATE KEY-----\nx\n"))

    def test_flags_plaintext_assignment(self):
        findings = find_plaintext_secrets('client_secret = "hunter2hunter2"')
        self.assertTrue(findings)
        self.assertIn("client_secret", findings[0])

    def test_allows_op_reference(self):
        self.assertEqual(find_plaintext_secrets('token = "op://d3HLPRV/cf/api_token"'), [])

    def test_allows_terraform_variable_reference(self):
        self.assertEqual(find_plaintext_secrets("token = var.cloudflare_api_token"), [])

    def test_allows_jinja_reference(self):
        self.assertEqual(find_plaintext_secrets('ansible_password: "{{ vault_password }}"'), [])

    def test_allows_clean_terraform(self):
        clean = 'variable "api_token" {\n  type = string\n}\n'
        self.assertEqual(find_plaintext_secrets(clean), [])


if __name__ == "__main__":
    unittest.main()
