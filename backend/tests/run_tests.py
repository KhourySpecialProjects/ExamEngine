#!/usr/bin/env python3
"""
Test runner script for the DSATUR algorithm tests
"""

import argparse
import os
import subprocess
import sys


def run_unit_tests():
    """Run unit tests."""
    print("Running Unit Tests")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_enhanced_dsatur_algorithm.py",
                "-v",
                "--tb=short",
            ],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Unit tests failed: {e}")
        return False


def run_integration_tests():
    """Run integration tests."""
    print("\nRunning Integration Tests")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_master_validation.py",
                "-v",
                "--tb=short",
                "-m",
                "integration",
            ],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Integration tests failed: {e}")
        return False


def run_original_algorithm_tests():
    """Run original algorithm tests."""
    print("\nRunning Original Algorithm Tests")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_original_algorithm.py",
                "-v",
                "--tb=short",
                "-m",
                "integration",
            ],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Original algorithm tests failed: {e}")
        return False


def run_algorithm_tests():
    """Run algorithm-specific tests."""
    print("\nRunning Algorithm Tests")
    print("=" * 50)

    try:
        # Run the algorithm test directly
        result = subprocess.run(
            [sys.executable, "test_enhanced_dsatur_algorithm.py", "--integration"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Algorithm tests failed: {e}")
        return False


def run_validation_tests():
    """Run validation tests."""
    print("\nRunning Validation Tests")
    print("=" * 50)

    try:
        # Run the validation test directly
        result = subprocess.run(
            [sys.executable, "test_master_validation.py"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Validation tests failed: {e}")
        return False


def run_master_validation(algorithm_type="enhanced"):
    """Run master validation script with algorithm selection."""
    algorithm_name = (
        "Original Algorithm" if algorithm_type == "original" else "Enhanced Algorithm"
    )
    print(f"\nRunning Master Validation ({algorithm_name})")
    print("=" * 50)

    try:
        args = [sys.executable, "master_validation.py"]
        if algorithm_type == "original":
            args.append("--original")
        elif algorithm_type == "enhanced":
            args.append("--enhanced")

        result = subprocess.run(
            args, cwd=os.path.dirname(__file__), capture_output=True, text=True
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"ERROR: Master validation failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("Running All Tests")
    print("=" * 60)

    results = []

    # Run unit tests
    results.append(("Unit Tests", run_unit_tests()))

    # Run algorithm tests
    results.append(("Algorithm Tests", run_algorithm_tests()))

    # Run validation tests
    results.append(("Validation Tests", run_validation_tests()))

    # Run integration tests
    results.append(("Integration Tests", run_integration_tests()))

    # Run original algorithm tests
    results.append(("Original Algorithm Tests", run_original_algorithm_tests()))

    # Run master validation for both algorithms
    results.append(("Enhanced Algorithm Validation", run_master_validation("enhanced")))
    results.append(("Original Algorithm Validation", run_master_validation("original")))

    # Print summary
    print("\nTest Results Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "SUCCESS: PASSED" if success else "ERROR: FAILED"
        print(f"{test_name:20} {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} test suites passed")

    if passed == total:
        print("SUCCESS: All tests passed!")
        return True
    else:
        print("ERROR: Some tests failed!")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run DSATUR algorithm tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--algorithm", action="store_true", help="Run algorithm tests only"
    )
    parser.add_argument(
        "--validation", action="store_true", help="Run validation tests only"
    )
    parser.add_argument(
        "--original", action="store_true", help="Run original algorithm tests only"
    )
    parser.add_argument(
        "--enhanced-validation",
        action="store_true",
        help="Run enhanced algorithm validation only",
    )
    parser.add_argument(
        "--original-validation",
        action="store_true",
        help="Run original algorithm validation only",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")

    args = parser.parse_args()

    # If no specific test type is specified, run all
    if not any(
        [
            args.unit,
            args.integration,
            args.algorithm,
            args.validation,
            args.original,
            args.enhanced_validation,
            args.original_validation,
        ]
    ):
        args.all = True

    success = True

    if args.unit or args.all:
        success &= run_unit_tests()

    if args.algorithm or args.all:
        success &= run_algorithm_tests()

    if args.validation or args.all:
        success &= run_validation_tests()

    if args.integration or args.all:
        success &= run_integration_tests()

    if args.original or args.all:
        success &= run_original_algorithm_tests()

    if args.enhanced_validation or args.all:
        success &= run_master_validation("enhanced")

    if args.original_validation or args.all:
        success &= run_master_validation("original")

    if success:
        print("\nSUCCESS: All requested tests passed!")
        sys.exit(0)
    else:
        print("\nERROR: Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
