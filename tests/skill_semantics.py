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
     ("`pending_approval` (waiting for approval): deny it", "`pending_permissions_assignment`, `scheduled`, `pending_dependency`, or `processing_access` (approved", "being provisioned): reject it", "`access_granted`, `denied`, or `rejected` (granted, denied, rejected): it is already closed", "any other status: stop", "the status decides the action, not the user's wording",
      "an approved request is never denied", "name the reject in the confirmation instead")),
    ("CLOSE_DENY_APPROVER", "deny only for a pending current-step approver", False,
     ("lowest-numbered step whose `status` is `pending`", "never pick one yourself", "never record a denial for someone who is not a pending approver of the current step", "always include `on_behalf_of_user_id`")),
    ("CLOSE_CONFIRMATION", "only a clear yes after the confirmation counts", False,
     ("only a clear yes given after this confirmation counts", "ask nothing else in that message", "will not receive this access",
      "a question, a change, or a partial yes means no write")),
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
    r"\b(?:deny|reject)\s+(?:it|them)\s+anyway\b",
    r"\b(?:unknown|unrecognized|unclassified|other)\s+status(?:es)?[^.]{0,40}\b(?:rejected|denied|reject|deny)\b",
    r"\b(?:go-ahead|go\s+ahead|yes)\b[^.]{0,60}\b(?:first|earlier|initial|original|opening)\s+message\b[^.]{0,40}"
    r"\b(?:works|counts|suffices|is\s+enough)\b",
)


def close_request_findings(skill: str, text: str) -> List[Finding]:
    if skill != "close-request":
        return []
    return _phrase_contract(
        text, CLOSE_REQUIREMENTS, CLOSE_CONTRADICTIONS, ("CLOSE_CONTRADICTION", "unsafe close prose"))


ONBOARD_REQUIREMENTS: PhraseRules = (
    ("ONBOARD_SCOPE", "onboard-user adds and onboards only; existing details are edited on the profile", False,
     ("it never edits an existing person's details", "point the user to the person's profile in accessowl",
      "onboarding is never used for it, because onboarding an active person sets any details sent with it",
      "never grants individual app access", "never offboards anyone", "onboarding is not a way to edit those details")),
    ("ONBOARD_ACTIVE_WARNING", "warn before onboarding an active person, as its own question", True,
     ("`active`: first check the manager", "then warn plainly that onboarding switches the person to onboarding",
      "provisions whatever access their access template matches", "cannot be undone through the api",
      "does not change their details", "this is its own question, not the confirmation",
      "never combine the warning and the confirmation")),
    ("ONBOARD_IDENTITY", "several records for one email are ambiguous and stop", False,
     ("several matches are ambiguous: say so and stop, and never guess",)),
    ("ONBOARD_ADDED_THIS_RUN", "only the person this run added, by user id, skips the active-person warning", False,
     ("who is `active` until onboarded",
      "a person whose add returned `201` (or was verified) in this run, same user id, is `active` too, but gets no warning",
      "a person added in an earlier conversation goes through the normal active warning")),
    ("ONBOARD_STATUS_GATES", "scheduled onboarding only reschedules; started, offboarding, and inactive stop", False,
     ("`onboarding_provisioning_planned` (onboarding scheduled): offer only a reschedule",
      "details are ignored on a reschedule",
      "`onboarding` (onboarding started): say onboarding has already started and cannot be rescheduled, and stop",
      "`offboarding_planned` (offboarding planned), `offboarding`, `offboarded`, or `inactive`: stop",
      "any other status: stop")),
    ("ONBOARD_MANAGER_REQUIRED", "an active or onboarding manager resolved to exactly one person is required", False,
     ("manager (required, because onboarding needs one)", "matches exactly one user case-insensitively",
      "ask which one is meant; never guess",
      "the manager must be active or onboarding (`active`, `onboarding_provisioning_planned`, or `onboarding`); "
      "otherwise say so and ask for another manager",
      "has no manager in accessowl, and onboarding needs one", "then ask again",
      "if the manager is not active or onboarding, say so the same way and stop")),
    ("ONBOARD_EXISTING_NO_DETAILS", "every onboard call carries only scheduled_at; the add carries the details", False,
     ("every onboard call sends only `scheduled_at`", "the add carries every confirmed detail",
      "never send details on any onboard call")),
    ("ONBOARD_DATES", "start dates need a timezone, past dates are refused", False,
     ("interpret every start date", "otherwise ask for the timezone", "always show the absolute date in the confirmation",
      "a start date in the past is not allowed", "offer to onboard now instead", "the utc offset in effect on that date")),
    ("ONBOARD_CONFIRMATION", "only a clear yes after the confirmation counts, asked alone", False,
     ("only a clear yes given after this confirmation counts", "is not the confirmation",
      "ask nothing else in that message", "a question, a change, or a partial yes means no write",
      "in one message", "always show the person's email in the warning and the confirmation", "there is already a")),
    ("ONBOARD_PREWRITE_RECHECK", "re-check the email and status right before each write", False,
     ("require that it still returns no one", "the same email and the same status as confirmed",
      "go back to step 3 for the current status (an active person gets the warning again)",
      "never write from the older snapshot")),
    ("ONBOARD_CREATE_ONCE", "a 400 or 422 on the add is never retried", True,
     ("a `400` or `422` means accessowl did not accept the change", "never retry the add", "re-read the email",
      "nothing was added", "fresh confirmation")),
    ("ONBOARD_PARTIAL_ADD", "an added but not onboarded person cannot be deleted", False,
     ("added to accessowl but not onboarded", "people cannot be deleted, only offboarded")),
    ("ONBOARD_UNCERTAIN", "an uncertain outcome stops all writes; a rescheduled date stays unverified", False,
     ("report the outcome as unknown and stop remaining writes", "fresh key needs a new confirmation",
      "report the new date as unverified")),
    ("ONBOARD_VERIFIED_REPORT", "report the re-read status in plain words, never specific apps", False,
     ("`onboarding_provisioning_planned`: onboarding scheduled", "`onboarding`: onboarding started now",
      "never list or promise specific applications")),
)
_EDITABLE = r"(?:manager|department|team|job\s+title|location|city|employment\s+type|details)"
_E = r"(?:manager|department|team|job\s+title|location|city|employment\s+type|details|`?manager_user_id`?)"
_KEY = r"`?idempotency-key`?"
ONBOARD_CONTRADICTIONS = (
    r"\b(?:use|call|run|send)\s+(?:the\s+)?onboard\w*[^.]{0,40}\bto\s+(?:update|change|edit|set)\b[^.]{0,40}" + _EDITABLE,
    r"\bonboard\w*\s+(?:(?:can|also|will|may)\s+){1,2}(?:update|change|edit)",
    r"\b(?:update|change|edit)\w*\s+(?:an?\s+)?(?:existing\s+)?(?:person's|user's|their)\s+" + _EDITABLE
    + r"[^.]{0,20}\b(?:by|through|via|with|,)\s*(?:re-?)?onboard",
    r"(?:earlier|already|before|previous(?:ly)?)[^.]{0,60}(?:counts?\s+as|treat[^.]{0,20}as)\s+(?:the\s+)?confirmation",
    r"(?:warning|continue)[^.]{0,60}(?:counts?\s+as|doubles?\s+as|serves?\s+as)\s+(?:the\s+)?confirmation",
    r"(?<!never )(?<!not )\b(?:combine|merge|skip)\w*\b[^.]{0,40}\b(?:warning|re-?check|confirmation)",
    r"\b(?:pick|choose|use|take)\s+(?:the\s+)?(?:first|newest|latest|most\s+recent\w*(?:\s+\w+)?)\s+"
    r"(?:match\w*|one|person|user|record)",
    r"\b(?:status|state)\b[^.]{0,40}\bchanged?\b[^.]{0,60}\banyway\b",
    r"\b(?:onboard|write|send|continue|proceed|go\s+ahead)\w*\s+(?:it\s+|them\s+)?anyway\b",
    r"past\s+(?:start\s+)?dates?[^.]{0,40}\b(?:is|are)\s+(?:allowed|accepted|fine|ok)",
    r"\b(?:accept|allow|send|use)\s+(?:a\s+)?(?:start\s+)?dates?\s+in\s+the\s+past",
    r"(?:422|already\s+exists)[^.]{0,60}(?<!never )\b(?:(?:retry|resend|repeat)\s+(?:the\s+)?(?:add|create)"
    r"|try\s+(?:the\s+add\s+)?again)",
    r"\b(?:offboarding|offboarded|inactive)[^.]{0,60}\b(?:can|may)\s+(?:still\s+)?be\s+onboarded",
    r"\bmanager[^.]{0,20}\bis\s+optional",
    r"\b(?:without|with\s+no)\s+(?:a\s+)?manager[^.]{0,30}\b(?:is\s+fine|works|is\s+allowed)",
    r"\bonboard\w*[^.]{0,40}\bwithout\s+(?:(?:an?\s+)?(?:new\s+|fresh\s+|its\s+own\s+)?" + _KEY + r"|one\b)",
    _KEY + r"[^.]{0,40}\b(?:optional|not\s+needed|unnecessary)\b[^.]{0,40}\bonboard",
    r"\b(?:skip|omit|drop)\w*\s+(?:the\s+)?" + _KEY + r"[^.]{0,40}\bonboard",
    r"\b(?:active|existing)\s+person\b[^.]{0,40}(?<!never )\b(?:also\s+)?(?:send|include|pass)\b[^.]{0,60}" + _E,
    r"\bonboard\w*\s+(?:call|request|body)s?\b[^.]{0,40}(?<!never )(?<!not )\b(?:also\s+)?"
    r"(?:sends?|includes?|pass(?:es)?|carr(?:y|ies))\b(?!\s+only)[^.]{0,60}" + _E,
    r"(?<!never )(?<!not )\b(?:send|include|pass)\b[^.]{0,40}" + _E
    + r"[^.]{0,40}\b(?:on|in|with)\s+(?:the\s+|every\s+|each\s+|any\s+)?onboard",
    r"(?<!never )\b(?:send|include|pass|add)\w*\s+(?:the\s+)?`?manager_user_id`?[^.]{0,30}\bonboard",
    r"\bno\s+manager\b[^.]{0,40}(?<!never )\b(?:send|include|pass)\b[^.]{0,40}\bmanager",
    r"\bnew\s+hire\b[^.]{0,80}\b(?:no|skip\w*|without)\s+(?:the\s+)?warning",
    r"\b(?:created|added|inserted)\b[^.]{0,40}\b(?:this|last|past)\s+(?:week|day|month|few)\b[^.]{0,40}\bno\s+warning",
    r"\b(?:already\s+)?started\b[^.]{0,40}\bcan\s+(?:still\s+)?be\s+rescheduled",
)


def onboard_user_findings(skill: str, text: str) -> List[Finding]:
    if skill != "onboard-user":
        return []
    return _phrase_contract(
        text, ONBOARD_REQUIREMENTS, ONBOARD_CONTRADICTIONS, ("ONBOARD_CONTRADICTION", "unsafe onboarding prose"))


OFFBOARD_REQUIREMENTS: PhraseRules = (
    ("OFFBOARD_SCOPE", "offboard-user only offboards or reschedules; no delete, no cancel, no single-app revoke", False,
     ("it never deletes people: accessowl does not support deleting people",
      "so \"delete this user\" means offboarding them", "it never cancels a planned offboarding: there is no api for that",
      "point the user to the person's profile in accessowl", "never revokes access to a single application",
      "never onboards anyone", "if the user asks to delete a person, say that accessowl does not delete people")),
    ("OFFBOARD_IDENTITY", "one exact person by email or unique full name; several matches never guess", False,
     ("several matches are ambiguous: say so and stop, and never guess",
      "by a full name that matches exactly one user case-insensitively", "ask which one is meant; never guess")),
    ("OFFBOARD_STATUS_GATES", "planned only reschedules; underway, offboarded, and unknown stop; inactive asks", False,
     ("`active`: offboard, now or on a date",
      "`offboarding_planned` (offboarding planned): offer only a reschedule, to a new date, "
      "or to now when the user explicitly asks for now",
      "`offboarding` (being offboarded): say offboarding is already underway, so nothing changes, and stop",
      "`offboarded`: say the person is already offboarded, so nothing changes, and stop",
      "`inactive`: say the person is inactive in accessowl and ask whether to continue with offboarding. "
      "this is its own question, not the confirmation",
      "any other status: stop")),
    ("OFFBOARD_ONBOARDING_WARNING", "warn before offboarding someone still onboarding, as its own question", True,
     ("`onboarding_provisioning_planned` (onboarding scheduled) or `onboarding` (onboarding started): "
      "warn plainly that this person has not finished onboarding yet",
      "ask whether to continue with offboarding", "this is its own question, not the confirmation",
      "never combine the warning and the confirmation")),
    ("OFFBOARD_NO_CANCEL", "cancelling is on the profile; never offboard now to cancel or fix a planned date", False,
     ("if the user asks to cancel a planned offboarding, say that a planned offboarding is cancelled on the "
      "person's profile in accessowl, and stop", "never offboard now to cancel or fix a planned offboarding",
      "offboarding now happens only when the user explicitly asks for now")),
    ("OFFBOARD_DATES", "dates need a timezone, past dates are refused, never switch to now alone", False,
     ("interpret every date", "otherwise ask for the timezone", "always show the absolute date in the confirmation",
      "a date or time in the past is not allowed", "offer to offboard now instead", "never switch to now on your own",
      "send `scheduled_at` as the start of that day (00:00) in that timezone",
      "the utc offset in effect on that date", "for now, leave `scheduled_at` out")),
    ("OFFBOARD_ONE_PERSON", "one person per confirmation, never bulk", False,
     ("handle one person per confirmation", "never offboard several people under one confirmation")),
    ("OFFBOARD_CONFIRMATION", "one confirmation with the consequence sentence; only a later clear yes counts", False,
     ("only a clear yes given after this confirmation counts", "is not the confirmation",
      "ask nothing else in that message", "never ask another question in the same message as the confirmation",
      "a question, a change, or a partial yes means no write",
      "always show the person's email in the warning and the confirmation",
      "\"this sends the offboarding notice and revokes the access accessowl tracks for <name>. "
      "it cannot be undone through the api.\"",
      "a reschedule to now carries the offboarding consequence sentence")),
    ("OFFBOARD_PREWRITE_RECHECK", "re-fetch the person right before the write and re-gate on drift", False,
     ("immediately before the write, re-fetch `get /users/{user_id}`", "the same email and the same status as confirmed",
      "go back to step 2 for the current status", "gets the warning again", "never write from the older snapshot")),
    ("OFFBOARD_CALL", "one offboard call with a fresh key and only scheduled_at or an empty body", False,
     ("send `post /users/{user_id}/offboard` with a fresh `idempotency-key`",
      "`{\"scheduled_at\": \"<scheduled_at>\"}` for a confirmed date and `{}` for now",
      "the documented success status is `200` with the person", "require the same person id and email",
      "after a `200`, re-read the person with `get /users/{user_id}`")),
    ("OFFBOARD_422", "a 400 or 422 re-reads, changes nothing, and never resends or switches to now", True,
     ("a `400` or `422` means accessowl did not accept the change", "re-read the person with `get /users/{user_id}`",
      "if the person is now being offboarded or is offboarded, say so plainly and that nothing changed",
      "if the date was rejected", "with a new confirmation", "never resend it or switch to now on your own")),
    ("OFFBOARD_UNCERTAIN", "an uncertain outcome stops all writes; a rescheduled date stays unverified", False,
     ("a `409` proves only that the attempt was received", "report the new date as unverified",
      "report the outcome as unknown and stop remaining writes", "fresh key needs a new confirmation")),
    ("OFFBOARD_VERIFIED_REPORT", "report the re-read status in plain words, never specific apps or removed access", False,
     ("`offboarding_planned`: offboarding planned for the confirmed date",
      "`offboarding` or `offboarded`: offboarding started now",
      "the status stays offboarding planned and the person's record does not show the date",
      "report the new date as accepted by accessowl", "if the status is not the one that was confirmed",
      "never list or promise specific applications, and never claim access was removed")),
)
_NOW = r"(?:switch\w*\s+to\s+now|offboard\w*\s+(?:them\s+|it\s+|the\s+person\s+)?now|send\w*\s+(?:it\s+)?(?:as\s+)?now)"
OFFBOARD_CONTRADICTIONS = (
    r"(?:^|[.!?:,]\s)(?:then\s+|instead,?\s+)?delete\s+(?:the|this|that)\s+(?:user|person|employee|record)",
    r"\b(?:people|users?|persons?|employees?)\s+(?:can|may)\s+(?:also\s+|still\s+)?be\s+deleted",
    r"(?<!never )(?<!not )\boffboard\w*\s+(?:(?:them|it|the\s+person)\s+)?now\s+(?:instead\s+)?to\s+"
    r"(?:cancel|fix|correct|undo|replace)",
    r"\bto\s+(?:cancel|fix|correct|undo)\b[^.]{0,40}\bplanned\s+(?:offboarding|date)\b[^.]{0,20},\s*" + _NOW,
    r"\bplanned\s+(?:date|offboarding)\b[^.]{0,40}\b(?:wrong|incorrect|a\s+mistake)\b[^.]{0,40}" + _NOW,
    r"(?<!never )(?<!not )\bcancel\w*\s+(?:the\s+|a\s+)?planned\s+offboarding\s+(?:through|via|with)\s+(?:the\s+)?api",
    r"\bapi\b[^.]{0,30}\bcan\s+cancel",
    r"(?:earlier|already|before|previous(?:ly)?)[^.]{0,60}(?:counts?\s+as|treat[^.]{0,20}as)\s+(?:the\s+)?confirmation",
    r"(?:warning|continue)[^.]{0,60}(?:counts?\s+as|doubles?\s+as|serves?\s+as)\s+(?:the\s+)?confirmation",
    r"(?<!never )(?<!not )\b(?:combine|merge|skip)\w*\b[^.]{0,40}\b(?:warning|re-?check|confirmation)",
    r"\b(?:pick|choose|use|take)\s+(?:the\s+)?(?:first|newest|latest|most\s+recent\w*(?:\s+\w+)?)\s+"
    r"(?:match\w*|one|person|user|record)",
    r"\b(?:status|state)\b[^.]{0,40}\bchanged?\b[^.]{0,60}\banyway\b",
    r"\b(?:offboard|write|send|continue|proceed|go\s+ahead)\w*\s+(?:it\s+|them\s+)?anyway\b",
    r"\b(?:422|400)\b[^.]{0,80}\banyway\b",
    r"\b(?:being\s+offboarded|offboarded|offboarding)\b[^.]{0,60}\b(?:offboard\w*\s+(?:them\s+|it\s+|the\s+person\s+)?again"
    r"|can\s+(?:still\s+|also\s+)?be\s+offboarded)",
    r"\boffboard\w*[^.]{0,40}\bwithout\s+(?:(?:an?\s+)?(?:new\s+|fresh\s+|its\s+own\s+)?" + _KEY + r"|one\b)",
    _KEY + r"[^.]{0,40}\b(?:optional|not\s+needed|unnecessary)\b[^.]{0,40}\boffboard",
    r"\b(?:skip|omit|drop)\w*\s+(?:the\s+)?" + _KEY + r"[^.]{0,40}\boffboard",
    r"\b(?:date|scheduled_at)\b[^.]{0,40}\b(?:rejected|refused|not\s+accepted|fails?)\b[^.]{0,60}(?<!never )(?<!not )\b" + _NOW,
    r"\b(?:422|400)\b[^.]{0,60}(?<!never )(?<!not )\b" + _NOW,
    r"\bpast\b[^.]{0,40},\s*(?:just\s+)?" + _NOW,
    r"past\s+(?:dates?|times?)[^.]{0,40}\b(?:is|are)\s+(?:allowed|accepted|fine|ok)",
    r"(?<!never )\boffboard\w*\s+(?:\w+\s+){0,2}(?:people|persons|users|employees)[^.]{0,30}\b(?:under|in|with)\s+"
    r"(?:one|a\s+single|the\s+same)\s+confirmation",
    r"\b(?:one|a\s+single)\s+confirmation\s+(?:can\s+|may\s+)?(?:covers?|for)\s+(?:several|multiple|all|many)",
    r"\bbulk\b[^.]{0,20}\boffboard",
    r"\bre-?read\b[^.]{0,40}(?<!cannot )(?<!not )\bshows?\s+the\s+(?:new\s+)?(?:planned\s+)?date",
    r"(?<!never )(?<!not )\b(?:report|say|claim)\w*\s+(?:that\s+)?(?:all\s+)?(?:the\s+)?access\s+(?:was|is|has\s+been)\s+"
    r"(?:removed|revoked)",
)


def offboard_user_findings(skill: str, text: str) -> List[Finding]:
    if skill != "offboard-user":
        return []
    return _phrase_contract(
        text, OFFBOARD_REQUIREMENTS, OFFBOARD_CONTRADICTIONS, ("OFFBOARD_CONTRADICTION", "unsafe offboarding prose"))


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
