"""Mutation tests prove that the contract validator rejects dangerous drift."""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from typing import List

from .contract_validator import (
    ALLOWED_REPOSITORY_FILES,
    APPROVED_CONTENT_SHA256,
    APPROVED_HARNESS_SHA256,
    MAX_FILE_BYTES,
    MAX_JSON_DEPTH,
    MAX_JSON_NUMBER_CHARS,
    MAX_REPOSITORY_BYTES,
    MAX_REPOSITORY_ENTRIES,
    MAX_TREE_DEPTH,
    Issue,
    VENDOR_CERTIFICATES,
    _validate_access_creation_invariants,
    _validate_destructive_invariants,
    _validate_idempotency,
    _validate_422_failure_semantics,
    _validate_reason_and_bulk,
    _validate_request_dedupe,
    _validate_target_statuses,
    decode_strict_utf8,
    extract_api_references,
    parse_frontmatter,
    parse_json_strict,
    secure_read_bytes,
    validate_approved_content,
    validate_approved_harness,
    validate_api_reference_text,
    validate_api_contracts,
    validate_manifest_values,
    validate_repository_files,
    validate_repository_inventory,
    validate_repository,
    validate_read_safety,
    validate_resilience_text,
    validate_skill_operation_scope,
    validate_write_safety,
)
from .run_tests import run_discovered_tests

class AdversarialOracleTests(unittest.TestCase):
    def assertCode(self, issues: List[object], expected: str) -> None:
        codes = {getattr(issue, "code") for issue in issues}
        self.assertIn(expected, codes, "expected %s, got %s" % (expected, sorted(codes)))

    def test_encoding_mutation_matrix(self) -> None:
        cases = (
            ("BOM", b"\xef\xbb\xbfhello", "UTF8_BOM"),
            ("NUL", b"hello\x00world", "NUL_BYTE"),
            ("bad continuation", b"\x80", "INVALID_UTF8"),
            ("truncated sequence", b"\xe2\x82", "INVALID_UTF8"),
            ("ANSI escape", b"safe\x1b[31m", "SOURCE_CONTROL_CHARACTER"),
            (
                "bidi override",
                "safe\u202eunsafe".encode("utf-8"),
                "SOURCE_CONTROL_CHARACTER",
            ),
        )
        for name, payload, code in cases:
            with self.subTest(name=name):
                _, issues = decode_strict_utf8(payload, "mutant.md")
                self.assertCode(issues, code)

    def test_frontmatter_mutation_matrix(self) -> None:
        baseline = "---\nname: sample-skill\ndescription: >\n  Useful description.\n---\n# Body\n"
        mutants = (
            ("unknown field", baseline.replace("description:", "license: MIT\ndescription:"), "FRONTMATTER_FIELD"),
            ("duplicate name", baseline.replace("description:", "name: other\ndescription:"), "FRONTMATTER_DUPLICATE"),
            ("one-space block", baseline.replace("  Useful", " Useful"), "FRONTMATTER_INDENT"),
            ("missing close", baseline.replace("---\n# Body", "# Body"), "FRONTMATTER_CLOSE"),
            ("empty body", baseline.replace("# Body\n", ""), "SKILL_BODY"),
        )
        parsed, baseline_issues = parse_frontmatter(baseline, "SKILL.md")
        self.assertIsNotNone(parsed)
        self.assertEqual([], baseline_issues)
        for name, value, code in mutants:
            with self.subTest(name=name):
                _, issues = parse_frontmatter(value, "SKILL.md")
                self.assertCode(issues, code)

    def test_json_duplicate_keys_are_rejected_at_every_depth(self) -> None:
        for payload in (
            b'{"name":"a","name":"b"}',
            b'{"outer":{"version":"1","version":"2"}}',
            b'{"plugins":[{"name":"a","name":"b"}]}',
        ):
            with self.subTest(payload=payload):
                value, issues = parse_json_strict(payload, "manifest.json")
                self.assertIsNone(value)
                self.assertCode(issues, "JSON_DUPLICATE_KEY")

    def test_json_non_rfc_numeric_constants_are_rejected(self) -> None:
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(constant=constant):
                value, issues = parse_json_strict(b'{"value":' + constant + b"}", "manifest.json")
                self.assertIsNone(value)
                self.assertCode(issues, "JSON_CONSTANT")

    def test_json_numeric_overflow_and_token_exhaustion_are_rejected(self) -> None:
        for number in (b"1e400", b"-1e400"):
            with self.subTest(number=number):
                value, issues = parse_json_strict(
                    b'{"value":' + number + b"}", "manifest.json"
                )
                self.assertIsNone(value)
                self.assertCode(issues, "JSON_NUMBER")

        exact_number = b"1" * MAX_JSON_NUMBER_CHARS
        value, issues = parse_json_strict(
            b'{"value":' + exact_number + b"}", "manifest.json"
        )
        self.assertIsNotNone(value)
        self.assertEqual([], issues)

        oversized_number = b"1" * (MAX_JSON_NUMBER_CHARS + 1)
        value, issues = parse_json_strict(
            b'{"value":' + oversized_number + b"}", "manifest.json"
        )
        self.assertIsNone(value)
        self.assertCode(issues, "JSON_NUMBER")

    def test_json_escaped_controls_surrogates_and_noncharacters_are_rejected(self) -> None:
        payloads = (
            b'{"value":"\\u0000"}',
            b'{"value":"\\u001b"}',
            b'{"value":"\\u202e"}',
            b'{"value":"\\ud800"}',
            b'{"value":"\\ufdd0"}',
            b'{"\\u202e":"value"}',
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                value, issues = parse_json_strict(payload, "manifest.json")
                self.assertIsNone(value)
                self.assertCode(issues, "JSON_STRING_CHARACTER")
        value, issues = parse_json_strict(
            b'{"value":"\\ud83d\\ude00"}', "manifest.json"
        )
        self.assertEqual({"value": "\U0001f600"}, value)
        self.assertEqual([], issues)

    def test_semantic_passes_propagate_skill_read_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for validator in (
                validate_api_contracts,
                validate_read_safety,
                validate_write_safety,
            ):
                with self.subTest(validator=validator.__name__):
                    self.assertCode(validator(root), "FILE_MISSING")

    def test_json_depth_cap_accepts_exact_and_rejects_next(self) -> None:
        exact = b"[" * MAX_JSON_DEPTH + b"0" + b"]" * MAX_JSON_DEPTH
        value, issues = parse_json_strict(exact, "manifest.json")
        self.assertIsNotNone(value)
        self.assertEqual([], issues)

        too_deep = b"[" * (MAX_JSON_DEPTH + 1) + b"0" + b"]" * (
            MAX_JSON_DEPTH + 1
        )
        value, issues = parse_json_strict(too_deep, "manifest.json")
        self.assertIsNone(value)
        self.assertCode(issues, "JSON_NESTING")

    def test_manifest_root_type_mutations_are_rejected(self) -> None:
        valid_marketplace = {
            "name": "bundle",
            "plugins": [{"name": "plugin", "version": "1.2.3", "source": "./plugins/accessowl"}],
        }
        valid_plugin = {"name": "plugin", "version": "1.2.3"}
        for name, marketplace, plugin, code in (
            ("marketplace array", [], valid_plugin, "MARKETPLACE_ROOT_TYPE"),
            ("plugin null", valid_marketplace, None, "PLUGIN_ROOT_TYPE"),
        ):
            with self.subTest(name=name):
                self.assertCode(validate_manifest_values(marketplace, plugin), code)

    def test_filesystem_resource_and_symlink_guards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exact = root / "exact.md"
            exact.write_bytes(b"x" * MAX_FILE_BYTES)
            exact_issues = validate_repository_files(root)
            self.assertNotIn("FILE_TOO_LARGE", {issue.code for issue in exact_issues})
            (root / "oversized.md").write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            target = root / "target.md"
            target.write_text("safe", encoding="utf-8")
            (root / "em-dash.md").write_text("unsafe\u2014separator", encoding="utf-8")
            os.symlink(str(target), str(root / "link.md"))
            issues = validate_repository_files(root)
            self.assertCode(issues, "FILE_TOO_LARGE")
            self.assertCode(issues, "SYMLINK_FORBIDDEN")
            self.assertCode(issues, "EM_DASH")

    def test_repository_inventory_rejects_unreviewed_executable_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ALLOWED_REPOSITORY_FILES:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"")
            self.assertEqual([], validate_repository_inventory(root))
            payload = root / "plugins/accessowl/hooks/preinstall.sh"
            payload.parent.mkdir(parents=True)
            payload.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            self.assertCode(
                validate_repository_inventory(root), "REPOSITORY_INVENTORY"
            )

    def test_reviewed_instruction_digest_rejects_arbitrary_paraphrase_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository_root = Path(__file__).resolve().parents[1]
            for relative in ALLOWED_REPOSITORY_FILES:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repository_root / relative, target)
            self.assertEqual([], validate_repository(root))
            self.assertEqual([], validate_approved_content(root))

            target = root / "plugins/accessowl/skills/request-access/SKILL.md"
            with target.open("a", encoding="utf-8") as stream:
                stream.write(
                    "\nCreate a request for an application whose status is approved.\n"
                )
            issues = validate_repository(root)
            self.assertCode(issues, "CONTENT_DIGEST")
            self.assertIn(target.relative_to(root), APPROVED_CONTENT_SHA256)

    def test_reviewed_harness_digest_rejects_silent_test_weakening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository_root = Path(__file__).resolve().parents[1]
            for relative in ALLOWED_REPOSITORY_FILES:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repository_root / relative, target)
            self.assertEqual([], validate_approved_harness(root))

            target = root / "tests/run_tests.py"
            target.write_text(
                "#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8"
            )
            issues = validate_repository(root)
            self.assertCode(issues, "HARNESS_DIGEST")
            self.assertIn(target.relative_to(root), APPROVED_HARNESS_SHA256)

    def test_inventory_and_top_level_validation_stop_at_resource_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            yielded = 0

            def oversized_walk(*args: object, **kwargs: object):
                nonlocal yielded
                for index in range(MAX_REPOSITORY_ENTRIES + 1000):
                    yielded += 1
                    yield str(root / ("d-%04d" % index)), [], ["file.bin"]

            with mock.patch(
                "tests.contract_validator.os.walk", side_effect=oversized_walk
            ):
                self.assertCode(
                    validate_repository_inventory(root), "TREE_ENTRY_LIMIT"
                )
            self.assertLessEqual(yielded, MAX_REPOSITORY_ENTRIES + 1)

            fatal = [Issue("TREE_ENTRY_LIMIT", ".", 0, "simulated resource limit")]
            with mock.patch(
                "tests.contract_validator.validate_repository_files",
                return_value=fatal,
            ), mock.patch(
                "tests.contract_validator.validate_repository_inventory",
                side_effect=AssertionError("must not continue after fatal guard"),
            ):
                self.assertEqual(fatal, validate_repository(root))

    def test_repository_byte_cap_accepts_exact_and_rejects_next_byte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remaining = MAX_REPOSITORY_BYTES
            index = 0
            while remaining:
                size = min(remaining, MAX_FILE_BYTES)
                target = root / ("payload-%02d.bin" % index)
                with target.open("wb") as stream:
                    stream.truncate(size)
                remaining -= size
                index += 1
            exact_codes = {issue.code for issue in validate_repository_files(root)}
            self.assertNotIn("REPOSITORY_BYTE_LIMIT", exact_codes)

            (root / "one-byte.bin").write_bytes(b"x")
            self.assertCode(
                validate_repository_files(root), "REPOSITORY_BYTE_LIMIT"
            )

    def test_filesystem_entry_cap_accepts_exact_and_rejects_next(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(MAX_REPOSITORY_ENTRIES):
                (root / ("entry-%04d.bin" % index)).touch()
            exact_issues = validate_repository_files(root)
            self.assertNotIn(
                "TREE_ENTRY_LIMIT", {issue.code for issue in exact_issues}
            )
            (root / "one-too-many.bin").touch()
            self.assertCode(validate_repository_files(root), "TREE_ENTRY_LIMIT")

    def test_filesystem_depth_cap_accepts_sixteen_and_rejects_seventeen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root
            for index in range(MAX_TREE_DEPTH):
                current = current / ("depth-%02d" % (index + 1))
                current.mkdir()
            exact_issues = validate_repository_files(root)
            self.assertNotIn("TREE_DEPTH_LIMIT", {issue.code for issue in exact_issues})
            (current / "depth-17").mkdir()
            self.assertCode(validate_repository_files(root), "TREE_DEPTH_LIMIT")

    def test_cache_named_symlink_is_rejected_before_skip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repository"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "payload.md").write_text("outside", encoding="utf-8")
            os.symlink(str(outside), str(root / "__pycache__"))
            self.assertCode(validate_repository_files(root), "SYMLINK_FORBIDDEN")

            (root / "__pycache__").unlink()
            (root / "__pycache__").mkdir()
            os.symlink(str(outside), str(root / "__pycache__" / "hidden-link"))
            self.assertCode(validate_repository_files(root), "SYMLINK_FORBIDDEN")

    def test_special_file_and_grow_during_read_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pipe = root / "pipe.md"
            os.mkfifo(str(pipe))
            self.assertCode(validate_repository_files(root), "FILE_NOT_REGULAR")

            result: List[object] = []
            reader = threading.Thread(
                target=lambda: result.append(secure_read_bytes(pipe, "pipe.md")),
                daemon=True,
            )
            reader.start()
            reader.join(1.0)
            self.assertFalse(reader.is_alive(), "secure read blocked while opening a FIFO")
            self.assertEqual(1, len(result))
            self.assertIsNone(result[0][0])
            self.assertCode(result[0][1], "FILE_NOT_REGULAR")

            growing = root / "growing.md"
            growing.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            real_fstat = os.fstat

            def stale_size(descriptor: int) -> os.stat_result:
                values = list(real_fstat(descriptor))
                values[6] = 0
                return os.stat_result(values)

            with mock.patch("tests.contract_validator.os.fstat", side_effect=stale_size):
                data, issues = secure_read_bytes(growing, "growing.md")
            self.assertIsNone(data)
            self.assertCode(issues, "FILE_TOO_LARGE")

    def test_read_errors_and_torn_snapshots_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            source.write_bytes(b"A" * (128 * 1024))

            with mock.patch(
                "tests.contract_validator.os.read",
                side_effect=OSError(5, "simulated I/O error"),
            ):
                data, issues = secure_read_bytes(source, "source.md")
            self.assertIsNone(data)
            self.assertCode(issues, "FILE_UNSAFE")

            real_read = os.read
            mutated = False

            def mutate_between_chunks(descriptor: int, count: int) -> bytes:
                nonlocal mutated
                chunk = real_read(descriptor, count)
                if chunk and not mutated:
                    with source.open("r+b") as writer:
                        writer.seek(64 * 1024)
                        writer.write(b"B" * (64 * 1024))
                        writer.flush()
                        os.fsync(writer.fileno())
                    mutated = True
                return chunk

            with mock.patch(
                "tests.contract_validator.os.read", side_effect=mutate_between_chunks
            ):
                data, issues = secure_read_bytes(source, "source.md")
            self.assertTrue(mutated)
            self.assertIsNone(data)
            self.assertCode(issues, "FILE_CHANGED")

            with mock.patch(
                "tests.contract_validator.os.read",
                side_effect=OSError(5, "simulated traversal read error"),
            ):
                self.assertCode(validate_repository_files(root), "FILE_UNSAFE")

    def test_directory_swap_cannot_escape_the_open_repository_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repository"
            inside = root / "inside"
            parked = root / "parked"
            outside = base / "outside"
            inside.mkdir(parents=True)
            outside.mkdir()
            (inside / "safe.md").write_text("safe", encoding="utf-8")
            (outside / "payload.md").write_text("outside\u2014payload", encoding="utf-8")

            real_open = os.open
            swapped = False

            def swap_before_directory_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
                nonlocal swapped
                if path == "inside" and kwargs.get("dir_fd") is not None and not swapped:
                    inside.rename(parked)
                    os.symlink(str(outside), str(inside))
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with mock.patch(
                "tests.contract_validator.os.open", side_effect=swap_before_directory_open
            ):
                issues = validate_repository_files(root)
            self.assertTrue(swapped)
            self.assertCode(issues, "FILE_UNSAFE")
            self.assertNotIn("EM_DASH", {issue.code for issue in issues})

            second_root = base / "repository-real-swap"
            second_inside = second_root / "inside"
            second_parked = second_root / "parked"
            second_outside = base / "outside-real-swap"
            second_inside.mkdir(parents=True)
            second_outside.mkdir()
            (second_inside / "safe.md").write_text("safe", encoding="utf-8")
            (second_outside / "payload.md").write_text(
                "outside\u2014payload", encoding="utf-8"
            )
            real_directory_swapped = False

            def replace_with_real_directory(
                path: object, flags: int, *args: object, **kwargs: object
            ) -> int:
                nonlocal real_directory_swapped
                if (
                    path == "inside"
                    and kwargs.get("dir_fd") is not None
                    and not real_directory_swapped
                ):
                    second_inside.rename(second_parked)
                    second_outside.rename(second_inside)
                    real_directory_swapped = True
                return real_open(path, flags, *args, **kwargs)

            with mock.patch(
                "tests.contract_validator.os.open",
                side_effect=replace_with_real_directory,
            ):
                issues = validate_repository_files(second_root)
            self.assertTrue(real_directory_swapped)
            self.assertCode(issues, "FILE_CHANGED")
            self.assertNotIn("EM_DASH", {issue.code for issue in issues})

    def test_api_mutation_matrix(self) -> None:
        cases = (
            ("wrong method", "`DELETE /users/{id}`", "API_OPERATION"),
            ("wrong path", "`GET /userz`", "API_OPERATION"),
            ("unknown query", "`GET /users?search=x`", "API_QUERY_PARAMETER"),
            ("duplicate query", "`GET /users?status=all&status=active`", "API_QUERY_DUPLICATE"),
            ("limit overflow", "`GET /users?limit=101`", "API_LIMIT"),
            ("unknown expansion", "`GET /access_states?expand=secrets`", "API_EXPAND"),
            ("raw space", "`GET /applications?title_like=hello world`", "API_QUERY_ENCODING"),
            ("raw Unicode", "`GET /applications?title_like=café`", "API_QUERY_ENCODING"),
            ("plus as space", "`GET /applications?title_like=hello+world`", "API_QUERY_ENCODING"),
            ("malformed percent", "`GET /applications?title_like=%ZZ`", "API_PERCENT_ESCAPE"),
            ("invalid UTF-8 percent byte", "`GET /applications?title_like=%FF`", "API_QUERY_UTF8"),
            ("overlong UTF-8 percent bytes", "`GET /applications?title_like=%C0%AF`", "API_QUERY_UTF8"),
            ("surrogate UTF-8 percent bytes", "`GET /applications?title_like=%ED%A0%80`", "API_QUERY_UTF8"),
            ("Unicode digit limit", "`GET /users?limit=1%D9%A3`", "API_LIMIT"),
            ("fragment", "`GET /users?status=all#ignored`", "API_FRAGMENT"),
            ("empty term", "`GET /users?status=all&&limit=100`", "API_QUERY_SYNTAX"),
            ("empty key", "`GET /users?=all`", "API_QUERY_EMPTY_KEY"),
            ("encoded key delimiter", "`GET /users?status%26admin=all`", "API_QUERY_PARAMETER"),
            ("evil absolute host", "`GET https://evil.example/api/v1/users?status=all`", "API_ABSOLUTE_URL"),
            ("empty value", "`GET /users?status=`", "API_QUERY_EMPTY_VALUE"),
            ("raw slash", "`GET /applications?title_like=R/D`", "API_QUERY_ENCODING"),
            ("raw equals", "`GET /applications?title_like=R=D`", "API_QUERY_ENCODING"),
            ("raw semicolon", "`GET /applications?title_like=R;D`", "API_QUERY_ENCODING"),
            ("unbackticked unsupported path", "GET /userz", "API_REFERENCE_NOT_CODE"),
            ("unbackticked grant bypass", "POST /access_requests/{id}/grant", "GRANT_ENDPOINT_FORBIDDEN"),
            ("invalid IPv6 authority", "`GET http://[`", "API_URL_SYNTAX"),
            ("unterminated IPv6 literal", "`GET https://[::1/users`", "API_URL_SYNTAX"),
            (
                "grant method before path prose",
                "Send a POST request to `/access_requests/{request_id}/grant`.",
                "GRANT_ENDPOINT_FORBIDDEN",
            ),
            (
                "grant path before method prose",
                "Use the `/access_requests/{request_id}/grant` endpoint with method POST.",
                "GRANT_ENDPOINT_FORBIDDEN",
            ),
        )
        for name, value, code in cases:
            with self.subTest(name=name):
                self.assertCode(validate_api_reference_text(value, "SKILL.md"), code)

        self.assertEqual(
            [],
            validate_api_reference_text(
                "`GET /applications?title_like=%C3%A9`", "SKILL.md"
            ),
        )

        self.assertEqual([], extract_api_references("`GET http://[`"))

    def test_read_only_skill_rejects_valid_but_out_of_scope_write(self) -> None:
        text = "Use `GET /users?status=all`. Also call `PATCH /applications/{id}`."
        self.assertCode(
            validate_skill_operation_scope("list-access", text, "SKILL.md"),
            "SKILL_OPERATION_SCOPE",
        )

    def test_write_semantics_mutation_matrix(self) -> None:
        idempotency = (
            "Send an Idempotency-Key using a fresh UUID for each logical write. "
            "Every retry uses the exact same method, path, body, and key, including "
            "429, timeout, network, and 5xx retries. A 409 replay proves the request was received but "
            "the outcome is unknown. Never treat it as success. After 409, verify "
            "with `GET /access_requests`, compare the baseline, and report only verified state."
        )
        self.assertEqual([], _validate_idempotency("request-access", idempotency, "SKILL.md"))
        self.assertCode(
            _validate_idempotency(
                "request-access",
                idempotency.replace("the outcome is unknown", "the outcome succeeded"),
                "SKILL.md",
            ),
            "IDEMPOTENCY_409_UNKNOWN",
        )
        self.assertCode(
            _validate_idempotency(
                "request-access",
                idempotency.replace(
                    "After 409, verify with `GET /access_requests`, compare the baseline, and report only verified state.",
                    "After 409, report the outcome as unknown.",
                ),
                "SKILL.md",
            ),
            "IDEMPOTENCY_VERIFY",
        )
        repository_root = Path(__file__).resolve().parents[1]
        revocation = (
            repository_root
            / "plugins/accessowl/skills/request-revocation/SKILL.md"
        ).read_text(encoding="utf-8")
        unverifiable_mutant = revocation.replace(
            "cannot be verified and ask\n  the user to check AccessOwl",
            "cannot be verified",
            1,
        )
        self.assertNotEqual(revocation, unverifiable_mutant)
        self.assertCode(
            _validate_idempotency(
                "request-revocation", unverifiable_mutant, "SKILL.md"
            ),
            "IDEMPOTENCY_UNVERIFIABLE",
        )

        boundaries = (
            "The required request_reason is at most 255 characters. Each bulk body "
            "contains 1 through 10 items, includes the required user_id, and covers one grantee."
        )
        self.assertEqual([], _validate_reason_and_bulk("request-access", boundaries, "SKILL.md"))
        for name, mutant, code in (
            ("reason cap", boundaries.replace("255", "256"), "REASON_255_BOUNDARY"),
            ("bulk cap", boundaries.replace("10 items", "11 items"), "BULK_ITEM_BOUNDARY"),
            ("grantee isolation", boundaries.replace("one grantee", "many grantees"), "BULK_ONE_GRANTEE"),
        ):
            with self.subTest(name=name):
                self.assertCode(
                    _validate_reason_and_bulk("request-access", mutant, "SKILL.md"), code
                )
        for unsafe, code in (
            ("A 256-character request_reason is accepted.", "REASON_255_BOUNDARY"),
            ("One bulk call may contain 11 items.", "BULK_ITEM_BOUNDARY"),
        ):
            with self.subTest(unsafe=unsafe):
                self.assertCode(
                    _validate_reason_and_bulk(
                        "request-access", boundaries + " " + unsafe, "SKILL.md"
                    ),
                    code,
                )

        dedupe = (
            "Pending request deduplication compares current active access. "
            "pending_approval, pending_permissions_assignment, processing_access, "
            "scheduled, and pending_dependency block. access_granted blocks only "
            "when a current active access state confirms it, because a historical "
            "grant may be revoked. denied and rejected do not block a new request."
        )
        self.assertEqual([], _validate_request_dedupe("request-access", dedupe, "SKILL.md"))
        self.assertCode(
            _validate_request_dedupe(
                "request-access", dedupe.replace("blocks only", "always blocks"), "SKILL.md"
            ),
            "REQUEST_GRANTED_CONDITIONAL",
        )
        for name, mutant, code in (
            (
                "blocking status inventory",
                dedupe.replace("pending_dependency", "dependency_pending"),
                "REQUEST_BLOCKING_STATUSES",
            ),
            (
                "nonblocking status semantics",
                dedupe.replace(
                    "denied and rejected do not block a new request",
                    "denied and rejected are reported",
                ),
                "REQUEST_NONBLOCKING_STATUSES",
            ),
            (
                "broad status class",
                dedupe + " Use open or completed request classes.",
                "REQUEST_BROAD_STATUS_CLASS",
            ),
            (
                "pending dedupe",
                dedupe.replace(
                    "Pending request deduplication compares current active access. ",
                    "",
                    1,
                ),
                "REQUEST_PENDING_DEDUPE",
            ),
        ):
            with self.subTest(name=name):
                self.assertCode(
                    _validate_request_dedupe("request-access", mutant, "SKILL.md"),
                    code,
                )

        creation = (
            "Immediately before every write, refetch application status requestable "
            "and stop if not.\n\nAn active state with resource_id: null is "
            "application-wide access and blocks a new resource-level request."
        )
        self.assertEqual(
            [],
            _validate_access_creation_invariants(
                "request-access", creation, "SKILL.md"
            ),
        )
        self.assertCode(
            _validate_access_creation_invariants(
                "request-access",
                creation.replace("status requestable", "status approved"),
                "SKILL.md",
            ),
            "APPLICATION_MUST_BE_REQUESTABLE",
        )

        statuses = (
            "active, onboarding, and onboarding_provisioning_planned are eligible. "
            "inactive, offboarding, and offboarded are ineligible, explain and stop. "
            "Show offboarding_planned and explicitly confirm. An unknown status must stop."
        )
        self.assertEqual([], _validate_target_statuses("request-access", statuses, "SKILL.md"))
        self.assertCode(
            _validate_target_statuses(
                "request-access", statuses.replace("ineligible", "eligible"), "SKILL.md"
            ),
            "TARGET_STATUS_INELIGIBLE",
        )

        validation_failure = (
            "On `422`, validate the documented error response and report a validation "
            "failure. The OpenAPI error fields are free-form and do not define a "
            "mandatory-resource code. Never infer a mandatory resource or synthesize "
            "a changed request body from error text. A user-specified changed request "
            "starts a new workflow with fresh reads, confirmation, and idempotency key."
        )
        self.assertEqual(
            [],
            _validate_422_failure_semantics(
                "request-access", validation_failure, "SKILL.md"
            ),
        )
        self.assertCode(
            _validate_422_failure_semantics(
                "request-access",
                validation_failure
                + " A 422 response lists the required mandatory permission.",
                "SKILL.md",
            ),
            "ACCESS_REQUEST_422_FAIL_CLOSED",
        )

        certificates = ", ".join(sorted(VENDOR_CERTIFICATES))
        vendor = (
            "After explicit confirmation and a clear yes, vendor_certificates, "
            "processed_data_types, and tags replace arrays, so preserve current values. "
            "The live slugs are %s. If lock_version is unavailable, refuse certificate, "
            "data type, tag, and notes read-modify-write changes. We cannot guarantee "
            "protection from a concurrent update without lock_version."
        ) % certificates
        self.assertEqual([], _validate_destructive_invariants("vendor-update", vendor, "SKILL.md"))
        self.assertCode(
            _validate_destructive_invariants(
                "vendor-update", vendor.replace("fsd_safe", "fsd_unknown"), "SKILL.md"
            ),
            "VENDOR_CERTIFICATE_ENUM",
        )

        request_guard = (
            "Require explicit confirmation after a clear yes. "
            "Never call the grant endpoint."
        )
        self.assertEqual(
            [],
            _validate_destructive_invariants(
                "request-access", request_guard, "SKILL.md"
            ),
        )
        for mutant, code in (
            (
                request_guard.replace(
                    "Require explicit confirmation after a clear yes.",
                    "Review the planned write.",
                ),
                "CONFIRM_BEFORE_WRITE",
            ),
            (
                request_guard.replace(
                    "Never call the grant endpoint.",
                    "The grant endpoint exists.",
                ),
                "NEVER_GRANT",
            ),
        ):
            with self.subTest(code=code):
                self.assertCode(
                    _validate_destructive_invariants(
                        "request-access", mutant, "SKILL.md"
                    ),
                    code,
                )

        revocation_guard = (
            "Require explicit confirmation after a clear yes. A revocation covers "
            "the whole entry; show all permissions and confirm them."
        )
        self.assertEqual(
            [],
            _validate_destructive_invariants(
                "request-revocation", revocation_guard, "SKILL.md"
            ),
        )
        self.assertCode(
            _validate_destructive_invariants(
                "request-revocation",
                revocation_guard.replace("whole entry", "selected record"),
                "SKILL.md",
            ),
            "REVOCATION_WHOLE_ENTRY",
        )

    def test_resilience_mutation_matrix(self) -> None:
        baseline = """
Use `GET /users?status=all` and request `limit=100` on every cursor endpoint.
Follow every nonempty `meta.next_cursor`. A repeated cursor, a duplicate record ID
within a page or across pages of one logical pagination traversal of one endpoint
and query, page failure, or the cap of
1,000 pages or 100,000 items makes the result incomplete. Track every cursor and
returned record ID. Reset cursor and record-ID tracking for each fresh query or
pre-write refetch. The same record ID may reappear across independent traversals;
a duplicate within one page or a repeat across pages within the same traversal
is inconsistent. The
100,000-item budget remains global across the run. Require `meta.limit` to be an
integer equal to the requested `limit=100`, and require the `meta.next_cursor` key
on every page. It must be either a nonempty string or explicit null. Explicit null
proves exhaustion. A missing key, empty string, wrong type, repeated cursor,
duplicate record ID, page longer than 100 records, or failed page makes the result
incomplete. Do not require or use `page`, `page_size`, `total_pages`, or
`total_count` as completion evidence. The live API cursor shape was verified on
2026-07-19; the current OpenAPI still describes absent page-number fields. Never
answer or write from an incomplete result.

For 429, validate Retry-After. Stop when it is missing, malformed, non-integer,
negative, or larger than 60 seconds, and allow at most two retries. Network and 5xx failures
also get at most two retries, then stop incomplete or unverified. Percent-encode
every dynamic query value. A 401 means a missing or invalid credential. Handle a
billing redirect separately.

Give every API attempt an enforced 30-second deadline covering DNS resolution,
TCP connection, TLS, redirects, response headers, and the streamed and decompressed body. A deadline
expiry is a network error and counts toward the same retry cap. If the caller
cannot enforce it, stop before making the request. Track monotonic elapsed time
and enforce an overall 15-minute run deadline. Before every attempt, stop if no
time remains or it cannot finish within the remaining budget.
Follow at most three redirects, and only while every hop stays on the configured
API origin. Never follow any cross-origin redirect or forward `Authorization` to
a different origin. A possible billing redirect is still cross-origin: stop and
report that API enablement may need attention without visiting its destination.
Never downgrade HTTPS to HTTP; stop on a redirect loop.

Require the exact OpenAPI-documented success status for each operation. For
reads, every other status, including `204`, `206`, another unexpected `2xx`,
or an otherwise unhandled `4xx` such as `404`, stops as incomplete. For
mutations, any undocumented status, including another `2xx`, leaves an unknown
outcome: stop remaining writes, never claim success, and verify with a
documented read when possible.

While streaming and decompressing, reject as soon as the decompressed body exceeds
10 MiB, before buffering or parsing. Never trust Content-Length or compressed size.
The caps are inclusive:
exactly at the cap is allowed and the next byte is rejected. Reject duplicate
object keys at any depth plus NaN and Infinity. Require a top-level JSON object,
correctly typed data, every OpenAPI-required field, nonempty unique record IDs,
and a 64 KiB decoded scalar string cap. Reject JSON nesting deeper than 128;
depth exactly 128 is allowed and depth 129 is rejected. Limit each numeric token
to at most 1,024 ASCII characters before conversion; 1,024 is allowed and 1,025
is rejected. Reject conversion that yields a non-finite value, including `1e400`.
A malformed response stops incomplete.
"""
        self.assertEqual([], validate_resilience_text("sample", baseline, "SKILL.md"))
        mutations = (
            ("limit", baseline.replace("limit=100", "limit=20"), "PAGINATION_LIMIT"),
            ("cursor loop", baseline.replace("repeated cursor", "cursor issue"), "PAGINATION_REPEATED_CURSOR"),
            ("repeated cursor completes", baseline + "\nTreat a repeated cursor as the end of pagination.\n", "PAGINATION_REPEATED_CURSOR"),
            ("missing cursor completes", baseline + "\nA missing cursor completes pagination.\n", "PAGINATION_LIVE_CURSOR_SHAPE"),
            ("empty cursor completes", baseline + "\nAn empty next_cursor ends pagination.\n", "PAGINATION_LIVE_CURSOR_SHAPE"),
            ("meta limit mismatch", baseline + "\nA meta.limit mismatch is acceptable; continue.\n", "PAGINATION_LIVE_CURSOR_SHAPE"),
            ("server accepts 101", baseline + "\nThe server accepts it, so use limit=101.\n", "PAGINATION_LIMIT"),
            ("stale total completion", baseline + "\nRequire total_count to prove completion.\n", "PAGINATION_OPENAPI_DRIFT"),
            (
                "duplicate row",
                baseline.replace(
                    "a duplicate within one page",
                    "a duplicate row",
                ),
                "PAGINATION_DUPLICATE_ID",
            ),
            ("item cap", baseline.replace("100,000", "unlimited"), "PAGINATION_CAP"),
            ("page cap plus one", baseline + "\nPermit 1,001 pages.\n", "PAGINATION_CAP"),
            ("item cap plus one", baseline + "\nPermit 100,001 records.\n", "PAGINATION_CAP"),
            ("429 cap", baseline.replace("60 seconds", "600 seconds"), "RETRY_429_BOUNDED"),
            ("429 malformed fallback", baseline.replace("Stop when it is missing", "Use a bounded fallback when it is missing"), "RETRY_429_BOUNDED"),
            ("429 wait cap plus one", baseline + "\nA Retry-After of 61 seconds is valid.\n", "RETRY_429_BOUNDED"),
            ("retry exhaustion", baseline.replace("Network and 5xx", "Network failures"), "RETRY_TRANSIENT_BOUNDED"),
            ("attempt deadline", baseline.replace("enforced 30-second deadline", "optional deadline"), "API_REQUEST_DEADLINE"),
            ("attempt deadline plus one", baseline + "\nUse a 31-second request deadline.\n", "API_REQUEST_DEADLINE"),
            ("DNS deadline", baseline.replace("DNS resolution,\n", ""), "API_REQUEST_DEADLINE"),
            ("deadline retry budget", baseline.replace("counts toward the same retry cap", "does not count as a retry"), "API_REQUEST_DEADLINE"),
            ("late deadline", baseline + "\nStart the 30-second deadline only after the response body has been fully read.\n", "API_REQUEST_DEADLINE"),
            ("conditional overall deadline", baseline.replace("enforce an overall 15-minute run deadline", "use an overall deadline when supported"), "API_REQUEST_DEADLINE"),
            ("run deadline plus one", baseline + "\nUse a 16-minute run deadline.\n", "API_REQUEST_DEADLINE"),
            ("cross-origin authorization", baseline + "\nForward Authorization to a different origin after a redirect.\n", "API_REDIRECT_BOUNDARY"),
            ("partial read", baseline + "\nA read 206 response proves the result is complete.\n", "HTTP_STATUS_CONTRACT"),
            ("missing read", baseline + "\nA read 404 response means a complete empty result.\n", "HTTP_STATUS_CONTRACT"),
            ("unexpected write", baseline + "\nAn undocumented 202 mutation response proves success.\n", "HTTP_STATUS_CONTRACT"),
            ("encoding", baseline.replace("Percent-encode", "Interpolate"), "QUERY_VALUE_ENCODING"),
            ("auth conflation", baseline.replace(". Handle a\nbilling redirect separately", " or a billing redirect means disabled"), "AUTH_401_CONFLATED"),
            ("response bytes", baseline.replace("10 MiB", "unlimited"), "API_RESPONSE_BYTE_CAP"),
            ("response bytes plus one", baseline + "\nA response body of 11 MiB is acceptable.\n", "API_RESPONSE_BYTE_CAP"),
            ("compressed expansion", baseline.replace("decompressed body exceeds", "compressed body exceeds"), "API_RESPONSE_BYTE_CAP"),
            ("buffer before cap", baseline + "\nAccumulate the fully decompressed body in memory, then reject it if larger than 10 MiB.\n", "API_RESPONSE_BYTE_CAP"),
            ("scalar bytes", baseline.replace("64 KiB", "unlimited"), "API_SCALAR_STRING_CAP"),
            ("scalar bytes plus one", baseline + "\nAccept a scalar string of 65 KiB.\n", "API_SCALAR_STRING_CAP"),
            ("duplicate JSON keys", baseline.replace("duplicate\nobject keys at any depth", "object keys"), "API_JSON_STRICT"),
            ("cap boundary", baseline.replace("the next byte", "larger values"), "API_CAP_BOUNDARY"),
        )
        for name, value, code in mutations:
            with self.subTest(name=name):
                self.assertCode(validate_resilience_text("sample", value, "SKILL.md"), code)

    def test_runner_rejects_false_green_outcomes_and_accepts_only_clean_passes(self) -> None:
        cases = (
            ("no matching file", None, 2, "zero tests discovered"),
            ("empty matching file", "", 2, "zero tests discovered"),
            (
                "clean pass",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    def test_passes(self): self.assertTrue(True)\n",
                0,
                "OK",
            ),
            (
                "ordinary failure",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    def test_fails(self): self.fail('mutant')\n",
                1,
                "FAILED",
            ),
            (
                "all skipped",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    @unittest.skip('mutant')\n"
                "    def test_skipped(self): pass\n",
                3,
                "skipped test(s) are not allowed",
            ),
            (
                "partially skipped",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    def test_passes(self): self.assertTrue(True)\n"
                "    @unittest.skip('mutant')\n"
                "    def test_skipped(self): pass\n",
                3,
                "1 skipped test(s) are not allowed",
            ),
            (
                "expected failure",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    @unittest.expectedFailure\n"
                "    def test_expected_failure(self): self.fail('mutant')\n",
                1,
                "expected failures are not allowed",
            ),
            (
                "unexpected success",
                "import unittest\nclass Case(unittest.TestCase):\n"
                "    @unittest.expectedFailure\n"
                "    def test_unexpected_success(self): self.assertTrue(True)\n",
                1,
                "unexpected success",
            ),
        )
        for index, (name, source, expected_code, expected_text) in enumerate(cases):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if source is not None:
                    (root / ("test_case_%d.py" % index)).write_text(
                        source, encoding="utf-8"
                    )
                stream = io.StringIO()
                result = run_discovered_tests(root, stream=stream)
                self.assertEqual(expected_code, result)
                self.assertIn(expected_text.casefold(), stream.getvalue().casefold())


if __name__ == "__main__":
    unittest.main()
