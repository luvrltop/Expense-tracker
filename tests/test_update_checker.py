import unittest
from unittest import mock

import update_checker as uc


def release(tag, prerelease=False, draft=False):
    return {"tag_name": tag, "prerelease": prerelease, "draft": draft,
            "html_url": f"https://github.com/x/releases/tag/{tag}"}


def fake_response(releases, status=200):
    response = mock.Mock(status_code=status)
    response.json.return_value = releases
    return response


class TestExtractVersion(unittest.TestCase):
    def test_keeps_prerelease_suffix(self):
        self.assertEqual(uc.extract_version("v5.6.7-beta1"), "5.6.7-beta1")
        self.assertEqual(uc.extract_version("V5.6.7"), "5.6.7")
        self.assertEqual(uc.extract_version("v1.3.0-rc.2"), "1.3.0-rc.2")
        self.assertEqual(uc.extract_version("release-2.0.0"), "2.0.0")
        self.assertIsNone(uc.extract_version("nonsense"))

    def test_project_tag_format(self):
        # tags on GitHub look like expense-tracker-V1.2.2
        self.assertEqual(uc.extract_version("expense-tracker-V1.2.2"), "1.2.2")
        self.assertEqual(uc.extract_version("expense-tracker-V2.1.0-beta1"), "2.1.0-beta1")


class TestLatestRelease(unittest.TestCase):
    RELEASES = [
        release("v1.4.0-beta2", prerelease=True),
        release("v1.4.0-beta1", prerelease=True),
        release("v1.3.1"),
        release("v1.5.0", draft=True),
        release("v1.3.0"),
    ]

    def latest(self, current, releases=None, status=200):
        if releases is None:
            releases = self.RELEASES
        with mock.patch.object(uc.requests, "get", return_value=fake_response(releases, status)):
            return uc.get_latest_release(current)

    def test_normal_user_gets_newest_stable(self):
        result = self.latest("1.2.2")
        self.assertEqual(result["version"], "1.3.1")
        self.assertTrue(result["url"].endswith("/v1.3.1"))
        self.assertTrue(uc.is_newer(result, "1.2.2"))

    def test_up_to_date(self):
        self.assertFalse(uc.is_newer(self.latest("1.3.1"), "1.3.1"))

    def test_beta_user_gets_newer_beta(self):
        result = self.latest("1.4.0-beta1")
        self.assertEqual(result["version"], "1.4.0-beta2")
        self.assertTrue(uc.is_newer(result, "1.4.0-beta1"))

    def test_beta_tag_without_github_flag_is_skipped(self):
        result = self.latest("1.3.0", [release("v1.4.0-beta1"), release("v1.3.1")])
        self.assertEqual(result["version"], "1.3.1")

    def test_beta_user_gets_final(self):
        result = self.latest("1.4.0-beta2", [release("v1.4.0"), release("v1.4.0-beta2", prerelease=True)])
        self.assertEqual(result["version"], "1.4.0")
        self.assertTrue(uc.is_newer(result, "1.4.0-beta2"))

    def test_http_error_is_none(self):
        self.assertIsNone(self.latest("1.2.2", status=500))

    def test_no_releases(self):
        result = self.latest("1.2.2", [])
        self.assertIsNone(result["version"])
        self.assertFalse(uc.is_newer(result, "1.2.2"))


if __name__ == "__main__":
    unittest.main()
