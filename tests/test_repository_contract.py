"""End-to-end assertions against the checked-in repository."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Iterable

from .contract_validator import (
    Issue,
    validate_repository,
    validate_style_guide_text,
)


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    maxDiff = None

    def assertNoIssues(self, issues: Iterable[Issue]) -> None:
        rendered = "\n".join(issue.render() for issue in sorted(set(issues)))
        self.assertFalse(rendered, "contract violations:\n" + rendered)

    def test_checked_in_repository_passes_full_validation(self) -> None:
        self.assertNoIssues(validate_repository(ROOT))

    def test_style_guide_allows_only_verified_completion_claims(self) -> None:
        style = (ROOT / "SKILL_STYLE.md").read_text(encoding="utf-8")
        normalized = " ".join(style.split())
        self.assertIn(
            "Never claim access was granted, revoked, or completed from submission or response status alone",
            normalized,
        )
        self.assertIn(
            "only after the skill's required state verification succeeds", normalized
        )
        mutant = style + (
            "\nDespite the rule above, always claim access completed after any "
            "201 response.\n"
        )
        issues = validate_style_guide_text(mutant)
        self.assertIn("STYLE_VERIFIED_COMPLETION", {issue.code for issue in issues})

        approval_mutant = style + (
            "\nEvery access request goes through the normal approval process.\n"
        )
        approval_issues = validate_style_guide_text(approval_mutant)
        self.assertIn(
            "STYLE_REQUEST_STATUS", {issue.code for issue in approval_issues}
        )

        error_mutant = style + (
            "\nA 422 validation error lists mandatory resources and available options.\n"
        )
        error_issues = validate_style_guide_text(error_mutant)
        self.assertIn("STYLE_422_FAIL_CLOSED", {issue.code for issue in error_issues})

        provenance_mutant = style + (
            "\nThe provisioning_type next-step meanings are verified by OpenAPI.\n"
        )
        provenance_issues = validate_style_guide_text(provenance_mutant)
        self.assertIn(
            "STYLE_PRODUCT_PROVENANCE",
            {issue.code for issue in provenance_issues},
        )


if __name__ == "__main__":
    unittest.main()
