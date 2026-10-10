"""Command-line entry point for batch and single-file HTML/UHF export."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from thelpviewer.help_database import load_help_database, lookup_help_database_entry

from .exporter import export_file, export_tree
from .writers.bundle import export_bundle, export_bundle_tree


def _fail_on_export_errors(results: Iterable[object]) -> None:
    """Exit unsuccessfully when an exporter reported a caught exception."""
    if any(getattr(result, "format_name", None) == "ERROR" for result in results):
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser used by ``python -m thelpviewer.server.converter``."""
    parser = argparse.ArgumentParser(
        prog="python -m thelpviewer.server.converter",
        description="Read Borland THELP, TurboVision FBHF, Software602 M602, HLX/HL6 or TVHC source files and export HTML.",
    )
    parser.add_argument("input", help="Input .hlp/.tph/.tch/*.t?h/.hlx/.hl6/.txt file or directory tree with help files.")
    parser.add_argument("output_dir", help="Directory where HTML files will be written.")
    parser.add_argument(
        "--encoding",
        default="auto",
        help="Display encoding for topic and index text. Use auto, cp437, cp852, latin1, latin2 or kamenicky.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the target directory before exporting a whole directory tree.",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="Also write document.json with the normalized HelpDocument model next to the HTML files.",
    )
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="Export as UHF 2.0 JSON bundles with a single-page viewer instead of individual HTML files.",
    )
    parser.add_argument(
        "--bundle-layout",
        choices=("site", "helps"),
        default="site",
        help="Bundle output layout: 'site' writes index/assets/docs, 'helps' writes only bundle data.",
    )
    return parser


def main() -> None:
    """Run the CLI and print a short export summary."""
    args = build_parser().parse_args()
    input_path = Path(args.input)

    if args.bundle:
        if input_path.is_dir():
            results = export_bundle_tree(
                input_path,
                args.output_dir,
                encoding=args.encoding,
                clean=args.clean,
                layout=args.bundle_layout,
            )
            for result in results:
                print(f"{result.format_name}\t{result.input_path.name}\t{result.json_path.name}")
            print(f"TOTAL\t{len(results)}")
            _fail_on_export_errors(results)
        else:
            help_database = load_help_database()
            result = export_bundle(
                input_path,
                args.output_dir,
                encoding=args.encoding,
                database_entry=lookup_help_database_entry(input_path, help_database),
            )
            print(f"{result.format_name}\t{result.input_path.name}\t{result.json_path.name}")
            _fail_on_export_errors((result,))
        return

    if input_path.is_dir():
        results = export_tree(
            input_path,
            args.output_dir,
            encoding=args.encoding,
            clean=args.clean,
            dump_json=args.dump_json,
        )
        for result in results:
            print(f"{result.format_name}\t{result.encoding}\t{result.input_path.name}")
        print(f"TOTAL\t{len(results)}")
        _fail_on_export_errors(results)
        return

    result = export_file(input_path, args.output_dir, encoding=args.encoding, dump_json=args.dump_json)
    print(f"{result.format_name}\t{result.encoding}\t{result.input_path.name}")
    _fail_on_export_errors((result,))


if __name__ == "__main__":
    main()
