"""Real-document mutation oracles for write and retry safety semantics."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Iterable, Set

from .contract_validator import (
    SKILL_ROOT,
    Issue,
    validate_resilience_text,
    validate_write_safety_text,
)


ROOT = Path(__file__).resolve().parents[1]


class WriteSemanticOracleTests(unittest.TestCase):
    def skill_text(self, skill: str) -> str:
        return (ROOT / SKILL_ROOT / skill / "SKILL.md").read_text(encoding="utf-8")

    def codes(self, issues: Iterable[Issue]) -> Set[str]:
        return {issue.code for issue in issues}

    def assertCode(self, issues: Iterable[Issue], expected: str) -> None:
        codes = self.codes(issues)
        self.assertIn(expected, codes, "expected %s, got %s" % (expected, sorted(codes)))

    def remove_paragraph(self, text: str, *needles: str) -> str:
        paragraphs = text.split("\n\n")
        kept = [
            paragraph
            for paragraph in paragraphs
            if not all(needle in paragraph for needle in needles)
        ]
        mutant = "\n\n".join(kept)
        self.assertNotEqual(text, mutant, "target paragraph was not found")
        return mutant

    def replace_in_paragraph(
        self, text: str, anchor: str, old: str, new: str
    ) -> str:
        paragraphs = text.split("\n\n")
        matches = [index for index, paragraph in enumerate(paragraphs) if anchor in paragraph]
        self.assertEqual([matches[0]] if matches else [], matches, "paragraph anchor must be unique")
        index = matches[0]
        replaced = paragraphs[index].replace(old, new, 1)
        self.assertNotEqual(paragraphs[index], replaced, "mutation anchor was not found")
        paragraphs[index] = replaced
        return "\n\n".join(paragraphs)

    def test_idempotency_retry_tuple_is_indivisible(self) -> None:
        text = self.skill_text("request-access")
        original = "Every retry uses the exact same method, path, body, and key."
        variants = (
            "Every retry uses the exact same path, body, and key.",
            "Every retry uses the exact same method, body, and key.",
            "Every retry uses the exact same method, path, and key.",
            "Every retry uses the exact same method, path, and body.",
        )
        for variant in variants:
            with self.subTest(variant=variant):
                mutant = text.replace(original, variant, 1)
                self.assertNotEqual(text, mutant)
                self.assertCode(
                    validate_write_safety_text("request-access", mutant, "SKILL.md"),
                    "IDEMPOTENCY_KEY_LIFECYCLE",
                )

        retry_clause = "includes a `429`, timeout, network error, or `5xx` response."
        for token in ("`429`", "timeout", "network error", "`5xx` response"):
            with self.subTest(retry_token=token):
                mutant = text.replace(retry_clause, retry_clause.replace(token, "other failure"), 1)
                self.assertNotEqual(text, mutant)
                self.assertCode(
                    validate_write_safety_text("request-access", mutant, "SKILL.md"),
                    "IDEMPOTENCY_ALL_RETRIES",
                )

    def test_retry_and_concurrency_contradictions_are_rejected(self) -> None:
        text = self.skill_text("request-access")
        cases = (
            (
                "A 409 outcome is unknown, but always treat it as success.",
                "IDEMPOTENCY_409_SUCCESS",
            ),
            (
                "Do not refetch immediately before each write or bulk chunk.",
                "CONCURRENCY_CONTRADICTION",
            ),
            (
                "A malformed write response should retry with a fresh key.",
                "WRITE_RESPONSE_RETRY_CONTRADICTION",
            ),
            (
                "An unknown outcome may continue with the remaining writes.",
                "MUTATION_BOUND_CONTRADICTION",
            ),
            (
                "Allow 101 mutation calls in one confirmed run.",
                "MUTATION_BOUND_CONTRADICTION",
            ),
            (
                "For timeout retries, use a fresh Idempotency-Key and a rebuilt body.",
                "IDEMPOTENCY_RETRY_CONTRADICTION",
            ),
            (
                "Skip the immediate refetch when the prior snapshot is less than a minute old.",
                "CONCURRENCY_CONTRADICTION",
            ),
            (
                "When 100 calls are insufficient, continue with extra batches under the same confirmation.",
                "MUTATION_BOUND_CONTRADICTION",
            ),
            (
                "When a write response is malformed, resubmit using a newly generated key.",
                "WRITE_RESPONSE_RETRY_CONTRADICTION",
            ),
            (
                "Use the cached snapshot in place of the immediate pre-write refetch.",
                "CONCURRENCY_CONTRADICTION",
            ),
            (
                "After a timeout, generate a replacement Idempotency-Key and repeat the write.",
                "IDEMPOTENCY_RETRY_CONTRADICTION",
            ),
            (
                "When the outcome is unknown, carry on with the next mutation.",
                "MUTATION_BOUND_CONTRADICTION",
            ),
            (
                "If a write response is corrupt, resubmit it with a different idempotency key.",
                "WRITE_RESPONSE_RETRY_CONTRADICTION",
            ),
            (
                "A denied request prevents a replacement request.",
                "REQUEST_STATUS_CONTRADICTION",
            ),
            (
                "A pending_dependency request may coexist with a new request.",
                "REQUEST_STATUS_CONTRADICTION",
            ),
            (
                "If the write response is damaged, resend with a separate key.",
                "WRITE_RESPONSE_RETRY_CONTRADICTION",
            ),
            (
                "A denied request rules out a replacement request.",
                "REQUEST_STATUS_CONTRADICTION",
            ),
            (
                "For writes, follow 307 and 308 redirects on the same origin.",
                "WRITE_REDIRECT_BOUNDARY",
            ),
            (
                "After a write redirect, retry with a fresh Idempotency-Key.",
                "WRITE_REDIRECT_BOUNDARY",
            ),
            (
                "After a write redirect, resend with the same key.",
                "WRITE_REDIRECT_BOUNDARY",
            ),
            (
                "Rewrite POST to GET after a 303 redirect.",
                "WRITE_REDIRECT_BOUNDARY",
            ),
        )
        for unsafe, code in cases:
            with self.subTest(code=code):
                self.assertCode(
                    validate_write_safety_text(
                        "request-access", text + "\n\n" + unsafe + "\n", "SKILL.md"
                    ),
                    code,
                )

    def test_each_write_revalidates_complete_state_and_records_a_baseline(self) -> None:
        text = self.skill_text("request-access")
        cases = (
            ("person's user status", "person"),
            ("its resource structure with", "its prior selection from"),
            (
                "GET /access_states?grantee_user_id=<id>&application_id=<id>&expand=application,resource,target_permissions&limit=100",
                "the prior access-state list",
            ),
            ("GET /access_requests?limit=100", "the prior request list"),
            ("Record the IDs", "Ignore the IDs"),
            ("reconfirm before", "continue before"),
        )
        for old, new in cases:
            with self.subTest(old=old):
                mutant = self.replace_in_paragraph(
                    text, "Immediately before each `POST`", old, new
                )
                self.assertCode(
                    validate_write_safety_text("request-access", mutant, "SKILL.md"),
                    "CONCURRENCY_COMPLETE_PREWRITE",
                )

        vendor_text = self.skill_text("vendor-update")
        for old, new in (
            ("every referenced owner or admin", "application metadata"),
            ("recompute list fields", "reuse list fields"),
            ("confirm the new body", "continue with the old body"),
        ):
            with self.subTest(vendor=old):
                mutant = self.replace_in_paragraph(
                    vendor_text, "Immediately after confirmation", old, new
                )
                self.assertCode(
                    validate_write_safety_text("vendor-update", mutant, "SKILL.md"),
                    "CONCURRENCY_VENDOR_COMPLETE_PREWRITE",
                )

        endpoint_cases = (
            ("request-access", "Immediately before each `POST`"),
            ("access-report", "immediately before each person's `POST`"),
            ("mirror-access", "Immediately before every bulk chunk"),
        )
        endpoint_replacements = (
            ("`GET /users/{id}`", "the current user record"),
            ("`GET /applications/{id}`", "the current application record"),
            (
                "`GET /applications/{id}/resources`",
                "the current resource structure",
            ),
        )
        for skill, anchor in endpoint_cases:
            text = self.skill_text(skill)
            for endpoint, replacement in endpoint_replacements:
                with self.subTest(skill=skill, endpoint=endpoint):
                    mutant = self.replace_in_paragraph(
                        text, anchor, endpoint, replacement
                    )
                    self.assertCode(
                        validate_write_safety_text(skill, mutant, "SKILL.md"),
                        "CONCURRENCY_REVALIDATE",
                    )

        result_cases = (
            ("request-access", "Only for `pending_approval`"),
            ("access-report", "Only\nfor `pending_approval`"),
            ("mirror-access", "Only for `pending_approval`"),
            ("request-revocation", "For a correlated `processing_access`"),
        )
        for skill, anchor in result_cases:
            with self.subTest(skill=skill, result_refetch=True):
                text = self.skill_text(skill)
                mutant = self.replace_in_paragraph(
                    text,
                    anchor,
                    "`GET /applications/{id}`",
                    "the current application record",
                )
                self.assertCode(
                    validate_write_safety_text(skill, mutant, "SKILL.md"),
                    "PROVISIONING_TYPE_REFETCH",
                )

    def test_write_redirect_and_display_identity_contracts_are_indivisible(self) -> None:
        for skill in (
            "access-report",
            "mirror-access",
            "request-access",
            "request-revocation",
            "vendor-update",
        ):
            with self.subTest(skill=skill, contract="write redirect"):
                text = self.skill_text(skill)
                mutant = text.replace(
                    "never follow a redirect of any\n  status",
                    "follow a redirect of any\n  status",
                    1,
                )
                self.assertNotEqual(text, mutant)
                self.assertCode(
                    validate_write_safety_text(skill, mutant, "SKILL.md"),
                    "WRITE_REDIRECT_BOUNDARY",
                )

        for skill in ("access-report", "mirror-access", "request-access"):
            with self.subTest(skill=skill, contract="display identity"):
                text = self.skill_text(skill)
                mutant = text.replace("displayed name or", "status or", 1)
                self.assertNotEqual(text, mutant)
                self.assertCode(
                    validate_write_safety_text(skill, mutant, "SKILL.md"),
                    "CONCURRENCY_DISPLAY_IDENTITY_DRIFT",
                )

        text = self.skill_text("request-access")
        mutant = text + (
            "\n\nIf a displayed name, email, or application title changes, "
            "submit the old selection anyway without reconfirming.\n"
        )
        self.assertCode(
            validate_write_safety_text("request-access", mutant, "SKILL.md"),
            "CONCURRENCY_DISPLAY_IDENTITY_DRIFT",
        )

    def test_destructive_selection_drift_is_fully_reconfirmed(self) -> None:
        revocation = self.skill_text("request-revocation")
        for old, new in (
            ("resource ID or null and\ntitle", "resource title"),
            ("complete permission IDs and titles", "permission titles"),
            ("customer-visible title", "description"),
        ):
            with self.subTest(revocation=old):
                mutant = revocation.replace(old, new, 1)
                self.assertNotEqual(revocation, mutant)
                self.assertCode(
                    validate_write_safety_text(
                        "request-revocation", mutant, "SKILL.md"
                    ),
                    "REVOCATION_SELECTION_DRIFT",
                )

        contradiction = revocation + (
            "\n\nIf a title or permission ID changed after confirmation, "
            "proceed with the revocation anyway.\n"
        )
        self.assertCode(
            validate_write_safety_text(
                "request-revocation", contradiction, "SKILL.md"
            ),
            "REVOCATION_SELECTION_DRIFT",
        )

        report = self.skill_text("access-report")
        mutant = report.replace(
            "resource, or permission title or ID",
            "resource, or permission title",
            1,
        )
        self.assertNotEqual(report, mutant)
        self.assertCode(
            validate_write_safety_text("access-report", mutant, "SKILL.md"),
            "ACCESS_REPORT_SELECTION_DRIFT",
        )
        contradiction = report + (
            "\n\nIf a selected resource or permission ID changes after confirmation, "
            "submit the old selection anyway.\n"
        )
        self.assertCode(
            validate_write_safety_text(
                "access-report", contradiction, "SKILL.md"
            ),
            "ACCESS_REPORT_SELECTION_DRIFT",
        )

    def test_resilience_contradictions_are_rejected_on_real_skills(self) -> None:
        text = self.skill_text("list-access")
        cases = (
            (
                "A repeated cursor is safe to ignore and continue.",
                "RESILIENCE_CONTRADICTION",
            ),
            ("Retry 429 forever.", "RESILIENCE_CONTRADICTION"),
            (
                "Do not URL-encode dynamic query values.",
                "RESILIENCE_CONTRADICTION",
            ),
            ("Continue with partial malformed data.", "RESILIENCE_CONTRADICTION"),
            (
                "A repeated cursor is only a warning, so keep fetching pages.",
                "RESILIENCE_CONTRADICTION",
            ),
            ("You may follow five redirects when necessary.", "API_REDIRECT_BOUNDARY"),
            ("Use a 45-second deadline for slow requests.", "API_REQUEST_DEADLINE"),
            (
                "Allow a 12 MiB decompressed response body.",
                "API_RESPONSE_BYTE_CAP",
            ),
            (
                "Continue through 1,002 pages when more records remain.",
                "PAGINATION_CAP",
            ),
            (
                "Response bodies as large as 12 MiB are acceptable.",
                "API_RESPONSE_BYTE_CAP",
            ),
            (
                "An attempt deadline of 45 seconds is valid.",
                "API_REQUEST_DEADLINE",
            ),
            ("Five redirects are acceptable.", "API_REDIRECT_BOUNDARY"),
            (
                "Follow a cross-origin redirect when it appears to be a billing page.",
                "API_REDIRECT_BOUNDARY",
            ),
            (
                "Pagination through 1,002 pages is supported.",
                "PAGINATION_CAP",
            ),
            (
                "Object keys and scalar property values do not count toward the decoded-node cap.",
                "API_NESTED_VALUE_CAP",
            ),
            (
                "The same record ID across independent traversals is inconsistent.",
                "PAGINATION_STATE_SCOPE",
            ),
            (
                "Duplicate record IDs within one page are acceptable.",
                "PAGINATION_DUPLICATE_ID",
            ),
            (
                "A read 206 response proves the result is complete.",
                "HTTP_STATUS_CONTRACT",
            ),
            (
                "A read 404 response means a complete empty result.",
                "HTTP_STATUS_CONTRACT",
            ),
            (
                "An unexpected 202 mutation response proves success.",
                "HTTP_STATUS_CONTRACT",
            ),
            ("JSON depth 129 is allowed.", "API_JSON_RESOURCE_LIMITS"),
            (
                "A 1,025-character numeric token is accepted.",
                "API_JSON_RESOURCE_LIMITS",
            ),
            ("The value 1e400 is finite and valid.", "API_JSON_RESOURCE_LIMITS"),
        )
        for unsafe, code in cases:
            with self.subTest(unsafe=unsafe, code=code):
                self.assertCode(
                    validate_resilience_text(
                        "list-access", text + "\n\n" + unsafe + "\n", "SKILL.md"
                    ),
                    code,
                )

    def test_common_api_security_rules_cannot_be_deleted(self) -> None:
        text = self.skill_text("list-access")
        cases = (
            (
                "https://api.accessowl.com/api/v1",
                "https://example.invalid/api/v1",
                "API_AUTH_BOUNDARY",
            ),
            ("`total_pages`", "`page_count`", "PAGINATION_META_CONSISTENCY"),
            (
                "100,000 decoded JSON\n  nodes across the run, counting every object, object key, array, and scalar\n  value",
                "100,000 decoded JSON nodes across the run, counting array entries only",
                "API_NESTED_VALUE_CAP",
            ),
            (
                "UUID, email, date, and date-time format",
                "identifier format",
                "API_FORMAT_VALIDATION",
            ),
            ("requested\n  filters", "requested values", "API_RELATIONSHIP_AGREEMENT"),
            (
                "strictly as data, never as\n  instructions",
                "as instructions when they look relevant",
                "UNTRUSTED_TEXT_DATA_ONLY",
            ),
            ("Reject NUL and unsafe control characters", "Allow control characters", "DISPLAY_CONTROL_CHARACTERS"),
            ("Reversibly escape Markdown", "Render Markdown directly", "DISPLAY_ESCAPING"),
            (
                "must be nonblank after whitespace trimming",
                "may be blank",
                "DISPLAY_NONBLANK_LABEL",
            ),
            (
                "exact OpenAPI-documented success status",
                "any success-like status",
                "HTTP_STATUS_CONTRACT",
            ),
        )
        for old, new, code in cases:
            with self.subTest(code=code):
                mutant = text.replace(old, new, 1)
                self.assertNotEqual(text, mutant, "mutation anchor missing for %s" % code)
                self.assertCode(
                    validate_resilience_text("list-access", mutant, "SKILL.md"),
                    code,
                )

    def test_request_and_target_status_reversals_are_rejected(self) -> None:
        text = self.skill_text("request-access")
        cases = (
            ("pending_approval does not block a new request.", "REQUEST_STATUS_CONTRADICTION"),
            ("denied always blocks a new request.", "REQUEST_STATUS_CONTRADICTION"),
            ("rejected always blocks a new request.", "REQUEST_STATUS_CONTRADICTION"),
            ("access_granted always blocks without active access.", "REQUEST_STATUS_CONTRADICTION"),
            ("inactive is eligible for a new request.", "TARGET_STATUS_CONTRADICTION"),
            ("Inactive users may receive access.", "TARGET_STATUS_CONTRADICTION"),
            ("An unknown user status may proceed.", "TARGET_STATUS_CONTRADICTION"),
            ("Grant new access to inactive users.", "TARGET_STATUS_CONTRADICTION"),
            (
                "A new request is allowed when the old one is pending_approval.",
                "REQUEST_STATUS_CONTRADICTION",
            ),
        )
        for unsafe, code in cases:
            with self.subTest(unsafe=unsafe):
                self.assertCode(
                    validate_write_safety_text(
                        "request-access", text + "\n\n" + unsafe + "\n", "SKILL.md"
                    ),
                    code,
                )

    def test_application_status_and_response_reversals_are_rejected(self) -> None:
        text = self.skill_text("request-access")
        cases = (
            ("Approved applications are requestable.", "APPLICATION_STATUS_CONTRADICTION"),
            (
                "An uncorrelated 201 response counts as success.",
                "WRITE_RESPONSE_CORRELATION_CONTRADICTION",
            ),
            (
                "An uncorrelated 201 may be reported as successful.",
                "WRITE_RESPONSE_CORRELATION_CONTRADICTION",
            ),
            (
                "A rejected response is success.",
                "WRITE_RESPONSE_CORRELATION_CONTRADICTION",
            ),
            (
                "Create a request for an application whose status is approved.",
                "APPLICATION_STATUS_CONTRADICTION",
            ),
            (
                "Ignore existing active app-wide access and create narrower grants.",
                "APP_WIDE_REQUEST_BLOCKER",
            ),
            (
                "Ignore the body of a 201 response and report success.",
                "WRITE_RESPONSE_CORRELATION_CONTRADICTION",
            ),
        )
        for unsafe, code in cases:
            with self.subTest(unsafe=unsafe):
                self.assertCode(
                    validate_write_safety_text(
                        "request-access", text + "\n\n" + unsafe + "\n", "SKILL.md"
                    ),
                    code,
                )

    def test_single_and_revocation_responses_require_full_correlation(self) -> None:
        request_text = self.skill_text("request-access")
        request_mutant = request_text.replace("normal single `201`", "single response", 1)
        self.assertNotEqual(request_text, request_mutant)
        self.assertCode(
            validate_write_safety_text("request-access", request_mutant, "SKILL.md"),
            "REQUEST_SINGLE_201_CORRELATION",
        )

        revocation_text = self.skill_text("request-revocation")
        correlation_mutant = revocation_text.replace("unique response ID", "response ID", 1)
        self.assertNotEqual(revocation_text, correlation_mutant)
        self.assertCode(
            validate_write_safety_text("request-revocation", correlation_mutant, "SKILL.md"),
            "REVOCATION_201_CORRELATION",
        )

        optional_mutant = revocation_text.replace(
            "A missing optional field is unavailable\ncorrelation evidence and alone does not make the result unknown.",
            "Missing optional correlation fields make the result unknown.",
            1,
        )
        self.assertNotEqual(revocation_text, optional_mutant)
        self.assertCode(
            validate_write_safety_text(
                "request-revocation", optional_mutant, "SKILL.md"
            ),
            "REVOCATION_201_CORRELATION",
        )

        for unsafe in (
            "permission_ids: null matches a nonempty intended permission set.",
            "resource_id: null matches a resource-scoped intent.",
            "Absence of resource_id in the response is an error.",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertCode(
                    validate_write_safety_text(
                        "request-revocation",
                        revocation_text + "\n\n" + unsafe + "\n",
                        "SKILL.md",
                    ),
                    "REVOCATION_201_CORRELATION",
                )

        optional_contradiction = revocation_text + (
            "\n\nAll three optional correlation fields must be present; "
            "otherwise mark the result unknown.\n"
        )
        self.assertCode(
            validate_write_safety_text(
                "request-revocation", optional_contradiction, "SKILL.md"
            ),
            "REVOCATION_201_CORRELATION",
        )

        completion_mutant = revocation_text.replace(
            "present,\nnon-null `effective_end` before saying removal is complete",
            "status before saying removal is complete",
            1,
        )
        self.assertNotEqual(revocation_text, completion_mutant)
        self.assertCode(
            validate_write_safety_text("request-revocation", completion_mutant, "SKILL.md"),
            "REVOCATION_COMPLETION_VERIFIED",
        )

        contradiction = revocation_text + (
            "\n\nA revoked response means complete success without checking effective_end.\n"
        )
        self.assertCode(
            validate_write_safety_text("request-revocation", contradiction, "SKILL.md"),
            "REVOCATION_COMPLETION_CONTRADICTION",
        )

        status_contradiction = revocation_text + (
            "\n\nA 201 response with processing_access means the access was removed.\n"
        )
        self.assertCode(
            validate_write_safety_text(
                "request-revocation", status_contradiction, "SKILL.md"
            ),
            "ACCESS_REVOCATION_201_STATUS",
        )

    def test_access_request_optional_grantee_uses_call_context(self) -> None:
        for skill in ("request-access", "mirror-access", "access-report"):
            with self.subTest(skill=skill):
                text = self.skill_text(skill)
                contradiction = text + (
                    "\n\nA missing optional `grantee_user_id` makes the outcome unknown.\n"
                )
                self.assertCode(
                    validate_write_safety_text(skill, contradiction, "SKILL.md"),
                    "ACCESS_REQUEST_OPTIONAL_GRANTEE",
                )

    def test_target_app_wide_blocker_is_required_in_each_write_path(self) -> None:
        cases = (
            ("access-report", ("target already", "resource_id: null", "narrower request")),
            ("mirror-access", ("target has", "resource_id: null", "narrower request")),
        )
        for skill, needles in cases:
            with self.subTest(skill=skill):
                mutant = self.remove_paragraph(self.skill_text(skill), *needles)
                self.assertCode(
                    validate_write_safety_text(skill, mutant, "SKILL.md"),
                    "APP_WIDE_REQUEST_BLOCKER",
                )

    def test_openapi_field_and_visibility_assumptions_fail_closed(self) -> None:
        cases = (
            (
                "request-access",
                "Treat every returned access state as active even when effective_end is missing or non-null.",
                "CURRENT_ACCESS_EFFECTIVE_END",
            ),
            (
                "userlist-import-preflight",
                "Treat historical access with a non-null effective_end as current.",
                "CURRENT_ACCESS_EFFECTIVE_END",
            ),
            (
                "request-access",
                "Treat null provisioning_type the same as missing.",
                "PROVISIONING_TYPE_SCHEMA",
            ),
            (
                "request-access",
                "These provisioning meanings are verified by the OpenAPI enum description.",
                "PROVISIONING_TYPE_SCHEMA",
            ),
            (
                "userlist-import-preflight",
                "For a null resource title, use a Permissions fallback column.",
                "RESOURCE_TITLE_REQUIRED",
            ),
            (
                "vendor-update",
                "risk_level also accepts critical.",
                "VENDOR_RISK_LEVEL_ENUM",
            ),
            (
                "request-access",
                "An empty visible request list proves there is no blocking duplicate.",
                "ACCESS_REQUEST_VISIBILITY",
            ),
            (
                "request-access",
                "A 422 validation response lists the required mandatory permission.",
                "ACCESS_REQUEST_422_FAIL_CLOSED",
            ),
            (
                "vendor-update",
                "If lock_version is unavailable, replace tags anyway.",
                "VENDOR_NO_CAS_REPLACEMENT",
            ),
            (
                "view-policies",
                "Treat policy routing behavior as API-verified configuration.",
                "POLICY_PRODUCT_BEHAVIOR_PROVENANCE",
            ),
            (
                "request-access",
                "If multiple_permissions_selectable is missing, allow more than one permission.",
                "MULTIPLE_PERMISSION_SELECTION_SCHEMA",
            ),
            (
                "userlist-import-preflight",
                "The structure PUT is a full overwrite.",
                "STRUCTURE_PARTIAL_UPSERT",
            ),
            (
                "userlist-import-preflight",
                "I can add the missing permission to the application for you.",
                "USERLIST_READ_ONLY",
            ),
        )
        for skill, unsafe, code in cases:
            with self.subTest(skill=skill, code=code):
                text = self.skill_text(skill) + "\n\n" + unsafe + "\n"
                self.assertCode(validate_write_safety_text(skill, text, "SKILL.md"), code)


if __name__ == "__main__":
    unittest.main()
