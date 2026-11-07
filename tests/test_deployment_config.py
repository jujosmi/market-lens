import unittest

from market_lens.config import hosted_watchlist_mode, public_watchlist_guard, setting_enabled


class DeploymentConfigTests(unittest.TestCase):
    def test_boolean_setting_is_explicit(self):
        self.assertTrue(setting_enabled("TRUE"))
        self.assertTrue(setting_enabled("1"))
        self.assertFalse(setting_enabled("enabled"))
        self.assertFalse(setting_enabled(""))

    def test_hosted_mode_accepts_environment_or_secret(self):
        self.assertTrue(hosted_watchlist_mode("true", ""))
        self.assertTrue(hosted_watchlist_mode("", "yes"))
        self.assertFalse(hosted_watchlist_mode("", "false"))

    def test_public_deployment_fails_closed_without_hosted_mode(self):
        message = public_watchlist_guard(public_environment_value="true")
        self.assertIn("MARKET_LENS_HOSTED=true", message)

    def test_public_deployment_accepts_hosted_mode_from_secret(self):
        self.assertIsNone(public_watchlist_guard(
            public_environment_value="true", hosted_secret_value="true",
        ))

    def test_local_mode_does_not_require_hosted_watchlists(self):
        self.assertIsNone(public_watchlist_guard())


if __name__ == "__main__":
    unittest.main()
