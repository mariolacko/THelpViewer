"""Generate HTML output for all sample help files in the repository."""

from __future__ import annotations

from pathlib import Path

from .exporter import export_tree


def main() -> None:
    """Export the repository sample tree into ``python/hlx2html/generated``."""
    project_root = Path(__file__).resolve().parents[2]
    input_root = project_root / "samples"
    output_root = project_root / "python" / "hlx2html" / "generated"

    results = export_tree(input_root, output_root, encoding="auto", clean=True)
    for result in results:
        relative_input = result.input_path.relative_to(project_root)
        relative_output = result.output_dir.relative_to(project_root)
        print(f"{result.format_name}\t{result.encoding}\t{relative_input}\t{relative_output}\t{result.html_count}")
    print(f"TOTAL\t{len(results)}\t{output_root.relative_to(project_root)}")


if __name__ == "__main__":
    main()
