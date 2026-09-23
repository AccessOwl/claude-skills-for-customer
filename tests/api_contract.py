"""Pinned, reviewed data tables for the repository contract suite.

Standard-library-only leaf module: it imports nothing from contract_validator.
contract_validator.py imports and re-exports every name here, so existing
imports keep working. Trust chain: contract_validator.py is the unpinned root;
its APPROVED_HARNESS_SHA256 pins this file's digest, and this file pins the
instruction content digests (APPROVED_CONTENT_SHA256).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Tuple


SKILL_ROOT = Path("plugins/accessowl/skills")
API_RULES_RELATIVE = Path("references/api-rules.md")

API_RULES_POINTER_SENTENCE = (
    "Before the first API call, read `references/api-rules.md` in this skill folder and follow it."
)
MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")
PLUGIN_MANIFEST_PATH = Path("plugins/accessowl/.claude-plugin/plugin.json")
CODEX_MARKETPLACE_PATH = Path(".agents/plugins/marketplace.json")
CODEX_PLUGIN_MANIFEST_PATH = Path("plugins/accessowl/.codex-plugin/plugin.json")
WORKFLOW_PATH = Path(".github/workflows/adversarial-tests.yml")
SYNC_WORKFLOW_PATH = Path(".github/workflows/sync-upstream.yml")

EXPECTED_MARKETPLACE_NAME = "accessowl-claude-skills"
EXPECTED_PLUGIN_NAME = "claudetag-for-accessowl"
# The Codex marketplace and its only plugin intentionally share this name.
EXPECTED_CODEX_PLUGIN_NAME = "accessowl-skills"
EXPECTED_DISPLAY_NAME = "AccessOwl Skills"
EXPECTED_CODEX_HOMEPAGE = "https://docs.accessowl.com/guides/ai/accessowl-skills"
EXPECTED_CODEX_POLICY = {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
# Same value the Claude PLUGIN_AUTHOR and MARKETPLACE_OWNER checks require.
EXPECTED_AUTHOR = {"name": "AccessOwl", "url": "https://github.com/AccessOwl"}
EXPECTED_PLUGIN_SOURCE = "./plugins/accessowl"
EXPECTED_PLUGIN_HOMEPAGE = "https://docs.accessowl.com/guides/ai/accessowl-skills"
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
    Path("tests/api_contract.py"),
    Path("tests/contract_validator.py"),
    Path("tests/run_tests.py"),
    Path("tests/skill_semantics.py"),
    Path("tests/test_adversarial_oracles.py"),
    Path("tests/test_api_semantic_oracles.py"),
    Path("tests/test_ci_manifest_oracles.py"),
    Path("tests/test_output_semantic_oracles.py"),
    Path("tests/test_repository_contract.py"),
    Path("tests/test_write_semantic_oracles.py"),
)

EXPECTED_SKILLS: Tuple[str, ...] = (
    "access-report",
    "close-request",
    "discovered-apps",
    "grant-access",
    "import-userlist",
    "list-access",
    "mirror-access",
    "offboard-user",
    "onboard-user",
    "request-access",
    "request-revocation",
    "vendor-update",
    "view-policies",
)
ALLOWED_REPOSITORY_FILES = frozenset(
    {
        Path("README.md"),
        Path("SKILL_STYLE.md"),
        MARKETPLACE_PATH,
        PLUGIN_MANIFEST_PATH,
        CODEX_MARKETPLACE_PATH,
        CODEX_PLUGIN_MANIFEST_PATH,
        WORKFLOW_PATH,
        SYNC_WORKFLOW_PATH,
    }
    | set(CORE_HARNESS_FILES)
    | {SKILL_ROOT / skill / "SKILL.md" for skill in EXPECTED_SKILLS}
    | {SKILL_ROOT / skill / API_RULES_RELATIVE for skill in EXPECTED_SKILLS}
)
APPROVED_CONTENT_SHA256: Mapping[Path, str] = {
    Path("README.md"): "1215b93334b2cb108a17571257298a8a016c85109c94c153465fafaea592a6e2",
    Path("SKILL_STYLE.md"): "f107d23881f0fd5b0db00af325c5131618f399292dcb416544a922e3cae53a68",
    SKILL_ROOT / "access-report" / "SKILL.md": "92287d7aa645ed8f19da7d49908f152f2114eadf97df201da986eca25422ce2c",
    SKILL_ROOT / "close-request" / "SKILL.md": "8929ba223407f7c8301a69d53d9c0e048c98daeb0919cb91a0b01d718c3b35be",
    SKILL_ROOT / "discovered-apps" / "SKILL.md": "7aea7fe5f24cb1978a930d3ee9b2279ca68744b75ef86428f481837c747b53eb",
    SKILL_ROOT / "grant-access" / "SKILL.md": "2b2fceb8ca3eefbc7ab6ffe586e313ade21db70dc6a52502d77b932b84ddd05c",
    SKILL_ROOT / "import-userlist" / "SKILL.md": "1ab19d46d2f60593c508a68186f9705e7afe74694bcd39c6e79dab314dde06e0",
    SKILL_ROOT / "list-access" / "SKILL.md": "3693984ed77b047aaa41c4fe4c8b9c2c96ab2a9ec5ffdcf413676f029908dfb5",
    SKILL_ROOT / "mirror-access" / "SKILL.md": "170a6624e952c3230ad0609acaaac897305c8b0cfcac1db158762231f86f490d",
    SKILL_ROOT / "offboard-user" / "SKILL.md": "a43abacc184fdf5f33aeacf6045797ff8ed4afb927eb8a29cbd1d29bdc34b18c",
    SKILL_ROOT / "onboard-user" / "SKILL.md": "4de5a4365e9b8c45d8fe114e788dec4890dccf83f55dfef975b965dae050c5f8",
    SKILL_ROOT / "request-access" / "SKILL.md": "2e77d57b60a1aca73cbc0df7e4b9216940000b35d2288d6d8bd091188f0c9f42",
    SKILL_ROOT / "request-revocation" / "SKILL.md": "a25058e628fcdfbb70ae31ec74d0910aee950bdbfd10ef936db90154e2bcb63a",
    SKILL_ROOT / "vendor-update" / "SKILL.md": "189f498b7daeb256e4ed8af65e62b1e4d604830185e52c364d7a27280de6357b",
    SKILL_ROOT / "view-policies" / "SKILL.md": "64b31b318ec336efd20a6559a360d9af7be32765b5c2e91971f21f16b704d7d2",
    SKILL_ROOT / "access-report" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "close-request" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "discovered-apps" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "grant-access" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "import-userlist" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "list-access" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "mirror-access" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "offboard-user" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "onboard-user" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "request-access" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "request-revocation" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "vendor-update" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
    SKILL_ROOT / "view-policies" / API_RULES_RELATIVE: "fff1fa2025879fe04c086f8bd3a46127051bc417d169ad20b2a1fab2ff7e0587",
}

# Curated from https://api.accessowl.com/api/openapi on 2026-09-23. The
# repository suite is intentionally offline and deterministic, so the facts
# that skill prose relies on are reviewed and pinned here.
API_OPERATIONS: Mapping[Tuple[str, str], frozenset[str]] = {
    ("GET", "/access_requests"): frozenset(
        {"limit", "cursor", "user_id", "application_id", "status"}
    ),
    ("POST", "/access_requests"): frozenset(),
    ("POST", "/access_requests/bulk"): frozenset(),
    ("GET", "/access_requests/{}"): frozenset(),
    ("POST", "/access_requests/{}/grant"): frozenset(),
    ("POST", "/access_requests/{}/deny"): frozenset(),
    ("POST", "/access_requests/{}/reject"): frozenset(),
    ("GET", "/access_revocations"): frozenset(
        {"limit", "cursor", "status", "user_id", "application_id"}
    ),
    ("POST", "/access_revocations"): frozenset(),
    ("GET", "/access_revocations/{}"): frozenset(),
    ("POST", "/access_revocations/{}/revoke"): frozenset(),
    ("POST", "/access_revocations/{}/reject"): frozenset(),
    ("GET", "/access_states"): frozenset(
        {"limit", "cursor", "application_id", "grantee_user_id", "expand"}
    ),
    ("GET", "/applications"): frozenset(
        {
            "limit",
            "cursor",
            "title_like",
            "category_contains_word",
            "status",
            "owner_user_id",
            "admin_user_id",
        }
    ),
    ("POST", "/applications"): frozenset(),
    ("GET", "/applications/{}/resources"): frozenset(),
    ("PUT", "/applications/{}/structure"): frozenset(),
    ("PUT", "/applications/{}/access_states"): frozenset(),
    ("GET", "/applications/{}"): frozenset(),
    ("PATCH", "/applications/{}"): frozenset(),
    ("PUT", "/applications/{}"): frozenset(),
    ("GET", "/policies"): frozenset({"limit", "cursor"}),
    ("PUT", "/policies/{}/applications"): frozenset(),
    ("GET", "/users"): frozenset({"limit", "cursor", "status", "email"}),
    ("POST", "/users"): frozenset(),
    ("GET", "/users/{}"): frozenset(),
    ("POST", "/users/{}/onboard"): frozenset(),
    ("POST", "/users/{}/offboard"): frozenset(),
}
CURSOR_ENDPOINTS = frozenset(
    {
        "/users",
        "/applications",
        "/access_states",
        "/access_requests",
        "/access_revocations",
        "/policies",
    }
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
    "close-request": frozenset(
        {("GET", "/users"), ("GET", "/applications"), ("GET", "/applications/{}/resources"),
         ("GET", "/access_requests"), ("GET", "/access_requests/{}"),
         ("POST", "/access_requests/{}/deny"), ("POST", "/access_requests/{}/reject")}
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
    "import-userlist": frozenset(
        {
            ("GET", "/users"),
            ("GET", "/applications"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("PUT", "/applications/{}/access_states"),
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
    "offboard-user": frozenset({("GET", "/users"), ("GET", "/users/{}"), ("POST", "/users/{}/offboard")}),
    "onboard-user": frozenset(
        {("GET", "/users"), ("GET", "/users/{}"), ("POST", "/users"), ("POST", "/users/{}/onboard")}
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
            ("GET", "/access_revocations"),
            ("GET", "/access_revocations/{}"),
            ("POST", "/access_revocations"),
            ("POST", "/access_revocations/{}/revoke"),
            ("POST", "/access_revocations/{}/reject"),
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
        {("GET", "/policies"), ("GET", "/applications"), ("GET", "/users")}
    ),
}
ALLOWED_OPERATIONS: Mapping[str, frozenset[Tuple[str, str]]] = {
    "access-report": REQUIRED_OPERATIONS["access-report"],
    "close-request": REQUIRED_OPERATIONS["close-request"],
    "discovered-apps": REQUIRED_OPERATIONS["discovered-apps"],
    "grant-access": REQUIRED_OPERATIONS["grant-access"],
    "import-userlist": REQUIRED_OPERATIONS["import-userlist"]
    | frozenset({("PUT", "/applications/{}/structure")}),
    "list-access": REQUIRED_OPERATIONS["list-access"],
    "mirror-access": REQUIRED_OPERATIONS["mirror-access"],
    "offboard-user": frozenset({("GET", "/users"), ("GET", "/users/{}"), ("POST", "/users/{}/offboard")}),
    "onboard-user": REQUIRED_OPERATIONS["onboard-user"],
    "request-access": REQUIRED_OPERATIONS["request-access"],
    "request-revocation": REQUIRED_OPERATIONS["request-revocation"],
    "vendor-update": REQUIRED_OPERATIONS["vendor-update"],
    "view-policies": REQUIRED_OPERATIONS["view-policies"]
    | frozenset({("PUT", "/policies/{}/applications")}),
}
REFUSED_OPERATIONS: Mapping[str, Tuple[str, str]] = {
    "import-userlist": ("PUT", "/applications/{}/structure"),
    "view-policies": ("PUT", "/policies/{}/applications"),
}

STATUS_ALL_SKILLS = frozenset(
    {
        "access-report",
        "close-request",
        "discovered-apps",
        "grant-access",
        "import-userlist",
        "list-access",
        "mirror-access",
        "offboard-user",
        "onboard-user",
        "request-access",
        "request-revocation",
        "vendor-update",
        "view-policies",
    }
)
EXPANSION_REQUIREMENTS: Mapping[str, frozenset[str]] = {
    "access-report": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
    "discovered-apps": frozenset({"grantee_user", "application"}),
    "grant-access": frozenset({"application", "resource", "target_permissions"}),
    "import-userlist": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
    "list-access": frozenset({"application", "resource", "target_permissions"}),
    "mirror-access": frozenset({"application", "resource", "target_permissions"}),
    "request-access": frozenset({"application", "resource", "target_permissions"}),
    "request-revocation": frozenset(
        {"grantee_user", "application", "resource", "target_permissions"}
    ),
}

WRITE_SKILLS = frozenset(
    {
        "access-report",
        "close-request",
        "grant-access",
        "import-userlist",
        "mirror-access",
        "offboard-user",
        "onboard-user",
        "request-access",
        "request-revocation",
        "vendor-update",
    }
)
IDEMPOTENCY_VERIFICATION: Mapping[str, Tuple[str, str]] = {
    "access-report": ("GET", "/access_requests"),
    "close-request": ("GET", "/access_requests/{}"),
    "grant-access": ("GET", "/access_requests"),
    "import-userlist": ("GET", "/access_states"),
    "mirror-access": ("GET", "/access_requests"),
    "offboard-user": ("GET", "/users/{}"),
    "onboard-user": ("GET", "/users/{}"),
    "request-access": ("GET", "/access_requests"),
    "request-revocation": ("GET", "/access_revocations"),
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
    "close-request": frozenset({("GET", "/access_requests/{}")}),
    "grant-access": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "import-userlist": frozenset(
        {("GET", "/access_states"), ("GET", "/applications/{}/resources")}
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
    "offboard-user": frozenset({("GET", "/users/{}")}),
    "onboard-user": frozenset({("GET", "/users/{}")}),
    "request-access": frozenset(
        {
            ("GET", "/users/{}"),
            ("GET", "/applications/{}"),
            ("GET", "/applications/{}/resources"),
            ("GET", "/access_states"),
            ("GET", "/access_requests"),
        }
    ),
    "request-revocation": frozenset(
        {("GET", "/access_states"), ("GET", "/access_revocations/{}")}
    ),
    "vendor-update": frozenset({("GET", "/applications/{}")}),
}
REASON_SKILLS: Mapping[str, str] = {
    "access-report": "request_reason",
    "close-request": "reason",
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
APPLICATION_STATUS_FILTERS = frozenset({"approved", "discovered", "ignored", "requestable"})
# The status query filter takes a different enum on each list endpoint.
QUERY_STATUS_VALUES: Mapping[str, frozenset[str]] = {
    "/users": USER_STATUSES,
    "/applications": APPLICATION_STATUS_FILTERS,
    "/access_requests": ACCESS_REQUEST_STATUSES,
    "/access_revocations": ACCESS_REVOCATION_STATUSES,
}

TITLE_LOOKUP_SKILLS = frozenset(
    {
        "access-report",
        "close-request",
        "discovered-apps",
        "grant-access",
        "import-userlist",
        "list-access",
        "request-access",
        "request-revocation",
        "vendor-update",
        "view-policies",
    }
)

# Exact key sets: Codex manifests can declare hooks and MCP servers, which are
# execution surfaces this repository does not ship. Add new top-level fields
# here only after confirming they do not execute anything.
CODEX_MARKETPLACE_FIELDS = frozenset({"name", "interface", "plugins"})
CODEX_MARKETPLACE_ENTRY_FIELDS = frozenset({"name", "source", "policy", "category"})
CODEX_PLUGIN_FIELDS = frozenset(
    {
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "skills",
        "interface",
    }
)


# Pinned phrase lists and messages used inside the validators.
STYLE_REQUEST_STATUS_TERMS = (
    "only `pending_approval` can be described as awaiting approval",
    "for every other status",
    "do not claim that approval did or did not happen",
    'say "after approval" only when the returned status is `pending_approval`',
)
STYLE_PRODUCT_PROVENANCE_TERMS = (
    "accessowl product behavior encoded by the skills",
    "not semantics supplied by the openapi enum description",
    "never describe them as openapi-verified behavior",
)
STYLE_422_ERROR_TERMS = (
    "on `422`",
    "openapi error fields are free-form",
    "do not define a mandatory-resource code",
    "never infer a mandatory resource",
    "synthesize a changed request body from error text",
    "user-specified correction starts a new workflow",
    "fresh reads, confirmation, and idempotency key",
)
PLUGIN_FIELDS = frozenset(
    {
        "name",
        "displayName",
        "description",
        "version",
        "author",
        "homepage",
        "repository",
    }
)
PAGINATION_DUPLICATE_ID_TERMS = (
    "track every cursor and returned record id",
    "a duplicate within one page or a repeat across pages within the same traversal is inconsistent",
)
PAGINATION_STATE_SCOPE_TERMS = (
    "one logical pagination traversal of one endpoint and query",
    "reset cursor and record-id tracking for each fresh query or pre-write refetch",
    "same record id may reappear across independent traversals",
    "a duplicate within one page or a repeat across pages within the same traversal is inconsistent",
    "budget of 100,000 decoded json nodes remains global across the run",
)
PAGINATION_LIVE_CURSOR_SHAPE_TERMS = (
    "`meta.limit`",
    "integer equal to the requested",
    "`meta.next_cursor` key on every page",
    "either a nonempty string or explicit null",
    "missing key",
    "wrong type",
)
PAGINATION_OPENAPI_DRIFT_TERMS = (
    "do not require or use",
    "page_size",
    "total_pages",
    "total_count",
    "live api cursor shape was verified on 2026-07-19",
    "openapi",
)
JSON_RESOURCE_TERMS = (
    "json nesting deeper than 128",
    "depth exactly 128 is allowed",
    "depth 129 is rejected",
    "numeric token to at most 1,024 ascii characters before conversion",
    "1,024 is allowed and 1,025 is rejected",
    "conversion that yields a non-finite value",
    "`1e400`",
)
REQUEST_DEADLINE_TERMS = (
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
READ_REDIRECT_TERMS = (
    "at most three redirects",
    "every hop stays on the configured api origin",
    "never follow any cross-origin redirect",
    "possible billing redirect is still cross-origin",
    "without visiting its destination",
    "never downgrade https to http",
    "redirect loop",
)
STATUS_CONTRACT_TERMS = (
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
LIVE_DETAIL_ENVELOPE_TERMS = (
    "user-detail and application-detail responses",
    "top-level `data` object",
    "require that envelope",
)
LIVE_USER_NAME_NULLABILITY_TERMS = (
    "`first_name` or `last_name` may be null",
    "trimmed nonblank `full_name`",
    "validated nonblank email address",
    "stop if neither exists",
    "never invent a name",
)
LIVE_RESOURCE_TITLE_NULLABILITY_TERMS = (
    "resource `title` may be null",
    "never invent or display any other fallback resource title",
    "exactly one resource and its title is null",
    "label that resource \"permission\" wherever a resource name is shown, as the accessowl ui does",
    "`1password | permission | 1password-user`", "\"1password, permission: 1password-user\"",
    "\"permission\" is accessowl's display label for an unnamed single resource, so it is not an invented title",
    "because it is the only resource",
    "such a resource still has its own resource id. its access is resource-level, never "
    "application-wide access (a state with `resource_id: null`), and every request for it "
    "carries that resource id",
    "when a reply presents or confirms such an application's permissions for a choice or a write, "
    "such as a list of options or a confirmation, say once in that reply, in plain words, that it "
    "has a single resource, so accessowl shows it as permission, and that what matters is the permission",
    "plain access listings and report tables show only the label and add no such sentence",
    "when a workflow sees a resource only through an expanded access state, a null title needs no "
    "resource count. name the application and the permission titles, show a state with no "
    "permissions as `<application> (resource-level access)`, and never label it application-wide "
    "access",
    "more than one resource and any of them has a null title",
    "treat that title as unavailable",
    "display, selection, csv output, or disambiguation",
    "otherwise stop incomplete as ambiguous",
    "permission titles must still be nonblank",
    "never write the displayed label back to accessowl",
    "the permission label is never sent as a resource title",
)
API_NESTED_VALUE_CAP_TERMS = (
    "every object",
    "object key",
    "array",
    "scalar value",
    "across the run",
)
DISPLAY_ESCAPING_TERMS = (
    "escape markdown",
    "table",
    "link",
    "html",
    "backtick",
    "line-break",
)
RESILIENCE_CONTRADICTION_PATTERNS = (
    r"repeated\s+cursor.{0,100}(?:safe\s+to\s+ignore|may\s+be\s+ignored|"
    r"only\s+a\s+warning|continue|proceed|keep\s+(?:fetching|paginating|going))",
    r"(?:ignore|continue\s+(?:past|after))\s+(?:a\s+)?repeated\s+cursor",
    r"(?:retry|retries).{0,30}429.{0,50}(?:forever|indefinitely|unbounded|without\s+(?:a\s+)?limit)",
    r"(?:do not|never|skip)\s+(?:percent|url)-encode",
    r"(?:continue|proceed)\s+(?:with|after|despite).{0,70}(?:malformed|incomplete|partial)",
    r"(?:disable|omit|skip|use\s+no)\s+(?:the\s+)?(?:request\s+)?deadline",
    r"(?:buffer|parse).{0,40}(?:before|then).{0,40}(?:enforc|check).{0,30}10\s+mib",
)
WRITE_REDIRECT_TERMS = (
    "for a `post`, `patch`, or `put` mutation",
    "never follow a redirect of any status",
    "`301`, `302`, `303`, `307`, or `308`",
    "even on the same origin",
    "write redirect leaves the outcome uncertain",
    "stop remaining writes",
    "never repeat it with a different method, body, or `idempotency-key`",
)
DISPLAY_IDENTITY_TERMS = (
    "displayed name or email",
    "selected application",
    "resource",
    "permission title or id",
    "requestability",
    "effective change",
    "differs",
    "reconfirm before",
)
REVOCATION_DRIFT_TERMS = (
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
REQUEST_VISIBILITY_TERMS = (
    "requests visible to the authenticated caller",
    "returned blocking request is definitive",
    "absence is not proof",
    "independently documented guarantee",
    "organization-wide request visibility",
    "guarantee is unavailable, stop before writing",
    "duplicate check may be incomplete",
)
WRITE_422_FAILURE_TERMS = (
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
PROVISIONING_TYPE_TERMS = (
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
MULTIPLE_PERMISSIONS_TERMS = (
    "`multiple_permissions_selectable` is present",
    "correctly typed as a boolean",
    "and `true`",
    "missing, null, wrong-type, or `false` blocks that multi-permission selection",
)
EFFECTIVE_END_TERMS = (
    "`effective_end` field is present and explicitly null",
    "missing, malformed, or non-null `effective_end`",
    "not current-access evidence",
)
USERLIST_RESOURCE_TITLE_TERMS = (
    "live api can return a null resource title",
    "despite the current openapi string requirement",
    "reject a missing, null, empty",
    "never invent a fallback column title",
    "only resource has a null title",
    "use the permission column the user has, and ask which column holds the permissions only if it is not",
    "never send `resource: null`, an empty string, or the application title",
    "the corrected-file-only path is not offered for an application whose only resource has no title: say "
    "the import itself works, but the corrected file format for such an application is not confirmed",
    "a re-read state matches only when its `resource_id` is that resource's id. a `resource_id: null` "
    "state is a difference",
    "for an application whose only resource has no title, do not produce it",
    "omit the optional `resource` field and carry permission titles only",
    "never write the application title back as its resource title",
    "next to any other resource stays rejected",
)
USERLIST_STRUCTURE_TERMS = (
    "partial upsert",
    "omitted resources and permissions remain untouched",
    "deletion requires an existing id plus `delete: true`",
    "updating the existing resource requires resending its title",
    "without a usable version token",
)
USERLIST_DESTRUCTIVE_MESSAGES = {
    "USERLIST_NEW_USERS": "unmatched emails remain unchanged and import as new users",
    "USERLIST_REPLACEMENT": "the replacement import must warn that absent current access is removed",
    "USERLIST_READ_ONLY": "the import never writes the application structure, refuses structure PUT, and directs structure changes in AccessOwl followed by rerun",
    "USERLIST_PERMISSION_AMBIGUITY": "duplicate permission titles and semicolons in titles must stop as ambiguous",
    "USERLIST_RESOURCE_CAPS": "CSV processing must enforce file, row, column, and decoded-field caps with no partial output",
    "USERLIST_WITHHOLD_OUTPUT": "withhold CSV and import instructions until every decision and destructive removal is resolved",
    "USERLIST_FINAL_REFRESH": "refresh structure, users, and access states immediately before final delivery",
}
POLICY_PROVENANCE_TERMS = (
    "accessowl product behavior outside the openapi schema",
    "not api-verified configuration",
    "for any exact current configuration",
    "settings, then policies",
)
OPTIONAL_GRANTEE_TERMS = (
    "`grantee_user_id` is optional",
    "exactly one confirmed grantee as context",
    "absence alone does not make the response unknown",
    "if `grantee_user_id` is present",
    "validate it as a uuid",
    "require an exact match",
)
REVOCATION_201_OPTIONAL_FIELD_TERMS = (
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
EFFECTIVE_START_TIMEZONE_TERMS = (
    "rfc3339 instant",
    "convert it to utc",
    "utc calendar date",
    "never use the machine's local timezone",
    "raw pre-offset date",
    "2026-01-01t00:30:00+02:00",
    "2025-12-31",
)
INPUT_FILE_IDENTITY_TERMS = (
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
FLAGGED_STATUS_TERMS = (
    "separately flag every match",
    "`inactive`",
    "`offboarding_planned`",
    "`offboarding`",
    "`offboarded`",
    "explicitly keeps or removes every flagged row",
    "unknown user status",
    "stop",
)
CSV_ARTIFACT_TERMS = (
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
REPLACEMENT_LISTS_TERMS = (
    "certificates, data types, and tags replace",
    "fetch the application's current values first",
    "send the combined list",
    "nothing already recorded is dropped",
)
VENDOR_NOTES_TERMS = (
    "refetch the latest notes",
    "append the new statement",
    "without replacing or rewriting any existing note content",
)
VENDOR_OWNER_TERMS = (
    "owner",
    "application admins",
    "`get /users?status=all&limit=100`",
    "do not assign an `inactive`, `offboarding`, or `offboarded` person",
    "`offboarding_planned`",
    "explicit confirmation",
    "unknown status",
    "stop",
)
VENDOR_USER_FIELDS_TERMS = (
    "`owner_user_id`",
    "one resolved uuid string or `null`",
    "`admin_user_ids`",
    "internally unique array of resolved uuid strings",
    "`[]` clears all application admins",
    "never send names, email addresses, user objects",
)
DEFAULT_POLICY_TERMS = (
    "exactly one policy with `default_policy: true`",
    "zero or several is inconsistent data",
    "stops that claim",
)
CI_EXPECTED_CONCURRENCY = [
    "concurrency:",
    "  group: adversarial-contract-${{ github.workflow }}-${{ github.ref }}",
    "  cancel-in-progress: true",
]
