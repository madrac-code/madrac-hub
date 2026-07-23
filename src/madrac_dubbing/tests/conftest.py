"""Pytest configuration"""
import sys
from pathlib import Path

# Add madrac_dubbing package to path (src/madrac_dubbing/src)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
