"""Verification script running linting, formatting check, and test suite."""

import subprocess
import sys


def run_step(title: str, command: list[str]) -> bool:
    print("\n==========================================")
    print(f"--> {title}")
    print("==========================================")
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"[FAIL] {title} failed with exit code {result.returncode}")
        return False
    print(f"[PASS] {title} succeeded.")
    return True


def main() -> int:
    steps = [
        ("Ruff Linter", [sys.executable, "-m", "ruff", "check", "."]),
        ("Black Formatter Check", [sys.executable, "-m", "black", "--check", "."]),
        ("Pytest Suite", [sys.executable, "-m", "pytest"]),
    ]

    for title, command in steps:
        if not run_step(title, command):
            return 1

    print("\n[SUCCESS] All pre-push checks passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
