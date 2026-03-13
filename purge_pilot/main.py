"""CLI entry point for PurgePilot."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import List

from .llm_client import estimate_purge_confidence, _SYSTEM_PROMPT
from .scanner import scan_directory


def parse_config(config_path: Path) -> dict:
    """Parse the markdown config file."""
    with open(config_path, encoding='utf-8') as f:
        content = f.read()

    config = {}
    # Find sections
    sections = re.split(r'^##\s+', content, flags=re.MULTILINE)
    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()
        if title == 'AI Prompt':
            # Find code block
            match = re.search(r'```\s*\n(.*?)\n\s*```', body, re.DOTALL)
            if match:
                config['prompt'] = match.group(1).strip()
        elif 'Important Data' in title:
            items = [re.sub(r'^\s*-\s*', '', line).strip() for line in body.split('\n') if re.match(r'^\s*-\s*', line)]
            config['important'] = items
        elif 'Trash Data' in title:
            items = [re.sub(r'^\s*-\s*', '', line).strip() for line in body.split('\n') if re.match(r'^\s*-\s*', line)]
            config['trash'] = items
    return config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="purge-pilot",
        description=(
            "Scan one or more data folders and use an LLM server to estimate "
            "how confident each file/folder can be purged."
        ),
    )
    parser.add_argument(
        "directories",
        metavar="DIR",
        nargs="+",
        help="One or more directories to scan.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("PURGE_PILOT_API_URL", "http://localhost:11434/v1"),
        help=(
            "Base URL of an OpenAI-compatible API endpoint. "
            "Defaults to $PURGE_PILOT_API_URL or http://localhost:11434/v1."
        ),
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("PURGE_PILOT_MODEL", "llama3"),
        help="Model name to use (default: $PURGE_PILOT_MODEL or llama3).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PURGE_PILOT_API_KEY"),
        help="Bearer token for the LLM API (default: $PURGE_PILOT_API_KEY).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        metavar="FLOAT",
        help="Confidence threshold for highlighting high-risk entries (default: 0.7).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        metavar="INT",
        help="Maximum recursion depth when scanning directories (default: 10).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories (names starting with '.').",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        metavar="SECONDS",
        help="HTTP request timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging.",
    )
    parser.add_argument(
        "--config",
        default="purge_config.md",
        help="Path to the configuration markdown file (default: purge_config.md).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1
    config = parse_config(config_path)
    system_prompt = config.get('prompt', _SYSTEM_PROMPT)

    exit_code = 0

    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
            exit_code = 1
            continue
        if not dir_path.is_dir():
            print(f"ERROR: Not a directory: {directory}", file=sys.stderr)
            exit_code = 1
            continue

        print(f"Scanning {dir_path.resolve()} …", file=sys.stderr)
        try:
            scan_result = scan_directory(
                dir_path,
                max_depth=args.max_depth,
                include_hidden=args.include_hidden,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Failed to scan {directory}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        print(
            f"  Found {len(scan_result.entries)} entries "
            f"({scan_result.total_size_bytes:,} bytes). "
            f"Querying LLM …",
            file=sys.stderr,
        )

        try:
            report = estimate_purge_confidence(
                scan_result,
                api_url=args.api_url,
                model=args.model,
                api_key=args.api_key,
                timeout=args.timeout,
                system_prompt=system_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: LLM request failed for {directory}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        # Apply config overrides
        important_paths = set(config.get('important', []))
        trash_paths = set(config.get('trash', []))
        for est in report.estimates:
            if est.path in important_paths:
                est.confidence = 0.0
                est.reason = "Never purge as per config"
            elif est.path in trash_paths:
                est.confidence = 1.0
                est.reason = "Always delete as per config"

        if args.output == "json":
            print(json.dumps(report.to_dict(), indent=2))
        else:
            _print_text_report(report, threshold=args.threshold)

    return exit_code


def _print_text_report(report, *, threshold: float) -> None:
    print(f"\nPurge confidence report for: {report.root}")
    print("-" * 72)
    if not report.estimates:
        print("  (no estimates returned by LLM)")
        return

    for est in sorted(report.estimates, key=lambda e: e.confidence, reverse=True):
        flag = "🔴" if est.confidence >= threshold else "🟢"
        bar_len = int(est.confidence * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"{flag}  [{bar}] {est.confidence:.2f}  {est.path}")
        print(f"        {est.reason}")
    print()

    high = report.high_confidence(threshold)
    print(
        f"Summary: {len(high)} of {len(report.estimates)} entries "
        f"above confidence threshold {threshold:.2f}"
    )


if __name__ == "__main__":
    sys.exit(main())
