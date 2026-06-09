import unittest

from d3hl_infra_crew.boundary import evaluate_boundary


class BoundaryTests(unittest.TestCase):
    def test_blocks_terraform_apply_under_plan_only(self):
        check = evaluate_boundary("Run terraform apply after review", "plan_only")
        self.assertFalse(check.passed)
        self.assertTrue(any("terraform" in finding for finding in check.findings))

    def test_allows_op_secret_reference(self):
        check = evaluate_boundary("Use op://d3HLPRV/proxmox_env/PROXMOX_API_TOKEN as a reference only", "plan_only")
        self.assertTrue(check.passed)

    def test_flags_plaintext_token_shape(self):
        check = evaluate_boundary("token = abcdefghijklmnop", "plan_only")
        self.assertFalse(check.passed)


if __name__ == "__main__":
    unittest.main()
