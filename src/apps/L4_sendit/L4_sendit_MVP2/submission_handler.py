# Deterministic reporting and optional submission orchestration for Stage 7.

from src.apps.L4_sendit.L4_sendit_MVP2.config import HubConfig
from src.apps.L4_sendit.L4_sendit_MVP2.hub_client import (
    build_verification_payload,
    mask_payload_for_storage,
    submit_verification,
)
from src.apps.L4_sendit.L4_sendit_MVP2.models import ReportingAndSubmissionResult, RenderedOutputResult


# Build reporting/submission artifacts and submit only when explicitly requested.
def prepare_reporting_and_optional_submission(
    rendered_output: RenderedOutputResult,
    submit: bool,
    hub_config: HubConfig | None,
) -> ReportingAndSubmissionResult:
    declaration_text = _require_declaration_text(rendered_output)
    active_hub_config = hub_config or _build_masked_payload_config()
    verification_payload = build_verification_payload(active_hub_config, declaration_text)
    masked_verification_payload = mask_payload_for_storage(verification_payload)

    hub_response = None
    if submit:
        if hub_config is None:
            raise ValueError("Hub configuration is required when submit=True.")
        hub_response = submit_verification(hub_config, verification_payload)

    return ReportingAndSubmissionResult(
        verification_payload=verification_payload,
        masked_verification_payload=masked_verification_payload,
        hub_response=hub_response,
        submission_requested=submit,
    )


# Read the declaration text required by the sendit Hub contract.
def _require_declaration_text(rendered_output: RenderedOutputResult) -> str:
    declaration_text = rendered_output.compatibility_declaration_text or rendered_output.final_output_text
    if not declaration_text:
        raise ValueError("Stage 7 requires a rendered declaration text artifact.")

    return declaration_text


# Build non-secret config used only to create a masked payload review artifact.
def _build_masked_payload_config() -> HubConfig:
    return HubConfig(
        api_key="not-loaded-without-submit",
        verify_url="not-loaded-without-submit",
        task_name="sendit",
    )
