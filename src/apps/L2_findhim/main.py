"""This file is the app entry point. Run it to start the full FindHim workflow."""

from __future__ import annotations

from .pipeline import run_pipeline


if __name__ == "__main__":
    run_pipeline()
