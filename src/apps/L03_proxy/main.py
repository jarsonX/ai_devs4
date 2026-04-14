# This module is the local application entry point for the L03_proxy app.

from __future__ import annotations

from .config import ensure_runtime_directories, get_config


def run_app() -> None:
    config = get_config()
    ensure_runtime_directories(config)

    raise NotImplementedError(
        "The HTTP server entry point will be implemented in a later step."
    )


if __name__ == "__main__":
    run_app()
