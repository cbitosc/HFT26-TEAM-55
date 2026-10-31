"""Master Test Runner for CodeCompass.

Discovers and executes all existing test suites in backend/tests
without duplicating or modifying tests, reports warnings separately,
and exits with a non-zero exit code if any test fails.
"""

import os
import sys
import time
import unittest
import warnings
from pathlib import Path

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def run_tests() -> int:
    """Run all discovered unit and integration tests and report diagnostics."""
    start_time = time.time()
    test_dir = Path(__file__).resolve().parent

    print("=" * 72)
    print("  CodeCompass Master Test Suite (Stage 5 & Stage 6)")
    print("=" * 72)
    print(f"Discovering tests in: {test_dir}\n")

    # Capture and report warnings separately from test pass/fail status
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")

        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(test_dir), pattern="test_*.py")

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

    elapsed = time.time() - start_time

    print("\n" + "=" * 72)
    print("  Test Execution Summary")
    print("=" * 72)
    print(f"Total Tests Run:  {result.testsRun}")
    print(f"Total Failures:   {len(result.failures)}")
    print(f"Total Errors:     {len(result.errors)}")
    print(f"Total Skipped:    {len(result.skipped)}")
    print(f"Execution Time:   {elapsed:.3f} seconds")

    # Separately report warnings as requested
    print("\n" + "-" * 72)
    print(f"Diagnostic Warnings Log ({len(captured_warnings)} recorded):")
    if captured_warnings:
        for idx, w in enumerate(captured_warnings, 1):
            fname = Path(w.filename).name
            print(f"  {idx}. [{w.category.__name__}] {w.message} ({fname}:{w.lineno})")
    else:
        print("  None. Clean execution with zero warnings.")
    print("-" * 72)

    if not result.wasSuccessful():
        print("\n[FAIL] RESULT: TEST SUITE FAILED")
        return 1
    else:
        print("\n[PASS] RESULT: ALL TESTS PASSED SUCCESSFULLY")
        return 0


if __name__ == "__main__":
    sys.exit(run_tests())
