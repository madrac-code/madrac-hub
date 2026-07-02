#!/usr/bin/env python3
"""
Build script for Nuitka — madrac-dubs ONEDIR build

Creates a self-contained directory with all dependencies.
"""

import subprocess
import sys
from pathlib import Path

# Ensure we're in madrac-dubs directory
MADRAC_DUBS = Path(r"D:\madrac-dubs")
if not MADRAC_DUBS.exists():
	print("ERROR: madrac-dubs directory not found")
	sys.exit(1)

OUTPUT_DIR = MADRAC_DUBS / "dist" / "madrac-dubbing-nuitka"
BUILD_DIR = MADRAC_DUBS / ".nuitka_build"

# Nuitka command
# https://nuitka.net/user-guide/
CMD = [
	sys.executable, "-m", "nuitka",
	"--onedir",                           # Create directory (vs one-file)
	"--windows-console-mode=attach",      # Attach to parent console if one exists
	"--include-package-data=madrac_dubbing",  # Bundle all package data
	"--include-package-data=demucs",      # Bundle Demucs data (files.txt, models)
	"--follow-imports",                   # Follow all imports
	"--python-flag=-u",                   # Unbuffered output
	f"--build-dir={BUILD_DIR}",          # Cache directory
	f"--output-dir={OUTPUT_DIR.parent}", # Output directory
	str(MADRAC_DUBS / "src" / "madrac_dubbing" / "__main__.py"),
]

print("="*70)
print("[BUILD] Nuitka build for madrac-dubs")
print("="*70)
print(f"\nOutput directory: {OUTPUT_DIR}\n")
print("Command:")
print(" ".join(CMD))
print("\nStarting build...\n")

try:
	result = subprocess.run(CMD, cwd=str(MADRAC_DUBS))
	sys.exit(result.returncode)
except Exception as e:
	print(f"ERROR: {e}")
	sys.exit(1)
