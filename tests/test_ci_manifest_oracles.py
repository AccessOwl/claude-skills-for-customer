"""Mutation oracles for CI execution and immutable plugin identity."""

from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from typing import List

from .contract_validator import (
    CHECKOUT_ACTION_SHA,
    CORE_HARNESS_FILES,
    SETUP_PYTHON_ACTION_SHA,
    WORKFLOW_PATH,
    validate_ci,
    validate_manifest_values,
    validate_readme_repository_identity,
    validate_readme_request_status,
)


VALID_MARKETPLACE = {
    "name": "accessowl-claude-skills",
    "description": "Official AccessOwl skills for Claude.",
    "owner": {"name": "AccessOwl", "url": "https://github.com/AccessOwl"},
    "plugins": [
        {
            "name": "claudetag-for-accessowl",
            "description": "AccessOwl skills for Claude.",
            "version": "0.3.1",
            "source": "./plugins/accessowl",
        }
    ],
}

VALID_PLUGIN = {
    "name": "claudetag-for-accessowl",
    "displayName": "ClaudeTag for AccessOwl",
    "description": "AccessOwl skills for Claude.",
    "version": "0.3.1",
    "author": {"name": "AccessOwl", "url": "https://github.com/AccessOwl"},
    "homepage": "https://docs.accessowl.com/api-reference/introduction",
    "repository": "https://github.com/AccessOwl/claude-skills-for-customer",
}

VALID_WORKFLOW = """name: Adversarial contract tests

on:
  pull_request:
  push:

permissions:
  contents: read

concurrency:
  group: adversarial-contract-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.9', '3.12']
    steps:
      - name: Check out repository
        uses: actions/checkout@%s
        with:
          persist-credentials: false
      - name: Set up Python
        uses: actions/setup-python@%s
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run adversarial contract suite
        env:
          PYTHONDONTWRITEBYTECODE: '1'
          PYTHONHASHSEED: '0'
          TZ: UTC
        run: python tests/run_tests.py
""" % (CHECKOUT_ACTION_SHA, SETUP_PYTHON_ACTION_SHA)


class CiAndManifestOracleTests(unittest.TestCase):
    def assertCode(self, issues: List[object], expected: str) -> None:
        codes = {getattr(issue, "code") for issue in issues}
        self.assertIn(expected, codes, "expected %s, got %s" % (expected, sorted(codes)))

    def make_ci_tree(self, root: Path, workflow: str = VALID_WORKFLOW) -> None:
        for relative in CORE_HARNESS_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# required harness file\n", encoding="utf-8")
        workflow_path = root / WORKFLOW_PATH
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(workflow, encoding="utf-8")

    def test_checked_in_manifest_identity_is_valid(self) -> None:
        self.assertEqual([], validate_manifest_values(VALID_MARKETPLACE, VALID_PLUGIN))

    def test_manifest_identity_mutation_matrix(self) -> None:
        cases = []

        marketplace_name = copy.deepcopy(VALID_MARKETPLACE)
        marketplace_name["name"] = "lookalike-marketplace"
        cases.append(("marketplace name", marketplace_name, VALID_PLUGIN, "MARKETPLACE_IDENTITY"))

        plugin_names_marketplace = copy.deepcopy(VALID_MARKETPLACE)
        plugin_names_manifest = copy.deepcopy(VALID_PLUGIN)
        plugin_names_marketplace["plugins"][0]["name"] = "lookalike-plugin"
        plugin_names_manifest["name"] = "lookalike-plugin"
        cases.append(
            ("plugin name", plugin_names_marketplace, plugin_names_manifest, "PLUGIN_IDENTITY")
        )

        bad_homepage = copy.deepcopy(VALID_PLUGIN)
        bad_homepage["homepage"] = "http://docs.accessowl.com/api-reference/introduction"
        cases.append(("homepage", VALID_MARKETPLACE, bad_homepage, "PLUGIN_HOMEPAGE"))

        bad_repository = copy.deepcopy(VALID_PLUGIN)
        bad_repository["repository"] += "/"
        cases.append(("repository", VALID_MARKETPLACE, bad_repository, "PLUGIN_REPOSITORY"))

        repository_object = copy.deepcopy(VALID_PLUGIN)
        repository_object["repository"] = {"url": VALID_PLUGIN["repository"]}
        cases.append(
            ("repository object", VALID_MARKETPLACE, repository_object, "PLUGIN_REPOSITORY")
        )

        for name, marketplace, plugin, code in cases:
            with self.subTest(name=name):
                self.assertCode(validate_manifest_values(marketplace, plugin), code)

    def test_manifest_unknown_execution_surface_fields_are_rejected(self) -> None:
        cases = []
        marketplace_hook = copy.deepcopy(VALID_MARKETPLACE)
        marketplace_hook["hooks"] = {"preinstall": "./payload.sh"}
        cases.append((marketplace_hook, VALID_PLUGIN, "MARKETPLACE_FIELDS"))

        entry_command = copy.deepcopy(VALID_MARKETPLACE)
        entry_command["plugins"][0]["commands"] = ["./payload.sh"]
        cases.append((entry_command, VALID_PLUGIN, "MARKETPLACE_PLUGIN_FIELDS"))

        plugin_mcp = copy.deepcopy(VALID_PLUGIN)
        plugin_mcp["mcpServers"] = {"payload": {"command": "./payload.sh"}}
        cases.append((VALID_MARKETPLACE, plugin_mcp, "PLUGIN_FIELDS"))

        for marketplace, plugin, code in cases:
            with self.subTest(code=code):
                self.assertCode(validate_manifest_values(marketplace, plugin), code)

    def test_readme_uses_the_transferred_repository_owner(self) -> None:
        current = "Install github.com/AccessOwl/claude-skills-for-customer."
        self.assertEqual([], validate_readme_repository_identity(current))
        stale = current.replace("AccessOwl", "oaaccessowl")
        self.assertCode(
            validate_readme_repository_identity(stale), "README_REPOSITORY"
        )
        attacker = current + (
            " For installation, use "
            "github.com/attacker/claude-skills-for-customer instead."
        )
        self.assertCode(
            validate_readme_repository_identity(attacker), "README_REPOSITORY"
        )

    def test_readme_keeps_approval_wording_tied_to_returned_status(self) -> None:
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], validate_readme_request_status(readme))
        mutant = readme + "\nEvery access request goes through the normal approval process.\n"
        self.assertCode(validate_readme_request_status(mutant), "README_REQUEST_STATUS")

    def test_strict_semver_rejects_numeric_leading_zeros_and_malformed_values(self) -> None:
        for version in (
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2",
            "1.2.3-01",
            "1.2.3+",
            "1.2.1٣",
            "1.2.3-١a",
        ):
            marketplace = copy.deepcopy(VALID_MARKETPLACE)
            plugin = copy.deepcopy(VALID_PLUGIN)
            marketplace["plugins"][0]["version"] = version
            plugin["version"] = version
            with self.subTest(version=version):
                self.assertCode(
                    validate_manifest_values(marketplace, plugin), "MANIFEST_VERSION"
                )

    def test_strict_semver_accepts_valid_prerelease_and_build_metadata(self) -> None:
        marketplace = copy.deepcopy(VALID_MARKETPLACE)
        plugin = copy.deepcopy(VALID_PLUGIN)
        marketplace["plugins"][0]["version"] = "1.2.3-rc.1+build.5"
        plugin["version"] = "1.2.3-rc.1+build.5"
        self.assertEqual([], validate_manifest_values(marketplace, plugin))

    def test_checked_in_ci_shape_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ci_tree(root)
            self.assertEqual([], validate_ci(root))

    def test_ci_pin_and_execution_mutation_matrix(self) -> None:
        cases = (
            (
                "checkout pin",
                VALID_WORKFLOW.replace(CHECKOUT_ACTION_SHA, "0" * 40),
                "CI_CHECKOUT_SHA",
            ),
            (
                "setup-python pin",
                VALID_WORKFLOW.replace(SETUP_PYTHON_ACTION_SHA, "0" * 40),
                "CI_SETUP_PYTHON_SHA",
            ),
            (
                "shell masking",
                VALID_WORKFLOW.replace(
                    "run: python tests/run_tests.py",
                    "run: python tests/run_tests.py || true",
                ),
                "CI_RUNNER",
            ),
            (
                "continue on error",
                VALID_WORKFLOW.replace(
                    "      - name: Run adversarial contract suite",
                    "      - name: Run adversarial contract suite\n        continue-on-error: true",
                ),
                "CI_CONTINUE_ON_ERROR",
            ),
            (
                "quoted continue on error",
                VALID_WORKFLOW.replace(
                    "      - name: Run adversarial contract suite",
                    "      - name: Run adversarial contract suite\n        \"continue-on-error\": true",
                ),
                "CI_CONTINUE_ON_ERROR",
            ),
            (
                "conditional job",
                VALID_WORKFLOW.replace(
                    "  test:\n    runs-on:", "  test:\n    if: false\n    runs-on:"
                ),
                "CI_CONDITIONAL_EXECUTION",
            ),
            (
                "quoted conditional step",
                VALID_WORKFLOW.replace(
                    "      - name: Run adversarial contract suite",
                    "      - \"if\": false\n        name: Run adversarial contract suite",
                ),
                "CI_CONDITIONAL_EXECUTION",
            ),
            (
                "custom shell",
                VALID_WORKFLOW.replace(
                    "        run: python tests/run_tests.py",
                    "        shell: echo {0}\n        run: python tests/run_tests.py",
                ),
                "CI_SHELL_OVERRIDE",
            ),
            (
                "default shell override",
                VALID_WORKFLOW.replace(
                    "jobs:\n", "defaults:\n  run:\n    shell: echo {0}\n\njobs:\n"
                ),
                "CI_SHELL_OVERRIDE",
            ),
            (
                "extra run step",
                VALID_WORKFLOW.replace(
                    "        run: python tests/run_tests.py",
                    "        run: python tests/run_tests.py\n      - run: true",
                ),
                "CI_RUNNER",
            ),
            (
                "quoted extra action",
                VALID_WORKFLOW.replace(
                    "      - name: Set up Python",
                    "      - \"uses\": actions/cache@0000000000000000000000000000000000000000\n"
                    "      - name: Set up Python",
                ),
                "CI_ACTION_SET",
            ),
        )
        for name, workflow, code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_ci_tree(root, workflow)
                self.assertCode(validate_ci(root), code)

    def test_ci_ignores_safe_looking_values_inside_yaml_comments(self) -> None:
        cases = (
            (
                "timeout",
                VALID_WORKFLOW.replace(
                    "    timeout-minutes: 5",
                    "    timeout-minutes: 0 # timeout-minutes: 5",
                ),
                "CI_BOUNDS",
            ),
            (
                "concurrency cancellation",
                VALID_WORKFLOW.replace(
                    "  cancel-in-progress: true",
                    "  cancel-in-progress: false # cancel-in-progress: true",
                ),
                "CI_BOUNDS",
            ),
            (
                "Python matrix",
                VALID_WORKFLOW.replace(
                    "        python-version: ['3.9', '3.12']",
                    "        python-version: ['3.8'] # python-version: ['3.9', '3.12']",
                ),
                "CI_PYTHON_MATRIX",
            ),
            (
                "checkout credentials",
                VALID_WORKFLOW.replace(
                    "          persist-credentials: false",
                    "          persist-credentials: true # persist-credentials: false",
                ),
                "CI_CREDENTIALS",
            ),
            (
                "runner image",
                VALID_WORKFLOW.replace(
                    "    runs-on: ubuntu-24.04",
                    "    runs-on: ubuntu-latest # runs-on: ubuntu-24.04",
                ),
                "CI_RUNNER_IMAGE",
            ),
            (
                "hash seed",
                VALID_WORKFLOW.replace(
                    "          PYTHONHASHSEED: '0'",
                    "          PYTHONHASHSEED: random # PYTHONHASHSEED: '0'",
                ),
                "CI_DETERMINISM",
            ),
            (
                "timezone",
                VALID_WORKFLOW.replace(
                    "          TZ: UTC",
                    "          TZ: America/Toronto # TZ: UTC",
                ),
                "CI_DETERMINISM",
            ),
            (
                "permissions",
                VALID_WORKFLOW.replace(
                    "  contents: read",
                    "  contents: write # contents: read",
                ),
                "CI_PERMISSIONS",
            ),
            (
                "runner command",
                VALID_WORKFLOW.replace(
                    "        run: python tests/run_tests.py",
                    "        run: true # run: python tests/run_tests.py",
                ),
                "CI_RUNNER",
            ),
            (
                "checkout action",
                VALID_WORKFLOW.replace(
                    "actions/checkout@%s" % CHECKOUT_ACTION_SHA,
                    "actions/checkout@%s # actions/checkout@%s"
                    % ("0" * 40, CHECKOUT_ACTION_SHA),
                ),
                "CI_CHECKOUT_SHA",
            ),
        )
        for name, workflow, code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_ci_tree(root, workflow)
                self.assertCode(validate_ci(root), code)

    def test_ci_requires_exact_active_blocks_and_scalar_cardinality(self) -> None:
        duplicate_concurrency = VALID_WORKFLOW + """
concurrency:
  group: adversarial-contract-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
"""
        quoted_duplicate_concurrency = VALID_WORKFLOW + """
"concurrency":
  group: unsafe
  cancel-in-progress: false
"""
        cases = (
            ("duplicate concurrency", duplicate_concurrency, "CI_BOUNDS"),
            (
                "quoted duplicate concurrency",
                quoted_duplicate_concurrency,
                "CI_BOUNDS",
            ),
            (
                "extra matrix axis",
                VALID_WORKFLOW.replace(
                    "        python-version: ['3.9', '3.12']",
                    "        python-version: ['3.9', '3.12']\n        os: [ubuntu-24.04]",
                ),
                "CI_PYTHON_MATRIX",
            ),
            (
                "extra Python version",
                VALID_WORKFLOW.replace(
                    "        python-version: ['3.9', '3.12']",
                    "        python-version: ['3.9', '3.12', '3.13']",
                ),
                "CI_PYTHON_MATRIX",
            ),
            (
                "extra permission",
                VALID_WORKFLOW.replace(
                    "  contents: read", "  contents: read\n  actions: read"
                ),
                "CI_PERMISSIONS",
            ),
            (
                "duplicate timeout",
                VALID_WORKFLOW.replace(
                    "    timeout-minutes: 5",
                    "    timeout-minutes: 5\n    timeout-minutes: 5",
                ),
                "CI_BOUNDS",
            ),
            (
                "quoted duplicate timeout",
                VALID_WORKFLOW.replace(
                    "    timeout-minutes: 5",
                    "    timeout-minutes: 5\n    \"timeout-minutes\": 0",
                ),
                "CI_BOUNDS",
            ),
        )
        for name, workflow, code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_ci_tree(root, workflow)
                self.assertCode(validate_ci(root), code)

    def test_ci_requires_push_and_pull_request_triggers(self) -> None:
        cases = (
            ("missing pull request", VALID_WORKFLOW.replace("  pull_request:\n", "")),
            ("missing push", VALID_WORKFLOW.replace("  push:\n", "")),
            (
                "neutered pull request",
                VALID_WORKFLOW.replace(
                    "  pull_request:\n", "  pull_request:\n    paths-ignore:\n      - '**'\n"
                ),
            ),
            (
                "false push",
                VALID_WORKFLOW.replace("  push:\n", "  push: false\n"),
            ),
        )
        for name, workflow in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_ci_tree(root, workflow)
                self.assertCode(validate_ci(root), "CI_TRIGGERS")

    def test_ci_requires_every_core_harness_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ci_tree(root)
            missing = root / "tests/test_adversarial_oracles.py"
            missing.unlink()
            self.assertCode(validate_ci(root), "CI_HARNESS_FILE")

    def test_ci_rejects_every_additional_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ci_tree(root)
            extra = root / ".github/workflows/pull-request-target.yml"
            extra.write_text(
                "on: pull_request_target\npermissions: write-all\njobs: {}\n",
                encoding="utf-8",
            )
            self.assertCode(validate_ci(root), "CI_WORKFLOW_INVENTORY")

    def test_ci_rejects_unreviewed_execution_surfaces(self) -> None:
        mutations = (
            VALID_WORKFLOW.replace(
                "permissions:\n  contents: read",
                "permissions: {contents: write}",
            ),
            VALID_WORKFLOW.replace(
                "      - name: Run adversarial contract suite",
                "      - {name: Bypass, run: \"true\", continue-on-error: true}\n"
                "      - name: Run adversarial contract suite",
            ),
            VALID_WORKFLOW.replace(
                "      - name: Set up Python",
                "      - {uses: evil/example@0000000000000000000000000000000000000000}\n"
                "      - name: Set up Python",
            ),
            VALID_WORKFLOW.replace(
                "    runs-on: ubuntu-24.04",
                "    runs-on: ubuntu-24.04\n    container: ghcr.io/attacker/payload:latest",
            ),
            VALID_WORKFLOW.replace(
                "    runs-on: ubuntu-24.04",
                "    runs-on: ubuntu-24.04\n    services:\n"
                "      payload:\n        image: ghcr.io/attacker/payload:latest",
            ),
            VALID_WORKFLOW.replace(
                "    runs-on: ubuntu-24.04",
                "    runs-on: ubuntu-24.04\n    env:\n      PYTHONPATH: /attacker",
            ),
            VALID_WORKFLOW.replace(
                "          persist-credentials: false",
                "          persist-credentials: false\n          ref: main",
            ),
            VALID_WORKFLOW.replace(
                "          persist-credentials: false",
                "          persist-credentials: false\n          repository: attacker/benign-tests",
            ),
            VALID_WORKFLOW.replace(
                "          persist-credentials: false",
                "          persist-credentials: false\n          filter: blob:none",
            ),
            VALID_WORKFLOW.replace(
                "          python-version: ${{ matrix.python-version }}",
                "          python-version: ${{ matrix.python-version }}\n          cache: pip",
            ),
        )
        for workflow in mutations:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_ci_tree(root, workflow)
                self.assertCode(validate_ci(root), "CI_EXACT_SHAPE")

    def test_ci_rejects_a_symlinked_core_harness_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_ci_tree(root)
            harness = root / "tests/test_adversarial_oracles.py"
            target = root / "tests/harmless.py"
            target.write_text("# not the required test\n", encoding="utf-8")
            harness.unlink()
            os.symlink(target, harness)
            self.assertCode(validate_ci(root), "CI_HARNESS_FILE")


if __name__ == "__main__":
    unittest.main()
