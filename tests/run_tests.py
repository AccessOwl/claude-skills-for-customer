#!/usr/bin/env python3
"""Discover and run tests, failing distinctly if discovery finds nothing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TextIO


def run_discovered_tests(start_dir: Path, stream: TextIO = sys.stderr) -> int:
    loader = unittest.TestLoader()
    if not any(start_dir.glob("test_*.py")):
        stream.write("ERROR: zero tests discovered; refusing a false-green run\n")
        return 2
    top_level = start_dir.parent if (start_dir / "__init__.py").is_file() else start_dir
    suite = loader.discover(str(start_dir), pattern="test_*.py", top_level_dir=str(top_level))
    count = suite.countTestCases()
    if count == 0:
        stream.write("ERROR: zero tests discovered; refusing a false-green run\n")
        return 2
    stream.write("Discovered %d tests\n" % count)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if result.skipped:
        stream.write(
            "ERROR: %d skipped test(s) are not allowed; refusing a false-green run\n"
            % len(result.skipped)
        )
        return 3
    if result.expectedFailures:
        stream.write("ERROR: expected failures are not allowed in the clean contract suite\n")
        return 1
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    sys.dont_write_bytecode = True
    return run_discovered_tests(Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main())
