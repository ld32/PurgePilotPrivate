"""CLI entry point for PurgePilot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from purgepilot.scanner import scan_folders


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="purgepilot",
        description="Scan a folder and list all subdirectories.",
    )
    parser.add_argument(
        "root",
        metavar="ROOT",
        help="Root directory to scan.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="Maximum recursion depth (default: unlimited).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden directories (names starting with '.').",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``purgepilot`` command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"Error: {root!r} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not root.is_dir():
        print(f"Error: {root!r} is not a directory.", file=sys.stderr)
        sys.exit(1)

    folders = scan_folders(
        root,
        max_depth=args.max_depth,
        include_hidden=args.include_hidden,
    )

    if not folders:
        print("No subdirectories found.")
        return

    for folder in folders:
        indent = "  " * folder.depth
        print(f"{indent}{folder.path}")


if __name__ == "__main__":  # pragma: no cover
    main()
