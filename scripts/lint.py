"""Helper script to run linter (ruff) and code formatter checks (black)."""

import subprocess
import sys


def run() -> int:
    print("=== Running Ruff Linter ===")
    ruff_res = subprocess.run([sys.executable, "-m", "ruff", "check", "."])
    if ruff_res.returncode != 0:
        return ruff_res.returncode

    print("\n=== Running Black Formatter Check ===")
    black_res = subprocess.run([sys.executable, "-m", "black", "--check", "."])
    return black_res.returncode


if __name__ == "__main__":
    sys.exit(run())
