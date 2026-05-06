#!/usr/bin/env python3
"""Launch AutoTyper."""
import sys
import os

# Add project root to path so the package resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autotyper.main import main
main()
