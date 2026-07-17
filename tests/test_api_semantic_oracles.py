"""Mutation oracles for per-call API and refused-operation semantics."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Iterable, Set

from .contract_validator import (
    SKILL_ROOT,
    Issue,
    _operation_has_affirmative_reference,
    _operation_has_negated_action_reference,
    validate_api_contract_text,
    validate_api_reference_text,
    validate_skill_operation_scope,
)


ROOT = Path(__file__).resolve().parents[1]


class ApiSemanticOracleTests(unittest.TestCase):
    def skill_text(self, skill: str) -> str:
        return (ROOT / SKILL_ROOT / skill / "SKILL.md").read_text(encoding="utf-8")

    def codes(self, issues: Iterable[Issue]) -> Set[str]:
        return {issue.code for issue in issues}

    def assertCode(self, issues: Iterable[Issue], expected: str) -> None:
        codes = self.codes(issues)
        self.assertIn(expected, codes, "expected %s, got %s" % (expected, sorted(codes)))

    def test_method_case_and_unbackticked_calls_cannot_bypass_scope(self) -> None:
        self.assertCode(
            validate_api_reference_text("Use `patch /applications/{id}`.", "SKILL.md"),
            "API_METHOD_CASE",
        )
        unbackticked = self.skill_text("list-access") + "\n\npatch /applications/{id}\n"
        self.assertCode(
            validate_api_reference_text(unbackticked, "SKILL.md"),
            "API_REFERENCE_NOT_CODE",
        )
        mutant = self.skill_text("list-access") + "\n\nUse `patch /applications/{id}`.\n"
        self.assertCode(
            validate_skill_operation_scope("list-access", mutant, "SKILL.md"),
            "SKILL_OPERATION_SCOPE",
        )

    def test_every_user_lookup_requires_status_all(self) -> None:
        text = self.skill_text("discovered-apps")
        mutant = text + "\n\nAlso use `GET /users?status=active&limit=100`.\n"
        self.assertCode(
            validate_api_contract_text("discovered-apps", mutant, "SKILL.md"),
            "USERS_STATUS_ALL",
        )

    def test_every_access_state_lookup_requires_its_full_expansion(self) -> None:
        text = self.skill_text("discovered-apps")
        original = (
            "GET /access_states?application_id=<id>&expand=grantee_user,application&limit=100"
        )
        mutant = text.replace(
            original,
            "GET /access_states?application_id=<id>&expand=grantee_user&limit=100",
            1,
        )
        self.assertNotEqual(text, mutant)
        self.assertCode(
            validate_api_contract_text("discovered-apps", mutant, "SKILL.md"),
            "ACCESS_STATE_EXPANSIONS",
        )

        revocation = self.skill_text("request-revocation")
        original = (
            "GET /access_states?grantee_user_id=<id>&application_id=<id>"
            "&expand=grantee_user,application,resource,target_permissions&limit=100"
        )
        mutant = revocation.replace(
            original,
            original.replace("grantee_user,", ""),
            1,
        )
        self.assertNotEqual(revocation, mutant)
        self.assertCode(
            validate_api_contract_text("request-revocation", mutant, "SKILL.md"),
            "ACCESS_STATE_EXPANSIONS",
        )

    def test_every_cursor_call_requires_limit_one_hundred(self) -> None:
        text = self.skill_text("list-access")
        mutant = text.replace(
            "GET /users?status=all&limit=100",
            "GET /users?status=all&limit=99",
            1,
        )
        self.assertNotEqual(text, mutant)
        self.assertCode(
            validate_api_contract_text("list-access", mutant, "SKILL.md"),
            "API_CURSOR_LIMIT_PER_CALL",
        )

    def test_refused_writes_cannot_be_reintroduced_beside_safe_prose(self) -> None:
        cases = (
            (
                "userlist-import-preflight",
                "Call `PUT /applications/{id}/structure` to fix the structure now.",
            ),
            (
                "view-policies",
                "Execute `PUT /policies/{policy_id}/applications` after the preview.",
            ),
            (
                "view-policies",
                "Submit `PUT /policies/{policy_id}/applications` after confirmation.",
            ),
        )
        for skill, unsafe in cases:
            with self.subTest(skill=skill):
                mutant = self.skill_text(skill) + "\n\n" + unsafe + "\n"
                self.assertCode(
                    validate_skill_operation_scope(skill, mutant, "SKILL.md"),
                    "REFUSED_OPERATION_CONTEXT",
                )

    def test_refusal_in_one_sentence_cannot_camouflage_an_action_in_the_next(self) -> None:
        cases = (
            (
                "userlist-import-preflight",
                "Do not call `PUT /applications/{id}/structure`. Now execute `PUT /applications/{id}/structure`.",
            ),
            (
                "view-policies",
                "Never call `PUT /policies/{policy_id}/applications`; now use `PUT /policies/{policy_id}/applications`.",
            ),
        )
        for skill, unsafe in cases:
            with self.subTest(skill=skill):
                mutant = self.skill_text(skill) + "\n\n" + unsafe + "\n"
                self.assertCode(
                    validate_skill_operation_scope(skill, mutant, "SKILL.md"),
                    "REFUSED_OPERATION_CONTEXT",
                )

    def test_required_operations_must_remain_affirmative(self) -> None:
        text = self.skill_text("request-access")
        cases = (
            (
                "List users via",
                "Never list users via",
            ),
            (
                "Find the application with",
                "Never find the application with",
            ),
            (
                "Fetch the application's structure with",
                "Never fetch the application's structure with",
            ),
        )
        for old, new in cases:
            with self.subTest(old=old):
                mutant = text.replace(old, new, 1)
                self.assertNotEqual(text, mutant)
                self.assertCode(
                    validate_api_contract_text("request-access", mutant, "SKILL.md"),
                    "API_REQUIRED_OPERATION_CONTEXT",
                )

        policies = self.skill_text("view-policies")
        mutant = policies.replace(
            "`GET /policies?limit=100`",
            "Omit `GET /policies?limit=100`",
            1,
        )
        self.assertNotEqual(policies, mutant)
        self.assertCode(
            validate_api_contract_text("view-policies", mutant, "SKILL.md"),
            "API_REQUIRED_OPERATION_CONTEXT",
        )

        operation = ("GET", "/users")
        safe = "Never skip `GET /users?status=all&limit=100`."
        self.assertTrue(_operation_has_affirmative_reference(safe, operation))
        self.assertFalse(_operation_has_negated_action_reference(safe, operation))

        unsafe = "Never fetch `GET /users?status=all&limit=100`."
        self.assertTrue(_operation_has_negated_action_reference(unsafe, operation))


if __name__ == "__main__":
    unittest.main()
