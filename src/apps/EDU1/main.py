"""This file is the app entry point. Run it to start the full EDU1 workflow."""

from __future__ import annotations

from pprint import pprint

from .pipeline import run_pipeline


def main() -> None:
    result = run_pipeline()
    pprint(result)


if __name__ == "__main__":
    main()
