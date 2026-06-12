import unittest

from d3hl_infra_crew.boundary import evaluate_boundary


class BoundaryTests(unittest.TestCase):
    def test_blocks_terraform_apply_under_plan_only(self):
        check = evaluate_boundary("Run terraform apply after review", "plan_only")
        self.assertFalse(check.passed)
        self.assertTrue(any("terraform" in finding for finding in check.findings))

    def test_blocks_terraform_login_under_plan_only(self):
        check = evaluate_boundary("Run terraform login before remote operations", "plan_only")
        self.assertFalse(check.passed)
        self.assertTrue(any("terraform" in finding for finding in check.findings))

    def test_blocks_terraform_plan_under_plan_only(self):
        check = evaluate_boundary("Run terraform plan to queue the remote run", "plan_only")
        self.assertFalse(check.passed)
        self.assertTrue(any("terraform" in finding for finding in check.findings))

    def test_allows_terraform_plan_under_live_read_check(self):
        check = evaluate_boundary("Run terraform plan to queue an approved read/check run", "live_read_check")
        self.assertTrue(check.passed, check.findings)

    def test_blocks_terraform_apply_under_live_read_check(self):
        check = evaluate_boundary("Run terraform apply after review", "live_read_check")
        self.assertFalse(check.passed)
        self.assertTrue(any("terraform" in finding for finding in check.findings))

    def test_allows_ansible_check_mode_under_live_read_check(self):
        check = evaluate_boundary(
            "Run ansible-playbook -i inventory/hosts.yml playbooks/configure.yml --check",
            "live_read_check",
        )
        self.assertTrue(check.passed, check.findings)

    def test_blocks_ansible_without_check_under_live_read_check(self):
        check = evaluate_boundary(
            "Run ansible-playbook -i inventory/hosts.yml playbooks/configure.yml",
            "live_read_check",
        )
        self.assertFalse(check.passed)
        self.assertTrue(any("ansible-playbook" in finding for finding in check.findings))

    def test_allows_static_terraform_validation_under_plan_only(self):
        check = evaluate_boundary(
            "Run terraform fmt -check -recursive and terraform -chdir=terraform/environments/dev validate",
            "plan_only",
        )
        self.assertTrue(check.passed)

    def test_allows_op_secret_reference(self):
        check = evaluate_boundary("Use op://d3HLPRV/proxmox_env/PROXMOX_API_TOKEN as a reference only", "plan_only")
        self.assertTrue(check.passed)

    def test_flags_plaintext_token_shape(self):
        check = evaluate_boundary("token = abcdefghijklmnop", "plan_only")
        self.assertFalse(check.passed)

    def test_flags_plaintext_token_shape_under_live_read_check(self):
        check = evaluate_boundary("token = abcdefghijklmnop", "live_read_check")
        self.assertFalse(check.passed)


if __name__ == "__main__":
    unittest.main()
