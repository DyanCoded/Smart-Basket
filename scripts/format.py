"""Helper script to auto-format code using ruff and black."""

import subprocess
import sys


def run() -> int:
    print("=== Auto-fixing with Ruff ===")
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", "."])

    print("\n=== Formatting with Black ===")
    black_res = subprocess.run([sys.executable, "-m", "black", "."])
    return black_res.returncode


if __name__ == "__main__":
    sys.exit(run())
