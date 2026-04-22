"""Compatibility wrapper for the old standalone WinWorld downloader entry point."""

from __future__ import annotations

import sys

try:
    from .__main__ import main as downloader_main
except ImportError:  # pragma: no cover - direct script fallback
    from thelpviewer.downloader.__main__ import main as downloader_main


def main() -> None:
    """Run the unified downloader CLI limited to the WinWorld provider."""
    if "--source" not in sys.argv:
        sys.argv.extend(["--source", "winworld"])
    downloader_main()


if __name__ == "__main__":
    main()
