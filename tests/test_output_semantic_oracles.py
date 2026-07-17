"""Mutation oracles for customer-visible output and generated CSV safety."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, Optional

from .contract_validator import _validate_reporting_and_csv_invariants


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "accessowl" / "skills"


class OutputSemanticOracleTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.documents: Dict[str, str] = {
            skill: (SKILL_ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
            for skill in (
                "access-report",
                "discovered-apps",
                "list-access",
                "userlist-import-preflight",
                "vendor-update",
                "view-policies",
            )
        }

    def assertMutationRejected(
        self,
        skill: str,
        expected_code: str,
        old: Optional[str] = None,
        new: Optional[str] = None,
        appended: Optional[str] = None,
    ) -> None:
        original = self.documents[skill]
        if appended is not None:
            self.assertIsNone(old)
            mutant = original + "\n\n" + appended + "\n"
        else:
            self.assertIsNotNone(old)
            self.assertIsNotNone(new)
            self.assertEqual(
                1,
                original.count(old or ""),
                "mutation source is not unique in %s: %r" % (skill, old),
            )
            mutant = original.replace(old or "", new or "", 1)
        issues = _validate_reporting_and_csv_invariants(
            skill, mutant, "%s/SKILL.md" % skill
        )
        codes = {issue.code for issue in issues}
        self.assertIn(expected_code, codes, "got %s" % sorted(codes))

    def test_userlist_malformed_email_and_status_mutations(self) -> None:
        cases = (
            (
                "malformed utf8 reversal",
                "USERLIST_MALFORMED_CSV",
                "Reject invalid UTF-8",
                "Accept invalid UTF-8",
                None,
            ),
            (
                "malformed appended contradiction",
                "USERLIST_MALFORMED_CSV",
                None,
                None,
                "For malformed CSV, accept invalid UTF-8 and continue past NUL bytes.",
            ),
            (
                "local part 65",
                "USERLIST_EMAIL_BOUNDARIES",
                "local part of at most 64 characters",
                "local part of at most 65 characters",
                None,
            ),
            (
                "total length 255",
                "USERLIST_EMAIL_BOUNDARIES",
                "at most 254\ncharacters total",
                "at most 255\ncharacters total",
                None,
            ),
            (
                "domain label 64",
                "USERLIST_EMAIL_BOUNDARIES",
                "are at most 63 characters",
                "are at most 64 characters",
                None,
            ),
            (
                "email appended contradiction",
                "USERLIST_EMAIL_BOUNDARIES",
                None,
                None,
                "Email local parts longer than 64 characters are accepted.",
            ),
            (
                "flagged status bypass",
                "USERLIST_FLAGGED_STATUSES",
                "explicitly keeps or removes every flagged\nrow",
                "silently accepts every flagged\nrow",
                None,
            ),
            (
                "flagged status appended contradiction",
                "USERLIST_FLAGGED_STATUSES",
                None,
                None,
                "Inactive and offboarded matches are safe without confirmation and are import-ready.",
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected(
                    "userlist-import-preflight", code, old, new, appended
                )

    def test_local_input_files_are_stable_regular_descriptors(self) -> None:
        for skill in ("access-report", "userlist-import-preflight"):
            with self.subTest(skill=skill, mutation="follow symlink"):
                self.assertMutationRejected(
                    skill,
                    "INPUT_FILE_IDENTITY",
                    "open it without following symlinks",
                    "open it by following symlinks",
                )
            with self.subTest(skill=skill, mutation="special file"):
                self.assertMutationRejected(
                    skill,
                    "INPUT_FILE_IDENTITY",
                    appended="Accept a FIFO or socket as a local input file.",
                )
            with self.subTest(skill=skill, mutation="changed during read"):
                self.assertMutationRejected(
                    skill,
                    "INPUT_FILE_IDENTITY",
                    appended=(
                        "If local file metadata changes during the read, "
                        "continue and use the data."
                    ),
                )
            with self.subTest(skill=skill, mutation="continue before change"):
                self.assertMutationRejected(
                    skill,
                    "INPUT_FILE_IDENTITY",
                    appended="Continue if local file metadata changes while reading.",
                )
            with self.subTest(skill=skill, mutation="reopen path"):
                self.assertMutationRejected(
                    skill,
                    "INPUT_FILE_IDENTITY",
                    appended="Reopen the path after the metadata check.",
                )

    def test_access_report_population_and_label_mutation_matrix(self) -> None:
        cases = (
            (
                "distinct users",
                "REPORT_DISTINCT_USERS",
                "count distinct user\nIDs, not access-state rows",
                "count access-state rows as people",
                None,
            ),
            (
                "distinct users contradiction",
                "REPORT_DISTINCT_USERS",
                None,
                None,
                "Count access-state rows as the number of people in the population.",
            ),
            (
                "unlinked separation",
                "REPORT_UNLINKED_SEPARATE",
                "report linked people and unlinked accounts\nas separate counts",
                "combine linked people and unlinked accounts into one count",
                None,
            ),
            (
                "unlinked contradiction",
                "REPORT_UNLINKED_SEPARATE",
                None,
                None,
                "Add all unlinked accounts to the people count.",
            ),
            (
                "application-wide bucket",
                "REPORT_ACCESS_LABELS",
                "explicit **Application-wide access** bucket",
                "generic access bucket",
                None,
            ),
            (
                "title-only grouping",
                "REPORT_ACCESS_LABELS",
                None,
                None,
                "Group permissions by title alone and drop application-wide access.",
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected("access-report", code, old, new, appended)

    def test_userlist_artifact_mutation_matrix(self) -> None:
        cases = (
            (
                "in-memory output",
                "Generate the final CSV as a stream, not as one in-memory string.",
                "Build the final CSV as one in-memory string.",
                None,
            ),
            ("non-random name", "random UUID", "application title", None),
            (
                "unsafe create",
                "Create a new regular file exclusively with owner-only mode `0600`\nregardless of the process umask, do not follow symlinks or overwrite an existing\npath",
                "Create or overwrite any path, and follow symlinks",
                None,
            ),
            (
                "retain overflow",
                "close and remove the incomplete artifact",
                "leave the incomplete artifact",
                None,
            ),
            (
                "skip reopen",
                "attachment, reopen\nwithout following symlinks",
                "attach without reopening",
                None,
            ),
            (
                "skip reparse",
                "parse it strictly again",
                "do not parse it again",
                None,
            ),
            (
                "permissive permissions",
                "owner-only mode `0600`",
                "group-readable mode `0644` is acceptable",
                None,
            ),
            (
                "appended overwrite",
                None,
                None,
                "For the final CSV artifact, it is acceptable to overwrite an existing path and follow symlinks.",
            ),
        )
        for name, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected(
                    "userlist-import-preflight",
                    "USERLIST_SECURE_ARTIFACT",
                    old,
                    new,
                    appended,
                )

    def test_vendor_value_and_identity_mutation_matrix(self) -> None:
        cases = (
            (
                "impossible date",
                "VENDOR_REAL_DATE",
                "Reject impossible\n  dates",
                "Accept impossible\n  dates",
                None,
            ),
            (
                "date appended contradiction",
                "VENDOR_REAL_DATE",
                None,
                None,
                "Vendor review dates accept impossible calendar dates.",
            ),
            (
                "drop existing replacement values",
                "VENDOR_REPLACEMENT_AND_NOTES",
                "send the combined list",
                "send only the requested list",
                None,
            ),
            (
                "rewrite notes",
                "VENDOR_REPLACEMENT_AND_NOTES",
                "append the new\n  statement without replacing or rewriting any existing note content",
                "replace the existing notes with the new statement",
                None,
            ),
            (
                "notes appended contradiction",
                "VENDOR_REPLACEMENT_AND_NOTES",
                None,
                None,
                "For notes, replace the existing notes with the new statement.",
            ),
            (
                "raw tag objects",
                "VENDOR_TAG_TITLES",
                "carry forward their `title` strings, not tag IDs or\nraw objects",
                "carry forward raw tag objects",
                None,
            ),
            (
                "tag appended contradiction",
                "VENDOR_TAG_TITLES",
                None,
                None,
                "Patch raw tag objects instead of their title strings.",
            ),
            (
                "inactive owner",
                "VENDOR_OWNER_STATUS",
                "Do not assign an `inactive`, `offboarding`, or `offboarded` person",
                "You may assign an `inactive`, `offboarding`, or `offboarded` person",
                None,
            ),
            (
                "owner appended contradiction",
                "VENDOR_OWNER_STATUS",
                None,
                None,
                "You may assign an inactive person as the owner or an Application Admin.",
            ),
            (
                "owner field mapping",
                "VENDOR_USER_FIELD_SHAPES",
                "Send `owner_user_id` as one resolved UUID string or `null`",
                "Send the owner as a user value",
                None,
            ),
            (
                "admin field mapping",
                "VENDOR_USER_FIELD_SHAPES",
                "Send `admin_user_ids` as an internally unique array of resolved",
                "Send the application admin list as resolved",
                None,
            ),
            (
                "admin replacement semantics",
                "VENDOR_USER_FIELD_SHAPES",
                "complete replacement array",
                "incremental array",
                None,
            ),
            (
                "owner name instead of uuid",
                "VENDOR_USER_FIELD_SHAPES",
                None,
                None,
                "For `owner_user_id`, send the person name instead of a UUID.",
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected("vendor-update", code, old, new, appended)

    def test_policy_output_mutation_matrix(self) -> None:
        cases = (
            (
                "application references",
                "POLICY_APPLICATION_REFERENCES",
                "internally\nunique, and fully resolvable to the complete application list",
                "used as returned without validation",
                None,
            ),
            (
                "application reference contradiction",
                "POLICY_APPLICATION_REFERENCES",
                None,
                None,
                "Missing, duplicate, or unresolved application_ids are acceptable, continue.",
            ),
            (
                "missing default stop",
                "POLICY_EXACTLY_ONE_DEFAULT",
                "zero or several is inconsistent data and stops that claim",
                "zero or several is acceptable and uses the first default",
                None,
            ),
            (
                "default appended contradiction",
                "POLICY_EXACTLY_ONE_DEFAULT",
                None,
                None,
                "If several default policies exist, use the first default and continue.",
            ),
            (
                "default first-record synonym",
                "POLICY_EXACTLY_ONE_DEFAULT",
                None,
                None,
                "Two defaults are resolved by selecting the first record.",
            ),
            (
                "wrong default field",
                "POLICY_EXACTLY_ONE_DEFAULT",
                "`default_policy: true`",
                "`default: true`",
                None,
            ),
            (
                "invent exclusivity",
                "POLICY_CROSS_SCOPE_OVERLAP",
                "The OpenAPI does not state that ordinary and elevated policy memberships are\nexclusive.",
                "Ordinary and elevated policy memberships are mutually exclusive.",
                None,
            ),
            (
                "exclusivity appended contradiction",
                "POLICY_CROSS_SCOPE_OVERLAP",
                None,
                None,
                "Ordinary and elevated memberships are mutually exclusive and cannot overlap.",
            ),
            (
                "scope rules out overlap",
                "POLICY_CROSS_SCOPE_OVERLAP",
                None,
                None,
                "Membership in an ordinary scope rules out membership in an elevated scope.",
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected("view-policies", code, old, new, appended)

    def test_list_access_output_mutation_matrix(self) -> None:
        cases = (
            (
                "permission identity",
                "LIST_IDENTITY_AND_ROLE",
                "permission ID, not by title",
                "permission title",
                None,
            ),
            (
                "role contradiction",
                "LIST_IDENTITY_AND_ROLE",
                None,
                None,
                "Group permissions by title and drop application-wide access.",
            ),
            (
                "discovered earliest date",
                "LIST_DISCOVERED_SNAPSHOT",
                "earliest valid `effective_start`",
                "latest `effective_start`",
                None,
            ),
            (
                "discovered active contradiction",
                "LIST_DISCOVERED_SNAPSHOT",
                None,
                None,
                "Discovered apps are currently active managed access.",
            ),
            (
                "show ended",
                "LIST_ACTIVE_ONLY",
                "are active; show only\nthose",
                "are historical; show every entry including ended access",
                None,
            ),
            (
                "ended appended contradiction",
                "LIST_ACTIVE_ONLY",
                None,
                None,
                "Always include ended, expired, or revoked access in the table.",
            ),
            (
                "show email",
                "LIST_EMAIL_HIDDEN",
                "Do not include the person's email address",
                "Always include the person's email address",
                None,
            ),
            (
                "email appended contradiction",
                "LIST_EMAIL_HIDDEN",
                None,
                None,
                "Always include the person's email in every answer.",
            ),
            (
                "effective start is discovery",
                "EFFECTIVE_START_MEANING",
                None,
                None,
                "effective_start is the first-discovery timestamp.",
            ),
            (
                "machine-local date",
                "EFFECTIVE_START_TIMEZONE",
                "convert it to UTC",
                "convert it to the machine's local timezone",
                None,
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected("list-access", code, old, new, appended)

    def test_discovered_output_mutation_matrix(self) -> None:
        cases = (
            (
                "dedupe earliest",
                "DISCOVERED_DEDUPE_EARLIEST",
                "earliest `effective_start`",
                "latest `effective_start`",
                None,
            ),
            (
                "state id contradiction",
                "DISCOVERED_DEDUPE_EARLIEST",
                None,
                None,
                "Distinct access-state IDs imply distinct people and applications.",
            ),
            (
                "unlinked aggregation",
                "DISCOVERED_UNLINKED_AGGREGATION",
                "Aggregate all unlinked rows into\none **Unlinked accounts (N)** row",
                "Emit each unlinked account as its own row",
                None,
            ),
            (
                "unlinked rows contradiction",
                "DISCOVERED_UNLINKED_AGGREGATION",
                None,
                None,
                "Emit several unlinked account rows instead of aggregating them.",
            ),
            (
                "missing effective end active",
                "DISCOVERED_NOT_CURRENT_ACTIVE",
                "An omitted or malformed `effective_end` is\nunknown, not active",
                "A missing or malformed `effective_end` is treated as active",
                None,
            ),
            (
                "active appended contradiction",
                "DISCOVERED_NOT_CURRENT_ACTIVE",
                None,
                None,
                "Describe every discovered entry as currently active, even when effective_end is missing.",
            ),
            (
                "combine count units",
                "DISCOVERED_SEPARATE_ACCOUNT_COUNTS",
                "Never\nadd those unlike quantities into one count",
                "Add those quantities into one people count",
                None,
            ),
            (
                "counts appended contradiction",
                "DISCOVERED_SEPARATE_ACCOUNT_COUNTS",
                None,
                None,
                "Sum linked people and unlinked accounts into one People count.",
            ),
            (
                "effective start is discovery",
                "EFFECTIVE_START_MEANING",
                None,
                None,
                "effective_start means the first discovery timestamp.",
            ),
            (
                "machine-local date",
                "EFFECTIVE_START_TIMEZONE",
                "convert it to UTC",
                "convert it to the machine's local timezone",
                None,
            ),
        )
        for name, code, old, new, appended in cases:
            with self.subTest(name=name):
                self.assertMutationRejected("discovered-apps", code, old, new, appended)


if __name__ == "__main__":
    unittest.main()
