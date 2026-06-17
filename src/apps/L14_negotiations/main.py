# This module is the CLI entrypoint for the L14_negotiations app skeleton.

from __future__ import annotations

import argparse
import json

from .catalog_loader import load_catalog
from .config import ensure_runtime_directories, get_config
from .server import run_server


# Parse local development commands for the app skeleton.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or inspect the L14_negotiations tool service.",
    )
    parser.add_argument(
        "--check-data",
        action="store_true",
        help="Load and validate local catalog CSV files, then print a summary.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the local JSON HTTP server.",
    )
    return parser.parse_args()


# Run one local command without making external API calls.
def main() -> None:
    args = parse_args()
    config = get_config()
    ensure_runtime_directories(config)

    if args.serve:
        run_server(config)
        return

    catalog = load_catalog(config)
    print(json.dumps(catalog.summary(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
