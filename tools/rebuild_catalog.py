#!/usr/bin/env python3
"""CLI adapter for the shared catalog builder."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.converter.catalog import main, rebuild_catalog

if __name__ == "__main__":
    raise SystemExit(main())
