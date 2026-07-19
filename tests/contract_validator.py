"""Fail-closed, standard-library-only validators for the skill repository."""

from __future__ import annotations

import codecs
import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import SplitResult, unquote_to_bytes, urlsplit


MAX_FILE_BYTES = 256 * 1024
MAX_REPOSITORY_BYTES = 4 * 1024 * 1024
MAX_REPOSITORY_ENTRIES = 4096
MAX_TREE_DEPTH = 16
MAX_JSON_DEPTH = 128
MAX_JSON_NUMBER_CHARS = 1024
SKILL_ROOT = Path("plugins/accessowl/skills")
MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")
PLUGIN_MANIFEST_PATH = Path("plugins/accessowl/.claude-plugin/plugin.json")
WORKFLOW_PATH = Path(".github/workflows/adversarial-tests.yml")
SYNC_WORKFLOW_PATH = Path(".github/workflows/sync-upstream.yml")

EXPECTED_MARKETPLACE_NAME = "accessowl-claude-skills"
EXPECTED_PLUGIN_NAME = "claudetag-for-accessowl"
EXPECTED_PLUGIN_SOURCE = "./plugins/accessowl"
EXPECTED_PLUGIN_HOMEPAGE = "https://docs.accessowl.com/api-reference/introduction"
EXPECTED_PLUGIN_REPOSITORY = "https://github.com/AccessOwl/claude-skills-for-customer"
EXPECTED_README_REPOSITORY = "github.com/AccessOwl/claude-skills-for-customer"
CHECKOUT_ACTION_SHA = "34e114876b0b11c390a56381ad16ebd13914f8d5"
SETUP_PYTHON_ACTION_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
EXPECTED_WORKFLOW_ACTIVE_LINES: Tuple[str, ...] = (
    "name: Adversarial contract tests",
    "on:",
    "  pull_request:",
    "  push:",
    "permissions:",
    "  contents: read",
    "concurrency:",
    "  group: adversarial-contract-${{ github.workflow }}-${{ github.ref }}",
    "  cancel-in-progress: true",
    "jobs:",
    "  test:",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 5",
    "    strategy:",
    "      fail-fast: false",
    "      matrix:",
    "        python-version: ['3.9', '3.12']",
    "    steps:",
    "      - name: Check out repository",
    "        uses: actions/checkout@%s" % CHECKOUT_ACTION_SHA,
    "        with:",
    "          persist-credentials: false",
    "      - name: Set up Python",
    "        uses: actions/setup-python@%s" % SETUP_PYTHON_ACTION_SHA,
    "        with:",
    "          python-version: ${{ matrix.python-version }}",
    "      - name: Run adversarial contract suite",
    "        env:",
    "          PYTHONDONTWRITEBYTECODE: '1'",
    "          PYTHONHASHSEED: '0'",
    "          TZ: UTC",
    "        run: python tests/run_tests.py",
)
EXPECTED_SYNC_WORKFLOW_ACTIVE_LINES: Tuple[str, ...] = (
    "name: Sync from AccessOwl upstream",
    "on:",
    "  schedule:",
    '    - cron: "23 6 * * *"',
    "  workflow_dispatch:",
    "jobs:",
    "  sync:",
    "    if: github.repository != 'AccessOwl/claude-skills-for-customer'",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 5",
    "    permissions:",
    "      contents: write",
    "    steps:",
    "      - name: Check out fork",
    "        uses: actions/checkout@%s" % CHECKOUT_ACTION_SHA,
    "        with:",
    "          fetch-depth: 0",
    "          persist-credentials: true",
    "      - name: Fast-forward main from upstream",
    "        run: |",
    "          git remote add upstream https://github.com/AccessOwl/claude-skills-for-customer.git",
    "          git fetch upstream main",
    "          git merge --ff-only upstream/main",
    "          git push origin main",
)
CORE_HARNESS_FILES: Tuple[Path, ...] = (
    Path("tests/__init__.py"),
    Path("tests/contract_validator.py"),
    Path("tests/run_tests.py"),
    Path("tests/test_adversarial_oracles.py"),
    Path("tests/test_api_semantic_oracles.py"),
    Path("tests/test_ci_manifest_oracles.py"),
    Path("tests/test_output_semantic_oracles.py"),
    Path("tests/test_repository_contract.py"),
    Path("tests/test_write_semantic_oracles.py"),
)

_SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)

EXPECTED_SKILLS: Tuple[str, ...] = (
    "access-report",
    "discovered-apps",
    "grant-access",
    "list-access",
    "mirror-access",
    "request-access",
    "request-revocation",
    "userlist-import-preflight",
    "vendor-update",
    "view-policies",
)
ALLOWED_REPOSITORY_FILES = frozenset(
    {
        Path("README.md"),
        Path("SKILL_STYLE.md"),
        MARKETPLACE_PATH,
        PLUGIN_MANIFEST_PATH,
        WORKFLOW_PATH,
        SYNC_WORKFLOW_PATH,
    }
    | set(CORE_HARNESS_FILES)
    | {SKILL_ROOT / skill / "SKILL.md" for skill in EXPECTED_SKILLS}
)
APPROVED_CONTENT_SHA256: Mapping[Path, str] = {
    Path("README.md"): "3771bf362ae75ce5b6cd1e70a3cb38951400af2e3b06a0f71665224a6492ab98",
    Path("SKILL_STYLE.md"): "0a87f4aa5a8f217961ebf72feeda18a38a2ee6f125db4aa51fdb6077f5d1fc4f",
    SKILL_ROOT / "access-report" / "SKILL.md": "04b0cb7596cbfc47d5bfdd94212cfc47eba37034edd6bb007d5eec0a78a684e2",
    SKILL_ROOT / "discovered-apps" / "SKILL.md": "5b44042f86381748e2e47867f52d712b4804828367bc1956cacfda2eaf919eaf",
    SKILL_ROOT / "grant-access" / "SKILL.md": "4526d14bfb164f3c259fcbb53049e48fc593c7cda5a5bdc32ee7c8b894c34118",
    SKILL_ROOT / "list-access" / "SKILL.md": "27ad420d032595be4b56ab3b3e4878f8675988ed1ed60130aafa4fce5caff230",
    SKILL_ROOT / "mirror-access" / "SKILL.md": "29278059cd301c935872cfd1a84ada9b71a26365285c54cd204ed56de15a4f34",
    SKILL_ROOT / "request-access" / "SKILL.md": "b0d2279cb572721b4fb5ebdfd1531875dc287908b3aa8cd624f127f04617820e",
    SKILL_ROOT / "request-revocation" / "SKILL.md": "03aa615fcc621693ac5053fecc361db7c2b218b7a2fb6884d5c0f4572a1955f9",
    SKILL_ROOT / "userlist-import-preflight" / "SKILL.md": "cf46be52a0ca4c6ab73cbba1638a60423e8f7388f8e603f3c338485b71486f5a",
    SKILL_ROOT / "vendor-update" / "SKILL.md": "43e09501d5407379b09c6ef0ed3d8a4209cb4b8783b3c270b3f2d193184b0dde",
    SKILL_ROOT / "view-policies" / "SKILL.md": "5069085ddd93aa5bff3ddc6dc50565c7690d701d0ae19c3bd33ceaccbc48e685",
}
APPROVED_HARNESS_SHA256: Mapping[Path, str] = {
    Path("tests/__init__.py"): "4edc2608a674618b5c120c5e3c0a534975575dc72b4f9905db9d40f41308befa",
    Path("tests/run_tests.py"): "e4799c9740af405e0a6edfd0d33d557cfed74603dd7fd560cce3b7a5c5f39d4f",
    Path("tests/test_adversarial_oracles.py"): "a9237701bce7c5b0a98a3e0eb712d6426e5f3f4b027a079dcbb8c48c6ac8cf19",
    Path("tests/test_api_semantic_oracles.py"): "4ad70ff26aaaa9e63a21adbf3b343e17a1f86629023c1586ce3d91d2eaf09ffa",
    Path("tests/test_ci_manifest_oracles.py"): "12a4f88b57cb45d53a5efe612d99ac6331d675b53aea5df710155759df58b8f1",
    Path("tests/test_output_semantic_oracles.py"): "839c0419b45111e6a3b0296979d7f549f84d7c0928ba18c0a436add2bd2959c7",
    Path("tests/test_repository_contract.py"): "ace6db9f382d7cbc7d1112531d8370675afe950907a3fa5006081fcdfde2fce2",
    Path("tests/test_write_semantic_oracles.py"): "283687a797d3610b9b1ba18f72d6a3fd56bfd372a77838e4f85e993850d9e96e",
}

# Curated from https://docs.accessowl.com/api-reference/openapi.json on 2026-07-17. The
# repository suite is intentionally offline and deterministic, so the facts
# that skill prose relies on are reviewed and pinned here.
API_OPERATIONS: Mapping[Tuple[str, str], frozenset[str]] = {
    ("GET", "/access_requests"): frozenset({"limit", "cursor"}),
    ("POST", "/access_requests"): frozenset(),
    ("POST", "/access_requests/bulk"): frozenset(),
    ("POST", "/access_requests/{}/grant"): frozenset(),
    ("POST", "/access_revocations"): frozenset(),
    ("GET", "/access_states"): frozenset(
        {"limit", "cursor", "application_id", "grantee_user_id", "expand"}
    ),
    ("GET", "/applications"): frozenset(
        {"limit", "cursor", "title_like", "category_contains_word"}
    ),
    ("POST", "/applications"): frozenset(),
    ("GET", "/applications/{}/resources"): frozenset(),
    ("PUT", "/applications/{}/structure"): frozenset(),
    ("GET", "/applications/{}"): frozenset(),
    ("PATCH", "/applications/{}"): frozenset(),
    ("PUT", "/applications/{}"): frozenset(),
    ("GET", "/policies"): frozenset({"limit", "cursor"}),
    ("PUT", "/policies/{}/applications"): frozenset(),
    ("GET", "/users"): frozenset({"limit", "cursor", "status"}),
    ("GET", "/users/{}"): frozenset(),
}
CURSOR_ENDPOINTS = frozenset(
    {"/users", "/applications", "/access_states", "/access_requests", "/policies"}
)
EXPAND_VALUES = frozenset(
    {"grantee_user", "application", "resource", "target_permissions"}
)
USER_STATUSES = frozenset(
    {
        "onboarding_provisioning_planned",
        "onboarding",
        "active",
        "inactive",
        "offboarding_planned",
        "offboarding",
        "offboarded",
        "all",
    }
)
VENDOR_CERTIFICATES = frozenset(
    {
        "iso_22301",
        "iso_27001",
        "iso_27017",
        "iso_27701",
        "iso_31000",
        "iso_42001",
        "soc1",
        "soc2_t1",
        "soc2_t2",
        "soc3",
        "pci_dss",
        "nist_csf",
        "fed_ramp",
        "hipaa",
        "hitrust_csf",
        "gdpr",
        "csa_star",
        "fsd_safe",
    }
)

REQUIRED_OPERATIONS: Mapping[str, frozenset[Tuple[str, str]]] = {
    "access-report": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/users/{}"),
            ("GET", "/access_states"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_requests"),
            ("POST", "/access_requests/bulk"),
        }
    ),
    "discovered-apps": frozenset(
        {("GET", "/users"), ("GET", "/applications"), ("GET", "/access_states")}
    ),
    "grant-access": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/users/{}"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_requests"),
            ("GET", "/access_states"),
            ("POST", "/access_requests/{}/grant"),
        }
    ),
    "list-access": frozenset(
        {("GET", "/users"), ("GET", "/access_states"), ("GET", "/applications")}
    ),
    "mirror-access": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/users/{}"),
            ("GET", "/access_states"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_requests"),
            ("POST", "/access_requests/bulk"),
        }
    ),
    "request-access": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/users/{}"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
            ("POST", "/access_requests"),
            ("POST", "/access_requests/bulk"),
        }
    ),
    "request-revocation": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("GET", "/access_states"),
            ("POST", "/access_revocations"),
        }
    ),
    "userlist-import-preflight": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/applications"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
        }
    ),
    "vendor-update": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("PATCH", "/applications/{}"),
        }
    ),
    "view-policies": frozenset(
        {("GET", "/policies"), ("GET", "/applications")}
    ),
}
ALLOWED_OPERATIONS: Mapping[str, frozenset[Tuple[str, str]]] = {
    "access-report": REQUIRED_OPERATIONS["access-report"],
    "discovered-apps": REQUIRED_OPERATIONS["discovered-apps"],
    "grant-access": REQUIRED_OPERATIONS["grant-access"],
    "list-access": REQUIRED_OPERATIONS["list-access"],
    "mirror-access": REQUIRED_OPERATIONS["mirror-access"],
    "request-access": REQUIRED_OPERATIONS["request-access"],
    "request-revocation": REQUIRED_OPERATIONS["request-revocation"],
    "userlist-import-preflight": REQUIRED_OPERATIONS["userlist-import-preflight"]
    | frozenset({("PUT", "/applications/{}/structure")}),
    "vendor-update": REQUIRED_OPERATIONS["vendor-update"],
    "view-policies": REQUIRED_OPERATIONS["view-policies"]
    | frozenset({("PUT", "/policies/{}/applications")}),
}
REFUSED_OPERATIONS: Mapping[str, Tuple[str, str]] = {
    "userlist-import-preflight": ("PUT", "/applications/{}/structure"),
    "view-policies": ("PUT", "/policies/{}/applications"),
}

STATUS_ALL_SKILLS = frozenset(
    {
        "access-report",
        "discovered-apps",
        "grant-access",
        "list-access",
        "mirror-access",
        "request-access",
        "request-revocation",
        "userlist-import-preflight",
        "vendor-update",
    }
)
EXPANSION_REQUIREMENTS: Mapping[str, frozenset[str]] = {
    "access-report": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
    "discovered-apps": frozenset({"grantee_user", "application"}),
    "grant-access": frozenset({"application", "resource", "target_permissions"}),
    "list-access": frozenset({"application", "resource", "target_permissions"}),
    "mirror-access": frozenset({"application", "resource", "target_permissions"}),
    "request-access": frozenset({"application", "resource", "target_permissions"}),
    "request-revocation": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
    "userlist-import-preflight": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
}

WRITE_SKILLS = frozenset(
    {
        "access-report",
        "grant-access",
        "mirror-access",
        "request-access",
        "request-revocation",
        "vendor-update",
    }
)
IDEMPOTENCY_VERIFICATION: Mapping[str, Tuple[str, str]] = {
    "access-report": ("GET", "/access_requests"),
    "grant-access": ("GET", "/access_requests"),
    "mirror-access": ("GET", "/access_requests"),
    "request-access": ("GET", "/access_requests"),
    "vendor-update": ("GET", "/applications/{}"),
}
CONCURRENCY_READS: Mapping[str, frozenset[Tuple[str, str]]] = {
    "access-report": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "grant-access": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "mirror-access": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "request-access": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "request-revocation": frozenset({("GET", "/access_states")}),
    "vendor-update": frozenset({("GET", "/applications/{}")}),
}
REASON_SKILLS: Mapping[str, str] = {
    "access-report": "request_reason",
    "mirror-access": "request_reason",
    "request-access": "request_reason",
    "request-revocation": "reason",
}
BULK_SKILLS = frozenset({"access-report", "mirror-access", "request-access"})
REQUEST_DEDUPE_SKILLS = BULK_SKILLS
ALWAYS_BLOCKING_REQUEST_STATUSES = frozenset(
    {
        "pending_approval",
        "pending_permissions_assignment",
        "processing_access",
        "scheduled",
        "pending_dependency",
    }
)
NONBLOCKING_REQUEST_STATUSES = frozenset({"denied", "rejected"})
TARGET_STATUS_SKILLS = frozenset({"access-report", "mirror-access", "request-access"})
TARGET_ELIGIBLE_STATUSES = frozenset(
    {"active", "onboarding", "onboarding_provisioning_planned"}
)
TARGET_INELIGIBLE_STATUSES = frozenset({"inactive", "offboarding", "offboarded"})
ACCESS_REQUEST_STATUSES = frozenset(
    {
        "pending_approval",
        "pending_permissions_assignment",
        "access_granted",
        "denied",
        "rejected",
        "processing_access",
        "scheduled",
        "pending_dependency",
    }
)
ACCESS_REVOCATION_STATUSES = frozenset({"processing_access", "rejected", "revoked"})
TITLE_LOOKUP_SKILLS = frozenset(
    {
        "access-report",
        "discovered-apps",
        "grant-access",
        "list-access",
        "request-access",
        "request-revocation",
        "userlist-import-preflight",
        "vendor-update",
        "view-policies",
    }
)


@dataclass(frozen=True, order=True)
class Issue:
    code: str
    path: str
    line: int
    message: str

    def render(self) -> str:
        location = self.path if not self.line else "%s:%d" % (self.path, self.line)
        return "[%s] %s: %s" % (self.code, location, self.message)


@dataclass(frozen=True)
class ApiReference:
    method: str
    normalized_path: str
    query: Mapping[str, str]
    raw: str
    line: int


@dataclass(frozen=True)
class Frontmatter:
    name: str
    description: str


class DuplicateJsonKey(ValueError):
    pass


class UnsafeJsonNumber(ValueError):
    pass


def _issue(code: str, path: Path | str, message: str, line: int = 0) -> Issue:
    return Issue(code, str(path), line, message)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _casefold_duplicates(values: Iterable[str]) -> Set[str]:
    seen: Set[str] = set()
    duplicates: Set[str] = set()
    for value in values:
        folded = value.casefold()
        if folded in seen:
            duplicates.add(value)
        seen.add(folded)
    return duplicates


def secure_read_bytes(path: Path, relative: Path | str) -> Tuple[Optional[bytes], List[Issue]]:
    issues: List[Issue] = []
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(str(path), flags)
    except FileNotFoundError:
        return None, [_issue("FILE_MISSING", relative, "required file is missing")]
    except OSError as exc:
        return None, [_issue("FILE_UNSAFE", relative, "cannot safely open file: %s" % exc)]
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None, [_issue("FILE_NOT_REGULAR", relative, "must be a regular file")]
        if metadata.st_size > MAX_FILE_BYTES:
            return None, [
                _issue(
                    "FILE_TOO_LARGE",
                    relative,
                    "is %d bytes, limit is %d" % (metadata.st_size, MAX_FILE_BYTES),
                )
            ]
        chunks: List[bytes] = []
        total = 0
        while True:
            try:
                chunk = os.read(descriptor, min(65536, MAX_FILE_BYTES + 1 - total))
            except OSError as exc:
                return None, [_issue("FILE_UNSAFE", relative, "read failed: %s" % exc)]
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                return None, [
                    _issue("FILE_TOO_LARGE", relative, "grew beyond the 256 KiB limit while read")
                ]
        try:
            final_metadata = os.fstat(descriptor)
        except OSError as exc:
            return None, [_issue("FILE_UNSAFE", relative, "final stat failed: %s" % exc)]
        initial_fingerprint = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        final_fingerprint = (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mtime_ns,
            final_metadata.st_ctime_ns,
        )
        if initial_fingerprint != final_fingerprint or total != final_metadata.st_size:
            return None, [
                _issue("FILE_CHANGED", relative, "file changed while it was being read")
            ]
        return b"".join(chunks), issues
    finally:
        os.close(descriptor)


def _secure_read_bytes_at(
    directory_descriptor: int,
    name: str,
    relative: Path | str,
    expected: os.stat_result,
) -> Tuple[Optional[bytes], List[Issue]]:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    except OSError as exc:
        return None, [_issue("FILE_UNSAFE", relative, "cannot safely open file: %s" % exc)]
    try:
        metadata = os.fstat(descriptor)
        if not os.path.samestat(expected, metadata):
            return None, [
                _issue("FILE_CHANGED", relative, "file identity changed during validation")
            ]
        if not stat.S_ISREG(metadata.st_mode):
            return None, [_issue("FILE_NOT_REGULAR", relative, "must be a regular file")]
        if metadata.st_size > MAX_FILE_BYTES:
            return None, [
                _issue(
                    "FILE_TOO_LARGE",
                    relative,
                    "is %d bytes, limit is %d" % (metadata.st_size, MAX_FILE_BYTES),
                )
            ]
        chunks: List[bytes] = []
        total = 0
        while True:
            try:
                chunk = os.read(descriptor, min(65536, MAX_FILE_BYTES + 1 - total))
            except OSError as exc:
                return None, [_issue("FILE_UNSAFE", relative, "read failed: %s" % exc)]
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                return None, [
                    _issue("FILE_TOO_LARGE", relative, "grew beyond the 256 KiB limit while read")
                ]
        try:
            final_metadata = os.fstat(descriptor)
        except OSError as exc:
            return None, [_issue("FILE_UNSAFE", relative, "final stat failed: %s" % exc)]
        initial_fingerprint = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        final_fingerprint = (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mtime_ns,
            final_metadata.st_ctime_ns,
        )
        if initial_fingerprint != final_fingerprint or total != final_metadata.st_size:
            return None, [
                _issue("FILE_CHANGED", relative, "file changed while it was being read")
            ]
        return b"".join(chunks), []
    finally:
        os.close(descriptor)


def decode_strict_utf8(data: bytes, relative: Path | str) -> Tuple[Optional[str], List[Issue]]:
    issues: List[Issue] = []
    if data.startswith(codecs.BOM_UTF8):
        issues.append(_issue("UTF8_BOM", relative, "UTF-8 BOM is forbidden"))
    if b"\x00" in data:
        issues.append(_issue("NUL_BYTE", relative, "NUL byte is forbidden"))
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        issues.append(
            _issue("INVALID_UTF8", relative, "invalid UTF-8 at byte %d" % exc.start)
        )
        return None, issues
    for offset, character in enumerate(text):
        category = unicodedata.category(character)
        if (category == "Cc" and character not in "\t\n\r") or category == "Cf":
            issues.append(
                _issue(
                    "SOURCE_CONTROL_CHARACTER",
                    relative,
                    "source contains a forbidden control or formatting character",
                    _line_number(text, offset),
                )
            )
            break
    return text, issues


def read_text(path: Path, relative: Path | str) -> Tuple[Optional[str], List[Issue]]:
    data, issues = secure_read_bytes(path, relative)
    if data is None:
        return None, issues
    text, decode_issues = decode_strict_utf8(data, relative)
    return text, issues + decode_issues


def validate_repository_files(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    text_suffixes = frozenset({".md", ".json", ".py", ".yml", ".yaml"})
    entries_seen = 0
    regular_bytes_seen = 0
    stopped = False
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW

    try:
        root_descriptor = os.open(str(root), directory_flags)
    except OSError as exc:
        return [_issue("TREE_UNREADABLE", Path("."), str(exc))]

    def scan_directory(
        directory_descriptor: int, relative_directory: Path, depth: int
    ) -> None:
        nonlocal entries_seen, regular_bytes_seen, stopped
        entries: List[Tuple[str, os.stat_result]] = []
        try:
            with os.scandir(directory_descriptor) as iterator:
                for entry in iterator:
                    relative = relative_directory / entry.name
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        entries_seen += 1
                        issues.append(_issue("FILE_UNSAFE", relative, str(exc)))
                        if entries_seen > MAX_REPOSITORY_ENTRIES:
                            issues.append(
                                _issue(
                                    "TREE_ENTRY_LIMIT",
                                    relative,
                                    "repository exceeds %d entries"
                                    % MAX_REPOSITORY_ENTRIES,
                                )
                            )
                            stopped = True
                            return
                        continue
                    if (
                        depth == 0
                        and entry.name == ".git"
                        and stat.S_ISDIR(metadata.st_mode)
                    ):
                        continue
                    entries_seen += 1
                    if entries_seen > MAX_REPOSITORY_ENTRIES:
                        issues.append(
                            _issue(
                                "TREE_ENTRY_LIMIT",
                                relative,
                                "repository exceeds %d entries"
                                % MAX_REPOSITORY_ENTRIES,
                            )
                        )
                        stopped = True
                        return
                    entries.append((entry.name, metadata))
        except OSError as exc:
            issues.append(_issue("TREE_UNREADABLE", relative_directory, str(exc)))
            return
        entries.sort(key=lambda item: item[0])
        for name, metadata in entries:
            if stopped:
                return
            relative = relative_directory / name
            if stat.S_ISLNK(metadata.st_mode):
                issues.append(_issue("SYMLINK_FORBIDDEN", relative, "symlinks are forbidden"))
                continue
            if stat.S_ISDIR(metadata.st_mode):
                if depth >= MAX_TREE_DEPTH:
                    issues.append(
                        _issue(
                            "TREE_DEPTH_LIMIT",
                            relative,
                            "repository exceeds maximum depth %d" % MAX_TREE_DEPTH,
                        )
                    )
                else:
                    try:
                        child_descriptor = os.open(
                            name, directory_flags, dir_fd=directory_descriptor
                        )
                    except OSError as exc:
                        issues.append(_issue("FILE_UNSAFE", relative, str(exc)))
                        continue
                    try:
                        current = os.fstat(child_descriptor)
                        if not os.path.samestat(metadata, current):
                            issues.append(
                                _issue(
                                    "FILE_CHANGED",
                                    relative,
                                    "directory identity changed during validation",
                                )
                            )
                            continue
                        if not stat.S_ISDIR(current.st_mode):
                            issues.append(
                                _issue("FILE_NOT_REGULAR", relative, "directory changed type")
                            )
                            continue
                        scan_directory(child_descriptor, relative, depth + 1)
                    finally:
                        os.close(child_descriptor)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                issues.append(
                    _issue("FILE_NOT_REGULAR", relative, "special files are forbidden")
                )
                continue
            regular_bytes_seen += metadata.st_size
            if regular_bytes_seen > MAX_REPOSITORY_BYTES:
                issues.append(
                    _issue(
                        "REPOSITORY_BYTE_LIMIT",
                        relative,
                        "repository regular files exceed %d bytes"
                        % MAX_REPOSITORY_BYTES,
                    )
                )
                stopped = True
                return
            if metadata.st_size > MAX_FILE_BYTES:
                issues.append(
                    _issue(
                        "FILE_TOO_LARGE",
                        relative,
                        "is %d bytes, limit is %d" % (metadata.st_size, MAX_FILE_BYTES),
                    )
                )
                continue
            if relative.suffix.lower() not in text_suffixes:
                continue
            data, file_issues = _secure_read_bytes_at(
                directory_descriptor, name, relative, metadata
            )
            issues.extend(file_issues)
            if data is None:
                continue
            text, decode_issues = decode_strict_utf8(data, relative)
            issues.extend(decode_issues)
            if text is not None and "\u2014" in text:
                offset = text.index("\u2014")
                issues.append(
                    _issue(
                        "EM_DASH",
                        relative,
                        "U+2014 is forbidden; use punctuation that does not hide a clause boundary",
                        _line_number(text, offset),
                    )
                )

    try:
        scan_directory(root_descriptor, Path("."), 0)
    finally:
        os.close(root_descriptor)
    return issues


def validate_repository_inventory(root: Path) -> List[Issue]:
    actual: Set[Path] = set()
    entries_seen = 0
    try:
        for directory, directory_names, file_names in os.walk(root, followlinks=False):
            entries_seen += len(directory_names) + len(file_names)
            if entries_seen > MAX_REPOSITORY_ENTRIES:
                return [
                    _issue(
                        "TREE_ENTRY_LIMIT",
                        Path("."),
                        "repository inventory exceeds %d entries"
                        % MAX_REPOSITORY_ENTRIES,
                    )
                ]
            directory_path = Path(directory)
            if directory_path == root:
                directory_names[:] = [name for name in directory_names if name != ".git"]
            directory_names.sort()
            for file_name in sorted(file_names):
                actual.add((directory_path / file_name).relative_to(root))
    except OSError as exc:
        return [_issue("REPOSITORY_INVENTORY", Path("."), str(exc))]
    missing = sorted(ALLOWED_REPOSITORY_FILES - actual)
    extra = sorted(actual - ALLOWED_REPOSITORY_FILES)
    if not missing and not extra:
        return []
    missing_text = ", ".join(str(path) for path in missing[:10]) or "none"
    extra_text = ", ".join(str(path) for path in extra[:10]) or "none"
    return [
        _issue(
            "REPOSITORY_INVENTORY",
            Path("."),
            "repository file inventory differs; missing: %s; extra: %s"
            % (missing_text, extra_text),
        )
    ]


def validate_approved_content(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    for relative, expected_digest in APPROVED_CONTENT_SHA256.items():
        data, read_issues = secure_read_bytes(root / relative, relative)
        issues.extend(read_issues)
        if data is None:
            continue
        actual_digest = hashlib.sha256(data).hexdigest()
        if actual_digest != expected_digest:
            issues.append(
                _issue(
                    "CONTENT_DIGEST",
                    relative,
                    "reviewed instruction content changed; update semantics and its approved digest together",
                )
            )
    return issues


def validate_approved_harness(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    for relative, expected_digest in APPROVED_HARNESS_SHA256.items():
        data, read_issues = secure_read_bytes(root / relative, relative)
        issues.extend(read_issues)
        if data is None:
            continue
        actual_digest = hashlib.sha256(data).hexdigest()
        if actual_digest != expected_digest:
            issues.append(
                _issue(
                    "HARNESS_DIGEST",
                    relative,
                    "reviewed test harness changed; review its assertions and approved digest together",
                )
            )
    return issues


def parse_frontmatter(text: str, relative: Path | str) -> Tuple[Optional[Frontmatter], List[Issue]]:
    issues: List[Issue] = []
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None, [_issue("FRONTMATTER_OPEN", relative, "first line must be exactly ---", 1)]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None, [_issue("FRONTMATTER_CLOSE", relative, "closing --- is missing", 1)]
    header = lines[1:end]
    fields: Dict[str, str] = {}
    order: List[str] = []
    current_block: Optional[str] = None
    block_lines: List[str] = []

    def finish_block() -> None:
        nonlocal current_block, block_lines
        if current_block is not None:
            fields[current_block] = " ".join(part.strip() for part in block_lines).strip()
            current_block = None
            block_lines = []

    for index, line in enumerate(header, start=2):
        if "\t" in line:
            issues.append(_issue("FRONTMATTER_TAB", relative, "tabs are forbidden", index))
            continue
        if not line.strip():
            if current_block is not None:
                block_lines.append("")
            continue
        if line.startswith(" "):
            if current_block is None or len(line) - len(line.lstrip(" ")) < 2:
                issues.append(
                    _issue(
                        "FRONTMATTER_INDENT",
                        relative,
                        "continuation must belong to an indented description block",
                        index,
                    )
                )
            else:
                block_lines.append(line)
            continue
        finish_block()
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):(?:[ ]+(.*))?", line)
        if not match:
            issues.append(
                _issue("FRONTMATTER_SYNTAX", relative, "malformed top-level field", index)
            )
            continue
        key, value = match.group(1), (match.group(2) or "")
        if key not in {"name", "description"}:
            issues.append(
                _issue(
                    "FRONTMATTER_FIELD",
                    relative,
                    "only name and description are allowed, found %s" % key,
                    index,
                )
            )
            continue
        if key in fields or key in order:
            issues.append(
                _issue("FRONTMATTER_DUPLICATE", relative, "duplicate %s field" % key, index)
            )
            continue
        order.append(key)
        if value in {">", ">-", ">+", "|", "|-", "|+"}:
            if key != "description":
                issues.append(
                    _issue(
                        "FRONTMATTER_SCALAR",
                        relative,
                        "name must be a single-line scalar",
                        index,
                    )
                )
            current_block = key
        else:
            fields[key] = value.strip()
    finish_block()
    if order != ["name", "description"]:
        issues.append(
            _issue(
                "FRONTMATTER_FIELDS",
                relative,
                "frontmatter must contain exactly name then description",
                1,
            )
        )
    if not fields.get("name"):
        issues.append(_issue("FRONTMATTER_NAME", relative, "name must be nonempty", 2))
    if not fields.get("description"):
        issues.append(
            _issue("FRONTMATTER_DESCRIPTION", relative, "description must be nonempty", 3)
        )
    if end + 1 >= len(lines) or not any(line.strip() for line in lines[end + 1 :]):
        issues.append(_issue("SKILL_BODY", relative, "skill body must be nonempty", end + 1))
    if issues:
        return None, issues
    return Frontmatter(fields["name"], fields["description"]), []


def validate_skill_inventory(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    skill_root = root / SKILL_ROOT
    try:
        entries = list(skill_root.iterdir())
    except OSError as exc:
        return [_issue("SKILL_ROOT", SKILL_ROOT, "cannot list skill root: %s" % exc)]
    names = [entry.name for entry in entries if entry.is_dir() and not entry.is_symlink()]
    for duplicate in sorted(_casefold_duplicates(names)):
        issues.append(
            _issue("SKILL_CASEFOLD_DUPLICATE", SKILL_ROOT, "casefold collision: %s" % duplicate)
        )
    actual = set(names)
    expected = set(EXPECTED_SKILLS)
    for missing in sorted(expected - actual):
        issues.append(_issue("SKILL_MISSING", SKILL_ROOT / missing, "expected skill is missing"))
    for extra in sorted(actual - expected):
        issues.append(_issue("SKILL_UNEXPECTED", SKILL_ROOT / extra, "unexpected skill directory"))
    frontmatter_names: List[str] = []
    for name in sorted(actual & expected):
        relative = SKILL_ROOT / name / "SKILL.md"
        text, file_issues = read_text(root / relative, relative)
        issues.extend(file_issues)
        if text is None:
            continue
        frontmatter, parse_issues = parse_frontmatter(text, relative)
        issues.extend(parse_issues)
        if frontmatter is None:
            continue
        frontmatter_names.append(frontmatter.name)
        if frontmatter.name != name:
            issues.append(
                _issue(
                    "SKILL_NAME_MISMATCH",
                    relative,
                    "frontmatter name %r must equal directory %r" % (frontmatter.name, name),
                    2,
                )
            )
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", frontmatter.name):
            issues.append(
                _issue("SKILL_NAME_FORMAT", relative, "name must be a lowercase kebab-case slug", 2)
            )
    for duplicate in sorted(_casefold_duplicates(frontmatter_names)):
        issues.append(
            _issue(
                "FRONTMATTER_CASEFOLD_DUPLICATE",
                SKILL_ROOT,
                "casefold collision in frontmatter names: %s" % duplicate,
            )
        )
    return issues


def parse_json_strict(data: bytes, relative: Path | str) -> Tuple[Optional[object], List[Issue]]:
    text, issues = decode_strict_utf8(data, relative)
    if text is None:
        return None, issues

    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                issues.append(
                    _issue(
                        "JSON_NESTING",
                        relative,
                        "JSON nesting exceeds the safety limit of %d" % MAX_JSON_DEPTH,
                    )
                )
                return None, issues
        elif character in "]}":
            depth = max(0, depth - 1)

    def no_duplicates(pairs: Sequence[Tuple[str, object]]) -> Dict[str, object]:
        result: Dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateJsonKey(key)
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError("non-RFC JSON numeric constant %s" % value)

    def parse_integer(value: str) -> int:
        if len(value) > MAX_JSON_NUMBER_CHARS:
            raise UnsafeJsonNumber("JSON integer token exceeds %d characters" % MAX_JSON_NUMBER_CHARS)
        return int(value)

    def parse_decimal(value: str) -> float:
        if len(value) > MAX_JSON_NUMBER_CHARS:
            raise UnsafeJsonNumber("JSON decimal token exceeds %d characters" % MAX_JSON_NUMBER_CHARS)
        parsed = float(value)
        if not math.isfinite(parsed):
            raise UnsafeJsonNumber("JSON number overflows to a non-finite value")
        return parsed

    try:
        value = json.loads(
            text,
            object_pairs_hook=no_duplicates,
            parse_constant=reject_constant,
            parse_int=parse_integer,
            parse_float=parse_decimal,
        )
    except DuplicateJsonKey as exc:
        issues.append(
            _issue("JSON_DUPLICATE_KEY", relative, "duplicate JSON key %r" % str(exc))
        )
        return None, issues
    except json.JSONDecodeError as exc:
        issues.append(_issue("JSON_SYNTAX", relative, exc.msg, exc.lineno))
        return None, issues
    except RecursionError:
        issues.append(
            _issue(
                "JSON_NESTING",
                relative,
                "JSON nesting exceeded the parser's safe recursion depth",
            )
        )
        return None, issues
    except UnsafeJsonNumber as exc:
        issues.append(_issue("JSON_NUMBER", relative, str(exc)))
        return None, issues
    except ValueError as exc:
        issues.append(_issue("JSON_CONSTANT", relative, str(exc)))
        return None, issues

    def invalid_json_string_character(candidate: str) -> Optional[str]:
        for character in candidate:
            codepoint = ord(character)
            if (
                unicodedata.category(character) in {"Cc", "Cf", "Cs"}
                or 0xFDD0 <= codepoint <= 0xFDEF
                or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}
            ):
                return "U+%04X" % codepoint
        return None

    pending: List[object] = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, item in current.items():
                invalid = invalid_json_string_character(key)
                if invalid is not None:
                    issues.append(
                        _issue(
                            "JSON_STRING_CHARACTER",
                            relative,
                            "JSON object key contains forbidden character %s" % invalid,
                        )
                    )
                    return None, issues
                pending.append(item)
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, str):
            invalid = invalid_json_string_character(current)
            if invalid is not None:
                issues.append(
                    _issue(
                        "JSON_STRING_CHARACTER",
                        relative,
                        "JSON string contains forbidden character %s" % invalid,
                    )
                )
                return None, issues
    return value, issues


def _load_json_file(root: Path, relative: Path) -> Tuple[Optional[object], List[Issue]]:
    data, issues = secure_read_bytes(root / relative, relative)
    if data is None:
        return None, issues
    value, json_issues = parse_json_strict(data, relative)
    return value, issues + json_issues


def _readme_skill_names(text: str) -> List[str]:
    section_match = re.search(r"(?m)^## The skills\s*$", text)
    if not section_match:
        return []
    tail = text[section_match.end() :]
    next_heading = re.search(r"(?m)^## ", tail)
    section = tail[: next_heading.start()] if next_heading else tail
    return re.findall(r"(?m)^\|\s*`([^`]+)`\s*\|", section)


def validate_readme_repository_identity(text: str) -> List[Issue]:
    repository_references = re.findall(
        r"github\.com/[A-Za-z0-9_.-]+/claude-skills-for-customer",
        text,
        re.I,
    )
    if (
        EXPECTED_README_REPOSITORY not in text
        or not repository_references
        or any(reference != EXPECTED_README_REPOSITORY for reference in repository_references)
    ):
        return [
            _issue(
                "README_REPOSITORY",
                Path("README.md"),
                "installation source must use the canonical AccessOwl repository owner",
            )
        ]
    return []


def validate_readme_request_status(text: str) -> List[Issue]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    safe = (
        "returned workflow status" in normalized
        and "`pending_approval`" in normalized
        and bool(
            re.search(
                r"(?:only\s+`pending_approval`.{0,40}awaiting\s+approval|"
                r"awaiting\s+approval\s+only.{0,40}`pending_approval`)",
                normalized,
            )
        )
    )
    contradiction = bool(
        re.search(
            r"(?:every\s+access\s+request|access\s+requests?)\s+"
            r"(?:always\s+)?(?:goes?|go)\s+through.{0,40}approval",
            normalized,
        )
    )
    if safe and not contradiction:
        return []
    return [
        _issue(
            "README_REQUEST_STATUS",
            Path("README.md"),
            "only a returned pending_approval status may be described as awaiting approval",
        )
    ]


def validate_style_guide_text(text: str) -> List[Issue]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    issues: List[Issue] = []
    completion_safe = (
        "never claim access was granted, revoked, or completed from submission or response status alone"
        in normalized
        and "only after the skill's required state verification succeeds" in normalized
    )
    completion_contradiction = bool(
        re.search(
            r"(?:always|may|can|should).{0,40}claim.{0,50}"
            r"(?:access\s+)?(?:granted|revoked|completed).{0,60}"
            r"(?:any\s+201|201\s+response|submission|response\s+status)",
            normalized,
        )
        or re.search(
            r"(?:any\s+201|201\s+response|submission|response\s+status)"
            r".{0,60}(?:proves?|means?|counts?\s+as).{0,40}"
            r"(?:granted|revoked|completed|success)",
            normalized,
        )
    )
    if not completion_safe or completion_contradiction:
        issues.append(
            _issue(
                "STYLE_VERIFIED_COMPLETION",
                Path("SKILL_STYLE.md"),
                "completion claims require the skill's state verification, never submission or status alone",
            )
        )
    request_status_safe = all(
        term in normalized
        for term in (
            "only `pending_approval` can be described as awaiting approval",
            "for every other status",
            "do not claim that approval did or did not happen",
            'say "after approval" only when the returned status is `pending_approval`',
        )
    )
    product_provenance_safe = all(
        term in normalized
        for term in (
            "accessowl product behavior encoded by the skills",
            "not semantics supplied by the openapi enum description",
            "never describe them as openapi-verified behavior",
        )
    )
    product_provenance_contradiction = bool(
        re.search(
            r"(?:provisioning_type|next-step meanings).{0,80}"
            r"(?:verified|defined|guaranteed).{0,40}openapi",
            normalized,
        )
        or re.search(
            r"openapi.{0,40}(?:verifies|defines|guarantees).{0,80}"
            r"(?:provisioning_type|next-step meanings)",
            normalized,
        )
    )
    if not product_provenance_safe or product_provenance_contradiction:
        issues.append(
            _issue(
                "STYLE_PRODUCT_PROVENANCE",
                Path("SKILL_STYLE.md"),
                "product behavior beyond an OpenAPI enum must be labeled as non-OpenAPI provenance",
            )
        )
    request_status_contradiction = bool(
        re.search(
            r"(?:every\s+access\s+request|access\s+requests?)\s+"
            r"(?:always\s+)?(?:goes?|go)\s+through.{0,40}approval",
            normalized,
        )
        or re.search(
            r"`automatic`.{0,100}automatically\s+after\s+approval(?!.{0,80}only\s+when)",
            normalized,
        )
    )
    if not request_status_safe or request_status_contradiction:
        issues.append(
            _issue(
                "STYLE_REQUEST_STATUS",
                Path("SKILL_STYLE.md"),
                "only pending_approval may be described as awaiting approval",
            )
        )
    error_safe = all(
        term in normalized
        for term in (
            "on `422`",
            "openapi error fields are free-form",
            "do not define a mandatory-resource code",
            "never infer a mandatory resource",
            "synthesize a changed request body from error text",
            "user-specified correction starts a new workflow",
            "fresh reads, confirmation, and idempotency key",
        )
    )
    error_contradiction = bool(
        re.search(
            r"(?:422|validation\s+(?:error|response)).{0,100}"
            r"(?:lists?|identifies?|provides?|surfaces?).{0,50}"
            r"(?:mandatory|required).{0,30}(?:resource|permission|option)",
            normalized,
        )
    )
    if not error_safe or error_contradiction:
        issues.append(
            _issue(
                "STYLE_422_FAIL_CLOSED",
                Path("SKILL_STYLE.md"),
                "422 error fields are free-form and must not supply inferred request options",
            )
        )
    return issues


def validate_style_guide(root: Path) -> List[Issue]:
    text, issues = read_text(root / "SKILL_STYLE.md", Path("SKILL_STYLE.md"))
    if text is None:
        return issues
    return issues + validate_style_guide_text(text)


def validate_manifest_values(marketplace: object, plugin: object) -> List[Issue]:
    issues: List[Issue] = []
    if not isinstance(marketplace, dict):
        issues.append(
            _issue("MARKETPLACE_ROOT_TYPE", MARKETPLACE_PATH, "manifest root must be an object")
        )
    if not isinstance(plugin, dict):
        issues.append(
            _issue("PLUGIN_ROOT_TYPE", PLUGIN_MANIFEST_PATH, "manifest root must be an object")
        )
    if isinstance(marketplace, dict):
        expected_marketplace_fields = {"name", "description", "owner", "plugins"}
        if set(marketplace) != expected_marketplace_fields:
            issues.append(
                _issue(
                    "MARKETPLACE_FIELDS",
                    MARKETPLACE_PATH,
                    "top-level keys must be exactly %s"
                    % ", ".join(sorted(expected_marketplace_fields)),
                )
            )
        owner = marketplace.get("owner")
        if not (
            isinstance(owner, dict)
            and set(owner) == {"name", "url"}
            and owner.get("name") == "AccessOwl"
            and owner.get("url") == "https://github.com/AccessOwl"
        ):
            issues.append(
                _issue(
                    "MARKETPLACE_OWNER",
                    MARKETPLACE_PATH,
                    "owner must be the exact AccessOwl name and GitHub URL object",
                )
            )
        if not isinstance(marketplace.get("description"), str) or not marketplace[
            "description"
        ].strip():
            issues.append(
                _issue(
                    "MARKETPLACE_DESCRIPTION",
                    MARKETPLACE_PATH,
                    "description must be a nonempty string",
                )
            )
        marketplace_name = marketplace.get("name")
        if not isinstance(marketplace_name, str) or not marketplace_name.strip():
            issues.append(
                _issue("MARKETPLACE_NAME", MARKETPLACE_PATH, "name must be a nonempty string")
            )
        elif marketplace_name != EXPECTED_MARKETPLACE_NAME:
            issues.append(
                _issue(
                    "MARKETPLACE_IDENTITY",
                    MARKETPLACE_PATH,
                    "name must be exactly %s" % EXPECTED_MARKETPLACE_NAME,
                )
            )
        plugin_entries = marketplace.get("plugins")
        if not isinstance(plugin_entries, list) or len(plugin_entries) != 1:
            issues.append(
                _issue(
                    "MARKETPLACE_PLUGIN_COUNT",
                    MARKETPLACE_PATH,
                    "marketplace must contain exactly one plugin",
                )
            )
        elif not isinstance(plugin_entries[0], dict):
            issues.append(
                _issue("MARKETPLACE_PLUGIN_TYPE", MARKETPLACE_PATH, "plugin entry must be an object")
            )
        else:
            entry = plugin_entries[0]
            expected_entry_fields = {"name", "description", "version", "source"}
            if set(entry) != expected_entry_fields:
                issues.append(
                    _issue(
                        "MARKETPLACE_PLUGIN_FIELDS",
                        MARKETPLACE_PATH,
                        "plugin entry keys must be exactly %s"
                        % ", ".join(sorted(expected_entry_fields)),
                    )
                )
            for field in ("name", "description", "version", "source"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    issues.append(
                        _issue(
                            "MARKETPLACE_PLUGIN_FIELD",
                            MARKETPLACE_PATH,
                            "%s must be a nonempty string" % field,
                        )
                    )
            if entry.get("name") != EXPECTED_PLUGIN_NAME:
                issues.append(
                    _issue(
                        "PLUGIN_IDENTITY",
                        MARKETPLACE_PATH,
                        "marketplace plugin name must be exactly %s" % EXPECTED_PLUGIN_NAME,
                    )
                )
            if entry.get("source") != EXPECTED_PLUGIN_SOURCE:
                issues.append(
                    _issue(
                        "MANIFEST_SOURCE",
                        MARKETPLACE_PATH,
                        "plugin source must be exactly %s" % EXPECTED_PLUGIN_SOURCE,
                    )
                )
            version = entry.get("version")
            if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
                issues.append(
                    _issue(
                        "MANIFEST_VERSION",
                        MARKETPLACE_PATH,
                        "version must be strict semantic versioning without numeric leading zeros",
                    )
                )
    if isinstance(plugin, dict):
        expected_plugin_fields = {
            "name",
            "displayName",
            "description",
            "version",
            "author",
            "homepage",
            "repository",
        }
        if set(plugin) != expected_plugin_fields:
            issues.append(
                _issue(
                    "PLUGIN_FIELDS",
                    PLUGIN_MANIFEST_PATH,
                    "plugin keys must be exactly %s"
                    % ", ".join(sorted(expected_plugin_fields)),
                )
            )
        author = plugin.get("author")
        if not (
            isinstance(author, dict)
            and set(author) == {"name", "url"}
            and author.get("name") == "AccessOwl"
            and author.get("url") == "https://github.com/AccessOwl"
        ):
            issues.append(
                _issue(
                    "PLUGIN_AUTHOR",
                    PLUGIN_MANIFEST_PATH,
                    "author must be the exact AccessOwl name and GitHub URL object",
                )
            )
        for field in ("name", "displayName", "description", "version"):
            if not isinstance(plugin.get(field), str) or not plugin[field].strip():
                issues.append(
                    _issue(
                        "PLUGIN_REQUIRED_FIELD",
                        PLUGIN_MANIFEST_PATH,
                        "%s must be a nonempty string" % field,
                    )
                )
        if plugin.get("name") != EXPECTED_PLUGIN_NAME:
            issues.append(
                _issue(
                    "PLUGIN_IDENTITY",
                    PLUGIN_MANIFEST_PATH,
                    "name must be exactly %s" % EXPECTED_PLUGIN_NAME,
                )
            )
        version = plugin.get("version")
        if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
            issues.append(
                _issue(
                    "MANIFEST_VERSION",
                    PLUGIN_MANIFEST_PATH,
                    "version must be strict semantic versioning without numeric leading zeros",
                )
            )
        if plugin.get("homepage") != EXPECTED_PLUGIN_HOMEPAGE:
            issues.append(
                _issue(
                    "PLUGIN_HOMEPAGE",
                    PLUGIN_MANIFEST_PATH,
                    "homepage must be exactly %s" % EXPECTED_PLUGIN_HOMEPAGE,
                )
            )
        if plugin.get("repository") != EXPECTED_PLUGIN_REPOSITORY:
            issues.append(
                _issue(
                    "PLUGIN_REPOSITORY",
                    PLUGIN_MANIFEST_PATH,
                    "repository must be exactly %s" % EXPECTED_PLUGIN_REPOSITORY,
                )
            )
    if isinstance(marketplace, dict) and isinstance(plugin, dict):
        plugin_entries = marketplace.get("plugins")
        if isinstance(plugin_entries, list) and len(plugin_entries) == 1 and isinstance(plugin_entries[0], dict):
            entry = plugin_entries[0]
            expected_pairs = (
                ("name", entry.get("name"), plugin.get("name")),
                ("version", entry.get("version"), plugin.get("version")),
            )
            for field, left, right in expected_pairs:
                if left != right:
                    issues.append(
                        _issue(
                            "MANIFEST_MISMATCH",
                            MARKETPLACE_PATH,
                            "%s differs between marketplace and plugin manifest" % field,
                        )
                    )
    return issues


def validate_manifests_and_readme(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    marketplace, marketplace_issues = _load_json_file(root, MARKETPLACE_PATH)
    plugin, plugin_issues = _load_json_file(root, PLUGIN_MANIFEST_PATH)
    issues.extend(marketplace_issues)
    issues.extend(plugin_issues)
    if marketplace is not None or not marketplace_issues:
        issues.extend(validate_manifest_values(marketplace, plugin))
    readme, readme_issues = read_text(root / "README.md", Path("README.md"))
    issues.extend(readme_issues)
    if readme is not None:
        issues.extend(validate_readme_repository_identity(readme))
        issues.extend(validate_readme_request_status(readme))
        names = _readme_skill_names(readme)
        if not names:
            issues.append(
                _issue("README_INVENTORY", "README.md", "The skills table is missing or empty")
            )
        for duplicate in sorted(_casefold_duplicates(names)):
            issues.append(
                _issue("README_CASEFOLD_DUPLICATE", "README.md", "casefold collision: %s" % duplicate)
            )
        actual = set(names)
        expected = set(EXPECTED_SKILLS)
        if actual != expected:
            missing = ", ".join(sorted(expected - actual)) or "none"
            extra = ", ".join(sorted(actual - expected)) or "none"
            issues.append(
                _issue(
                    "README_INVENTORY",
                    "README.md",
                    "inventory mismatch, missing: %s; extra: %s" % (missing, extra),
                )
            )
        folded = readme.casefold()
        if not re.search(r"email.{0,100}(?:only.{0,40}(?:ambigu|disambigu|distinguish)|(?:ambigu|disambigu|distinguish).{0,40}only)", folded, re.S):
            issues.append(
                _issue(
                    "README_EMAIL_DISAMBIGUATION",
                    "README.md",
                    "email must be used only when needed to disambiguate a person",
                )
            )
        if not (
            "access request" in folded
            and "revocation" in folded
            and "removal" in folded
            and re.search(r"vendor.{0,120}direct|direct.{0,120}vendor", folded, re.S)
            and "policy" in folded
            and ("unprotected" in folded or "refus" in folded)
        ):
            issues.append(
                _issue(
                    "README_WRITE_BEHAVIOR",
                    "README.md",
                    "README must distinguish access and revocation requests, direct vendor updates, and refused policy API writes",
                )
            )
        if not (
            re.search(r"structure.{0,180}(?:no usable|missing|unavailable|absent).{0,80}(?:version|lock_version)|structure.{0,180}(?:version|lock_version).{0,80}(?:no usable|missing|unavailable|absent)", folded, re.S)
            and "policy" in folded
            and ("full-set replacement" in folded or "complete-set replacement" in folded)
            and ("unprotected" in folded or "unsafe" in folded or "refus" in folded)
        ):
            issues.append(
                _issue(
                    "README_CAS_LIMITS",
                    "README.md",
                    "README must distinguish the structure version-token limit from unsafe full-set policy replacement",
                )
            )
    return issues


_API_REFERENCE_RE = re.compile(
    r"`(GET|POST|PUT|PATCH|DELETE)\s+([^`]+)`", re.IGNORECASE
)
_ANY_API_REFERENCE_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`]+)", re.IGNORECASE
)
_FORBIDDEN_GRANT_RE = re.compile(
    r"\bPOST\s+(?:/api/v1)?/access_requests/[^/\s`]+/grant\b",
    re.IGNORECASE,
)
_FORBIDDEN_GRANT_PATH_RE = re.compile(
    r"(?:/api/v1)?/access_requests/(?:\{[^{}\s/]+\}|<[^<>\s/]+>|[^/\s`]+)/grant",
    re.IGNORECASE,
)


def normalize_api_path(path: str) -> str:
    if path.startswith("/api/v1"):
        path = path[len("/api/v1") :] or "/"
    path = re.sub(r"\{[^{}\/]+\}|<[^<>\/]+>", "{}", path)
    return path


def _safe_urlsplit(target: str) -> Optional[SplitResult]:
    try:
        return urlsplit(target)
    except ValueError:
        return None


def _query_value_is_encoded(raw_value: str, key: str) -> bool:
    if re.fullmatch(r"<[^<>/]+>", raw_value):
        return True
    allowed_literals = r"[A-Za-z0-9._~-]"
    if key == "expand":
        allowed_literals = r"[A-Za-z0-9._~,-]"
    position = 0
    while position < len(raw_value):
        character = raw_value[position]
        if re.fullmatch(allowed_literals, character):
            position += 1
            continue
        if character == "%" and re.fullmatch(
            r"[0-9A-Fa-f]{2}", raw_value[position + 1 : position + 3]
        ):
            position += 3
            continue
        return False
    return True


def _strict_unquote(value: str) -> Optional[str]:
    try:
        return unquote_to_bytes(value).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None


def extract_api_references(text: str) -> List[ApiReference]:
    references: List[ApiReference] = []
    for match in _API_REFERENCE_RE.finditer(text):
        method, target = match.group(1).upper(), match.group(2).strip()
        parts = _safe_urlsplit(target)
        if parts is None:
            continue
        query: Dict[str, str] = {}
        if parts.query:
            for component in parts.query.split("&"):
                if "=" in component:
                    raw_key, raw_value = component.split("=", 1)
                else:
                    raw_key, raw_value = component, ""
                key = _strict_unquote(raw_key)
                value = _strict_unquote(raw_value)
                if key is not None and value is not None:
                    query[key] = value
        references.append(
            ApiReference(
                method=method,
                normalized_path=normalize_api_path(parts.path),
                query=query,
                raw=target,
                line=_line_number(text, match.start()),
            )
        )
    return references


def _reference_set(references: Iterable[ApiReference]) -> Set[Tuple[str, str]]:
    return {(reference.method, reference.normalized_path) for reference in references}


def _operation_has_affirmative_reference(
    text: str, operation: Tuple[str, str]
) -> bool:
    negative_intent = re.compile(
        r"\b(?:never|skip|omit|ignore|exclude|disable|suppress|bypass|avoid|"
        r"forbid|leave\s+out|without|refuse(?:\s+to)?|do\s+not|don't|"
        r"must\s+not|should\s+not|cannot|can't)\b"
    )
    affirmative_intent = re.compile(
        r"\b(?:list|fetch|re-?fetch|resolve|find|look\s+up|check|query|use|"
        r"send|create|submit|patch|retrieve|read|load|request|paginate|match|"
        r"identify|process|compare)\b"
    )
    for match in _API_REFERENCE_RE.finditer(text):
        parts = _safe_urlsplit(match.group(2).strip())
        if parts is None:
            continue
        candidate = (match.group(1).upper(), normalize_api_path(parts.path))
        if candidate != operation:
            continue
        sentence_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind(";", 0, match.start()),
        ) + 1
        sentence_ends = [
            position
            for position in (
                text.find(".", match.end()),
                text.find("!", match.end()),
                text.find("?", match.end()),
                text.find(";", match.end()),
            )
            if position >= 0
        ]
        sentence_end = min(sentence_ends) if sentence_ends else len(text)
        sentence = text[sentence_start:sentence_end].casefold()
        endpoint_directive = bool(
            re.match(
                r"\s*(?:[-*]\s*)?(?:[^.!?;]{0,80}:\s*)?"
                r"`(?:get|post|put|patch|delete)\s+",
                sentence,
            )
        )
        double_negative_omission = bool(
            re.search(
                r"\b(?:never|do\s+not|don't|must\s+not|should\s+not|"
                r"cannot|can't)\s+(?:skip|omit|ignore|exclude|disable|"
                r"suppress|bypass|avoid|leave\s+out)\b",
                sentence,
            )
        )
        if (
            (not negative_intent.search(sentence) or double_negative_omission)
            and (
                endpoint_directive
                or affirmative_intent.search(sentence)
                or double_negative_omission
            )
        ):
            return True
    return False


def _operation_has_negated_action_reference(
    text: str, operation: Tuple[str, str]
) -> bool:
    action = (
        r"(?:call|list|fetch|re-?fetch|resolve|find|look\s+up|check|query|use|"
        r"send|create|submit|patch|retrieve|read|load|request|paginate|match|"
        r"identify|process|compare)"
    )
    for match in _API_REFERENCE_RE.finditer(text):
        parts = _safe_urlsplit(match.group(2).strip())
        if parts is None:
            continue
        candidate = (match.group(1).upper(), normalize_api_path(parts.path))
        if candidate != operation:
            continue
        sentence_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind(";", 0, match.start()),
        ) + 1
        sentence_ends = [
            position
            for position in (
                text.find(".", match.end()),
                text.find("!", match.end()),
                text.find("?", match.end()),
                text.find(";", match.end()),
            )
            if position >= 0
        ]
        sentence_end = min(sentence_ends) if sentence_ends else len(text)
        sentence = text[sentence_start:sentence_end].casefold()
        local_start = match.start() - sentence_start
        local_end = match.end() - sentence_start
        prefix = sentence[max(0, local_start - 140) : local_start]
        suffix = sentence[local_end : local_end + 100]
        double_negative_omission = re.search(
            r"\b(?:never|do\s+not|don't|must\s+not|should\s+not|"
            r"cannot|can't)\s+(?:skip|omit|ignore|exclude|disable|"
            r"suppress|bypass|avoid|leave\s+out)\b.{0,100}$",
            prefix,
        )
        if double_negative_omission:
            continue
        if (
            re.search(
                r"\b(?:never|do\s+not|don't|must\s+not|should\s+not|"
                r"cannot|can't|refuse\s+to)\s+" + action + r"\b.{0,100}$",
                prefix,
            )
            or re.search(
                r"\b(?:skip|omit|ignore|exclude|disable|suppress|bypass|"
                r"avoid|leave\s+out|without)\b.{0,100}$",
                prefix,
            )
            or re.search(
                r"^.{0,60}\b(?:must\s+not|should\s+not|cannot|can't)\s+"
                r"(?:be\s+)?(?:called|used|fetched|queried|sent)",
                suffix,
            )
        ):
            return True
    return False


def validate_api_reference_text(
    text: str, relative: Path | str, allow_grant: bool = False
) -> List[Issue]:
    issues: List[Issue] = []
    if not allow_grant and _FORBIDDEN_GRANT_RE.search(text):
        match = _FORBIDDEN_GRANT_RE.search(text)
        assert match is not None
        issues.append(
            _issue(
                "GRANT_ENDPOINT_FORBIDDEN",
                relative,
                "customer skills must never call the grant endpoint",
                _line_number(text, match.start()),
            )
        )
    for match in _FORBIDDEN_GRANT_PATH_RE.finditer(text):
        if allow_grant:
            break
        window = text[max(0, match.start() - 120) : min(len(text), match.end() + 120)]
        if re.search(r"\bPOST\b", window, re.I):
            issues.append(
                _issue(
                    "GRANT_ENDPOINT_FORBIDDEN",
                    relative,
                    "customer skills must never call the grant endpoint",
                    _line_number(text, match.start()),
                )
            )
    for broad_match in _ANY_API_REFERENCE_RE.finditer(text):
        before = text[broad_match.start() - 1 : broad_match.start()]
        after = text[broad_match.end() : broad_match.end() + 1]
        if before != "`" or after != "`":
            issues.append(
                _issue(
                    "API_REFERENCE_NOT_CODE",
                    relative,
                    "HTTP method/path references must be fully enclosed in one code span",
                    _line_number(text, broad_match.start()),
                )
            )
    for match in _API_REFERENCE_RE.finditer(text):
        raw_method, target = match.group(1), match.group(2).strip()
        method = raw_method.upper()
        parts = _safe_urlsplit(target)
        if parts is None:
            issues.append(
                _issue(
                    "API_URL_SYNTAX",
                    relative,
                    "malformed URL syntax in API reference",
                    _line_number(text, match.start()),
                )
            )
            continue
        normalized = normalize_api_path(parts.path)
        line = _line_number(text, match.start())
        operation = (method, normalized)
        if raw_method != method:
            issues.append(
                _issue(
                    "API_METHOD_CASE",
                    relative,
                    "HTTP methods must use canonical uppercase spelling",
                    line,
                )
            )
        if parts.scheme or parts.netloc or not target.startswith("/"):
            issues.append(
                _issue(
                    "API_ABSOLUTE_URL",
                    relative,
                    "operation references must use relative AccessOwl API paths",
                    line,
                )
            )
        if parts.fragment:
            issues.append(
                _issue("API_FRAGMENT", relative, "URL fragments are forbidden in API calls", line)
            )
        if operation not in API_OPERATIONS:
            issues.append(
                _issue(
                    "API_OPERATION",
                    relative,
                    "unknown live API operation %s %s" % operation,
                    line,
                )
            )
            continue
        allowed = API_OPERATIONS[operation]
        seen: Set[str] = set()
        if parts.query:
            for component in parts.query.split("&"):
                if not component or "=" not in component:
                    issues.append(
                        _issue("API_QUERY_SYNTAX", relative, "query terms must use key=value", line)
                    )
                    continue
                raw_key, raw_value = component.split("=", 1)
                key = _strict_unquote(raw_key)
                value = _strict_unquote(raw_value)
                if key is None or value is None:
                    issues.append(
                        _issue(
                            "API_QUERY_UTF8",
                            relative,
                            "percent-encoded query keys and values must decode as strict UTF-8",
                            line,
                        )
                    )
                    continue
                if not raw_key or not key:
                    issues.append(
                        _issue("API_QUERY_EMPTY_KEY", relative, "query parameter key is empty", line)
                    )
                if re.search(r"%(?![0-9A-Fa-f]{2})", raw_key + raw_value):
                    issues.append(
                        _issue("API_PERCENT_ESCAPE", relative, "malformed percent escape", line)
                    )
                if raw_value == "":
                    issues.append(
                        _issue(
                            "API_QUERY_EMPTY_VALUE",
                            relative,
                            "%s requires a nonempty documented value" % (key or "query parameter"),
                            line,
                        )
                    )
                if key in seen:
                    issues.append(
                        _issue("API_QUERY_DUPLICATE", relative, "duplicate query key %s" % key, line)
                    )
                seen.add(key)
                if key not in allowed:
                    issues.append(
                        _issue(
                            "API_QUERY_PARAMETER",
                            relative,
                            "%s is not allowed on %s %s" % (key, method, normalized),
                            line,
                        )
                    )
                if (
                    any(ord(character) < 32 for character in raw_value)
                    or any(ord(character) < 32 for character in value)
                    or any(ord(character) > 127 for character in raw_value)
                    or "+" in raw_value
                    or " " in raw_value
                    or " " in value and "%20" not in raw_value.casefold()
                    or not _query_value_is_encoded(raw_value, key)
                ):
                    issues.append(
                        _issue("API_QUERY_ENCODING", relative, "query values must be encoded", line)
                    )
                if key == "limit" and value and not re.fullmatch(r"(?:[1-9]|[1-9][0-9]|100)", value):
                    issues.append(
                        _issue("API_LIMIT", relative, "limit must be an integer from 1 through 100", line)
                    )
                if key == "status" and value and not value.startswith("<") and value not in USER_STATUSES:
                    issues.append(
                        _issue("API_STATUS", relative, "unknown user status %s" % value, line)
                    )
                if key == "expand" and value:
                    expanded = set(value.split(","))
                    unknown = expanded - EXPAND_VALUES
                    if unknown:
                        issues.append(
                            _issue(
                                "API_EXPAND",
                                relative,
                                "unknown expansions: %s" % ", ".join(sorted(unknown)),
                                line,
                            )
                        )
    return issues


def _skill_documents(
    root: Path,
) -> Iterable[Tuple[str, Path, Optional[str], List[Issue]]]:
    for skill in EXPECTED_SKILLS:
        relative = SKILL_ROOT / skill / "SKILL.md"
        text, issues = read_text(root / relative, relative)
        yield skill, relative, text, issues


def validate_api_contract_text(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    issues: List[Issue] = []
    issues.extend(
        validate_api_reference_text(
            text, relative, allow_grant=skill == "grant-access"
        )
    )
    references = extract_api_references(text)
    operations = _reference_set(references)
    issues.extend(validate_skill_operation_scope(skill, text, relative))
    required_operations = REQUIRED_OPERATIONS[skill]
    for missing in sorted(required_operations - operations):
        issues.append(
            _issue(
                "API_REQUIRED_OPERATION",
                relative,
                "required operation is not documented: %s %s" % missing,
            )
        )
    for operation in sorted(required_operations & operations):
        if not _operation_has_affirmative_reference(
            text, operation
        ) or _operation_has_negated_action_reference(text, operation):
            issues.append(
                _issue(
                    "API_REQUIRED_OPERATION_CONTEXT",
                    relative,
                    "required operation is documented only in negative context: %s %s"
                    % operation,
                )
            )
    if skill != "grant-access" and ("POST", "/access_requests/{}/grant") in operations:
        issues.append(
            _issue(
                "GRANT_ENDPOINT_FORBIDDEN",
                relative,
                "customer skills must never call the grant endpoint",
            )
        )
    if skill in STATUS_ALL_SKILLS:
        user_references = [
            reference
            for reference in references
            if (reference.method, reference.normalized_path) == ("GET", "/users")
        ]
        if not user_references:
            issues.append(
                _issue(
                    "USERS_STATUS_ALL",
                    relative,
                    "user lookup must explicitly use GET /users?status=all",
                )
            )
        for reference in user_references:
            if reference.query.get("status") != "all":
                issues.append(
                    _issue(
                        "USERS_STATUS_ALL",
                        relative,
                        "every user lookup must explicitly use status=all",
                        reference.line,
                    )
                )
    required_expansions = EXPANSION_REQUIREMENTS.get(skill)
    if required_expansions:
        candidates = [
            reference
            for reference in references
            if (reference.method, reference.normalized_path) == ("GET", "/access_states")
        ]
        if not candidates:
            issues.append(
                _issue(
                    "ACCESS_STATE_EXPANSIONS",
                    relative,
                    "access_states must expand %s"
                    % ",".join(sorted(required_expansions)),
                )
            )
        for reference in candidates:
            expanded = set(filter(None, reference.query.get("expand", "").split(",")))
            if not required_expansions <= expanded:
                issues.append(
                    _issue(
                        "ACCESS_STATE_EXPANSIONS",
                        relative,
                        "every access_states lookup must expand %s"
                        % ",".join(sorted(required_expansions)),
                        reference.line,
                    )
                )
    for reference in references:
        if (
            reference.method == "GET"
            and reference.normalized_path in CURSOR_ENDPOINTS
            and reference.query.get("limit") != "100"
        ):
            issues.append(
                _issue(
                    "API_CURSOR_LIMIT_PER_CALL",
                    relative,
                    "every cursor endpoint reference must request limit=100",
                    reference.line,
                )
            )
    return issues


def validate_api_contracts(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    for skill, relative, text, read_issues in _skill_documents(root):
        issues.extend(read_issues)
        if text is None:
            continue
        issues.extend(validate_api_contract_text(skill, text, relative))
    return issues


def validate_skill_operation_scope(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    operations = _reference_set(extract_api_references(text))
    issues = [
        _issue(
            "SKILL_OPERATION_SCOPE",
            relative,
            "%s must not document or call %s %s" % (skill, method, path),
        )
        for method, path in sorted(operations - ALLOWED_OPERATIONS[skill])
    ]
    refused = REFUSED_OPERATIONS.get(skill)
    if refused is not None:
        refusal_terms = ("do not call", "never call", "must not call", "refuse")
        for paragraph in _paragraphs(text):
            if not _has_operation_in_paragraph(paragraph, refused):
                continue
            folded = paragraph.casefold()
            if not any(term in folded for term in refusal_terms):
                issues.append(
                    _issue(
                        "REFUSED_OPERATION_CONTEXT",
                        relative,
                        "%s %s may appear only in an explicit refusal"
                        % refused,
                    )
                )
            for match in _API_REFERENCE_RE.finditer(paragraph):
                parts = _safe_urlsplit(match.group(2).strip())
                if parts is None:
                    continue
                operation = (match.group(1).upper(), normalize_api_path(parts.path))
                if operation != refused:
                    continue
                sentence_start = max(
                    paragraph.rfind(".", 0, match.start()),
                    paragraph.rfind("!", 0, match.start()),
                    paragraph.rfind("?", 0, match.start()),
                    paragraph.rfind(";", 0, match.start()),
                ) + 1
                sentence_ends = [
                    position
                    for position in (
                        paragraph.find(".", match.end()),
                        paragraph.find("!", match.end()),
                        paragraph.find("?", match.end()),
                        paragraph.find(";", match.end()),
                    )
                    if position >= 0
                ]
                sentence_end = min(sentence_ends) if sentence_ends else len(paragraph)
                sentence = paragraph[sentence_start:sentence_end].casefold()
                action_verb = re.compile(
                    r"\b(?:call|invoke|execute|send|submit|write|update|apply|use|run|issue|perform)\b"
                )
                for verb in action_verb.finditer(sentence):
                    prefix = sentence[max(0, verb.start() - 24) : verb.start()]
                    if re.search(r"(?:do not|never|must not|cannot|refuse to)\s+$", prefix):
                        continue
                    issues.append(
                        _issue(
                            "REFUSED_OPERATION_CONTEXT",
                            relative,
                            "%s %s must never be presented as an action to execute"
                            % refused,
                        )
                    )
                    break
    return issues


def _paragraphs(text: str) -> List[str]:
    return [paragraph for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]


def _paragraph_with(text: str, *needles: str) -> bool:
    folded_needles = tuple(needle.casefold() for needle in needles)
    return any(
        all(needle in paragraph.casefold() for needle in folded_needles)
        for paragraph in _paragraphs(text)
    )


def _allows_numeric_value_over_cap(
    text: str, cap: int, unit_pattern: str, context_pattern: str
) -> bool:
    positive = re.compile(
        r"\b(?:allow|permit|accept|use|set|follow|continue|process|fetch|support|handle)\b"
    )
    negative_near_value = re.compile(
        r"(?:reject|refuse|stop|fail|forbid|never|must\s+not|do\s+not|"
        r"at\s+most|no\s+more\s+than|maximum(?:\s+of)?|cap(?:ped)?\s+at)"
        r".{0,40}$"
    )
    value_pattern = re.compile(
        r"(?<![0-9A-Za-z_])([0-9][0-9,]*)\s*(?:-\s*)?" + unit_pattern
    )
    for sentence in (
        re.sub(r"\s+", " ", value).strip()
        for value in re.split(r"[.!?]+", text.casefold())
        if value.strip()
    ):
        if not re.search(context_pattern, sentence):
            continue
        for match in value_pattern.finditer(sentence):
            try:
                value = int(match.group(1).replace(",", ""))
            except ValueError:
                continue
            if value <= cap:
                continue
            prefix = sentence[max(0, match.start() - 100) : match.start()]
            suffix = sentence[match.end() : match.end() + 100]
            positive_after = bool(
                re.search(
                    r"^.{0,60}\b(?:acceptable|allowed|permitted|valid|supported)\b",
                    suffix,
                )
                and not re.search(
                    r"^.{0,60}\b(?:not|never)\b.{0,20}"
                    r"(?:acceptable|allowed|permitted|valid|supported)",
                    suffix,
                )
            )
            if (
                positive.search(prefix) and not negative_near_value.search(prefix)
            ) or positive_after:
                return True
    return False


def validate_resilience_text(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    normalized = re.sub(r"\s+", " ", folded)
    operations = _reference_set(extract_api_references(text))
    has_cursor_endpoint = any(method == "GET" and path in CURSOR_ENDPOINTS for method, path in operations)
    if has_cursor_endpoint:
        if re.search(
            r"(?:repeated|duplicate)\s+cursor.{0,50}"
            r"(?:end|complete|finish|exhaust)(?:s|es|ed)?\s+(?:of\s+)?(?:the\s+)?pagination",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "PAGINATION_REPEATED_CURSOR",
                    relative,
                    "a repeated cursor is inconsistent and cannot prove pagination completion",
                )
            )
        if re.search(
            r"(?:missing|absent|empty)\s+(?:next_)?cursor.{0,80}"
            r"(?:complete|end|finish|exhaust)\w*",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "PAGINATION_LIVE_CURSOR_SHAPE",
                    relative,
                    "only an explicit null next_cursor proves pagination exhaustion",
                )
            )
        if re.search(
            r"meta\.limit.{0,80}(?:mismatch|different|wrong).{0,80}"
            r"(?:acceptable|allowed|ignored|safe|continue)",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "PAGINATION_LIVE_CURSOR_SHAPE",
                    relative,
                    "meta.limit must equal the requested limit",
                )
            )
        if re.search(
            r"(?:request|use|allow|permit).{0,40}limit\s*=\s*(?:10[1-9]|1[1-9]\d|[2-9]\d{2,})",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "PAGINATION_LIMIT",
                    relative,
                    "clients must not exceed limit=100 even if the server accepts it",
                )
            )
        if re.search(
            r"(?:^|[.!?]\s+)(?:require|use|rely\s+on).{0,80}"
            r"(?:page_size|total_pages|total_count).{0,80}"
            r"(?:complete|completion|exhaust)",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "PAGINATION_OPENAPI_DRIFT",
                    relative,
                    "stale OpenAPI page fields cannot prove cursor completion",
                )
            )
        if re.search(
            r"duplicate\s+record\s+ids?.{0,40}(?:within|in)\s+"
            r"(?:one|the\s+same|a\s+single)\s+page.{0,50}"
            r"(?:acceptable|allowed|permitted|valid|ignored|safe)",
            normalized,
        ):
            issues.append(
                _issue(
                    "PAGINATION_DUPLICATE_ID",
                    relative,
                    "duplicate record IDs within one page make the traversal incomplete",
                )
            )
        if (
            _allows_numeric_value_over_cap(
                folded, 1000, r"pages?\b", r"\bpages?\b"
            )
            or _allows_numeric_value_over_cap(
                folded, 100000, r"(?:items?|records?)\b", r"\b(?:items?|records?)\b"
            )
        ):
            issues.append(
                _issue(
                    "PAGINATION_CAP",
                    relative,
                    "pagination may not process page 1,001 or item 100,001",
                )
            )
        requirements: Sequence[Tuple[str, bool, str]] = (
            ("PAGINATION_LIMIT", "limit=100" in folded, "cursor endpoints must request limit=100"),
            (
                "PAGINATION_NONEMPTY_CURSOR",
                "nonempty" in folded and "next_cursor" in folded,
                "follow each nonempty meta.next_cursor",
            ),
            (
                "PAGINATION_REPEATED_CURSOR",
                bool(re.search(r"(?:repeated\s+cursor|cursor.{0,30}repeat)", folded, re.S)),
                "a repeated cursor must stop as incomplete",
            ),
            (
                "PAGINATION_DUPLICATE_ID",
                all(
                    term in normalized
                    for term in (
                        "track every cursor and returned record id",
                        "a duplicate within one page or a repeat across pages within the same traversal is inconsistent",
                    )
                ),
                "duplicate record IDs within one page or across pages of one traversal must stop as incomplete",
            ),
            (
                "PAGINATION_STATE_SCOPE",
                all(
                    term in normalized
                    for term in (
                        "one logical pagination traversal of one endpoint and query",
                        "reset cursor and record-id tracking for each fresh query or pre-write refetch",
                        "same record id may reappear across independent traversals",
                        "a duplicate within one page or a repeat across pages within the same traversal is inconsistent",
                        "100,000-item budget remains global across the run",
                    )
                )
                and not re.search(
                    r"same\s+record\s+id.{0,60}independent\s+traversals"
                    r".{0,40}(?:is\s+)?inconsistent",
                    normalized,
                    re.S,
                ),
                "reset cursor and ID uniqueness per logical traversal while keeping item budgets global",
            ),
            (
                "PAGINATION_NULL_CURSOR",
                bool(re.search(r"explicit\s+null.{0,40}(?:proves|means).{0,40}exhaust", folded, re.S)),
                "an explicit null next_cursor proves exhaustion",
            ),
            (
                "PAGINATION_LIVE_CURSOR_SHAPE",
                all(
                    term in normalized
                    for term in (
                        "`meta.limit`",
                        "integer equal to the requested",
                        "`meta.next_cursor` key on every page",
                        "either a nonempty string or explicit null",
                        "missing key",
                        "wrong type",
                    )
                ),
                "require the live meta.limit and next_cursor response shape",
            ),
            (
                "PAGINATION_OPENAPI_DRIFT",
                all(
                    term in normalized
                    for term in (
                        "do not require or use",
                        "page_size",
                        "total_pages",
                        "total_count",
                        "live api cursor shape was verified on 2026-07-19",
                        "openapi",
                    )
                ),
                "record the verified cursor schema drift and do not rely on stale page fields",
            ),
            (
                "PAGINATION_CAP",
                ("1,000 pages" in normalized or "1000 pages" in normalized)
                and bool(
                    re.search(
                        r"100,?000(?:\s+|-)(?:items?|records?)", normalized
                    )
                ),
                "pagination must cap at 1,000 pages and 100,000 items",
            ),
            (
                "PAGINATION_INCOMPLETE",
                "incomplete" in folded and ("do not" in folded or "never" in folded),
                "page failures and unproved completion must stop as incomplete",
            ),
        )
        for code, passed, message in requirements:
            if not passed:
                issues.append(_issue(code, relative, message))
    invalid_retry_terms = r"(?:missing|malformed|non-integer|negative|larger)"
    invalid_retry_fallback = any(
        re.search(invalid_retry_terms, sentence)
        and ("fallback" in sentence or bool(re.search(r"\b(?:continue|retry)\b", sentence)))
        and not re.search(
            r"\b(?:stop|reject|refuse|fail)\b.{0,80}" + invalid_retry_terms,
            sentence,
        )
        and "do not retry" not in sentence
        and "never retry" not in sentence
        for sentence in (
            re.sub(r"\s+", " ", value).strip()
            for value in re.split(r"[.!?]+", folded)
            if value.strip()
        )
    )
    retry_after_contradiction = bool(
        invalid_retry_fallback
        or re.search(r"retry\s+(?:a\s+)?429\s+(?:four|4)\s+times", folded)
        or re.search(r"wait\s+(?:for\s+)?61\s+seconds.{0,40}retry-after", folded)
        or re.search(
            r"retry-after.{0,30}61\s+seconds.{0,30}(?:valid|acceptable|allowed|permitted)",
            folded,
        )
    )
    if not (
        "429" in folded
        and "retry-after" in folded
        and bool(re.search(r"(?:at most|no more than)\s+(?:two|three|2|3)\s+(?:times|retries)", folded))
        and "60 seconds" in folded
        and "missing" in folded
        and "malformed" in folded
        and "non-integer" in folded
        and "negative" in folded
        and "larger" in folded
        and "stop" in folded
    ) or retry_after_contradiction:
        issues.append(
            _issue(
                "RETRY_429_BOUNDED",
                relative,
                "429 handling must validate Retry-After, cap waits at 60 seconds, and allow at most two retries",
            )
        )
    if not (
        "network" in folded
        and "5xx" in folded
        and bool(
            re.search(
                r"(?:at most|no more than)\s+(?:two|2)\s+retries|retry\s+(?:at most|no more than)\s+(?:twice|two times|2 times)",
                folded,
            )
        )
        and ("incomplete" in folded or "unverified" in folded)
    ):
        issues.append(
            _issue(
                "RETRY_TRANSIENT_BOUNDED",
                relative,
                "network and 5xx retries must be capped at two and then stop incomplete or unverified",
            )
        )
    if not ("percent-encode" in folded or "url-encode" in folded):
        issues.append(
            _issue(
                "QUERY_VALUE_ENCODING",
                relative,
                "every dynamic query value must be percent-encoded",
            )
        )
    if not (
        "top-level json object" in normalized
        and (
            "accessowl api-required field" in normalized
            or "openapi-required field" in normalized
        )
        and "correctly typed" in normalized
        and "nonempty unique record ids" in normalized
        and "malformed" in normalized
        and "incomplete" in normalized
    ):
        issues.append(
            _issue(
                "API_RESPONSE_SCHEMA",
                relative,
                "validate response shape, required fields, types, enums, and unique IDs before use",
            )
        )
    if not (
        "duplicate" in folded
        and "object key" in folded
        and ("any depth" in folded or "every depth" in folded)
        and "nan" in folded
        and "infinity" in folded
    ):
        issues.append(
            _issue(
                "API_JSON_STRICT",
                relative,
                "API JSON must reject duplicate object keys at any depth and non-RFC NaN/Infinity constants",
            )
        )
    json_resource_safe = all(
        term in normalized
        for term in (
            "json nesting deeper than 128",
            "depth exactly 128 is allowed",
            "depth 129 is rejected",
            "numeric token to at most 1,024 ascii characters before conversion",
            "1,024 is allowed and 1,025 is rejected",
            "conversion that yields a non-finite value",
            "`1e400`",
        )
    )
    json_resource_contradiction = bool(
        re.search(
            r"(?:depth\s+129|1,?025-character\s+numeric\s+token|`?1e400`?)"
            r".{0,50}(?:is\s+)?(?:allowed|accepted|valid|finite)",
            normalized,
        )
    )
    if not json_resource_safe or json_resource_contradiction:
        issues.append(
            _issue(
                "API_JSON_RESOURCE_LIMITS",
                relative,
                "bound JSON depth and numeric-token size before conversion and reject non-finite overflow",
            )
        )
    byte_cap_contradiction = bool(
        re.search(
            r"(?:accumulate|buffer).{0,60}(?:fully\s+)?decompressed\s+body"
            r".{0,80}(?:then|after).{0,40}(?:reject|check|enforce)",
            folded,
            re.S,
        )
        or re.search(r"accept.{0,30}(?:11\s+mib|response.{0,20}11\s+mib)", folded)
        or re.search(
            r"(?:response\s+body.{0,20})?11\s+mib.{0,30}"
            r"(?:is\s+)?(?:acceptable|allowed|valid)",
            folded,
        )
        or _allows_numeric_value_over_cap(
            folded,
            10,
            r"mi?b\b",
            r"(?:decompress|response\s+bod(?:y|ies)|body\s+size)",
        )
    )
    if not (
        ("10 mib" in folded or "10 mb" in folded)
        and "streaming and decompressing" in folded
        and "decompressed body exceeds" in folded
        and "before buffering" in folded
        and "parsing" in folded
        and "content-length" in folded
        and "compressed size" in folded
    ) or byte_cap_contradiction:
        issues.append(
            _issue(
                "API_RESPONSE_BYTE_CAP",
                relative,
                "enforce the 10 MiB decompressed-body cap while streaming, before buffering or parsing",
            )
        )
    deadline_contradiction = bool(
        re.search(
            r"start.{0,40}(?:30-second\s+)?deadline.{0,40}only\s+after"
            r".{0,60}response\s+body.{0,40}fully\s+read",
            folded,
            re.S,
        )
        or re.search(r"(?:allow|permit|use).{0,40}(?:attempt|request).{0,30}31(?:-second|\s+seconds)", folded)
        or re.search(r"use.{0,30}31-second.{0,30}(?:attempt|request)\s+deadline", folded)
        or re.search(r"(?:allow|permit|use).{0,40}(?:overall\s+)?run.{0,30}16(?:-minute|\s+minutes)", folded)
        or re.search(r"use.{0,30}16-minute.{0,30}(?:overall\s+)?run\s+deadline", folded)
        or re.search(r"overall\s+deadline.{0,50}(?:optional|if supported|when supported)", folded)
        or _allows_numeric_value_over_cap(
            folded,
            30,
            r"seconds?\b",
            r"(?:attempt|request|deadline)",
        )
    )
    if not (
        "enforced 30-second deadline" in normalized
        and all(
            term in normalized
            for term in (
                "dns resolution",
                "tcp connection",
                "tls",
                "redirects",
                "response headers",
                "streamed and decompressed body",
                "counts toward the same retry cap",
                "cannot enforce it, stop before making the request",
                "track monotonic elapsed time",
                "overall 15-minute run deadline",
                "before every attempt",
                "no time remains",
                "remaining budget",
            )
        )
        and bool(re.search(r"deadline\s+expiry is a network error", folded))
    ) or deadline_contradiction:
        issues.append(
            _issue(
                "API_REQUEST_DEADLINE",
                relative,
                "every API attempt needs an enforced 30-second deadline and supported runs need a 15-minute overall deadline",
            )
        )
    authorization_forward_claims = list(
        re.finditer(
            r"(?:forward|preserve|send).{0,30}`?authorization`?.{0,50}"
            r"(?:different|cross-origin|redirected)\s+origin",
            normalized,
        )
    )

    def redirect_claim_is_negated(match: re.Match[str]) -> bool:
        prefix = normalized[max(0, match.start() - 120) : match.start()]
        return bool(re.search(r"(?:never|do not|must not)[^.!?]{0,110}$", prefix))

    cross_origin_redirect_claims = list(
        re.finditer(
            r"(?:allow|permit|accept|follow|visit).{0,60}"
            r"(?:cross-origin|different\s+origin)\s+redirect",
            normalized,
        )
    )

    redirect_safe = all(
        term in normalized
        for term in (
            "at most three redirects",
            "every hop stays on the configured api origin",
            "never follow any cross-origin redirect",
            "possible billing redirect is still cross-origin",
            "without visiting its destination",
            "never downgrade https to http",
            "redirect loop",
        )
    ) and bool(authorization_forward_claims) and all(
        redirect_claim_is_negated(match)
        for match in authorization_forward_claims
    )
    redirect_contradiction = bool(
        any(
            not redirect_claim_is_negated(match)
            for match in authorization_forward_claims
        )
        or any(
            not redirect_claim_is_negated(match)
            for match in cross_origin_redirect_claims
        )
        or re.search(
            r"(?:allow|permit|accept|follow|use).{0,30}"
            r"(?:four|five|six|seven|eight|nine|ten|unlimited|unbounded)"
            r".{0,20}redirect",
            folded,
        )
        or re.search(
            r"(?:four|five|six|seven|eight|nine|ten|unlimited|unbounded)"
            r".{0,20}redirects?.{0,40}"
            r"(?:acceptable|allowed|permitted|valid|supported)",
            folded,
        )
        or _allows_numeric_value_over_cap(
            folded, 3, r"redirects?\b", r"\bredirects?\b"
        )
        or re.search(r"(?:allow|follow|use).{0,40}https.{0,20}(?:to|downgrade).{0,20}http", folded)
    )
    if not redirect_safe or redirect_contradiction:
        issues.append(
            _issue(
                "API_REDIRECT_BOUNDARY",
                relative,
                "cap redirects at three and never forward credentials across origins",
            )
        )
    status_contract_provenance = (
        "exact accessowl api-documented success status for each operation"
        in normalized
        or "exact openapi-documented success status for each operation"
        in normalized
    )
    status_contract_safe = status_contract_provenance and all(
        term in normalized
        for term in (
            "reads, every other status",
            "`204`",
            "`206`",
            "unexpected `2xx`",
            "unhandled `4xx` such as `404`",
            "stops as incomplete",
            "mutations, any undocumented status",
            "unknown outcome",
            "stop remaining writes",
            "never claim success",
            "verify with a documented read when possible",
        )
    )
    status_contract_contradiction = bool(
        re.search(
            r"(?:read|response).{0,40}(?:`?206`?|`?404`?).{0,60}"
            r"(?:is|means|proves).{0,20}(?:complete|successful|empty)",
            normalized,
        )
        or re.search(
            r"(?:undocumented|unexpected).{0,30}(?:`?2\d\d`?|2xx).{0,60}"
            r"(?:mutation|write).{0,30}(?:is|means|proves).{0,20}success",
            normalized,
        )
        or re.search(
            r"(?:mutation|write).{0,40}(?:undocumented|unexpected)"
            r".{0,30}(?:`?2\d\d`?|2xx).{0,30}(?:is|means|proves).{0,20}success",
            normalized,
        )
    )
    if not status_contract_safe or status_contract_contradiction:
        issues.append(
            _issue(
                "HTTP_STATUS_CONTRACT",
                relative,
                "accept only each operation's documented success status and fail closed on every other status",
            )
        )
    if not (
        re.search(r"64\s+k(?:i)?b", folded)
        and re.search(r"scalar\s+string", folded)
    ) or re.search(
        r"(?:accept|allow|permit|use).{0,40}(?:scalar\s+string.{0,20})?65\s+k(?:i)?b",
        folded,
    ):
        issues.append(
            _issue(
                "API_SCALAR_STRING_CAP",
                relative,
                "reject decoded scalar strings over 64 KiB",
            )
        )
    if not (
        "inclusive" in folded
        and ("exactly at" in folded or "exact cap" in folded)
        and ("next byte" in folded or "cap + 1" in folded or "cap+1" in folded)
    ):
        issues.append(
            _issue(
                "API_CAP_BOUNDARY",
                relative,
                "resource caps are inclusive: exact cap is accepted and cap+1 is rejected",
            )
        )
    if not (
        "401" in folded
        and ("invalid credential" in folded or "missing or invalid" in folded or "invalid or missing" in folded)
        and ("billing redirect" in folded or "redirect" in folded and "billing" in folded)
    ):
        issues.append(
            _issue(
                "AUTH_401_SEMANTICS",
                relative,
                "401 must mean a missing or invalid credential and billing redirect must be handled separately",
            )
        )
    if (
        re.search(r"401.{0,25}\b(?:or|and)\b\s+(?:a\s+)?(?:billing|redirect)", folded, re.S)
        or re.search(r"(?:credential|token).{0,20}\b(?:or|and)\b\s+(?:a\s+)?(?:billing|redirect)", folded, re.S)
    ):
        issues.append(
            _issue(
                "AUTH_401_CONFLATED",
                relative,
                "401 cannot be conflated with a billing redirect",
            )
        )
    if skill in EXPECTED_SKILLS:
        common_requirements: Sequence[Tuple[str, bool, str]] = (
            (
                "API_AUTH_BOUNDARY",
                "https://api.accessowl.com/api/v1" in folded
                and "bearer token" in folded
                and "do not ask" in folded
                and "token in chat" in folded
                and "403" in folded
                and "lacks permission" in folded
                and "billing" in folded
                and "redirect" in folded,
                "pin the API base path and keep configured Bearer credentials out of chat while distinguishing 403 and billing redirects",
            ),
            (
                "LIVE_DETAIL_ENVELOPE",
                all(
                    term in normalized
                    for term in (
                        "user-detail and application-detail responses",
                        "top-level `data` object",
                        "require that envelope",
                    )
                ),
                "require the live detail response data envelope",
            ),
            (
                "LIVE_USER_NAME_NULLABILITY",
                all(
                    term in normalized
                    for term in (
                        "`first_name` or `last_name` may be null",
                        "trimmed nonblank `full_name`",
                        "validated nonblank email address",
                        "stop if neither exists",
                        "never invent a name",
                    )
                ),
                "handle live nullable user names without inventing a label",
            ),
            (
                "LIVE_RESOURCE_TITLE_NULLABILITY",
                all(
                    term in normalized
                    for term in (
                        "resource `title` may be null",
                        "treat it as unavailable",
                        "never invent or display a fallback title",
                        "display, selection, csv output, or disambiguation",
                        "otherwise stop incomplete",
                    )
                ),
                "handle live nullable resource titles only where a title is not needed",
            ),
            (
                "LIVE_OPENAPI_EXCEPTIONS",
                "sandbox-verified exceptions" in folded
                and "2026-07-19" in folded
                and "every other documented" in folded
                and "specific stale openapi claims" in folded,
                "scope the live OpenAPI exceptions narrowly and keep other validation strict",
            ),
            (
                "API_NESTED_VALUE_CAP",
                bool(re.search(r"100,?000\s+decoded\s+json\s+nodes", normalized))
                and all(
                    term in normalized
                    for term in (
                        "every object",
                        "object key",
                        "array",
                        "scalar value",
                        "across the run",
                    )
                )
                and not re.search(
                    r"(?:object\s+keys?|scalar\s+(?:property\s+)?values?)"
                    r".{0,60}(?:do\s+not\s+count|are\s+excluded|may\s+be\s+ignored)",
                    folded,
                    re.S,
                ),
                "cap every decoded JSON container, object key, and scalar value at 100,000 nodes across the run",
            ),
            (
                "API_FORMAT_VALIDATION",
                all(term in folded for term in ("uuid", "email", "date", "date-time"))
                and "validate every documented" in folded,
                "validate documented UUID, email, date, and date-time formats before use",
            ),
            (
                "API_RELATIONSHIP_AGREEMENT",
                bool(re.search(r"requested\s+filters", folded))
                and bool(re.search(r"expanded\s+ids", folded))
                and bool(re.search(r"foreign\s+keys", folded))
                and bool(re.search(r"parent\s+records", folded)),
                "returned filters, expansions, foreign keys, and parent records must agree",
            ),
            (
                "UNTRUSTED_TEXT_DATA_ONLY",
                bool(re.search(r"apis,\s+files,\s+and\s+users", folded))
                and bool(re.search(r"strictly\s+as\s+data", folded))
                and bool(re.search(r"never\s+as\s+instructions", folded)),
                "treat API, file, and user text as untrusted data, never instructions",
            ),
            (
                "DISPLAY_CONTROL_CHARACTERS",
                "nul" in folded and "unsafe control characters" in folded and "reject" in folded,
                "reject NUL and unsafe control characters in identifiers and display labels",
            ),
            (
                "DISPLAY_ESCAPING",
                all(
                    term in folded
                    for term in (
                        "escape markdown",
                        "table",
                        "link",
                        "html",
                        "backtick",
                        "line-break",
                    )
                ),
                "escape Markdown, table, link, HTML, backtick, and line-break delimiters",
            ),
            (
                "DISPLAY_NONBLANK_LABEL",
                "every displayed application" in folded
                and "person label" in folded
                and "nonblank after whitespace trimming" in folded
                and "safe placeholder" in folded,
                "display labels must be trimmed, nonblank, and use placeholders only for legitimate absence",
            ),
        )
        for code, passed, message in common_requirements:
            if not passed:
                issues.append(_issue(code, relative, message))
    contradiction_patterns = (
        r"repeated\s+cursor.{0,100}(?:safe\s+to\s+ignore|may\s+be\s+ignored|"
        r"only\s+a\s+warning|continue|proceed|keep\s+(?:fetching|paginating|going))",
        r"(?:ignore|continue\s+(?:past|after))\s+(?:a\s+)?repeated\s+cursor",
        r"(?:retry|retries).{0,30}429.{0,50}(?:forever|indefinitely|unbounded|without\s+(?:a\s+)?limit)",
        r"(?:do not|never|skip)\s+(?:percent|url)-encode",
        r"(?:continue|proceed)\s+(?:with|after|despite).{0,70}(?:malformed|incomplete|partial)",
        r"(?:disable|omit|skip|use\s+no)\s+(?:the\s+)?(?:request\s+)?deadline",
        r"(?:buffer|parse).{0,40}(?:before|then).{0,40}(?:enforc|check).{0,30}10\s+mib",
    )
    if any(re.search(pattern, folded, re.S) for pattern in contradiction_patterns):
        issues.append(
            _issue(
                "RESILIENCE_CONTRADICTION",
                relative,
                "unsafe prose must not override cursor, retry, encoding, or malformed-data stop rules",
            )
        )
    return issues


def validate_read_safety(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    for skill, relative, text, read_issues in _skill_documents(root):
        issues.extend(read_issues)
        if text is None:
            continue
        issues.extend(validate_resilience_text(skill, text, relative))
        folded = text.casefold()
        references = extract_api_references(text)
        if skill in TITLE_LOOKUP_SKILLS and any(
            reference.normalized_path == "/applications"
            and "title_like" in reference.query
            for reference in references
        ):
            if not (
                "application title" in folded
                and "nonblank" in folded
                and "unique case-insensitively" in folded
                and "stop" in folded
            ):
                issues.append(
                    _issue(
                        "APPLICATION_TITLE_UNIQUENESS",
                        relative,
                        "title-based selection requires nonblank, casefold-unique application titles or it stops",
                    )
                )
    return issues


def _has_operation_in_paragraph(paragraph: str, operation: Tuple[str, str]) -> bool:
    return operation in _reference_set(extract_api_references(paragraph))


def _validate_idempotency(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    if not (
        "idempotency-key" in folded
        and "fresh" in folded
        and "uuid" in folded
        and "every retry uses the exact same method, path, body, and key" in folded
        and (
            "logical write" in folded
            or "different write" in folded
            or re.search(r"changed\s+write\s+is\s+a\s+new\s+mutation", folded)
        )
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_KEY_LIFECYCLE",
                relative,
                "use one fresh UUID per logical write and reuse the same key and body only for retries",
            )
        )
    if not (
        "409" in folded and "received" in folded and "outcome" in folded and "unknown" in folded
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_409_UNKNOWN",
                relative,
                "a replay 409 proves receipt but leaves the write outcome unknown",
            )
        )
    if (
        re.search(r"\b(?:so|then|therefore)\s+treat\b.{0,30}\bas success\b", folded)
        or re.search(r"\b409\b.{0,20}\bmeans\s+success\b", folded)
        or re.search(
            r"(?:\b409\b|outcome\s+is\s+unknown).{0,120}"
            r"(?:always|may|can|should)\s+treat.{0,40}(?:as\s+)?success",
            folded,
            re.S,
        )
        or re.search(
            r"(?<!never\s)(?<!do\snot\s)(?<!must\snot\s)treat.{0,40}"
            r"\b409\b.{0,40}(?:as\s+)?success",
            folded,
            re.S,
        )
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_409_SUCCESS",
                relative,
                "a 409 must not be treated as successful outcome evidence",
            )
        )
    verification = IDEMPOTENCY_VERIFICATION.get(skill)
    if verification is None:
        if not (
            "409" in folded
            and "cannot be verified" in folded
            and "check accessowl" in folded
        ):
            issues.append(
                _issue(
                    "IDEMPOTENCY_UNVERIFIABLE",
                    relative,
                    "when no read endpoint can verify a replay 409, report unknown and require an AccessOwl check",
                )
            )
    elif not (
        verification in _reference_set(extract_api_references(text))
        and "409" in folded
        and ("verif" in folded or "refetch" in folded or "query" in folded)
        and ("baseline" in folded or "report only" in folded)
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_VERIFY",
                relative,
                "after replay 409, verify outcome with %s %s" % verification,
            )
        )
    tuple_phrase = "every retry uses the exact same method, path, body, and key"
    retry_tuple_contexts = [
        folded[match.start() : match.start() + 320]
        for match in re.finditer(re.escape(tuple_phrase), folded)
    ]
    if not any(
        all(term in context for term in ("429", "5xx", "timeout", "network"))
        for context in retry_tuple_contexts
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_ALL_RETRIES",
                relative,
                "429, 5xx, timeout, and network retries must preserve the same key and exact body",
            )
        )
    if re.search(
        r"\b(?:429|5xx|timeout|network)(?:\s+(?:error|failure|retry|retries))?"
        r".{0,100}\b(?:fresh|new|another|replacement|newly\s+generated)\b.{0,30}"
        r"(?:idempotency-?key|key|body)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_RETRY_CONTRADICTION",
                relative,
                "transport and retryable HTTP failures must reuse the exact key and body",
            )
        )
    if re.search(
        r"(?m)^\s*(?:generate|create|use)\b.{0,40}"
        r"(?:another|new|fresh)\b.{0,20}(?:idempotency-?\s*)?key"
        r".{0,80}(?:timeout|times?\s+out|network\s+(?:error|failure))",
        folded,
    ):
        issues.append(
            _issue(
                "IDEMPOTENCY_RETRY_CONTRADICTION",
                relative,
                "transport and retryable HTTP failures must reuse the exact key and body",
            )
        )
    return issues


def _validate_write_redirects(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    required = (
        "for a `post`, `patch`, or `put` mutation",
        "never follow a redirect of any status",
        "`301`, `302`, `303`, `307`, or `308`",
        "even on the same origin",
        "write redirect leaves the outcome uncertain",
        "stop remaining writes",
        "never repeat it with a different method, body, or `idempotency-key`",
    )
    unsafe_redirect_action = False
    for match in re.finditer(r"\b(?:follow|allow|permit)\b", normalized):
        sentence_start = max(
            normalized.rfind(mark, 0, match.start()) for mark in ".!?"
        ) + 1
        following_boundaries = [
            position
            for mark in ".!?"
            for position in (normalized.find(mark, match.end()),)
            if position != -1
        ]
        sentence_end = min(following_boundaries) if following_boundaries else len(normalized)
        sentence = normalized[sentence_start:sentence_end]
        prefix = normalized[sentence_start:match.start()]
        if (
            any(term in sentence for term in ("write", "mutation", "post", "patch", "put"))
            and any(term in sentence for term in ("redirect", "307", "308"))
            and not re.search(r"(?:never|do not|must not)[^.!?]{0,40}$", prefix)
        ):
            unsafe_redirect_action = True
            break
    unsafe_redirect_repeat = False
    for match in re.finditer(r"\b(?:retry|repeat|resend)\b", normalized):
        sentence_start = max(
            normalized.rfind(mark, 0, match.start()) for mark in ".!?"
        ) + 1
        following_boundaries = [
            position
            for mark in ".!?"
            for position in (normalized.find(mark, match.end()),)
            if position != -1
        ]
        sentence_end = min(following_boundaries) if following_boundaries else len(normalized)
        sentence = normalized[sentence_start:sentence_end]
        prefix = normalized[sentence_start:match.start()]
        if (
            "write redirect" in sentence
            and not re.search(r"(?:never|do not|must not)[^.!?]{0,40}$", prefix)
        ):
            unsafe_redirect_repeat = True
            break
    contradiction = bool(
        unsafe_redirect_action
        or re.search(
            r"(?:rewrite|change).{0,30}(?:post|patch|put).{0,30}(?:to|get)"
            r".{0,30}(?:301|302|303|redirect)",
            normalized,
        )
        or re.search(
            r"same-origin.{0,30}write\s+redirect.{0,30}"
            r"(?:may|can|should).{0,20}(?:follow|continue)",
            normalized,
        )
        or unsafe_redirect_repeat
    )
    if not all(term in normalized for term in required) or contradiction:
        return [
            _issue(
                "WRITE_REDIRECT_BOUNDARY",
                relative,
                "never follow mutation redirects; stop with an uncertain outcome and preserve the write tuple",
            )
        ]
    return []


def _validate_concurrency(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    paragraphs = _paragraphs(text)
    if re.search(
        r"(?:do not|never|skip)\s+(?:re-?fetch|revalidat\w*).{0,80}"
        r"(?:immediately\s+)?before.{0,30}(?:write|post|patch|chunk)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "CONCURRENCY_CONTRADICTION",
                relative,
                "unsafe prose must not disable immediate pre-write revalidation",
            )
        )
    if re.search(
        r"\bskip.{0,40}(?:immediate(?:ly)?\s+)?(?:re-?fetch|revalidat\w*)"
        r".{0,100}(?:prior|recent|cached|old)\s+(?:snapshot|state)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "CONCURRENCY_CONTRADICTION",
                relative,
                "a recent snapshot must not replace immediate pre-write revalidation",
            )
        )
    if re.search(
        r"(?:cached|prior|old|recent)\s+(?:snapshot|state).{0,50}"
        r"(?:in\s+place\s+of|instead\s+of|replaces?).{0,50}"
        r"(?:immediate(?:ly)?\s+)?(?:pre-write\s+)?(?:re-?fetch|revalidat\w*)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "CONCURRENCY_CONTRADICTION",
                relative,
                "a cached snapshot must not replace immediate pre-write revalidation",
            )
        )
    for operation in CONCURRENCY_READS[skill]:
        if not any(
            ("immediately before" in paragraph.casefold())
            and ("re-fetch" in paragraph.casefold() or "refetch" in paragraph.casefold())
            and _has_operation_in_paragraph(paragraph, operation)
            for paragraph in paragraphs
        ):
            issues.append(
                _issue(
                    "CONCURRENCY_REVALIDATE",
                    relative,
                    "immediately before each write, re-fetch %s %s" % operation,
                )
            )
    if skill in BULK_SKILLS and not (
        re.search(r"(?:each|every).{0,30}(?:bulk\s+)?chunk", folded, re.S)
        and "immediately before" in folded
        and ("revalid" in folded or "refetch" in folded)
    ):
        issues.append(
            _issue(
                "CONCURRENCY_EACH_CHUNK",
                relative,
                "each bulk chunk needs its own immediate prewrite revalidation",
            )
        )
    if skill in BULK_SKILLS:
        complete_prewrite = False
        for paragraph in paragraphs:
            paragraph_folded = paragraph.casefold()
            if not (
                "immediately before" in paragraph_folded
                and _has_operation_in_paragraph(paragraph, ("GET", "/access_states"))
                and _has_operation_in_paragraph(paragraph, ("GET", "/access_requests"))
            ):
                continue
            complete_prewrite = (
                bool(re.search(r"users?'?\s+status|user\s+status|users'\s+statuses", paragraph_folded))
                and "application" in paragraph_folded
                and bool(re.search(r"resource\s+structures?", paragraph_folded))
                and ("older snapshot" in paragraph_folded or "batch-wide snapshot" in paragraph_folded)
                and "record the ids" in paragraph_folded
                and bool(re.search(r"pre-write\s+snapshot", paragraph_folded))
                and "baseline" in paragraph_folded
                and ("changed" in paragraph_folded or "differs" in paragraph_folded)
                and ("reconfirm" in paragraph_folded or "confirm it" in paragraph_folded)
            )
            if complete_prewrite:
                break
        if not complete_prewrite:
            issues.append(
                _issue(
                    "CONCURRENCY_COMPLETE_PREWRITE",
                    relative,
                    "each access-write call must refetch user, application, structure, access, and requests, detect drift, reconfirm, and record a baseline",
                )
            )
        display_identity_safe = any(
            all(
                term in re.sub(r"\s+", " ", paragraph.casefold())
                for term in (
                    "displayed name or email",
                    "selected application",
                    "resource",
                    "permission title or id",
                    "requestability",
                    "effective change",
                    "differs",
                    "reconfirm before",
                )
            )
            for paragraph in paragraphs
        )
        display_identity_contradiction = bool(
            re.search(
                r"(?:displayed\s+name|email|application\s+title).{0,80}"
                r"(?:change\w*|differ\w*).{0,100}"
                r"(?:continue|submit|proceed).{0,60}"
                r"(?:without\s+reconfirm|anyway|old\s+selection)",
                folded,
                re.S,
            )
        )
        if not display_identity_safe or display_identity_contradiction:
            issues.append(
                _issue(
                    "CONCURRENCY_DISPLAY_IDENTITY_DRIFT",
                    relative,
                    "reconfirm changes to displayed people, application, resource, and permission identities before writing",
                )
            )
    if skill == "request-revocation" and not (
        "each" in folded and "exact access state" in folded and "immediately before" in folded
    ):
        issues.append(
            _issue(
                "CONCURRENCY_EACH_REVOCATION",
                relative,
                "re-fetch each exact access state immediately before its POST",
            )
        )
    revocation_drift_safe = any(
        all(
            term in re.sub(r"\s+", " ", paragraph.casefold())
            for term in (
                "entire confirmed entry",
                "access-state id",
                "user and application ids and titles",
                "resource id or null and title",
                "complete permission ids and titles",
                "customer-visible title",
                "whole-entry impact",
                "confirm again",
                "refetch that same state id",
            )
        )
        for paragraph in paragraphs
    )
    revocation_drift_contradiction = bool(
        re.search(
            r"(?:title|permission\s+id).{0,80}change\w*.{0,80}"
            r"(?:proceed|continue|submit|revoke).{0,50}(?:anyway|old\s+selection|without\s+reconfirm)",
            folded,
            re.S,
        )
    )
    if skill == "request-revocation" and (
        not revocation_drift_safe or revocation_drift_contradiction
    ):
        issues.append(
            _issue(
                "REVOCATION_SELECTION_DRIFT",
                relative,
                "revocation must compare and reconfirm the entire selected customer-visible entry and its IDs",
            )
        )
    access_report_drift_safe = any(
        "any selected application" in paragraph.casefold()
        and "resource, or permission title or id" in paragraph.casefold()
        and "requestability" in paragraph.casefold()
        and "effective change" in paragraph.casefold()
        and "reconfirm" in paragraph.casefold()
        for paragraph in paragraphs
    )
    access_report_drift_contradiction = bool(
        re.search(
            r"selected.{0,40}(?:resource|permission)\s+id.{0,50}change\w*"
            r".{0,80}(?:submit|continue|proceed).{0,50}(?:old\s+selection|anyway)",
            folded,
            re.S,
        )
    )
    if skill == "access-report" and (
        not access_report_drift_safe or access_report_drift_contradiction
    ):
        issues.append(
            _issue(
                "ACCESS_REPORT_SELECTION_DRIFT",
                relative,
                "access-report must reconfirm application, resource, permission, title, ID, requestability, and impact drift",
            )
        )
    if skill == "vendor-update" and not (
        ("each application" in folded or "process applications one at a time" in folded)
        and re.search(r"immediately\s+before\s+(?:its|each|the)\s+patch", folded)
    ):
        issues.append(
            _issue(
                "CONCURRENCY_EACH_PATCH",
                relative,
                "re-fetch each application immediately before each sequential PATCH",
            )
        )
    if skill == "vendor-update" and not any(
        "immediately before its patch" in paragraph.casefold()
        and "every referenced owner or admin" in paragraph.casefold()
        and "recompute list fields" in paragraph.casefold()
        and all(
            term in paragraph.casefold()
            for term in ("certificates", "data types", "tags", "owners", "admins")
        )
        and "differs" in paragraph.casefold()
        and "confirm the new body" in paragraph.casefold()
        and bool(re.search(r"refetch\s+and\s+revalidate", paragraph.casefold()))
        for paragraph in paragraphs
    ):
        issues.append(
            _issue(
                "CONCURRENCY_VENDOR_COMPLETE_PREWRITE",
                relative,
                "each vendor PATCH must refetch the app and referenced people, recompute list fields, and reconfirm drift",
            )
        )
    if skill == "vendor-update":
        if not (
            "lock_version" in text
            and (
                "when returned" in folded
                or "if returned" in folded
                or "if a usable" in folded
                or "when the api returns" in folded
            )
        ):
            issues.append(
                _issue(
                    "LOCK_VERSION_CONDITIONAL",
                    relative,
                    "include lock_version when, and only when, a usable value was returned",
                )
            )
        if re.search(
            r"lock_version.{0,40}(?:unavailable|missing|not returned)"
            r".{0,80}(?:replace|update|change).{0,50}"
            r"(?:tags?|certificates?|data types?|notes).{0,30}anyway",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "VENDOR_NO_CAS_REPLACEMENT",
                    relative,
                    "without lock_version, replacement arrays and notes must not be changed anyway",
                )
            )
    return issues


def _validate_reason_and_bulk(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    field = REASON_SKILLS.get(skill)
    if field and not (
        field in text
        and re.search(r"(?:at most|max(?:imum)?)\s+255\s+(?:unicode\s+)?characters", folded)
    ):
        issues.append(
            _issue(
                "REASON_255_BOUNDARY",
                relative,
                "%s must be explicitly bounded to at most 255 characters" % field,
            )
        )
    if field and re.search(
        r"256-character\s+(?:request_)?reason.{0,30}(?:is\s+)?"
        r"(?:accepted|allowed|valid|permitted)",
        folded,
    ):
        issues.append(
            _issue(
                "REASON_255_BOUNDARY",
                relative,
                "%s cannot accept 256 characters" % field,
            )
        )
    if skill in BULK_SKILLS:
        if not re.search(r"(?:1\s*(?:to|through|-)\s*10|between\s+1\s+and\s+10)\s+items", folded):
            issues.append(
                _issue(
                    "BULK_ITEM_BOUNDARY",
                    relative,
                    "bulk request calls must contain 1 through 10 items",
                )
            )
        if re.search(
            r"bulk\s+call.{0,30}(?:may|can|should)\s+contain\s+11\s+items",
            folded,
        ):
            issues.append(
                _issue(
                    "BULK_ITEM_BOUNDARY",
                    relative,
                    "a bulk call cannot contain 11 items",
                )
            )
        if not (
            "one grantee" in folded
            and "user_id" in text
            and ("required" in folded or "include" in folded)
        ):
            issues.append(
                _issue(
                    "BULK_ONE_GRANTEE",
                    relative,
                    "each bulk body must include user_id and cover exactly one grantee",
                )
            )
    return issues


def _validate_request_dedupe(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    missing_blockers = sorted(status for status in ALWAYS_BLOCKING_REQUEST_STATUSES if status not in text)
    if missing_blockers:
        issues.append(
            _issue(
                "REQUEST_BLOCKING_STATUSES",
                relative,
                "missing always-blocking request statuses: %s" % ", ".join(missing_blockers),
            )
        )
    for status in sorted(ALWAYS_BLOCKING_REQUEST_STATUSES):
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,50}}(?:does\s+not|doesn't|must\s+not|never)\s+block",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REQUEST_STATUS_CONTRADICTION",
                    relative,
                    "%s must remain an always-blocking request status" % status,
                )
            )
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,80}}"
            r"(?:may|can|should|is\s+allowed\s+to).{0,30}"
            r"(?:coexist|overlap|remain).{0,50}(?:new|replacement)\s+request",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REQUEST_STATUS_CONTRADICTION",
                    relative,
                    "%s must remain an always-blocking request status" % status,
                )
            )
        if re.search(
            r"(?:new\s+request|create\s+(?:a\s+)?(?:new\s+)?request)"
            r".{0,60}(?:is\s+)?(?:allowed|permitted|okay|acceptable)"
            rf".{{0,100}}\b{re.escape(status)}\b",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REQUEST_STATUS_CONTRADICTION",
                    relative,
                    "%s must remain an always-blocking request status" % status,
                )
            )
    for status in sorted(NONBLOCKING_REQUEST_STATUSES):
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,30}}(?<!not\s)(?<!never\s)"
            rf"(?<!doesn't\s)(?:always\s+)?blocks?\b",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REQUEST_STATUS_CONTRADICTION",
                    relative,
                    "%s must not block a new request" % status,
                )
            )
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,80}}"
            r"(?:prevents?|forbids?|disallows?|stops?|precludes?|rules?\s+out)\b.{0,50}"
            r"(?:new|replacement)\s+request",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REQUEST_STATUS_CONTRADICTION",
                    relative,
                    "%s must not block a new request" % status,
                )
            )
    if re.search(
        r"\baccess_granted\b.{0,60}(?:always\s+blocks?|blocks?\s+without)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "REQUEST_STATUS_CONTRADICTION",
                relative,
                "access_granted alone must not block without current active access",
            )
        )
    if not all(status in text for status in NONBLOCKING_REQUEST_STATUSES) or not re.search(
        r"(?:denied.{0,50}rejected|rejected.{0,50}denied).{0,80}(?:do\s+not\s+block|non-blocking)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "REQUEST_NONBLOCKING_STATUSES",
                relative,
                "denied and rejected requests must not block a new request",
            )
        )
    if not (
        "access_granted" in text
        and "active access state" in folded
        and ("alone" in folded or "historical" in folded)
        and ("does not block" in folded or "only blocks" in folded or "blocks only" in folded)
    ):
        issues.append(
            _issue(
                "REQUEST_GRANTED_CONDITIONAL",
                relative,
                "access_granted blocks only when a current active access state confirms it",
            )
        )
    if "open or completed" in folded:
        issues.append(
            _issue(
                "REQUEST_BROAD_STATUS_CLASS",
                relative,
                "broad open or completed status classification is unsafe",
            )
        )
    if not (
        "pending" in folded
        and "request" in folded
        and ("dedup" in folded or "duplicate" in folded)
        and "active access" in folded
    ):
        issues.append(
            _issue(
                "REQUEST_PENDING_DEDUPE",
                relative,
                "current access and pending requests must both participate in deduplication",
            )
        )
    return issues


def _validate_request_visibility(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    if skill not in REQUEST_DEDUPE_SKILLS:
        return []
    normalized = re.sub(r"\s+", " ", text.casefold())
    safe = all(
        term in normalized
        for term in (
            "requests visible to the authenticated caller",
            "returned blocking request is definitive",
            "absence is not proof",
            "independently documented guarantee",
            "organization-wide request visibility",
            "guarantee is unavailable, stop before writing",
            "duplicate check may be incomplete",
        )
    )
    contradiction = bool(
        re.search(
            r"(?:absence|no returned request|empty result|empty visible request list).{0,70}"
            r"(?:proves?|guarantees?|confirms?).{0,40}(?:no|without)"
            r".{0,30}(?:duplicate|blocking request)",
            normalized,
        )
    )
    if safe and not contradiction:
        return []
    return [
        _issue(
            "ACCESS_REQUEST_VISIBILITY",
            relative,
            "absence from the caller-visible request list cannot prove organization-wide absence",
        )
    ]


def _validate_target_statuses(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    for status in sorted(TARGET_INELIGIBLE_STATUSES):
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,40}}(?:is|are|remains?|counts?\s+as)\s+(?:an?\s+)?eligible",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "TARGET_STATUS_CONTRADICTION",
                    relative,
                    "%s must not be treated as eligible" % status,
                )
            )
        if re.search(
            rf"(?m)^\s*(?:grant|give|assign|provide)\b.{{0,50}}"
            rf"(?:new\s+)?access.{{0,50}}\b{re.escape(status)}\b",
            folded,
        ):
            issues.append(
                _issue(
                    "TARGET_STATUS_CONTRADICTION",
                    relative,
                    "%s must not receive new access" % status,
                )
            )
        if re.search(
            rf"\b{re.escape(status)}\b.{{0,50}}\b(?:may|can|should)\b"
            r".{0,30}(?:receive|request|be\s+granted)\s+access",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "TARGET_STATUS_CONTRADICTION",
                    relative,
                    "%s must not receive new access" % status,
                )
            )
    if re.search(
        r"unknown\s+(?:user\s+)?status.{0,50}(?:continue|proceed|eligible|submit)",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "TARGET_STATUS_CONTRADICTION",
                relative,
                "unknown target status must stop",
            )
        )
    if not all(status in text for status in TARGET_ELIGIBLE_STATUSES) or "eligible" not in folded:
        issues.append(
            _issue(
                "TARGET_STATUS_ELIGIBLE",
                relative,
                "active, onboarding, and onboarding_provisioning_planned targets are eligible",
            )
        )
    if not all(status in text for status in TARGET_INELIGIBLE_STATUSES) or not (
        ("ineligible" in folded or "do not submit" in folded) and "stop" in folded
    ):
        issues.append(
            _issue(
                "TARGET_STATUS_INELIGIBLE",
                relative,
                "inactive, offboarding, and offboarded targets are ineligible and must stop",
            )
        )
    if not (
        "offboarding_planned" in text
        and ("show" in folded or "warn" in folded)
        and "confirm" in folded
    ):
        issues.append(
            _issue(
                "TARGET_STATUS_OFFBOARDING_PLANNED",
                relative,
                "offboarding_planned must be shown and explicitly confirmed",
            )
        )
    if not ("unknown status" in folded and "stop" in folded):
        issues.append(
            _issue("TARGET_STATUS_UNKNOWN", relative, "an unknown user status must stop")
        )
    if skill == "mirror-access" and not (
        "source" in folded
        and "warn" in folded
        and all(status in text for status in TARGET_INELIGIBLE_STATUSES)
    ):
        issues.append(
            _issue(
                "MIRROR_SOURCE_STATUS",
                relative,
                "warn before copying from an inactive, offboarding, or offboarded source",
            )
        )
    return issues


def _validate_422_failure_semantics(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    if skill not in BULK_SKILLS:
        return []
    normalized = re.sub(r"\s+", " ", text.casefold())
    safe = all(
        term in normalized
        for term in (
            "on `422`",
            "validate the documented error response",
            "report a validation failure",
            "openapi error fields are free-form",
            "do not define a mandatory-resource code",
            "never infer a mandatory resource",
            "synthesize a changed request body from error text",
            "user-specified changed request starts a new workflow",
            "fresh reads, confirmation, and idempotency key",
        )
    )
    contradiction = bool(
        re.search(
            r"(?:422|validation (?:error|response)).{0,100}"
            r"(?<!not\s)(?<!never\s)(?:lists?|identifies?|defines?).{0,50}"
            r"(?:mandatory|required)"
            r".{0,30}(?:resource|permission)",
            normalized,
        )
        or re.search(
            r"(?<!never\s)(?<!do not\s)(?:infer|choose|add|synthesize)"
            r".{0,50}(?:mandatory|required)"
            r".{0,30}(?:resource|permission).{0,80}(?:from|using)"
            r".{0,30}(?:error|message|response)",
            normalized,
        )
    )
    if safe and not contradiction:
        return []
    return [
        _issue(
            "ACCESS_REQUEST_422_FAIL_CLOSED",
            relative,
            "422 responses are free-form validation failures and must not synthesize a new request body",
        )
    ]


def _validate_openapi_field_semantics(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    normalized = re.sub(r"\s+", " ", text.casefold())
    issues: List[Issue] = []
    if skill in {
        "access-report",
        "mirror-access",
        "request-access",
        "request-revocation",
    }:
        provisioning_safe = all(
            term in normalized
            for term in (
                "provisioning_type",
                "missing",
                "present but null",
                "wrong type",
                "outside those two documented values",
                "inconsistent application data",
                "no next-step inference",
                "malformed data as allowed absence",
                "product behavior encoded by this skill",
                "not semantics supplied by the openapi enum description",
                "never describe them as openapi-verified behavior",
            )
        )
        provisioning_contradiction = bool(
            re.search(
                r"(?:null|unknown|out-of-enum).{0,30}provisioning_type"
                r".{0,50}(?:same as|treat.{0,15}as|is)\s+(?:missing|allowed|absent)",
                normalized,
            )
            or re.search(
                r"provisioning_type.{0,30}(?:null|unknown|out-of-enum)"
                r".{0,50}(?:same as|treat.{0,15}as|is)\s+(?:missing|allowed|absent)",
                normalized,
            )
            or re.search(
                r"(?:provisioning_type|provisioning\s+meanings).{0,80}"
                r"(?:verified|defined|guaranteed).{0,40}openapi",
                normalized,
            )
            or re.search(
                r"openapi.{0,40}(?:verifies|defines|guarantees).{0,80}"
                r"(?:provisioning_type|provisioning\s+meanings)",
                normalized,
            )
        )
        if not provisioning_safe or provisioning_contradiction:
            issues.append(
                _issue(
                    "PROVISIONING_TYPE_SCHEMA",
                    relative,
                    "missing provisioning_type is allowed, but present null, wrong-type, or unknown-enum values are malformed",
                )
            )
        provisioning_refetch = any(
            "refetch" in paragraph.casefold()
            and "provisioning_type" in paragraph.casefold()
            and _has_operation_in_paragraph(
                paragraph, ("GET", "/applications/{}")
            )
            for paragraph in _paragraphs(text)
        )
        if not provisioning_refetch:
            issues.append(
                _issue(
                    "PROVISIONING_TYPE_REFETCH",
                    relative,
                    "next-step wording requires an explicit application detail refetch",
                )
            )
    if skill in {"access-report", "mirror-access", "request-access"}:
        multiple_permission_safe = all(
            term in normalized
            for term in (
                "`multiple_permissions_selectable` is present",
                "correctly typed as a boolean",
                "and `true`",
                "missing, null, wrong-type, or `false` blocks that multi-permission selection",
            )
        )
        multiple_permission_contradiction = bool(
            re.search(
                r"(?:missing|null|wrong-type|malformed).{0,60}"
                r"multiple_permissions_selectable.{0,80}"
                r"(?:allow|permit|accept|treat).{0,50}(?:multiple|more\s+than\s+one)",
                normalized,
            )
            or re.search(
                r"multiple_permissions_selectable.{0,60}"
                r"(?:missing|null|wrong-type|malformed).{0,80}"
                r"(?:allow|permit|accept|treat).{0,50}(?:multiple|more\s+than\s+one)",
                normalized,
            )
        )
        if not multiple_permission_safe or multiple_permission_contradiction:
            issues.append(
                _issue(
                    "MULTIPLE_PERMISSION_SELECTION_SCHEMA",
                    relative,
                    "multi-permission requests require a present boolean-true multiple_permissions_selectable field",
                )
            )
    if skill in {"request-access", "userlist-import-preflight"}:
        effective_end_safe = all(
            term in normalized
            for term in (
                "`effective_end` field is present and explicitly null",
                "missing, malformed, or non-null `effective_end`",
                "not current-access evidence",
            )
        )
        effective_end_contradiction = bool(
            re.search(
                r"(?:missing|malformed|non-null|historical).{0,50}effective_end"
                r".{0,60}(?:is|counts?\s+as|treat.{0,15}as)\s+(?:current|active)",
                normalized,
            )
            or re.search(
                r"(?:treat|count|use).{0,60}(?:missing|malformed|non-null|historical)"
                r".{0,30}effective_end.{0,40}(?:as\s+)?(?:current|active)",
                normalized,
            )
            or re.search(
                r"(?:treat|count|use).{0,80}(?:as\s+)?(?:current|active)"
                r".{0,80}effective_end.{0,30}(?:missing|malformed|non-null)",
                normalized,
            )
        )
        if not effective_end_safe or effective_end_contradiction:
            issues.append(
                _issue(
                    "CURRENT_ACCESS_EFFECTIVE_END",
                    relative,
                    "only a present explicit-null effective_end proves current access",
                )
            )
    if skill == "userlist-import-preflight":
        resource_title_safe = all(
            term in normalized
            for term in (
                "live api can return a null resource title",
                "despite the current openapi string requirement",
                "reject a missing, null, empty",
                "never invent a fallback column title",
            )
        )
        if not resource_title_safe or re.search(
            r"(?:null|missing)\s+resource\s+title.{0,60}"
            r"(?:use|name|fallback).{0,30}(?:permissions|column)",
            normalized,
        ):
            issues.append(
                _issue(
                    "RESOURCE_TITLE_REQUIRED",
                    relative,
                    "a nullable resource title cannot be used or replaced as a CSV header",
                )
            )
        structure_safe = all(
            term in normalized
            for term in (
                "partial upsert",
                "omitted resources and permissions remain untouched",
                "deletion requires an existing id plus `delete: true`",
                "updating the existing resource requires resending its title",
                "without a usable version token",
            )
        )
        structure_contradiction = bool(
            re.search(
                r"structure.{0,80}(?:full\s+overwrite|replaces?\s+(?:the\s+)?entire)",
                normalized,
            )
            or re.search(
                r"omitted.{0,40}(?:resource|permission).{0,40}"
                r"(?:is|are|gets?|becomes?)\s+(?:deleted|removed)",
                normalized,
            )
        )
        if not structure_safe or structure_contradiction:
            issues.append(
                _issue(
                    "STRUCTURE_PARTIAL_UPSERT",
                    relative,
                    "structure PUT is a partial upsert with explicit deletion and no readable concurrency token",
                )
            )
    if skill == "vendor-update":
        risk_safe = "`risk_level`: low, medium, high" in normalized
        risk_contradiction = bool(
            re.search(
                r"risk_level.{0,40}(?:also\s+)?(?:accepts?|allows?|supports?|may\s+be)"
                r".{0,20}critical",
                normalized,
            )
        )
        if not risk_safe or risk_contradiction:
            issues.append(
                _issue(
                    "VENDOR_RISK_LEVEL_ENUM",
                    relative,
                    "risk_level is limited to low, medium, and high",
                )
            )
    return issues


def _validate_destructive_invariants(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    normalized = re.sub(r"\s+", " ", folded)
    if skill in WRITE_SKILLS and not (
        "confirm" in folded and ("clear yes" in folded or "explicit confirmation" in folded)
    ):
        issues.append(
            _issue("CONFIRM_BEFORE_WRITE", relative, "every write requires one explicit confirmation")
        )
    if skill in {"request-access", "mirror-access"} and "never call the grant endpoint" not in folded:
        issues.append(
            _issue("NEVER_GRANT", relative, "request skills must explicitly forbid the grant endpoint")
        )
    if skill == "request-revocation" and not (
        "whole entry" in folded
        and "all" in folded
        and "permission" in folded
        and "confirm" in folded
    ):
        issues.append(
            _issue(
                "REVOCATION_WHOLE_ENTRY",
                relative,
                "confirm every permission because a revocation covers the whole access state",
            )
        )
    if skill == "userlist-import-preflight":
        userlist_write_offer = bool(
            re.search(
                r"\b(?:i|we)\s+(?:can|will|could)\s+add.{0,60}"
                r"(?:permission|role).{0,50}(?:application|accessowl)",
                folded,
                re.S,
            )
            or re.search(
                r"offer.{0,30}to\s+add.{0,60}(?:permission|role).{0,50}application",
                folded,
                re.S,
            )
        )
        required = (
            ("USERLIST_NEW_USERS", "new users" in folded and "never correct" in folded),
            (
                "USERLIST_REPLACEMENT",
                "replaces" in folded and "removed" in folded and "warn" in folded,
            ),
            (
                "USERLIST_READ_ONLY",
                ("read-only" in folded or "never writes" in folded)
                and "put /applications/{id}/structure" in folded
                and ("refuse" in folded or "never call" in folded or "do not call" in folded)
                and "rerun" in folded,
            ),
            (
                "USERLIST_PERMISSION_AMBIGUITY",
                bool(re.search(r"permission.{0,120}(?:duplicate|duplicates)", folded, re.S))
                and "semicolon" in folded
                and ("stop" in folded or "without producing" in folded),
            ),
            (
                "USERLIST_RESOURCE_CAPS",
                ("10 mib" in folded or "10 mb" in folded)
                and ("100,000" in folded or "100000" in folded)
                and ("1,000 columns" in folded or "1000 columns" in folded)
                and ("64 kib" in folded or "64 kb" in folded)
                and ("no partial" in folded or "partial output" in folded or "no output" in folded),
            ),
            (
                "USERLIST_WITHHOLD_OUTPUT",
                "withhold" in folded
                and "csv" in folded
                and "import instructions" in folded
                and "replacement" in folded
                and "resolved" in folded,
            ),
            (
                "USERLIST_FINAL_REFRESH",
                "final" in folded
                and ("re-fetch" in folded or "refetch" in folded)
                and "structure" in folded
                and "users" in folded
                and "access state" in folded
                and ("before delivery" in folded or "otherwise deliver" in folded),
            ),
        )
        messages = {
            "USERLIST_NEW_USERS": "unmatched emails remain unchanged and import as new users",
            "USERLIST_REPLACEMENT": "the replacement import must warn that absent current access is removed",
            "USERLIST_READ_ONLY": "the preflight is read-only, refuses structure PUT, and directs UI changes followed by rerun",
            "USERLIST_PERMISSION_AMBIGUITY": "duplicate permission titles and semicolons in titles must stop as ambiguous",
            "USERLIST_RESOURCE_CAPS": "CSV processing must enforce file, row, column, and decoded-field caps with no partial output",
            "USERLIST_WITHHOLD_OUTPUT": "withhold CSV and import instructions until every decision and destructive removal is resolved",
            "USERLIST_FINAL_REFRESH": "refresh structure, users, and access states immediately before final delivery",
        }
        for code, passed in required:
            if not passed:
                issues.append(_issue(code, relative, messages[code]))
        if userlist_write_offer:
            issues.append(
                _issue(
                    "USERLIST_READ_ONLY",
                    relative,
                    "the preflight must tell the user to make structure changes in AccessOwl, never offer to make them",
                )
            )
    if skill == "vendor-update":
        missing = sorted(VENDOR_CERTIFICATES - set(re.findall(r"\b[a-z][a-z0-9_]*\b", text)))
        if missing:
            issues.append(
                _issue(
                    "VENDOR_CERTIFICATE_ENUM",
                    relative,
                    "missing live certificate slugs: %s" % ", ".join(missing),
                )
            )
        if not (
            all(field in text for field in ("vendor_certificates", "processed_data_types", "tags"))
            and "replace" in folded
            and ("combined" in folded or "preserve" in folded)
        ):
            issues.append(
                _issue(
                    "VENDOR_REPLACEMENT_FIELDS",
                    relative,
                    "replacement arrays must preserve current values through a fresh read-modify-write",
                )
            )
        if not (
            "lock_version" in text
            and (
                "unavailable" in folded
                or "not returned" in folded
                or "does not expose" in folded
            )
            and ("refuse" in folded or "do not" in folded)
            and all(term in folded for term in ("certificate", "data type", "tag", "notes"))
        ):
            issues.append(
                _issue(
                    "VENDOR_NO_CAS_REPLACEMENT",
                    relative,
                    "without lock_version, refuse replacement-array and appended-notes read-modify-write updates",
                )
            )
        if not (
            ("cannot guarantee" in folded or "cannot claim" in folded or "never claim" in folded)
            and "concurrent" in folded
            and "lock_version" in text
        ):
            issues.append(
                _issue(
                    "VENDOR_NO_LOCK_CAVEAT",
                    relative,
                    "do not claim concurrent-overwrite protection when lock_version is unavailable",
                )
            )
    if skill == "view-policies":
        policy_provenance_safe = all(
            term in normalized
            for term in (
                "accessowl product behavior outside the openapi schema",
                "not api-verified configuration",
                "for any exact current configuration",
                "settings, then policies",
            )
        )
        policy_provenance_contradiction = bool(
            re.search(
                r"policy\s+routing\s+behavior.{0,60}"
                r"(?:is|as)\s+api-verified\s+configuration",
                folded,
            )
        )
        if not policy_provenance_safe or policy_provenance_contradiction:
            issues.append(
                _issue(
                    "POLICY_PRODUCT_BEHAVIOR_PROVENANCE",
                    relative,
                    "policy routing behavior outside OpenAPI must be labeled and checked in AccessOwl",
                )
            )
        if not (
            "put /policies/{policy_id}/applications" in folded
            and ("refuse" in folded or "never call" in folded or "do not call" in folded)
            and "settings" in folded
            and "policies" in folded
            and ("full" in folded or "complete" in folded)
            and "replace" in folded
        ):
            issues.append(
                _issue(
                    "POLICY_REPLACEMENT_REFUSED",
                    relative,
                    "refuse the unprotected full-set policy replacement and direct the user to Settings, then Policies",
                )
            )
        if not (
            "elevated" in folded
            and "application" in folded
            and ("attached" in folded or "assigned" in folded or "covers" in folded)
            and ("not org-wide" in folded or "not organization-wide" in folded or "only" in folded)
        ):
            issues.append(
                _issue(
                    "POLICY_ELEVATED_SCOPE",
                    relative,
                    "an elevated policy applies only to its attached applications, not organization-wide",
                )
            )
    return issues


def _validate_stale_retry(skill: str, text: str, relative: Path | str) -> List[Issue]:
    if skill != "vendor-update":
        return []
    folded = text.casefold()
    if not (
        re.search(r"stale.{0,12}409", folded, re.S)
        and (
            "first response" in folded
            or "first-response" in folded
            or "first attempt" in folded
        )
        and "fresh key" in folded
        and ("new attempt" in folded or "new logical write" in folded)
    ):
        return [
            _issue(
                "STALE_409_FRESH_KEY",
                relative,
                "a conclusive stale 409 on a fresh-key first response requires a rebuilt attempt with a fresh key",
            )
        ]
    return []


def _validate_mutation_bounds(skill: str, text: str, relative: Path | str) -> List[Issue]:
    if skill not in WRITE_SKILLS:
        return []
    folded = text.casefold()
    issues: List[Issue] = []
    if (
        re.search(r"(?:allow|permit|make|execute|continue).{0,40}(?:101|over\s+100|more\s+than\s+100).{0,30}(?:write|mutation|call)", folded, re.S)
        or re.search(
            r"unknown\s+outcome.{0,80}(?:continue|proceed|keep\s+writing|"
            r"carry\s+on|resume|keep\s+going)",
            folded,
            re.S,
        )
        or re.search(
            r"outcome\s+(?:is\s+)?unknown.{0,80}(?:continue|proceed|"
            r"keep\s+writing|carry\s+on|resume|keep\s+going)",
            folded,
            re.S,
        )
        or re.search(
            r"\b100\b.{0,60}(?:insufficient|not\s+enough).{0,80}"
            r"(?:continue|extra|additional).{0,40}(?:batch|write|mutation|call)",
            folded,
            re.S,
        )
        or re.search(
            r"(?:continue|proceed).{0,30}(?:extra|additional).{0,30}"
            r"(?:batch|write|mutation|call).{0,80}(?:same|existing|prior)\s+confirmation",
            folded,
            re.S,
        )
    ):
        issues.append(
            _issue(
                "MUTATION_BOUND_CONTRADICTION",
                relative,
                "unsafe prose must not exceed 100 first attempts or continue after an unknown outcome",
            )
        )
    if not (
        ("at most 100" in folded or "maximum of 100" in folded)
        and ("mutations" in folded or re.search(r"mutation\s+calls", folded))
        and (re.search(r"above.{0,30}\bcap\b", folded, re.S) or "101" in folded)
        and "no writes" in folded
        and "unknown outcome stops" in folded
    ):
        issues.append(
            _issue(
                "MUTATION_CALL_CAP",
                relative,
                "allow at most 100 first-attempt mutations; 101 makes no writes, and unknown outcome stops the run",
            )
        )
    if (
        re.search(
            r"(?:malformed|missing|unreadable|unparseable|invalid|corrupt|corrupted|damaged|broken|truncated).{0,60}write\s+response.{0,80}"
            r"(?<!never\s)(?<!do\snot\s)(?<!must\snot\s)"
            r"(?:retry|repeat|resend|resubmit|try.{0,15}again).{0,50}"
            r"(?:fresh|new|another|different|separate|replacement|newly\s+generated)\s+"
            r"(?:idempotency-?\s*)?key",
            folded,
            re.S,
        )
        or re.search(
            r"write\s+response.{0,30}(?:is\s+)?"
            r"(?:malformed|missing|unreadable|unparseable|invalid|corrupt|corrupted|damaged|broken|truncated).{0,80}"
            r"(?<!never\s)(?<!do\snot\s)(?<!must\snot\s)"
            r"(?:retry|repeat|resend|resubmit|try.{0,15}again).{0,50}"
            r"(?:fresh|new|another|different|separate|replacement|newly\s+generated)\s+"
            r"(?:idempotency-?\s*)?key",
            folded,
            re.S,
        )
        or re.search(
            r"(?:retry|repeat|resend|resubmit|try.{0,15}again).{0,50}"
            r"(?:fresh|new|another|different|separate|replacement|newly\s+generated)\s+"
            r"(?:idempotency-?\s*)?key.{0,80}"
            r"(?:malformed|missing|unreadable|unparseable|invalid|corrupt|corrupted|damaged|broken|truncated).{0,40}write\s+response",
            folded,
            re.S,
        )
    ):
        issues.append(
            _issue(
                "WRITE_RESPONSE_RETRY_CONTRADICTION",
                relative,
                "a malformed or missing write response must not be retried with a fresh key",
            )
        )
    if not (
        "malformed or missing" in folded
        and "write response" in folded
        and "uncertain outcome" in folded
        and "fresh key" in folded
    ):
        issues.append(
            _issue(
                "WRITE_RESPONSE_UNCERTAIN",
                relative,
                "a malformed or missing write response is uncertain and must not be repeated with a fresh key",
            )
        )
    return issues


def _validate_write_response_correlation(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    issues: List[Issue] = []
    folded = text.casefold()
    normalized = re.sub(r"\s+", " ", folded)
    if re.search(
        r"(?:uncorrelated|mismatched|extra|missing|duplicate|rejected|unknown(?:-status)?)"
        r".{0,60}(?:201\s+)?(?:response|item|result)?.{0,30}(?:is|counts?\s+as|treat.{0,10}as)\s+success",
        folded,
        re.S,
    ) or re.search(
        r"(?:uncorrelated|mismatched|extra|missing|duplicate|rejected|unknown(?:-status)?)"
        r".{0,100}(?:may|can|should)?\s*(?:be\s+)?"
        r"(?:reported|treated|counted)\s+as\s+success(?:ful)?",
        folded,
        re.S,
    ) or re.search(
        r"(?:count|report|treat).{0,30}(?:a\s+)?201.{0,60}"
        r"does\s+not\s+match.{0,60}(?:as\s+)?success(?:ful)?",
        folded,
        re.S,
    ) or re.search(
        r"ignore.{0,30}(?:the\s+)?body.{0,30}(?:of\s+)?(?:a\s+)?201"
        r".{0,50}(?:report|count|treat).{0,20}success",
        folded,
        re.S,
    ):
        issues.append(
            _issue(
                "WRITE_RESPONSE_CORRELATION_CONTRADICTION",
                relative,
                "uncorrelated, mismatched, rejected, or unknown write responses cannot count as success",
            )
        )
    if skill in BULK_SKILLS:
        if not (
            "normal bulk" in folded
            and "201" in folded
            and "one-to-one" in folded
            and "exactly one" in folded
            and "no extra" in folded
            and ("partial or unknown" in folded or "partial or an unknown" in folded)
            and "stops remaining writes" in folded
        ):
            issues.append(
                _issue(
                    "BULK_201_CORRELATION",
                    relative,
                    "normal bulk 201 data must correlate one-to-one with every intended item and no extras",
                )
            )
        missing = sorted(ACCESS_REQUEST_STATUSES - set(re.findall(r"\b[a-z][a-z0-9_]*\b", text)))
        if missing or not (
            "classify" in folded and "actual status" in folded and "unknown" in folded
        ):
            issues.append(
                _issue(
                    "ACCESS_REQUEST_201_STATUS",
                    relative,
                    "classify every correlated AccessRequest 201 status exactly; missing: %s"
                    % (", ".join(missing) or "status handling"),
                )
            )
        optional_grantee_safe = all(
            term in normalized
            for term in (
                "`grantee_user_id` is optional",
                "exactly one confirmed grantee as context",
                "absence alone does not make the response unknown",
                "if `grantee_user_id` is present",
                "validate it as a uuid",
                "require an exact match",
            )
        )
        optional_grantee_contradiction = bool(
            re.search(
                r"(?:missing|absent).{0,30}(?:optional\s+)?`?grantee_user_id`?"
                r".{0,80}(?:makes?|mark|treat).{0,30}(?:unknown|invalid|error)",
                folded,
                re.S,
            )
            or re.search(
                r"`?grantee_user_id`?.{0,50}(?:must|required\s+to)\s+be\s+present",
                folded,
                re.S,
            )
        )
        if not optional_grantee_safe or optional_grantee_contradiction:
            issues.append(
                _issue(
                    "ACCESS_REQUEST_OPTIONAL_GRANTEE",
                    relative,
                    "missing optional grantee_user_id uses the one-grantee call context; a present value must match",
                )
            )
    if skill == "request-access" and not (
        "normal single" in folded
        and "201" in folded
        and "returned request" in folded
        and "intended" in folded
        and "mismatch" in folded
        and ("partial or unknown" in folded or "partial or an unknown" in folded)
    ):
        issues.append(
            _issue(
                "REQUEST_SINGLE_201_CORRELATION",
                relative,
                "a normal single 201 must correlate exactly to the intended request",
            )
        )
    if skill == "request-revocation":
        missing = sorted(
            ACCESS_REVOCATION_STATUSES - set(re.findall(r"\b[a-z][a-z0-9_]*\b", text))
        )
        if missing or not (
            "201" in folded
            and "correlat" in folded
            and "actual status" in folded
            and "unknown" in folded
        ):
            issues.append(
                _issue(
                    "ACCESS_REVOCATION_201_STATUS",
                    relative,
                    "correlate and classify processing_access, rejected, and revoked on normal 201 responses",
                )
            )
        if re.search(
            r"processing_access[^.!?\n]{0,50}(?:means|is|counts?\s+as)"
            r"[^.!?\n]{0,30}(?:access\s+was\s+removed|removed|complete|revoked)",
            folded,
        ):
            issues.append(
                _issue(
                    "ACCESS_REVOCATION_201_STATUS",
                    relative,
                    "processing_access is in progress and cannot mean access was removed",
                )
            )
        optional_field_contradiction = bool(
            re.search(
                r"(?:all\s+three\s+)?optional\s+correlation\s+fields.{0,50}"
                r"must\s+be\s+present.{0,80}(?:otherwise|or).{0,50}"
                r"(?:unknown|mark.{0,20}unknown)",
                folded,
                re.S,
            )
            or re.search(
                r"(?:missing|absent|absence\s+of)\s+(?:optional\s+)?`?resource_id`?"
                r".{0,80}(?:mismatch|error|invalid|unknown)",
                folded,
                re.S,
            )
            or re.search(
                r"permission_ids.{0,20}(?::|=|is)?\s*null.{0,80}"
                r"(?:matches?|correlates?).{0,50}(?:nonempty|non-empty)"
                r".{0,20}(?:permission|set)",
                folded,
                re.S,
            )
            or re.search(
                r"resource_id.{0,20}(?::|=|is)?\s*null.{0,80}"
                r"(?:matches?|correlates?).{0,50}resource-scoped",
                folded,
                re.S,
            )
        )
        if not (
            "unique response id" in normalized
            and "required `application_id` and `reason`" in normalized
            and "documented" in normalized
            and "`status`" in normalized
            and all(
                term in normalized
                for term in (
                    "`grantee_user_id`",
                    "`resource_id`",
                    "`permission_ids`",
                    "are optional",
                    "a missing optional field is unavailable correlation evidence",
                    "alone does not make the result unknown",
                    "validate it as a uuid or null",
                    "null matches only app-wide intent",
                    "validate it as a unique uuid array or null",
                    "interpret null as no permissions",
                    "matches only an empty intended permission set",
                    "nonempty array must match the complete intended set",
                )
            )
            and "missing required fields" in normalized
            and "any type error or mismatch" in normalized
            and "outcome" in normalized
            and "unknown" in normalized
            and "stops remaining writes" in normalized
        ) or optional_field_contradiction:
            issues.append(
                _issue(
                    "REVOCATION_201_CORRELATION",
                    relative,
                    "a normal revocation 201 must require documented fields and validate optional correlation fields only when present",
                )
            )
        completion_safe = any(
            "revoked" in paragraph
            and "refetch the exact source access state" in paragraph
            and bool(
                re.search(
                    r"present,?\s+non-null\s+`effective_end`"
                    r".{0,50}before saying removal is complete",
                    paragraph,
                )
            )
            and "inconsistent or unknown" in paragraph
            for paragraph in (
                re.sub(r"\s+", " ", value.casefold())
                for value in _paragraphs(text)
            )
        )
        if not completion_safe:
            issues.append(
                _issue(
                    "REVOCATION_COMPLETION_VERIFIED",
                    relative,
                    "revoked is complete only after the source state has a present non-null effective_end",
                )
            )
        if re.search(
            r"\brevoked\b.{0,80}(?:is|means|counts?\s+as|treat.{0,10}as)\s+"
            r"(?:complete|success).{0,80}(?:without|regardless\s+of).{0,30}effective_end",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REVOCATION_COMPLETION_CONTRADICTION",
                    relative,
                    "revoked cannot be called complete without verifying effective_end",
                )
            )
        if re.search(
            r"(?:declare|call|report).{0,50}(?:removal\s+)?complete"
            r".{0,80}\brevoked\b.{0,80}(?:even\s+if|when|while)"
            r".{0,30}effective_end.{0,20}(?:is\s+)?null",
            folded,
            re.S,
        ):
            issues.append(
                _issue(
                    "REVOCATION_COMPLETION_CONTRADICTION",
                    relative,
                    "revoked cannot be called complete while effective_end is null",
                )
            )
    return issues


def _validate_access_creation_invariants(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    if skill not in BULK_SKILLS:
        return []
    folded = text.casefold()
    issues: List[Issue] = []
    if (
        re.search(
            r"\b(?:approved|ignored|discovered)\b.{0,50}"
            r"(?:is|are|remains?|counts?\s+as)\s+requestable",
            folded,
            re.S,
        )
        or re.search(
            r"(?:submit|create).{0,60}\b(?:approved|ignored|discovered)\b.{0,30}application",
            folded,
            re.S,
        )
        or re.search(
            r"(?m)^\s*(?:submit|create)\b.{0,80}(?:request|access)"
            r".{0,80}application.{0,50}(?:status\s+(?:is|=)\s+)?"
            r"(?:approved|ignored|discovered)\b",
            folded,
        )
    ):
        issues.append(
            _issue(
                "APPLICATION_STATUS_CONTRADICTION",
                relative,
                "approved, ignored, and discovered applications are not requestable",
            )
        )
    if not (
        "status" in folded
        and "requestable" in folded
        and ("immediately before" in folded or "refetch" in folded)
        and ("stop" in folded or "remove" in folded)
    ):
        issues.append(
            _issue(
                "APPLICATION_MUST_BE_REQUESTABLE",
                relative,
                "every access-create path must revalidate application status=requestable",
            )
        )
    app_wide_paragraphs = [
        paragraph.casefold()
        for paragraph in _paragraphs(text)
        if "resource_id: null" in paragraph
        and (
            "app-wide" in paragraph.casefold()
            or "application-wide" in paragraph.casefold()
        )
    ]
    if skill in {"access-report", "mirror-access"}:
        app_wide_safe = any(
            "target" in paragraph
            and "active" in paragraph
            and ("block" in paragraph or "skip" in paragraph or "remove" in paragraph)
            and "narrower" in paragraph
            for paragraph in app_wide_paragraphs
        )
    else:
        app_wide_safe = any(
            "active" in paragraph and ("block" in paragraph or "skip" in paragraph)
            for paragraph in app_wide_paragraphs
        )
    app_wide_contradiction = bool(
        re.search(
            r"(?:ignore|bypass|disregard).{0,50}(?:active\s+)?"
            r"(?:app-wide|application-wide)\s+access.{0,80}"
            r"(?:create|submit|grant|narrower)",
            folded,
            re.S,
        )
    )
    if not app_wide_safe or app_wide_contradiction:
        issues.append(
            _issue(
                "APP_WIDE_REQUEST_BLOCKER",
                relative,
                "active app-wide access must be represented and block or safely skip resource-based creation",
            )
        )
    return issues


def _validate_reporting_and_csv_invariants(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    folded = text.casefold()
    normalized = re.sub(r"\s+", " ", folded)
    paragraphs = [
        re.sub(r"\s+", " ", paragraph.casefold()).strip()
        for paragraph in _paragraphs(text)
    ]
    issues: List[Issue] = []

    def require(code: str, passed: bool, message: str) -> None:
        if not passed:
            issues.append(_issue(code, relative, message))

    def has_paragraph(*needles: str) -> bool:
        folded_needles = tuple(needle.casefold() for needle in needles)
        return any(
            all(needle in paragraph for needle in folded_needles)
            for paragraph in paragraphs
        )

    if skill in {"list-access", "discovered-apps"}:
        effective_start_safe = any(
            "`effective_start`" in paragraph
            and "when the recorded access became effective" in paragraph
            and "access effective since" in paragraph
            and (
                "not when it was first discovered" in paragraph
                or "not a first-discovery timestamp" in paragraph
                or "not proof of first discovery" in paragraph
            )
            for paragraph in paragraphs
        )
        effective_start_contradiction = any(
            re.search(
                r"effective_start.{0,30}(?:is|means)\s+(?:the\s+)?"
                r"(?:first[- ]discovery|first discovered|discovery timestamp)",
                paragraph,
            )
            or re.search(
                r"(?:label|treat|use).{0,30}"
                r"(?:first[- ]discovery|first discovered|discovery timestamp)"
                r".{0,30}(?:as|for).{0,20}effective_start",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "EFFECTIVE_START_MEANING",
            effective_start_safe and not effective_start_contradiction,
            "effective_start is the access-effective time, not evidence of first discovery",
        )
        effective_start_timezone_safe = all(
            term in normalized
            for term in (
                "rfc3339 instant",
                "convert it to utc",
                "utc calendar date",
                "never use the machine's local timezone",
                "raw pre-offset date",
                "2026-01-01t00:30:00+02:00",
                "2025-12-31",
            )
        ) and bool(
            re.search(r"earliest(?:\s+valid)?\s+`effective_start`\s+instant", normalized)
        )
        effective_start_timezone_contradiction = bool(
            re.search(
                r"effective_start.{0,100}(?:machine|system|local)\s+timezone",
                normalized,
                re.S,
            )
            and not re.search(r"never\s+use.{0,50}(?:machine|system|local)\s+timezone", normalized)
        ) or bool(
            re.search(
                r"(?:use|preserve|display).{0,60}raw\s+(?:source\s+)?(?:calendar\s+)?date",
                normalized,
                re.S,
            )
        )
        require(
            "EFFECTIVE_START_TIMEZONE",
            effective_start_timezone_safe
            and not effective_start_timezone_contradiction,
            "effective_start must be compared as an instant and rendered with a deterministic UTC date",
        )

    if skill in {"access-report", "userlist-import-preflight"}:
        input_file_identity_safe = all(
            term in normalized
            for term in (
                "local file path",
                "open it without following symlinks",
                "opened object to be a regular file",
                "reject a symlink, fifo, socket, or device",
                "opened file descriptor",
                "device, inode, size, modification time, and change time",
                "stream from that same descriptor with the inclusive 10 mib input cap",
                "again after the read",
                "compare every recorded identity and metadata value",
                "if any value changed, stop as an unstable read",
                "never reopen the path between those checks",
                "uploaded attachment supplied as a stable byte snapshot",
            )
        )
        input_file_identity_contradiction = bool(
            re.search(
                r"(?<!never\s)(?<!do not\s)(?<!must not\s)"
                r"\b(?:follow|accept|allow|use)\b.{0,60}"
                r"(?:symlink|fifo|socket|device)",
                normalized,
            )
            or re.search(
                r"(?<!never\s)(?<!do not\s)(?<!must not\s)"
                r"reopen.{0,50}(?:path|file).{0,60}(?:after|between)"
                r".{0,40}(?:check|stat|metadata)",
                normalized,
            )
            or re.search(
                r"(?:file|metadata|identity).{0,40}(?:change\w*|differ\w*)"
                r".{0,60}(?:continue|proceed|ignore|use\s+the\s+data)",
                normalized,
            )
            or re.search(
                r"(?:continue|proceed|ignore|use\s+the\s+data).{0,50}"
                r"(?:if|when|after|despite).{0,40}"
                r"(?:file|metadata|identity).{0,40}(?:change\w*|differ\w*)",
                normalized,
            )
        )
        require(
            "INPUT_FILE_IDENTITY",
            input_file_identity_safe and not input_file_identity_contradiction,
            "local inputs must use one no-follow regular descriptor and fail closed on identity or metadata changes",
        )

    if skill == "access-report":
        distinct_users_safe = has_paragraph(
            "count distinct user ids",
            "not access-state rows",
            "must never count the same user twice",
            "conflicting identity data",
            "stop",
        )
        distinct_users_contradiction = any(
            re.search(
                r"(?:count|sum).{0,30}access-state rows.{0,50}(?:people|population|users?)",
                paragraph,
            )
            or re.search(
                r"same user.{0,40}(?:may|can|should).{0,20}(?:count twice|multiple times)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "REPORT_DISTINCT_USERS",
            distinct_users_safe and not distinct_users_contradiction,
            "population totals must count distinct user IDs, never access-state rows",
        )

        unlinked_safe = has_paragraph(
            "unlinked account",
            "grantee_user_account_id",
            "never add them to a people count",
            "separate counts",
            "state that the answer is incomplete",
            "do not create requests",
        )
        unlinked_contradiction = any(
            re.search(
                r"(?:add|sum|combine).{0,50}unlinked accounts?.{0,50}(?:people|user) count",
                paragraph,
            )
            or re.search(r"(?:drop|ignore).{0,40}unlinked accounts?", paragraph)
            for paragraph in paragraphs
        )
        require(
            "REPORT_UNLINKED_SEPARATE",
            unlinked_safe and not unlinked_contradiction,
            "unlinked accounts must be deduplicated and reported separately from linked people",
        )

        access_labels_safe = has_paragraph(
            "resource_id: null",
            "application-wide access",
            "resource-level access",
            "permission id, not title alone",
            "customer-facing labels still collide",
            "never drop an access state",
        )
        access_labels_contradiction = any(
            re.search(
                r"(?:drop|ignore|omit).{0,50}(?:application-wide|resource-level).{0,30}access",
                paragraph,
            )
            or re.search(r"group permissions by title alone", paragraph)
            for paragraph in paragraphs
        )
        require(
            "REPORT_ACCESS_LABELS",
            access_labels_safe and not access_labels_contradiction,
            "application-wide, resource-level, and permission-ID distinctions must remain explicit",
        )

        if not (
            "email" in folded
            and "authoritative" in folded
            and (
                re.search(r"do\s+not\s+fall\s+back", folded)
                or re.search(r"never\s+fall\s+back", folded)
                or "no name fallback" in folded
            )
            and ("only when no email" in folded or "no email value" in folded)
        ):
            issues.append(
                _issue(
                    "REPORT_EMAIL_AUTHORITATIVE",
                    relative,
                    "a supplied unmatched email remains unmatched; name matching is only for input without email",
                )
            )
        if not (
            re.search(r"10\s+m(?:i)?b", folded)
            and re.search(r"100,?000\s+logical", folded)
            and re.search(r"1,?000\s+columns", folded)
            and re.search(r"64\s+k(?:i)?b", folded)
            and "pasted" in folded
            and ("inclusive" in folded or "exact cap" in folded)
        ):
            issues.append(
                _issue(
                    "REPORT_INPUT_CAPS",
                    relative,
                    "reconciliation files and pasted input need inclusive 10 MiB, 100,000-record, 1,000-column, and 64 KiB-field caps",
                )
            )
    if skill == "userlist-import-preflight":
        malformed_csv_safe = has_paragraph(
            "parse quoted csv fields correctly",
            "never split rows on commas by hand",
            "invalid utf-8",
            "nul bytes",
            "an empty file",
            "duplicate headers",
            "missing or duplicate **email** header",
            "wrong number of fields",
            "do not produce a partial output file",
        )
        malformed_csv_contradiction = any(
            re.search(
                r"\b(?:accept|allow|ignore|continue past)\b.{0,80}"
                r"(?:invalid utf-8|nul bytes?|duplicate headers?|wrong number of fields|malformed csv)",
                paragraph,
            )
            or re.search(
                r"\b(?:may|can|should)\s+split\b.{0,40}\brows?\b.{0,20}\bcommas?\b",
                paragraph,
            )
            for paragraph in paragraphs
            if "csv" in paragraph or "quoted" in paragraph
        )
        require(
            "USERLIST_MALFORMED_CSV",
            malformed_csv_safe and not malformed_csv_contradiction,
            "malformed CSV structure must stop with no partial output",
        )

        email_boundary_safe = has_paragraph(
            "email cell",
            "one `@`",
            "local part of at most 64 characters",
            "at most 254 characters total",
            "domain labels",
            "at most 63 characters",
            "reject malformed values without correcting them",
        )
        email_boundary_contradiction = any(
            re.search(
                r"(?:local parts?|email).{0,50}(?:longer than 64|65 characters?).{0,40}"
                r"(?:accept|allow|valid)",
                paragraph,
            )
            or re.search(
                r"(?:emails?|total length).{0,50}(?:longer than 254|255 characters?).{0,40}"
                r"(?:accept|allow|valid)",
                paragraph,
            )
            or re.search(
                r"domain labels?.{0,50}(?:longer than 63|64 characters?).{0,40}"
                r"(?:accept|allow|valid)",
                paragraph,
            )
            for paragraph in paragraphs
            if "email" in paragraph or "domain label" in paragraph
        )
        require(
            "USERLIST_EMAIL_BOUNDARIES",
            email_boundary_safe and not email_boundary_contradiction,
            "email validation must enforce 64-character local, 254-character total, and 63-character domain-label limits",
        )

        flagged_status_safe = any(
            all(
                term in paragraph
                for term in (
                    "separately flag every match",
                    "`inactive`",
                    "`offboarding_planned`",
                    "`offboarding`",
                    "`offboarded`",
                    "explicitly keeps or removes every flagged row",
                    "unknown user status",
                    "stop",
                )
            )
            for paragraph in paragraphs
        )
        flagged_status_contradiction = any(
            re.search(
                r"(?:inactive|offboarding_planned|offboarding|offboarded).{0,80}"
                r"(?:is safe|are safe|without (?:confirmation|review)|import-ready)",
                paragraph,
            )
            or re.search(
                r"unknown (?:user )?status.{0,50}(?:assume|treat).{0,20}(?:safe|eligible)",
                paragraph,
            )
            or re.search(
                r"(?:continue|proceed).{0,50}(?:unknown|unrecognized)"
                r"(?: user)? status",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "USERLIST_FLAGGED_STATUSES",
            flagged_status_safe and not flagged_status_contradiction,
            "leaving and inactive users must remain flagged until explicitly kept or removed; unknown status stops",
        )

        artifact_safe = any(
            all(
                term in paragraph
                for term in (
                    "final csv as a stream",
                    "not as one in-memory string",
                    "random uuid",
                    "never derive a path",
                    "new regular file exclusively",
                    "owner-only mode `0600`",
                    "regardless of the process umask",
                    "do not follow symlinks",
                    "overwrite an existing path",
                    "at most 10 mib",
                    "byte 10 mib plus 1",
                    "close and remove the incomplete artifact",
                    "write or close failure",
                    "reopen without following symlinks",
                    "confirm it is the created regular file",
                    "verify its mode is exactly `0600`",
                    "parse it strictly again",
                    "verify the exact header",
                    "logical row count",
                    "expected entitlement values",
                )
            )
            for paragraph in paragraphs
        )
        artifact_contradiction = any(
            re.search(
                r"(?:acceptable|allowed|okay|may|can|should)\s+(?:to\s+)?"
                r"(?:overwrite an? existing path|follow symlinks?)",
                paragraph,
            )
            or re.search(
                r"(?:derive|build)\s+(?:the\s+)?(?:output\s+)?path.{0,50}"
                r"(?:application|api|customer).{0,20}(?:title|text|name)",
                paragraph,
            )
            or re.search(
                r"(?:leave|keep).{0,30}(?:partial|incomplete).{0,20}(?:csv|artifact|file)",
                paragraph,
            )
            or re.search(
                r"(?:skip|omit|do not)\s+(?:the\s+)?(?:reopen|re-?parse|verification)",
                paragraph,
            )
            or re.search(
                r"(?:mode\s+)?(?:0644|0666|world-readable|group-readable)"
                r".{0,40}(?:acceptable|allowed|okay|permitted)",
                paragraph,
            )
            for paragraph in paragraphs
            if "csv" in paragraph or "artifact" in paragraph or "output" in paragraph
        )
        require(
            "USERLIST_SECURE_ARTIFACT",
            artifact_safe and not artifact_contradiction,
            "stream output to a random exclusive 0600 regular file, enforce and clean up at 10 MiB, then securely reopen, verify, and reparse it",
        )

        if not (
            "resource_id: null" in text
            and "application-wide access" in folded
            and "blocker" in folded
            and "withhold" in folded
        ):
            issues.append(
                _issue(
                    "USERLIST_APP_WIDE_BLOCKER",
                    relative,
                    "application-wide access that CSV cannot represent must block and withhold output",
                )
            )
        if not (
            (
                "entitlement-level" in folded
                or "every entitlement" in folded
                or "every current resource or permission missing" in folded
            )
            and (
                "permission change" in folded
                or "changed permission" in folded
                or "current resource or permission missing" in folded
            )
            and ("removed" in folded or "remove" in folded or "removal" in folded)
            and "replacement" in folded
        ):
            issues.append(
                _issue(
                    "USERLIST_ENTITLEMENT_DIFF",
                    relative,
                    "replacement analysis must diff every entitlement, including changed or removed permissions for retained users",
                )
            )
        if not (
            "inclusive" in folded
            and ("exact cap" in folded or "exactly" in folded)
            and ("cap + 1" in folded or "cap+1" in folded or "next byte" in folded)
        ):
            issues.append(
                _issue(
                    "USERLIST_CAP_BOUNDARY",
                    relative,
                    "CSV limits are inclusive: exact cap is accepted and cap+1 is rejected with no output",
                )
            )
    if skill == "vendor-update":
        date_safe = has_paragraph(
            "`last_vendor_review_at`",
            "real calendar date",
            "yyyy-mm-dd",
            "reject impossible dates",
        )
        date_contradiction = any(
            re.search(
                r"(?:accept|allow|normalize|roll over).{0,40}impossible (?:calendar )?dates?",
                paragraph,
            )
            or re.search(
                r"impossible (?:calendar )?dates?.{0,40}(?:are|as).{0,20}(?:valid|accepted)",
                paragraph,
            )
            for paragraph in paragraphs
            if "date" in paragraph
        )
        require(
            "VENDOR_REAL_DATE",
            date_safe and not date_contradiction,
            "vendor review dates must be real calendar dates; impossible dates are rejected",
        )

        replacement_lists_safe = any(
            all(
                term in paragraph
                for term in (
                    "certificates, data types, and tags replace",
                    "fetch the application's current values first",
                    "send the combined list",
                    "nothing already recorded is dropped",
                )
            )
            for paragraph in paragraphs
        )
        notes_safe = any(
            all(
                term in paragraph
                for term in (
                    "refetch the latest notes",
                    "append the new statement",
                    "without replacing or rewriting any existing note content",
                )
            )
            for paragraph in paragraphs
        )
        replacement_contradiction = any(
            re.search(
                r"(?:send|patch|write)\s+only\s+(?:the\s+)?(?:new|requested|added).{0,30}"
                r"(?:certificate|data type|tag|list)",
                paragraph,
            )
            or re.search(
                r"(?:replace|rewrite|discard)\s+(?:the\s+)?(?:current|existing)\s+notes?",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "VENDOR_REPLACEMENT_AND_NOTES",
            replacement_lists_safe and notes_safe and not replacement_contradiction,
            "replacement lists must preserve current values, and notes must append without rewriting existing content",
        )

        tag_safe = has_paragraph(
            "existing tags are response objects",
            "carry forward their `title` strings",
            "not tag ids or raw objects",
        )
        tag_contradiction = any(
            re.search(
                r"(?:send|patch)\s+(?:the\s+)?(?:raw tag objects?|tag ids?)"
                r"|carry forward\s+(?:the\s+)?(?:raw tag objects?|tag ids?)",
                paragraph,
            )
            for paragraph in paragraphs
            if "tag" in paragraph
        )
        require(
            "VENDOR_TAG_TITLES",
            tag_safe and not tag_contradiction,
            "existing tag response objects must be converted to title strings, never sent as IDs or raw objects",
        )

        owner_safe = any(
            all(
                term in paragraph
                for term in (
                    "owner",
                    "application admins",
                    "`get /users?status=all&limit=100`",
                    "do not assign an `inactive`, `offboarding`, or `offboarded` person",
                    "`offboarding_planned`",
                    "explicit confirmation",
                    "unknown status",
                    "stop",
                )
            )
            for paragraph in paragraphs
        )
        owner_contradiction = any(
            re.search(
                r"(?:may|can|should)\s+assign.{0,60}"
                r"(?:inactive|offboarding|offboarded).{0,30}(?:owner|admin|person)?",
                paragraph,
            )
            or re.search(
                r"(?:inactive|offboarding|offboarded).{0,50}(?:is|are).{0,20}eligible",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "VENDOR_OWNER_STATUS",
            owner_safe and not owner_contradiction,
            "owners and application admins must be status-checked; ineligible or unknown users cannot be assigned",
        )

        user_fields_safe = any(
            all(
                term in re.sub(r"\s+", " ", paragraph)
                for term in (
                    "`owner_user_id`",
                    "one resolved uuid string or `null`",
                    "`admin_user_ids`",
                    "internally unique array of resolved uuid strings",
                    "`[]` clears all application admins",
                    "never send names, email addresses, user objects",
                )
            )
            for paragraph in paragraphs
        ) and any(
            "`admin_user_ids` is also a complete replacement array"
            in re.sub(r"\s+", " ", paragraph)
            and "complete recomputed array" in re.sub(r"\s+", " ", paragraph)
            and "`lock_version` safety rule" in re.sub(r"\s+", " ", paragraph)
            for paragraph in paragraphs
        )
        user_fields_contradiction = any(
            re.search(
                r"`?(?:owner_user_id|admin_user_ids)`?.{0,60}"
                r"(?:send|use|supply).{0,40}(?:person\s+)?(?:name|email|object)"
                r".{0,40}(?:instead\s+of|rather\s+than).{0,20}(?:uuid|array)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "VENDOR_USER_FIELD_SHAPES",
            user_fields_safe and not user_fields_contradiction,
            "owner_user_id is a nullable UUID and admin_user_ids is a complete replacement array of unique UUIDs",
        )

    if skill == "view-policies":
        application_refs_safe = any(
            "application_ids" in paragraph
            and "present" in paragraph
            and "internally unique" in paragraph
            and "fully resolvable" in paragraph
            and "complete application list" in paragraph
            for paragraph in paragraphs
        )
        application_refs_contradiction = any(
            re.search(
                r"(?:missing|duplicate|unresolved).{0,40}application_ids?.{0,40}"
                r"(?:ignore|allow|continue|acceptable)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "POLICY_APPLICATION_REFERENCES",
            application_refs_safe and not application_refs_contradiction,
            "policy application IDs must be present, unique, and resolvable to the complete application list",
        )

        default_safe = any(
            all(
                term in paragraph
                for term in (
                    "exactly one policy with `default_policy: true`",
                    "zero or several is inconsistent data",
                    "stops that claim",
                )
            )
            for paragraph in paragraphs
        )
        default_contradiction = any(
            re.search(
                r"(?:if|when).{0,30}(?:several|multiple|zero|more\s+than\s+one)"
                r".{0,40}default.{0,50}"
                r"(?:use|choose|pick|continue|acceptable)",
                paragraph,
            )
            or re.search(
                r"(?:two|several|multiple|more\s+than\s+one)\s+defaults?"
                r".{0,80}(?:select|choose|use|pick)(?:ing)?\s+(?:the\s+)?first",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "POLICY_EXACTLY_ONE_DEFAULT",
            default_safe and not default_contradiction,
            "fallback claims require exactly one default policy; zero or multiple defaults stop",
        )

        cross_scope_safe = any(
            "ordinary and elevated" in paragraph
            and "not state" in paragraph
            and "exclusive" in paragraph
            and "may appear in several" in paragraph
            and "never invent a move, removal" in paragraph
            and "precedence rule" in paragraph
            for paragraph in paragraphs
        )
        cross_scope_contradiction = any(
            re.search(
                r"ordinary and elevated.{0,80}(?:mutually exclusive|cannot overlap|must not overlap)",
                paragraph,
            )
            or re.search(
                r"(?:always|must|should)\s+(?:move|remove).{0,80}(?:ordinary|elevated)\s+policy",
                paragraph,
            )
            or re.search(
                r"(?:ordinary|elevated)\s+(?:policy\s+)?(?:membership|scope)"
                r".{0,40}(?:rules?\s+out|excludes?|precludes?|prevents?)"
                r".{0,40}(?:ordinary|elevated)\s+(?:policy\s+)?(?:membership|scope)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "POLICY_CROSS_SCOPE_OVERLAP",
            cross_scope_safe and not cross_scope_contradiction,
            "ordinary and elevated memberships are separate, potentially overlapping scopes with no invented move or precedence",
        )

    if skill == "list-access":
        identity_safe = any(
            "collapse rows by application id" in paragraph
            and "permission id, not by title" in paragraph
            and "resource-level access" in paragraph
            and "application-wide access" in paragraph
            and "instead of dropping it" in paragraph
            for paragraph in paragraphs
        )
        identity_contradiction = any(
            re.search(
                r"(?:collapse|deduplicate|group).{0,40}(?:application|permission).{0,20}"
                r"(?<!not\s)by title",
                paragraph,
            )
            or re.search(r"(?:drop|omit|ignore).{0,40}(?:application-wide|resource-level) access", paragraph)
            for paragraph in paragraphs
        )
        require(
            "LIST_IDENTITY_AND_ROLE",
            identity_safe and not identity_contradiction,
            "list-access must deduplicate by IDs and preserve resource-level and application-wide roles",
        )

        discovered_snapshot_safe = any(
            "status: discovered" in paragraph
            and "discovered usage, not access managed" in paragraph
            and "discovered entry is a snapshot" in paragraph
            and "never describe it as active" in paragraph
            for paragraph in paragraphs
        ) and any(
            "collapse states by application id" in paragraph
            and "earliest valid `effective_start`" in paragraph
            and "never emit duplicate applications" in paragraph
            for paragraph in paragraphs
        )
        discovered_snapshot_contradiction = any(
            re.search(r"discovered.{0,40}(?:currently active|still active|managed access)", paragraph)
            or re.search(r"(?:latest|most\s+recent|arbitrary).{0,30}effective_start", paragraph)
            for paragraph in paragraphs
        )
        require(
            "LIST_DISCOVERED_SNAPSHOT",
            discovered_snapshot_safe and not discovered_snapshot_contradiction,
            "discovered follow-up rows are snapshots deduplicated by app with the earliest valid date",
        )

        active_only_safe = any(
            "`effective_end` field is present and explicitly null" in paragraph
            and "are active" in paragraph
            and "show only those" in paragraph
            and "missing, malformed, or non-null value is unknown, not active" in paragraph
            for paragraph in paragraphs
        ) and any(
            "do not mention what ended, expired, or was revoked" in paragraph
            for paragraph in paragraphs
        )
        active_only_contradiction = any(
            re.search(
                r"(?:always\s+)?(?:show|include|report).{0,50}(?:ended|expired|revoked)\s+access",
                paragraph,
            )
            or re.search(
                r"effective_end.{0,50}(?:non-null|missing|any value).{0,50}"
                r"(?:is active|are active|show|include)",
                paragraph,
            )
            or re.search(
                r"(?:missing|absent|omitted).{0,30}effective_end.{0,50}"
                r"(?:is active|are active|treat.{0,15}as active|show|include)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "LIST_ACTIVE_ONLY",
            active_only_safe and not active_only_contradiction,
            "list-access output must include only effective_end:null access and omit ended, expired, or revoked access",
        )

        email_hidden_safe = any(
            "trimmed nonblank `full_name`" in paragraph
            and "if it is unavailable" in paragraph
            and "validated nonblank email address" in paragraph
            and "bare email" in paragraph
            and "never use link syntax" in paragraph
            for paragraph in paragraphs
        )
        email_hidden_contradiction = any(
            re.search(
                r"(?:always|normally|generally|should)\s+(?:show|include|display).{0,50}"
                r"(?:person's )?email",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "LIST_EMAIL_HIDDEN",
            email_hidden_safe and not email_hidden_contradiction,
            "list-access prefers full_name and uses bare email only as a verified fallback or disambiguator",
        )

    if skill == "discovered-apps":
        dedupe_safe = any(
            "collapse active states by `(application_id, grantee_user_id)`" in paragraph
            and "collapse by `(application_id, grantee_user_account_id)`" in paragraph
            and "earliest `effective_start`" in paragraph
            and "per-person list, collapse by application id" in paragraph
            and "stop as inconsistent" in paragraph
            for paragraph in paragraphs
        )
        dedupe_contradiction = any(
            re.search(
                r"distinct access-state ids?.{0,40}"
                r"(?<!not\s)(?:mean|imply|count as).{0,30}distinct",
                paragraph,
            )
            or re.search(r"(?:latest|arbitrary).{0,30}effective_start", paragraph)
            for paragraph in paragraphs
        )
        require(
            "DISCOVERED_DEDUPE_EARLIEST",
            dedupe_safe and not dedupe_contradiction,
            "discovered results must deduplicate by stable identities and use the earliest effective_start",
        )

        unlinked_aggregate_safe = any(
            "aggregate all unlinked rows into one" in paragraph
            and "unlinked accounts (n)" in paragraph
            and "earliest applicable access effective date" in paragraph
            and "never emit several indistinguishable" in paragraph
            for paragraph in paragraphs
        )
        unlinked_aggregate_contradiction = any(
            re.search(
                r"(?<!never\s)(?<!do\snot\s)(?:emit|show|list).{0,40}"
                r"(?:each|several|multiple).{0,30}unlinked account",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "DISCOVERED_UNLINKED_AGGREGATION",
            unlinked_aggregate_safe and not unlinked_aggregate_contradiction,
            "per-application output must aggregate unlinked accounts and show the earliest date",
        )

        current_filter_safe = any(
            "`effective_end` field is present and explicitly null" in paragraph
            and "omitted or malformed `effective_end` is unknown, not active" in paragraph
            for paragraph in paragraphs
        ) and any(
            "never add words like \"still active\"" in paragraph
            for paragraph in paragraphs
        )
        current_filter_contradiction = any(
            re.search(
                r"(?:describe|label|call).{0,50}(?:discovered (?:entry|app)|every discovered)"
                r".{0,50}(?:still active|currently active|in use)",
                paragraph,
            )
            or re.search(
                r"(?:missing|omitted|malformed).{0,30}effective_end.{0,40}"
                r"(?:treat|assume|count|consider).{0,20}(?:as\s+)?active",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "DISCOVERED_NOT_CURRENT_ACTIVE",
            current_filter_safe and not current_filter_contradiction,
            "discovered rows need explicit null effective_end but must not be described as currently active",
        )

        separate_counts_safe = any(
            "linked-person counts" in paragraph
            and "unlinked account counts" in paragraph
            and "never add those unlike quantities into one count" in paragraph
            for paragraph in paragraphs
        ) and any(
            "separate **linked people** and **unlinked accounts** columns" in paragraph
            and "never label or sum the mixed quantities" in paragraph
            for paragraph in paragraphs
        )
        separate_counts_contradiction = any(
            re.search(
                r"(?:sum|add|combine).{0,40}linked (?:people|persons?).{0,40}"
                r"(?:and|with).{0,20}unlinked accounts?.{0,50}(?:one|single|people|count)",
                paragraph,
            )
            for paragraph in paragraphs
        )
        require(
            "DISCOVERED_SEPARATE_ACCOUNT_COUNTS",
            separate_counts_safe and not separate_counts_contradiction,
            "linked people and unlinked accounts are distinct units and must be counted and displayed separately",
        )
    return issues


def _validate_grant_access_semantics(
    skill: str, text: str, relative: Path | str
) -> List[Issue]:
    if skill != "grant-access":
        return []
    normalized = re.sub(r"\s+", " ", text.casefold())
    paragraphs = [
        re.sub(r"\s+", " ", paragraph.casefold())
        for paragraph in text.split("\n\n")
    ]
    issues: List[Issue] = []
    requirements: Sequence[Tuple[str, bool, str]] = (
        (
            "GRANT_SCOPE",
            "this is a direct write. it is not approval and it is not a new request" in normalized
            and "never approves requests" in normalized,
            "grant-access records completed provisioning but never approves or creates a request",
        ),
        (
            "GRANT_MANUAL_ELIGIBILITY",
            all(
                term in normalized
                for term in (
                    "`provisioning_type` is `application_admin`",
                    "exact request status is `processing_access`",
                    "only `processing_access` is eligible for granting",
                    "`pending_approval`",
                    "ineligible",
                    "never call the grant endpoint for an ineligible request",
                )
            ),
            "only a processing_access request for application_admin provisioning is grant-eligible",
        ),
        (
            "GRANT_EXACT_SELECTION",
            all(
                term in normalized
                for term in (
                    "require exactly one case-insensitive match",
                    "complete permission ids",
                    "never choose by a hidden id",
                )
            ),
            "resolve one exact person, application, request, resource, and permission set",
        ),
        (
            "GRANT_DUPLICATE_ACCESS",
            all(
                term in normalized
                for term in (
                    "exact application, resource, and complete permission set",
                    "different resource or permission",
                    "does not block this grant",
                    "exact requested access is already current",
                    "stop",
                    "duplicate state",
                )
            ),
            "block an exact current duplicate without blocking different access in the same app",
        ),
        (
            "GRANT_CONFIRMATION",
            "person, application, resource, and complete permission set" in normalized
            and "clearly confirms that provisioning is complete" in normalized
            and "earlier request to create or approve access" in normalized,
            "confirm the exact completed provisioning immediately before granting",
        ),
        (
            "GRANT_RESPONSE_CORRELATION",
            all(
                term in normalized
                for term in (
                    "exact documented success status is `200`",
                    "same request id, grantee, application, resource, and complete permission set",
                    "status exactly `access_granted`",
                    "exactly one current access state",
                    "zero or multiple exact matches",
                    "outcome as unknown",
                )
            ),
            "correlate the 200 response and verify exactly one matching current state",
        ),
        (
            "GRANT_422_FAIL_CLOSED",
            any(
                all(
                    term in paragraph
                    for term in (
                        "on `422`",
                        "did not consider the request grant-eligible",
                        "never infer approval",
                        "retry with a new body or key",
                    )
                )
                for paragraph in paragraphs
            ),
            "422 must stop without inferring approval or synthesizing another grant",
        ),
    )
    for code, passed, message in requirements:
        if not passed:
            issues.append(_issue(code, relative, message))
    contradictions = (
        r"pending_approval.{0,80}(?:is|counts?\s+as|treat.{0,20}as).{0,30}grant-eligible",
        r"(?:grant|mark).{0,80}pending_approval",
        r"(?:different|other).{0,30}(?:resource|permission).{0,50}(?<!not )(?:blocks?|prevents?).{0,30}grant",
        r"(?:response\s+status|http\s+200).{0,60}(?:alone|by itself).{0,40}(?:proves?|confirms?).{0,30}grant",
        r"(?<!never )(?<!not )(?:skip|omit).{0,40}(?:confirmation|current\s+access|read-back|verification)",
    )
    if any(re.search(pattern, normalized, re.S) for pattern in contradictions):
        issues.append(
            _issue(
                "GRANT_CONTRADICTION",
                relative,
                "unsafe prose must not bypass approval, duplicate, confirmation, or read-back checks",
            )
        )
    return issues


def validate_write_safety_text(skill: str, text: str, relative: Path | str) -> List[Issue]:
    issues: List[Issue] = []
    if skill in WRITE_SKILLS:
        issues.extend(_validate_idempotency(skill, text, relative))
        issues.extend(_validate_write_redirects(skill, text, relative))
        issues.extend(_validate_concurrency(skill, text, relative))
        issues.extend(_validate_reason_and_bulk(skill, text, relative))
        issues.extend(_validate_stale_retry(skill, text, relative))
        issues.extend(_validate_mutation_bounds(skill, text, relative))
        issues.extend(_validate_write_response_correlation(skill, text, relative))
    if skill in REQUEST_DEDUPE_SKILLS:
        issues.extend(_validate_request_dedupe(skill, text, relative))
        issues.extend(_validate_request_visibility(skill, text, relative))
        issues.extend(_validate_422_failure_semantics(skill, text, relative))
    if skill in TARGET_STATUS_SKILLS:
        issues.extend(_validate_target_statuses(skill, text, relative))
    issues.extend(_validate_access_creation_invariants(skill, text, relative))
    issues.extend(_validate_openapi_field_semantics(skill, text, relative))
    issues.extend(_validate_reporting_and_csv_invariants(skill, text, relative))
    issues.extend(_validate_destructive_invariants(skill, text, relative))
    issues.extend(_validate_grant_access_semantics(skill, text, relative))
    return issues


def validate_write_safety(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    for skill, relative, text, read_issues in _skill_documents(root):
        issues.extend(read_issues)
        if text is None:
            continue
        issues.extend(validate_write_safety_text(skill, text, relative))
    return issues


def _strip_unquoted_yaml_comment(line: str) -> str:
    """Return one YAML line with only its active, non-comment text."""

    in_single = False
    in_double = False
    escaped = False
    index = 0
    while index < len(line):
        character = line[index]
        if in_single:
            if character == "'":
                if index + 1 < len(line) and line[index + 1] == "'":
                    index += 2
                    continue
                in_single = False
        elif in_double:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_double = False
        elif character == "'":
            in_single = True
        elif character == '"':
            in_double = True
        elif character == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
        index += 1
    return line.rstrip()


def _active_yaml_text(text: str) -> str:
    return "\n".join(_strip_unquoted_yaml_comment(line) for line in text.splitlines())


def _yaml_blocks(text: str, key: str, indent: int) -> List[List[str]]:
    """Extract active block lines for a semantic YAML key and exact indentation."""

    lines = text.splitlines()
    header_pattern = re.compile(
        r"^%s(?:%s|'%s'|\"%s\")[ ]*:[ ]*$"
        % (" " * indent, re.escape(key), re.escape(key), re.escape(key))
    )
    blocks: List[List[str]] = []
    for index, line in enumerate(lines):
        if header_pattern.fullmatch(line) is None:
            continue
        block = [line]
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            if candidate_indent <= indent:
                break
            block.append(candidate)
        blocks.append(block)
    return blocks


def _yaml_scalar_lines(text: str, key: str) -> List[str]:
    escaped = re.escape(key)
    pattern = re.compile(
        r"^ *(?:%s|'%s'|\"%s\")[ ]*:[ ]*.*$" % (escaped, escaped, escaped)
    )
    return [line for line in text.splitlines() if pattern.fullmatch(line)]


def validate_ci(root: Path) -> List[Issue]:
    issues: List[Issue] = []
    workflow_directory = root / WORKFLOW_PATH.parent
    try:
        with os.scandir(workflow_directory) as iterator:
            workflow_entries = sorted(entry.name for entry in iterator)
    except OSError as exc:
        workflow_entries = []
        issues.append(_issue("CI_WORKFLOW_INVENTORY", WORKFLOW_PATH.parent, str(exc)))
    expected_workflow_entries = sorted(
        (WORKFLOW_PATH.name, SYNC_WORKFLOW_PATH.name)
    )
    if workflow_entries != expected_workflow_entries:
        issues.append(
            _issue(
                "CI_WORKFLOW_INVENTORY",
                WORKFLOW_PATH.parent,
                "workflows must be exactly %s"
                % ", ".join(expected_workflow_entries),
            )
        )
    sync_text, sync_workflow_issues = read_text(
        root / SYNC_WORKFLOW_PATH, SYNC_WORKFLOW_PATH
    )
    issues.extend(sync_workflow_issues)
    if sync_text is not None:
        sync_active = _active_yaml_text(sync_text)
        sync_active_lines = tuple(
            line.rstrip() for line in sync_active.splitlines() if line.strip()
        )
        if sync_active_lines != EXPECTED_SYNC_WORKFLOW_ACTIVE_LINES:
            issues.append(
                _issue(
                    "CI_SYNC_EXACT_SHAPE",
                    SYNC_WORKFLOW_PATH,
                    "fork sync must retain its reviewed trigger, guard, permissions, pinned action, and ff-only commands",
                )
            )
    for relative in CORE_HARNESS_FILES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            issues.append(
                _issue(
                    "CI_HARNESS_FILE",
                    relative,
                    "required regular harness file is missing",
                )
            )

    text, workflow_issues = read_text(root / WORKFLOW_PATH, WORKFLOW_PATH)
    issues.extend(workflow_issues)
    if text is None:
        return issues
    active = _active_yaml_text(text)
    active_lines = tuple(line.rstrip() for line in active.splitlines() if line.strip())
    if active_lines != EXPECTED_WORKFLOW_ACTIVE_LINES:
        issues.append(
            _issue(
                "CI_EXACT_SHAPE",
                WORKFLOW_PATH,
                "active workflow must exactly match the reviewed execution shape",
            )
        )

    if _yaml_blocks(active, "on", 0) != [["on:", "  pull_request:", "  push:"]]:
        issues.append(
            _issue(
                "CI_TRIGGERS",
                WORKFLOW_PATH,
                "workflow must enable unfiltered pull_request and push triggers",
            )
        )

    if _yaml_blocks(active, "permissions", 0) != [
        ["permissions:", "  contents: read"]
    ]:
        issues.append(
            _issue(
                "CI_PERMISSIONS",
                WORKFLOW_PATH,
                "workflow permissions must be exactly contents: read",
            )
        )
    if re.search(r"(?mi):\s*write\s*$|\bwrite-all\b", active):
        issues.append(
            _issue("CI_WRITE_PERMISSION", WORKFLOW_PATH, "workflow must not request write permissions")
        )
    expected_concurrency = [
        "concurrency:",
        "  group: adversarial-contract-${{ github.workflow }}-${{ github.ref }}",
        "  cancel-in-progress: true",
    ]
    if (
        _yaml_blocks(active, "concurrency", 0) != [expected_concurrency]
        or _yaml_scalar_lines(active, "timeout-minutes") != ["    timeout-minutes: 5"]
    ):
        issues.append(
            _issue("CI_BOUNDS", WORKFLOW_PATH, "workflow needs five-minute timeout and canceling concurrency")
        )
    expected_matrix = ["      matrix:", "        python-version: ['3.9', '3.12']"]
    expected_python_lines = [
        "        python-version: ['3.9', '3.12']",
        "          python-version: ${{ matrix.python-version }}",
    ]
    if (
        _yaml_blocks(active, "matrix", 6) != [expected_matrix]
        or _yaml_scalar_lines(active, "python-version") != expected_python_lines
    ):
        issues.append(
            _issue(
                "CI_PYTHON_MATRIX",
                WORKFLOW_PATH,
                "matrix must test only Python 3.9 and 3.12 and setup-python must use it",
            )
        )
    actions = re.findall(
        r"(?m)^[ \t]*(?:-[ \t]+)?(?:uses|['\"]uses['\"])[ \t]*:[ \t]*([^\s#]+)",
        active,
    )
    expected_actions = {"actions/checkout", "actions/setup-python"}
    seen_actions: Set[str] = set()
    for action in actions:
        if "@" not in action:
            issues.append(_issue("CI_ACTION_PIN", WORKFLOW_PATH, "action is not pinned: %s" % action))
            seen_actions.add(action)
            continue
        name, revision = action.rsplit("@", 1)
        seen_actions.add(name)
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            issues.append(
                _issue("CI_ACTION_PIN", WORKFLOW_PATH, "%s must use a full 40-character SHA" % name)
            )
    if seen_actions != expected_actions:
        issues.append(
            _issue(
                "CI_ACTION_SET",
                WORKFLOW_PATH,
                "workflow must use only checkout and setup-python actions",
            )
        )
    expected_checkout = "actions/checkout@%s" % CHECKOUT_ACTION_SHA
    expected_setup = "actions/setup-python@%s" % SETUP_PYTHON_ACTION_SHA
    if actions.count(expected_checkout) != 1:
        issues.append(
            _issue("CI_CHECKOUT_SHA", WORKFLOW_PATH, "checkout must use the reviewed pinned SHA")
        )
    if actions.count(expected_setup) != 1:
        issues.append(
            _issue(
                "CI_SETUP_PYTHON_SHA",
                WORKFLOW_PATH,
                "setup-python must use the reviewed pinned SHA",
            )
        )
    if len(actions) != 2:
        issues.append(
            _issue(
                "CI_ACTION_SET",
                WORKFLOW_PATH,
                "workflow must contain exactly one checkout and one setup-python action",
            )
        )
    if _yaml_scalar_lines(active, "persist-credentials") != [
        "          persist-credentials: false"
    ]:
        issues.append(
            _issue("CI_CREDENTIALS", WORKFLOW_PATH, "checkout credentials must not persist")
        )
    if _yaml_scalar_lines(active, "runs-on") != ["    runs-on: ubuntu-24.04"]:
        issues.append(_issue("CI_RUNNER_IMAGE", WORKFLOW_PATH, "runner must be pinned to ubuntu-24.04"))
    if (
        _yaml_scalar_lines(active, "PYTHONHASHSEED") != ["          PYTHONHASHSEED: '0'"]
        or _yaml_scalar_lines(active, "TZ") != ["          TZ: UTC"]
    ):
        issues.append(
            _issue("CI_DETERMINISM", WORKFLOW_PATH, "set PYTHONHASHSEED=0 and TZ=UTC")
        )
    run_directives = re.findall(
        r"(?m)^[ \t]*(?:-[ \t]+)?(?:run|['\"]run['\"])[ \t]*:[^\n]*$", active
    )
    if run_directives != ["        run: python tests/run_tests.py"]:
        issues.append(
            _issue(
                "CI_RUNNER",
                WORKFLOW_PATH,
                "workflow must contain exactly the executable run: python tests/run_tests.py step",
            )
        )
    if re.search(
        r"(?mi)^[ \t]*(?:-[ \t]+)?(?:continue-on-error|['\"]continue-on-error['\"])[ \t]*:",
        active,
    ):
        issues.append(
            _issue(
                "CI_CONTINUE_ON_ERROR",
                WORKFLOW_PATH,
                "continue-on-error is forbidden for the contract job",
            )
        )
    if re.search(
        r"(?mi)^[ \t]*(?:-[ \t]+)?(?:if|['\"]if['\"])[ \t]*:", active
    ):
        issues.append(
            _issue(
                "CI_CONDITIONAL_EXECUTION",
                WORKFLOW_PATH,
                "conditional jobs and steps are forbidden because they can skip validation",
            )
        )
    if re.search(
        r"(?mi)^[ \t]*(?:-[ \t]+)?(?:shell|['\"]shell['\"])[ \t]*:", active
    ) or re.search(r"(?mi)^[ \t]*(?:defaults|['\"]defaults['\"])[ \t]*:", active):
        issues.append(
            _issue(
                "CI_SHELL_OVERRIDE",
                WORKFLOW_PATH,
                "custom shells are forbidden because they can avoid executing the runner",
            )
        )
    return issues


def validate_repository(root: Path) -> List[Issue]:
    issues = validate_repository_files(root)
    fatal_filesystem_codes = {
        "TREE_ENTRY_LIMIT",
        "TREE_DEPTH_LIMIT",
        "TREE_UNREADABLE",
        "REPOSITORY_BYTE_LIMIT",
        "FILE_TOO_LARGE",
        "FILE_UNSAFE",
        "FILE_CHANGED",
        "FILE_NOT_REGULAR",
        "SYMLINK_FORBIDDEN",
    }
    if any(issue.code in fatal_filesystem_codes for issue in issues):
        return sorted(set(issues))
    validators: Sequence[Callable[[Path], List[Issue]]] = (
        validate_repository_inventory,
        validate_approved_content,
        validate_approved_harness,
        validate_skill_inventory,
        validate_manifests_and_readme,
        validate_style_guide,
        validate_api_contracts,
        validate_read_safety,
        validate_write_safety,
        validate_ci,
    )
    for validator in validators:
        issues.extend(validator(root))
    return sorted(set(issues))
