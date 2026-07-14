import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "plugins" / "accessowl" / "skills"
SKILL_FILES = sorted(SKILLS_ROOT.glob("*/SKILL.md"))

WRITE_SKILLS = {
    "access-report",
    "mirror-access",
    "request-access",
    "request-revocation",
    "update-policy",
    "userlist-import-preflight",
    "vendor-update",
}


def skill_text(name: str) -> str:
    return (SKILLS_ROOT / name / "SKILL.md").read_text()


class ContractHardeningTests(unittest.TestCase):
    def test_expected_skills_are_covered(self):
        self.assertEqual(8, len(SKILL_FILES))

    def test_every_skill_requires_complete_cursor_pagination(self):
        for path in SKILL_FILES:
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                self.assertIn("Every list endpoint is paginated", text)
                self.assertIn("`limit=100`", text)
                self.assertIn("`meta.next_cursor`", text)
                self.assertIn("partial", text)

    def test_every_write_skill_requires_idempotency(self):
        for name in WRITE_SKILLS:
            with self.subTest(skill=name):
                text = skill_text(name)
                self.assertIn("`Idempotency-Key`", text)
                self.assertIn("exact same method, path, and body", text)
                self.assertIn("returns `409`", text)

    def test_user_resolution_can_include_non_active_users(self):
        for name in (
            "access-report",
            "list-access",
            "mirror-access",
            "request-access",
            "request-revocation",
            "userlist-import-preflight",
            "vendor-update",
        ):
            with self.subTest(skill=name):
                self.assertIn("status=all", skill_text(name))

    def test_access_state_titles_have_explicit_expansions(self):
        expected = {
            "access-report": "expand=grantee_user,application,resource,target_permissions",
            "list-access": "expand=application,resource,target_permissions",
            "mirror-access": "expand=application,resource,target_permissions",
            "request-revocation": "expand=application,resource,target_permissions",
            "userlist-import-preflight": "expand=grantee_user,application,resource,target_permissions",
        }
        for name, query in expected.items():
            with self.subTest(skill=name):
                self.assertIn(query, skill_text(name))

    def test_import_skill_does_not_predict_undocumented_outcomes(self):
        text = skill_text("userlist-import-preflight")
        for unsupported_claim in (
            "import as new users",
            "will be imported as a new user",
            "will lose that access on import",
            "The import replaces the application's userlist",
        ):
            with self.subTest(claim=unsupported_claim):
                self.assertNotIn(unsupported_claim, text)
        self.assertIn("public import documentation does not say", text)
        self.assertIn("verify unmatched emails in the import preview", text)
        self.assertIn("without predicting the import's effect", text)

    def test_customer_content_has_no_em_dash(self):
        for path in [ROOT / "README.md", ROOT / "SKILL_STYLE.md", *SKILL_FILES]:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("\N{EM DASH}", path.read_text())


if __name__ == "__main__":
    unittest.main()
