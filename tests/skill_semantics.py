"""Per-skill semantic contracts: exact safety wording pinned for one skill.

Standard library only, and nothing here imports contract_validator, so the
validator imports this module at load time without a cycle. Each check
returns (code, message) findings; contract_validator turns them into Issues
and re-exports its original _validate_* names.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

Finding = Tuple[str, str]
PhraseRules = Sequence[Tuple[str, str, bool, Tuple[str, ...]]]


def _phrase_contract(
    text: str, requirements: PhraseRules, contradictions: Sequence[str], contradiction: Finding
) -> List[Finding]:
    """Rule: (code, message, per_paragraph, phrases)."""
    normalized = re.sub(r"\s+", " ", text.casefold())
    paragraphs = [re.sub(r"\s+", " ", part.casefold()) for part in text.split("\n\n")]
    issues = [
        (code, message)
        for code, message, scoped, terms in requirements
        if not any(all(term in scope for term in terms) for scope in (paragraphs if scoped else [normalized]))
    ]
    if any(re.search(pattern, normalized, re.S) for pattern in contradictions):
        issues.append(contradiction)
    return issues


GRANT_REQUIREMENTS: PhraseRules = (
    ("GRANT_SCOPE", "grant-access records completed provisioning but never approves or creates a request", False,
     ("this is a direct write. it is not approval and it is not a new request", "never approves requests")),
    ("GRANT_MANUAL_ELIGIBILITY", "only a processing_access request for application_admin provisioning is grant-eligible", False,
     ("`provisioning_type` is `application_admin`", "exact request status is `processing_access`", "only `processing_access` is eligible for granting", "`pending_approval`", "ineligible", "never call the grant endpoint for an ineligible request")),
    ("GRANT_EXACT_SELECTION", "resolve one exact person, application, request, resource, and permission set", False,
     ("require exactly one case-insensitive match", "complete permission ids", "never choose by a hidden id")),
    ("GRANT_DUPLICATE_ACCESS", "block an exact current duplicate without blocking different access in the same app", False,
     ("exact application, resource, and complete permission set", "different resource or permission", "does not block this grant", "exact requested access is already current", "stop", "duplicate state")),
    ("GRANT_CONFIRMATION", "confirm the exact completed provisioning immediately before granting", False,
     ("person, application, resource, and complete permission set", "clearly confirms that provisioning is complete", "earlier request to create or approve access")),
    ("GRANT_RESPONSE_CORRELATION", "correlate the 200 response and verify exactly one matching current state", False,
     ("exact documented success status is `200`", "same request id, grantee, application, resource, and complete permission set", "status exactly `access_granted`", "exactly one current access state", "zero or multiple exact matches", "outcome as unknown")),
    ("GRANT_422_FAIL_CLOSED", "422 must stop without inferring approval or synthesizing another grant", True,
     ("on `422`", "did not consider the request grant-eligible", "never infer approval", "retry with a new body or key")),
)
GRANT_CONTRADICTIONS = (
    r"pending_approval.{0,80}(?:is|counts?\s+as|treat.{0,20}as).{0,30}grant-eligible",
    r"(?:grant|mark).{0,80}pending_approval",
    r"(?:different|other).{0,30}(?:resource|permission).{0,50}(?<!not )(?:blocks?|prevents?).{0,30}grant",
    r"(?:response\s+status|http\s+200).{0,60}(?:alone|by itself).{0,40}(?:proves?|confirms?).{0,30}grant",
    r"(?<!never )(?<!not )(?:skip|omit).{0,40}(?:confirmation|current\s+access|read-back|verification)",
)


def grant_access_findings(skill: str, text: str) -> List[Finding]:
    if skill != "grant-access":
        return []
    return _phrase_contract(text, GRANT_REQUIREMENTS, GRANT_CONTRADICTIONS, (
        "GRANT_CONTRADICTION", "unsafe prose must not bypass approval, duplicate, confirmation, or read-back checks"))


CLOSE_REQUIREMENTS: PhraseRules = (
    ("CLOSE_SCOPE", "close-request only denies or rejects", False,
     ("never approves or grants a request", "never revokes access someone already has", "never changes approvers, approval steps, or policies")),
    ("CLOSE_STATUS_ACTION", "the status alone picks deny, reject, or stop", False,
     ("`pending_approval` (waiting for approval): deny it", "`pending_permissions_assignment`, `scheduled`, `pending_dependency`, or `processing_access` (approved", "being provisioned): reject it", "`access_granted`, `denied`, or `rejected` (granted, denied, rejected): it is already closed", "any other status: stop", "the status decides the action, not the user's wording")),
    ("CLOSE_DENY_APPROVER", "deny only for a pending current-step approver", False,
     ("lowest-numbered step whose `status` is `pending`", "never pick one yourself", "never record a denial for someone who is not a pending approver of the current step", "always include `on_behalf_of_user_id`")),
    ("CLOSE_CONFIRMATION", "only a clear yes after the confirmation counts", False,
     ("only a clear yes given after this confirmation counts", "ask nothing else in that message", "will not receive this access")),
    ("CLOSE_PREWRITE_RECHECK", "re-check status and approver before each write", False,
     ("same current step with the confirmed approver still pending", "never write from the older snapshot")),
    ("CLOSE_422", "422 re-reads and changes nothing", True,
     ("a `422` means", "re-read it", "nothing changed", "needs a new confirmation")),
    ("CLOSE_UNCERTAIN", "an uncertain outcome stops all writes", False,
     ("report the outcome as unknown and stop remaining writes", "fresh key needs a new confirmation")),
)
CLOSE_CONTRADICTIONS = (
    r"`pending_approval`[^.]{0,80}\breject\b",
    r"(?:pending_permissions_assignment|processing_access)[^.]{0,80}\bdeny\b",
    r"on_behalf_of_user_id[^.]{0,60}\b(?:optional|omit|skip|grantee|requester)\b",
    r"\b(?:pick|choose|use)\s+(?:the\s+)?first\s+(?:pending\s+)?approver",
    r"(?:earlier|already|before|previous(?:ly)?)[^.]{0,60}(?:counts?\s+as|treat[^.]{0,20}as)\s+(?:the\s+)?confirmation",
)


def close_request_findings(skill: str, text: str) -> List[Finding]:
    if skill != "close-request":
        return []
    return _phrase_contract(
        text, CLOSE_REQUIREMENTS, CLOSE_CONTRADICTIONS, ("CLOSE_CONTRADICTION", "unsafe close prose"))


def userlist_import_findings(skill: str, text: str) -> List[Finding]:
    """The import is one full-replace PUT; pin its preview and write-path safety."""
    if skill != "import-userlist":
        return []
    normalized = re.sub(r"\s+", " ", text.casefold())
    paragraphs = [
        re.sub(r"\s+", " ", p.casefold()) for p in re.split(r"\n\s*\n", text) if p.strip()
    ]
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    negation = re.compile(r"\b(?:never|do not|must not)\b")

    def paragraph_with(*needles: str) -> bool:
        return any(all(needle in paragraph for needle in needles) for paragraph in paragraphs)

    def anywhere(anchor: str, pattern: str) -> bool:
        # Phrases that are unsafe on their own, whatever negation sits nearby.
        return any(
            re.search(anchor, sentence) and re.search(pattern, sentence)
            for sentence in sentences
        )

    def unnegated(anchor: str, pattern: str) -> bool:
        # ponytail: sentence-level negation, enough for appended unsafe prose
        return any(
            re.search(anchor, sentence)
            and re.search(pattern, sentence)
            and not negation.search(sentence)
            for sentence in sentences
        )

    checks: Sequence[Tuple[str, bool, str]] = (
        (
            "USERLIST_FULL_REPLACE_STATEMENT",
            "anyone not in the file, or in it with no permissions, is removed from the"
            in normalized
            and "user list in accessowl" in normalized
            and not unnegated(
                r"not in the file", r"\b(?:keeps?|retains?|stays?|remains?)\b.{0,30}\baccess\b"
            )
            and not anywhere(
                r"not in the file|left out|absent|missing from the file",
                r"\b(?:keeps?|retains?)\s+(?:their\s+|its\s+|all\s+)?access\b",
            ),
            "state before confirmation that anyone not in the file, or in it with no permissions, is removed from the user list",
        ),
        (
            "USERLIST_REMOVED_ALWAYS_SHOWN",
            paragraph_with(
                "**removed**",
                "always show this line",
                '"removed: none"',
                "never shorten this list",
            ),
            "the preview always shows Removed, including Removed: None, and names every removed person",
        ),
        (
            "USERLIST_UNCHANGED_IN_BODY",
            paragraph_with("`put /applications/{application_id}/access_states`", "unchanged people too")
            and not unnegated(r"unchanged", r"\b(?:omit|skip|leave out|drop|exclude)\b"),
            "the full-replace body must include unchanged people, because anyone left out is removed",
        ),
        (
            "USERLIST_NEW_PEOPLE_LIST",
            paragraph_with(
                "**new people accessowl will create**",
                "at least one entry",
                "double-check their spelling",
                "cannot be deleted later, only offboarded",
            ),
            "list the people the import will create and warn they cannot be deleted later, only offboarded",
        ),
        (
            "USERLIST_DRIFT_RECONFIRM",
            paragraph_with(
                "immediately before the import",
                "if the fresh read reveals any blocker, go back to step 5",
                "show the new preview and ask again",
            ),
            "a fresh pre-write read must return blockers to step 5 and reconfirm any preview drift",
        ),
        (
            "USERLIST_422_NO_AUTOFIX",
            paragraph_with(
                "on `422`",
                "re-read the current access states",
                "never fix rows from the error text",
                "never resend the import after a `422`",
            )
            and not unnegated(r"\b422\b", r"\b(?:resend|retry|resubmit|fix)\w*"),
            "after a 422, re-read, report rejected rows, and never auto-fix or resend",
        ),
        (
            "USERLIST_SINGLE_CALL",
            paragraph_with("send it as one call", "never split it")
            and not unnegated(r"\bsplit\b", r"\b(?:batch|batches|chunk|chunks|calls)\b")
            and not anywhere(
                r"\bimport\b|access_states",
                r"\b(?:batch(?:es)?|chunks?|(?:several|multiple)\s+(?:smaller\s+)?(?:requests|calls)|smaller\s+requests)\b",
            ),
            "the full-replace import is one call and must never be split",
        ),
        (
            "USERLIST_REREAD_AFTER_200",
            paragraph_with(
                "on `200`",
                "re-read the current access states",
                "per person",
                "report them only as entries, never as people",
            ),
            "after a 200, re-read access states and report per person; response counts are entries",
        ),
        (
            "USERLIST_POST_PREVIEW_YES",
            "only a yes given after this preview counts" in normalized
            and not unnegated(
                r"\b(?:earlier|already|before|previous(?:ly)?|in advance|upfront)\b",
                r"\btreat\b.{0,60}\bas\s+(?:the\s+|a\s+)?(?:yes|confirmation)\b"
                r"|\bcounts?\s+as\s+(?:the\s+|a\s+)?(?:yes|confirmation)\b",
            ),
            "only a yes given after the preview confirms the import; an earlier go-ahead never counts",
        ),
        (
            "USERLIST_IMPORT_QUESTION_ALONE",
            paragraph_with(
                "ok to replace the <application> user list?",
                "never ask another question in the same message as the import question",
            )
            and paragraph_with(
                "**decisions**",
                "the mandatory-resource question from step 2, until the user names resources or says to skip it",
            ),
            "the import question stands alone, and the step 2 mandatory-resource question stays open until answered",
        ),
        (
            "USERLIST_BLOCKER_FRESH_READ",
            "never because the user says it is fine" in normalized
            and not unnegated(
                r"\bblockers?\b",
                r"\bclears?\b.{0,60}\b(?:user|they)\s+(?:says?|confirms?|agrees?)\b",
            ),
            "a blocker clears only on a fresh read, never because the user says it is fine",
        ),
    )
    return [(code, message) for code, passed, message in checks if not passed]
