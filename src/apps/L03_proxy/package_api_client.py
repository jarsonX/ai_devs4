# This module defines the external packages API client contract for the L03_proxy app.

from __future__ import annotations

from typing import Any

from .config import AppConfig


# This client wraps low-level communication with the external packages API.
class PackageApiClient:
    # This initializer stores application configuration needed by the API client.
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # This method will call the package status endpoint for one package ID.
    def check_package(self, package_id: str) -> dict[str, Any]:
        raise NotImplementedError(
            "The packages API check action will be implemented in a later step."
        )

    # This method will call the package redirect endpoint with operator-provided inputs.
    def redirect_package(
        self,
        package_id: str,
        destination: str,
        code: str,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "The packages API redirect action will be implemented in a later step."
        )
