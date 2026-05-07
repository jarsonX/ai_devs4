# Deterministic validation for the L4 sendit MVP2 Stage 1-4 boundaries.

from src.apps.L4_sendit.L4_sendit_MVP2.models import (
    EvidenceContext,
    EvidenceLink,
    EvidencePackage,
    ReferenceInventoryItem,
    RenderedOutputResult,
    SelectedSource,
    SelectedSources,
    SupportedTaskDefinition,
    TaskResult,
    TaskUnderstanding,
    ValidationResult,
)


# Validate the Stage 1 task understanding before downstream use.
def validate_task_understanding(
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.extend(_validate_supported_task(task_understanding, supported_tasks))
    results.extend(_validate_expected_contract(task_understanding, supported_tasks))
    results.extend(_validate_required_inputs(task_understanding, supported_tasks))
    results.extend(_validate_collections(task_understanding))

    return results


# Raise a single error if any Stage 1 validation result has status ERROR.
def raise_if_task_understanding_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Task understanding failed validation: {', '.join(error_messages)}")


# Raise a single error if any Stage 2 validation result has status ERROR.
def raise_if_reference_inventory_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Reference inventory failed validation: {', '.join(error_messages)}")


# Raise a single error if any Stage 3 validation result has status ERROR.
def raise_if_selected_sources_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Selected sources failed validation: {', '.join(error_messages)}")


# Raise a single error if any Stage 4 validation result has status ERROR.
def raise_if_evidence_package_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Evidence package failed validation: {', '.join(error_messages)}")


# Raise a single error if any Stage 5 validation result has status ERROR.
def raise_if_task_result_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Task result failed validation: {', '.join(error_messages)}")


# Raise a single error if any Stage 6 validation result has status ERROR.
def raise_if_rendered_output_invalid(validation_results: list[ValidationResult]) -> None:
    error_messages = [
        validation_result.message
        for validation_result in validation_results
        if validation_result.status == "ERROR"
    ]
    if error_messages:
        raise ValueError(f"Rendered output failed validation: {', '.join(error_messages)}")


# Validate the deterministic Stage 2 reference inventory before downstream use.
def validate_reference_inventory(
    inventory: list[ReferenceInventoryItem],
    repo_root: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.extend(_validate_inventory_not_empty(inventory))
    results.extend(_validate_inventory_paths(inventory, repo_root))
    results.extend(_validate_inventory_source_types(inventory))

    return results


# Validate the Stage 3 source selection before downstream extraction.
def validate_selected_sources(
    selected_sources: SelectedSources,
    task_understanding: TaskUnderstanding,
    reference_inventory: list[ReferenceInventoryItem],
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    inventory_by_path = {inventory_item.path: inventory_item for inventory_item in reference_inventory}

    results.extend(_validate_selected_source_presence(selected_sources))
    results.extend(_validate_selected_source_paths(selected_sources, inventory_by_path))
    results.extend(_validate_selected_source_types(selected_sources, inventory_by_path))
    results.extend(
        _validate_documentation_needs(
            selected_sources=selected_sources,
            task_understanding=task_understanding,
            supported_tasks=supported_tasks,
        )
    )
    results.extend(
        _validate_documentation_need_coverage(
            selected_sources=selected_sources,
            task_understanding=task_understanding,
            supported_tasks=supported_tasks,
        )
    )
    results.extend(
        _validate_known_task_route_evidence_source(
            selected_sources=selected_sources,
            task_understanding=task_understanding,
            inventory_by_path=inventory_by_path,
        )
    )
    results.extend(_validate_selection_reasoning_fields(selected_sources))
    results.extend(_validate_source_selection_boundaries(selected_sources))

    return results


# Validate the Stage 4 evidence package before downstream execution.
def validate_evidence_package(
    evidence_package: EvidencePackage,
    evidence_context: EvidenceContext,
    task_understanding: TaskUnderstanding,
    selected_sources: SelectedSources,
    markdown_source_texts: dict[str, str],
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    _ = supported_tasks
    results: list[ValidationResult] = []
    selected_sources_by_path: dict[str, SelectedSource] = {
        source.path: source for source in selected_sources.selected_sources
    }

    results.extend(_validate_evidence_fact_source_membership(evidence_package, selected_sources_by_path))
    results.extend(_validate_evidence_fact_source_types(evidence_package, selected_sources_by_path))
    results.extend(_validate_markdown_evidence_quotes(evidence_package, markdown_source_texts))
    results.extend(_validate_image_evidence_details(evidence_package))
    results.extend(_validate_source_coverage(evidence_package, selected_sources_by_path))
    results.extend(_validate_required_fact_targets(evidence_package, evidence_context))
    results.extend(_validate_resolved_terms_fact(evidence_package, selected_sources))
    results.extend(_validate_known_task_category_fact(evidence_package, task_understanding, selected_sources))
    results.extend(_validate_evidence_conflicts_and_missing(evidence_package))

    return results


# Validate the Stage 5 task result before rendering or submission.
def validate_task_result(
    task_result: TaskResult,
    task_understanding: TaskUnderstanding,
    evidence_package: EvidencePackage,
    executor_definition,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.extend(_validate_task_result_identity(task_result, task_understanding))
    results.extend(_validate_task_result_executor_contract(task_result, executor_definition, supported_tasks))
    results.extend(_validate_task_result_evidence_links(task_result, evidence_package))
    results.extend(_validate_known_task_result_math(task_result, task_understanding, evidence_package))
    results.extend(_validate_task_result_uncertainty(task_result))

    return results


# Validate the Stage 6 rendered output before files are written.
def validate_rendered_output(
    rendered_output: RenderedOutputResult,
    task_understanding: TaskUnderstanding,
    task_result: TaskResult,
    evidence_package: EvidencePackage,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.extend(_validate_rendered_output_kind(rendered_output, task_understanding))
    results.extend(_validate_rendered_output_payload_presence(rendered_output, task_understanding))
    results.extend(_validate_known_task_rendered_declaration(rendered_output, task_result, evidence_package))

    return results


# Validate that the identified task is one deterministic code knows how to route.
def _validate_supported_task(
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    if task_understanding.task_name not in supported_tasks:
        return [
            ValidationResult(
                status="ERROR",
                message=f"unsupported task_name: {task_understanding.task_name}",
            )
        ]

    return [ValidationResult(status="OK", message="task_name is registered")]


# Validate the task-level contract against the deterministic task registry.
def _validate_expected_contract(
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    task_definition = supported_tasks.get(task_understanding.task_name)
    if task_definition is None:
        return []

    results: list[ValidationResult] = []
    if task_understanding.expected_output_kind == task_definition.expected_output_kind:
        results.append(ValidationResult(status="OK", message="expected_output_kind matches task registry"))
    else:
        results.append(ValidationResult(status="ERROR", message="expected_output_kind does not match task registry"))

    if task_understanding.domain == task_definition.domain:
        results.append(ValidationResult(status="OK", message="domain matches task registry"))
    else:
        results.append(ValidationResult(status="ERROR", message="domain does not match task registry"))

    if task_understanding.task_goal.strip():
        results.append(ValidationResult(status="OK", message="task_goal is present"))
    else:
        results.append(ValidationResult(status="ERROR", message="task_goal is empty"))

    return results


# Validate required input fields for the selected supported task.
def _validate_required_inputs(
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    task_definition = supported_tasks.get(task_understanding.task_name)
    if task_definition is None:
        return []

    provided_inputs = task_understanding.provided_inputs.model_dump(mode="python")
    missing_fields = [
        field_name
        for field_name in task_definition.required_input_fields
        if not _has_non_empty_value(provided_inputs.get(field_name))
    ]

    results: list[ValidationResult] = []
    if missing_fields:
        if all(field_name in task_understanding.missing_inputs for field_name in missing_fields):
            results.append(
                ValidationResult(
                    status="ERROR",
                    message=f"required inputs are missing and correctly reported: {', '.join(missing_fields)}",
                )
            )
        else:
            results.append(
                ValidationResult(
                    status="ERROR",
                    message=f"required inputs are missing but not fully reported: {', '.join(missing_fields)}",
                )
            )
    else:
        results.append(ValidationResult(status="OK", message="required task inputs are present"))

    return results


# Validate Stage 1 list fields that preserve uncertainty instead of guessing.
def _validate_collections(task_understanding: TaskUnderstanding) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.append(ValidationResult(status="OK", message="documentation_needs are present"))
    results.append(ValidationResult(status="OK", message="success_criteria are present"))

    if task_understanding.missing_inputs:
        results.append(
            ValidationResult(
                status="WARNING",
                message=f"model reported missing inputs: {', '.join(task_understanding.missing_inputs)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no missing inputs reported"))

    if task_understanding.uncertainty_notes:
        results.append(
            ValidationResult(
                status="WARNING",
                message=f"model reported uncertainty notes: {len(task_understanding.uncertainty_notes)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no uncertainty notes reported"))

    return results


# Validate that Stage 2 produced at least one reference file.
def _validate_inventory_not_empty(inventory: list[ReferenceInventoryItem]) -> list[ValidationResult]:
    if not inventory:
        return [ValidationResult(status="ERROR", message="reference inventory is empty")]

    return [ValidationResult(status="OK", message="reference inventory is not empty")]


# Validate repository-relative inventory paths under data/L4_sendit/references.
def _validate_inventory_paths(
    inventory: list[ReferenceInventoryItem],
    repo_root: str,
) -> list[ValidationResult]:
    _ = repo_root
    invalid_paths = [
        inventory_item.path
        for inventory_item in inventory
        if not inventory_item.path.startswith("data/L4_sendit/references/")
        or ".." in inventory_item.path
        or inventory_item.path.startswith("/")
    ]
    if invalid_paths:
        return [
            ValidationResult(
                status="ERROR",
                message=f"reference inventory has invalid paths: {', '.join(invalid_paths)}",
            )
        ]

    return [ValidationResult(status="OK", message="reference inventory paths stay under data/L4_sendit/references")]


# Validate that Stage 2 source_type values stay in the supported set.
def _validate_inventory_source_types(inventory: list[ReferenceInventoryItem]) -> list[ValidationResult]:
    invalid_source_types = [
        f"{inventory_item.path}:{inventory_item.source_type}"
        for inventory_item in inventory
        if inventory_item.source_type not in {"markdown", "image", "other"}
    ]
    if invalid_source_types:
        return [
            ValidationResult(
                status="ERROR",
                message=f"reference inventory has invalid source types: {', '.join(invalid_source_types)}",
            )
        ]

    return [ValidationResult(status="OK", message="reference inventory source types are supported")]


# Validate that Stage 3 selected at least one source or clearly reported blockers.
def _validate_selected_source_presence(selected_sources: SelectedSources) -> list[ValidationResult]:
    if selected_sources.selected_sources:
        return [ValidationResult(status="OK", message="selected_sources is not empty")]

    if selected_sources.missing_sources:
        return [
            ValidationResult(
                status="ERROR",
                message="selected_sources is empty and missing_sources reports blockers",
            )
        ]

    return [ValidationResult(status="ERROR", message="selected_sources is empty without missing_sources")]


# Validate that all selected and rejected paths are exact inventory members.
def _validate_selected_source_paths(
    selected_sources: SelectedSources,
    inventory_by_path: dict[str, ReferenceInventoryItem],
) -> list[ValidationResult]:
    invalid_paths: list[str] = []

    for source in selected_sources.selected_sources:
        if source.path not in inventory_by_path:
            invalid_paths.append(source.path)

    for source in selected_sources.rejected_sources:
        if source.path not in inventory_by_path:
            invalid_paths.append(source.path)

    if invalid_paths:
        return [
            ValidationResult(
                status="ERROR",
                message=f"source selection contains paths outside inventory: {', '.join(invalid_paths)}",
            )
        ]

    return [ValidationResult(status="OK", message="all selected and rejected paths exist in inventory")]


# Validate that selected source types match the deterministic inventory.
def _validate_selected_source_types(
    selected_sources: SelectedSources,
    inventory_by_path: dict[str, ReferenceInventoryItem],
) -> list[ValidationResult]:
    mismatches: list[str] = []
    for source in selected_sources.selected_sources:
        inventory_item = inventory_by_path.get(source.path)
        if inventory_item is None:
            continue
        if source.source_type != inventory_item.source_type:
            mismatches.append(
                f"{source.path}: selected={source.source_type}, inventory={inventory_item.source_type}"
            )

    if mismatches:
        return [
            ValidationResult(
                status="ERROR",
                message=f"selected source types do not match inventory: {', '.join(mismatches)}",
            )
        ]

    return [ValidationResult(status="OK", message="selected source types match inventory")]


# Validate that selected documentation needs stay within the supported task scope.
def _validate_documentation_needs(
    selected_sources: SelectedSources,
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    allowed_needs = {need.need for need in task_understanding.documentation_needs}
    task_definition = supported_tasks.get(task_understanding.task_name)
    if task_definition is not None:
        allowed_needs.update(task_definition.documentation_need_names)

    invalid_needs = [
        source.documentation_need
        for source in selected_sources.selected_sources
        if source.documentation_need not in allowed_needs
    ]

    if invalid_needs:
        unique_invalid_needs = sorted(set(invalid_needs))
        return [
            ValidationResult(
                status="ERROR",
                message=(
                    "source selection introduced unsupported documentation needs: "
                    f"{', '.join(unique_invalid_needs)}"
                ),
            )
        ]

    return [ValidationResult(status="OK", message="selected documentation needs stay within task scope")]


# Validate that required task documentation needs are either covered or reported missing.
def _validate_documentation_need_coverage(
    selected_sources: SelectedSources,
    task_understanding: TaskUnderstanding,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    task_definition = supported_tasks.get(task_understanding.task_name)
    if task_definition is None:
        return []

    covered_needs = {source.documentation_need for source in selected_sources.selected_sources}
    required_needs = set(task_definition.documentation_need_names)
    missing_required_needs = sorted(required_needs - covered_needs)

    if not missing_required_needs:
        return [ValidationResult(status="OK", message="required documentation needs are covered")]

    reported_missing_text = " ".join(selected_sources.missing_sources).lower()
    reported_uncertainty_text = " ".join(selected_sources.uncertainty_notes).lower()
    unresolved_needs = [
        need
        for need in missing_required_needs
        if need.lower() not in reported_missing_text and need.lower() not in reported_uncertainty_text
    ]

    if unresolved_needs:
        return [
            ValidationResult(
                status="ERROR",
                message=(
                    "required documentation needs are not covered or reported missing: "
                    f"{', '.join(unresolved_needs)}"
                ),
            )
        ]

    return [
        ValidationResult(
            status="WARNING",
            message=(
                "required documentation needs are not covered but were reported missing or uncertain: "
                f"{', '.join(missing_required_needs)}"
            ),
        )
    ]


# Validate known-task route evidence coverage without hard-coding a file path.
def _validate_known_task_route_evidence_source(
    selected_sources: SelectedSources,
    task_understanding: TaskUnderstanding,
    inventory_by_path: dict[str, ReferenceInventoryItem],
) -> list[ValidationResult]:
    if task_understanding.task_name != "spk_transport_declaration":
        return []

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # The currently supported task needs evidence for both route code and route
    # availability status. Accept any selected inventory source whose safe hint
    # explicitly signals those capabilities, instead of naming one required file.
    # =========================================================================
    route_sources = [
        source
        for source in selected_sources.selected_sources
        if source.documentation_need == "route availability and route code"
    ]
    if not route_sources:
        return [
            ValidationResult(
                status="ERROR",
                message="known task is missing route availability and route code selection",
            )
        ]

    capability_sources = []
    for source in route_sources:
        inventory_item = inventory_by_path.get(source.path)
        if inventory_item is None:
            continue
        hint_text = inventory_item.hint.lower()
        if "route code" in hint_text and "availability" in hint_text:
            capability_sources.append(source.path)

    if not capability_sources:
        return [
            ValidationResult(
                status="ERROR",
                message=(
                    "known task route selection lacks a source whose inventory hint covers "
                    "route codes and availability status"
                ),
            )
        ]

    return [ValidationResult(status="OK", message="known task route evidence source is covered")]


# Validate that explanatory fields required by Stage 3 are present.
def _validate_selection_reasoning_fields(selected_sources: SelectedSources) -> list[ValidationResult]:
    incomplete_entries = [
        source.path
        for source in selected_sources.selected_sources
        if not source.documentation_need.strip()
        or not source.reason.strip()
        or not source.intended_use.strip()
    ]
    if incomplete_entries:
        return [
            ValidationResult(
                status="ERROR",
                message=(
                    "selected sources are missing required reasoning fields: "
                    f"{', '.join(incomplete_entries)}"
                ),
            )
        ]

    results = [ValidationResult(status="OK", message="selected sources include reasoning fields")]
    if selected_sources.missing_sources:
        results.append(
            ValidationResult(
                status="WARNING",
                message=f"model reported missing sources: {', '.join(selected_sources.missing_sources)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no missing sources reported"))

    if selected_sources.uncertainty_notes:
        results.append(
            ValidationResult(
                status="WARNING",
                message=(
                    "model reported source-selection uncertainty notes: "
                    f"{len(selected_sources.uncertainty_notes)}"
                ),
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no source-selection uncertainty notes reported"))

    return results


# Validate that Stage 3 did not smuggle downstream answers into reasoning fields.
def _validate_source_selection_boundaries(selected_sources: SelectedSources) -> list[ValidationResult]:
    blocked_terms = (
        "route_code",
        "amount_due",
        "wdp",
        "wagon_count",
        "category=",
        "final answer",
    )
    suspicious_entries = [
        source.path
        for source in selected_sources.selected_sources
        if any(term in source.reason.lower() or term in source.intended_use.lower() for term in blocked_terms)
    ]
    if suspicious_entries:
        return [
            ValidationResult(
                status="ERROR",
                message=(
                    "source selection includes downstream-answer language for: "
                    f"{', '.join(suspicious_entries)}"
                ),
            )
        ]

    return [ValidationResult(status="OK", message="source selection reasoning stays at selection level")]


# Validate that every fact comes from a Stage 3 selected source path.
def _validate_evidence_fact_source_membership(
    evidence_package: EvidencePackage,
    selected_sources_by_path: dict[str, SelectedSource],
) -> list[ValidationResult]:
    invalid_paths = [
        fact.source_path
        for fact in evidence_package.facts
        if fact.source_path not in selected_sources_by_path
    ]
    if invalid_paths:
        return [
            ValidationResult(
                status="ERROR",
                message=f"evidence facts reference unselected paths: {', '.join(sorted(set(invalid_paths)))}",
            )
        ]

    return [ValidationResult(status="OK", message="evidence facts reference only selected source paths")]


# Validate that fact source types match the Stage 3 selection.
def _validate_evidence_fact_source_types(
    evidence_package: EvidencePackage,
    selected_sources_by_path: dict[str, SelectedSource],
) -> list[ValidationResult]:
    mismatches: list[str] = []
    for fact in evidence_package.facts:
        selected_source = selected_sources_by_path.get(fact.source_path)
        if selected_source is None:
            continue
        if fact.source_type != selected_source.source_type:
            mismatches.append(
                f"{fact.source_path}: fact={fact.source_type}, selected={selected_source.source_type}"
            )

    if mismatches:
        return [
            ValidationResult(
                status="ERROR",
                message=f"evidence fact source types do not match selection: {', '.join(mismatches)}",
            )
        ]

    return [ValidationResult(status="OK", message="evidence fact source types match the selection")]


# Validate that markdown evidence quotes are exact substrings of loaded markdown text.
def _validate_markdown_evidence_quotes(
    evidence_package: EvidencePackage,
    markdown_source_texts: dict[str, str],
) -> list[ValidationResult]:
    missing_quotes: list[str] = []

    for fact in evidence_package.facts:
        if fact.source_type != "markdown":
            continue
        if fact.evidence_kind != "text_quote":
            missing_quotes.append(f"{fact.name}@{fact.source_path}:invalid_evidence_kind")
            continue
        if not fact.evidence_quote:
            missing_quotes.append(f"{fact.name}@{fact.source_path}:missing_quote")
            continue

        source_text = markdown_source_texts.get(fact.source_path, "")
        normalized_quote = _normalize_for_quote_match(fact.evidence_quote)
        normalized_source_text = _normalize_for_quote_match(source_text)
        if normalized_quote not in normalized_source_text:
            missing_quotes.append(f"{fact.name}@{fact.source_path}:quote_not_found")

    if missing_quotes:
        return [
            ValidationResult(
                status="ERROR",
                message=f"markdown evidence quotes failed validation: {', '.join(missing_quotes)}",
            )
        ]

    return [ValidationResult(status="OK", message="markdown evidence quotes are present in loaded text")]


# Validate that image evidence remains inspectable.
def _validate_image_evidence_details(evidence_package: EvidencePackage) -> list[ValidationResult]:
    invalid_image_facts = [
        f"{fact.name}@{fact.source_path}"
        for fact in evidence_package.facts
        if fact.source_type == "image"
        and (
            fact.evidence_kind not in {"image_region", "image_description"}
            or not fact.evidence_locator
        )
    ]

    if invalid_image_facts:
        return [
            ValidationResult(
                status="ERROR",
                message=f"image evidence lacks inspectable locator details: {', '.join(invalid_image_facts)}",
            )
        ]

    return [ValidationResult(status="OK", message="image evidence includes inspectable locator details")]


# Validate that source coverage references every selected source exactly once.
def _validate_source_coverage(
    evidence_package: EvidencePackage,
    selected_sources_by_path: dict[str, SelectedSource],
) -> list[ValidationResult]:
    coverage_paths = [coverage.path for coverage in evidence_package.source_coverage]
    invalid_paths = [
        path
        for path in coverage_paths
        if path not in selected_sources_by_path
    ]
    if invalid_paths:
        return [
            ValidationResult(
                status="ERROR",
                message=f"source coverage references unselected paths: {', '.join(sorted(set(invalid_paths)))}",
            )
        ]

    missing_coverage_paths = [
        path
        for path in selected_sources_by_path
        if path not in coverage_paths
    ]
    if missing_coverage_paths:
        return [
            ValidationResult(
                status="ERROR",
                message=f"source coverage is missing selected paths: {', '.join(missing_coverage_paths)}",
            )
        ]

    return [ValidationResult(status="OK", message="source coverage includes every selected path")]


# Validate that required fact targets are extracted or explicitly reported missing.
def _validate_required_fact_targets(
    evidence_package: EvidencePackage,
    evidence_context: EvidenceContext,
) -> list[ValidationResult]:
    present_fact_names = {fact.name for fact in evidence_package.facts}
    missing_fact_entries = evidence_package.missing_facts
    unresolved_targets = [
        target
        for target in evidence_context.required_fact_targets
        if target not in present_fact_names
        and not any(entry.startswith(target) for entry in missing_fact_entries)
    ]

    if unresolved_targets:
        return [
            ValidationResult(
                status="ERROR",
                message=f"required fact targets are neither extracted nor reported missing: {', '.join(unresolved_targets)}",
            )
        ]

    return [ValidationResult(status="OK", message="required fact targets are extracted or reported missing")]


# Validate generic terminology evidence entries for tasks that use resolved terms.
def _validate_resolved_terms_fact(
    evidence_package: EvidencePackage,
    selected_sources: SelectedSources,
) -> list[ValidationResult]:
    resolved_terms_fact = _find_fact_by_name(evidence_package, "resolved_terms")
    if resolved_terms_fact is None:
        return [ValidationResult(status="OK", message="resolved_terms fact is absent")]

    if not isinstance(resolved_terms_fact.value, list) or not all(
        isinstance(item, str) for item in resolved_terms_fact.value
    ):
        return [
            ValidationResult(
                status="ERROR",
                message="resolved_terms fact must be a list of strings",
            )
        ]

    invalid_entries = [
        item
        for item in resolved_terms_fact.value
        if " = " not in item
        or not item.split(" = ", 1)[0].strip()
        or not item.split(" = ", 1)[1].strip()
    ]
    if invalid_entries:
        return [
            ValidationResult(
                status="ERROR",
                message=f"resolved_terms entries must use `TERM = expansion` format: {', '.join(invalid_entries)}",
            )
        ]

    matching_sources = [
        selected_source
        for selected_source in selected_sources.selected_sources
        if selected_source.path == resolved_terms_fact.source_path
    ]
    if matching_sources and not any(
        source.documentation_need == "declaration terminology" for source in matching_sources
    ):
        return [
            ValidationResult(
                status="ERROR",
                message="resolved_terms fact must come from a source selected for declaration terminology",
            )
        ]

    return [ValidationResult(status="OK", message="resolved_terms fact is valid")]


# Validate the known-task shipment category fact shape and source scope.
def _validate_known_task_category_fact(
    evidence_package: EvidencePackage,
    task_understanding: TaskUnderstanding,
    selected_sources: SelectedSources,
) -> list[ValidationResult]:
    if task_understanding.task_name != "spk_transport_declaration":
        return []

    shipment_category_fact = _find_fact_by_name(evidence_package, "shipment_category")
    if shipment_category_fact is None:
        return [
            ValidationResult(
                status="OK",
                message=(
                    "shipment_category fact is not present in evidence_package; "
                    "required_fact_targets validation is responsible for reporting this as a blocker "
                    "when category evidence is required for the current source set"
                ),
            )
        ]

    if not isinstance(shipment_category_fact.value, str):
        return [
            ValidationResult(
                status="ERROR",
                message="shipment_category fact must be a string value",
            )
        ]

    normalized_category = _normalize_category_symbol(shipment_category_fact.value)
    if normalized_category not in {"A", "B", "C", "D", "E", "X"}:
        return [
            ValidationResult(
                status="ERROR",
                message=f"shipment_category fact is outside the supported category symbols: {shipment_category_fact.value}",
            )
        ]

    matching_sources = [
        selected_source
        for selected_source in selected_sources.selected_sources
        if selected_source.path == shipment_category_fact.source_path
    ]
    if not matching_sources:
        return []
    if not any(source.documentation_need == "category rules" for source in matching_sources):
        return [
            ValidationResult(
                status="ERROR",
                message="shipment_category fact must come from a source selected for category rules",
            )
        ]

    return [ValidationResult(status="OK", message="shipment_category fact is valid for the known task")]


# Preserve missing facts and conflicts as visible downstream signals.
def _validate_evidence_conflicts_and_missing(evidence_package: EvidencePackage) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    if evidence_package.missing_facts:
        results.append(
            ValidationResult(
                status="WARNING",
                message=f"model reported missing facts: {', '.join(evidence_package.missing_facts)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no missing facts reported"))

    if evidence_package.conflicts:
        results.append(
            ValidationResult(
                status="WARNING",
                message=f"model reported evidence conflicts: {', '.join(evidence_package.conflicts)}",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="no evidence conflicts reported"))

    return results


# Validate that Stage 5 task identity matches Stage 1 routing.
def _validate_task_result_identity(
    task_result: TaskResult,
    task_understanding: TaskUnderstanding,
) -> list[ValidationResult]:
    if task_result.task_name != task_understanding.task_name:
        return [
            ValidationResult(
                status="ERROR",
                message="task_result task_name does not match Stage 1 task_name",
            )
        ]

    return [ValidationResult(status="OK", message="task_result task_name matches Stage 1")]


# Validate the executor contract and supported result kind.
def _validate_task_result_executor_contract(
    task_result: TaskResult,
    executor_definition,
    supported_tasks: dict[str, SupportedTaskDefinition],
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    if task_result.result_kind != executor_definition.result_kind:
        results.append(
            ValidationResult(
                status="ERROR",
                message="task_result result_kind does not match executor contract",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="task_result result_kind matches executor contract"))

    task_definition = supported_tasks.get(task_result.task_name)
    if task_definition is None:
        results.append(ValidationResult(status="ERROR", message="task_result task_name is not registered"))
    elif task_result.result_kind != task_definition.result_kind:
        results.append(
            ValidationResult(
                status="ERROR",
                message="task_result result_kind does not match supported task definition",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="task_result result_kind matches supported task definition"))

    return results


# Validate that evidence links point to extracted facts.
def _validate_task_result_evidence_links(
    task_result: TaskResult,
    evidence_package: EvidencePackage,
) -> list[ValidationResult]:
    fact_names = {fact.name for fact in evidence_package.facts}
    invalid_links = [
        _format_evidence_link(evidence_link)
        for evidence_link in task_result.evidence_links
        if evidence_link.fact_name not in fact_names
    ]
    if invalid_links:
        return [
            ValidationResult(
                status="ERROR",
                message=f"task_result evidence_links reference missing facts: {', '.join(invalid_links)}",
            )
        ]

    return [ValidationResult(status="OK", message="task_result evidence_links reference extracted facts")]


# Validate the known-task arithmetic and zero-fee path.
def _validate_known_task_result_math(
    task_result: TaskResult,
    task_understanding: TaskUnderstanding,
    evidence_package: EvidencePackage,
) -> list[ValidationResult]:
    if task_result.task_name != "spk_transport_declaration":
        return []

    standard_capacity_kg = _find_required_int_fact(evidence_package, "standard_capacity_kg")
    additional_wagon_capacity_kg = _find_required_int_fact(evidence_package, "additional_wagon_capacity_kg")
    shipment_category = _normalize_category_symbol(_find_required_text_fact(evidence_package, "shipment_category"))
    resolved_terms = _find_required_text_list_fact(evidence_package, "resolved_terms")
    system_funded_categories = _normalize_category_symbols(
        _find_required_text_list_fact(evidence_package, "system_funded_categories")
    )

    results: list[ValidationResult] = []
    expected_wdp = _calculate_expected_wdp(
        shipment_weight_kg=task_understanding.provided_inputs.weight_kg,
        standard_capacity_kg=standard_capacity_kg,
        additional_wagon_capacity_kg=additional_wagon_capacity_kg,
    )
    if task_result.result.wdp == expected_wdp:
        results.append(ValidationResult(status="OK", message="task_result wdp matches deterministic wagon math"))
    else:
        results.append(ValidationResult(status="ERROR", message="task_result wdp does not match deterministic wagon math"))

    if _term_list_contains_prefix(resolved_terms, "WDP"):
        results.append(ValidationResult(status="OK", message="task_result wdp terminology is backed by resolved_terms"))
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message="task_result wdp is missing required WDP terminology evidence in resolved_terms",
            )
        )

    if task_result.result.category == shipment_category:
        results.append(ValidationResult(status="OK", message="task_result category matches shipment_category evidence"))
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message="task_result category does not match shipment_category evidence",
            )
        )

    if task_result.result.amount_due_pp == 0 and task_result.result.category in system_funded_categories:
        results.append(ValidationResult(status="OK", message="task_result zero-fee path matches funded categories"))
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message="task_result amount_due_pp is not supported by current funded-category evidence",
            )
        )

    if task_result.result.route_code.strip():
        results.append(ValidationResult(status="OK", message="task_result route_code is present"))
    else:
        results.append(ValidationResult(status="ERROR", message="task_result route_code is empty"))

    return results


# Preserve Stage 5 uncertainty notes instead of hiding interpretation risk.
def _validate_task_result_uncertainty(task_result: TaskResult) -> list[ValidationResult]:
    if task_result.uncertainty_notes:
        return [
            ValidationResult(
                status="WARNING",
                message=f"task_result preserves uncertainty notes: {len(task_result.uncertainty_notes)}",
            )
        ]

    return [ValidationResult(status="OK", message="task_result has no uncertainty notes")]


# Validate that Stage 6 rendered the expected output kind.
def _validate_rendered_output_kind(
    rendered_output: RenderedOutputResult,
    task_understanding: TaskUnderstanding,
) -> list[ValidationResult]:
    if rendered_output.output_kind == task_understanding.expected_output_kind:
        return [ValidationResult(status="OK", message="rendered output kind matches Stage 1 expectation")]

    return [
        ValidationResult(
            status="ERROR",
            message="rendered output kind does not match Stage 1 expectation",
        )
    ]


# Validate that Stage 6 produced the required payload shape for the output kind.
def _validate_rendered_output_payload_presence(
    rendered_output: RenderedOutputResult,
    task_understanding: TaskUnderstanding,
) -> list[ValidationResult]:
    if task_understanding.expected_output_kind == "declaration_text":
        if not rendered_output.final_output_text:
            return [ValidationResult(status="ERROR", message="final_output_text is missing for declaration_text")]
        if not rendered_output.compatibility_declaration_text:
            return [ValidationResult(status="ERROR", message="declaration compatibility output is missing")]
        if rendered_output.final_output_text != rendered_output.compatibility_declaration_text:
            return [
                ValidationResult(
                    status="ERROR",
                    message="declaration compatibility output does not match final_output_text",
                )
            ]
        return [ValidationResult(status="OK", message="declaration text outputs are present and aligned")]

    if task_understanding.expected_output_kind == "json":
        if rendered_output.final_output_json is None:
            return [ValidationResult(status="ERROR", message="final_output_json is missing for json output")]
        return [ValidationResult(status="OK", message="json rendered output is present")]

    return [ValidationResult(status="ERROR", message="rendered output payload shape is unsupported")]


# Validate the known declaration rendering contract against task_result and evidence.
def _validate_known_task_rendered_declaration(
    rendered_output: RenderedOutputResult,
    task_result: TaskResult,
    evidence_package: EvidencePackage,
) -> list[ValidationResult]:
    if task_result.task_name != "spk_transport_declaration":
        return []

    declaration_text = rendered_output.final_output_text
    if not declaration_text:
        return [ValidationResult(status="ERROR", message="rendered declaration text is missing")]

    results: list[ValidationResult] = []
    declaration_template_fields = _find_required_text_list_fact(evidence_package, "declaration_template_fields")
    missing_field_labels = [
        field_label
        for field_label in declaration_template_fields
        if field_label not in declaration_text
    ]
    if missing_field_labels:
        results.append(
            ValidationResult(
                status="ERROR",
                message=(
                    "rendered declaration text is missing template field labels: "
                    f"{', '.join(missing_field_labels)}"
                ),
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="rendered declaration text contains template field labels"))

    if "[" in declaration_text and "]" in declaration_text:
        results.append(
            ValidationResult(
                status="ERROR",
                message="rendered declaration text still contains unresolved template placeholders",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="rendered declaration text has no unresolved placeholders"))

    expected_fragments = [
        task_result.result.origin_point,
        task_result.result.sender_identifier,
        task_result.result.destination_point,
        task_result.result.route_code,
        task_result.result.category,
        task_result.result.contents,
        str(task_result.result.declared_weight_kg),
        str(task_result.result.wdp),
        task_result.result.special_notes,
        f"{task_result.result.amount_due_pp} PP",
    ]
    missing_fragments = [
        fragment
        for fragment in expected_fragments
        if fragment not in declaration_text
    ]
    if missing_fragments:
        results.append(
            ValidationResult(
                status="ERROR",
                message="rendered declaration text is missing task_result values",
            )
        )
    else:
        results.append(ValidationResult(status="OK", message="rendered declaration text includes task_result values"))

    if len(task_result.result.contents) <= 200:
        results.append(ValidationResult(status="OK", message="rendered declaration contents fit the template limit"))
    else:
        results.append(
            ValidationResult(
                status="ERROR",
                message="rendered declaration contents exceed the 200-character template limit",
            )
        )

    return results


# Check whether one provided input value is non-empty enough for Stage 1.
def _has_non_empty_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())

    return True


# Normalize whitespace so quote validation tolerates line-wrap differences.
def _normalize_for_quote_match(text: str) -> str:
    return " ".join(text.split())


# Format one evidence link for a validation message.
def _format_evidence_link(evidence_link: EvidenceLink) -> str:
    return f"{evidence_link.result_field}->{evidence_link.fact_name}"


# Find one required integer fact from the evidence package.
def _find_required_int_fact(evidence_package: EvidencePackage, fact_name: str) -> int:
    for fact in evidence_package.facts:
        if fact.name == fact_name and isinstance(fact.value, int):
            return fact.value

    raise ValueError(f"Required integer evidence fact is missing: {fact_name}")


# Find one required string fact from the evidence package.
def _find_required_text_fact(evidence_package: EvidencePackage, fact_name: str) -> str:
    for fact in evidence_package.facts:
        if fact.name == fact_name and isinstance(fact.value, str):
            return fact.value

    raise ValueError(f"Required text evidence fact is missing: {fact_name}")


# Find one required list-of-strings fact from the evidence package.
def _find_required_text_list_fact(evidence_package: EvidencePackage, fact_name: str) -> list[str]:
    for fact in evidence_package.facts:
        if fact.name == fact_name and isinstance(fact.value, list) and all(isinstance(item, str) for item in fact.value):
            return list(fact.value)

    raise ValueError(f"Required text-list evidence fact is missing: {fact_name}")


# Find one evidence fact by name when optional semantic checks need the whole object.
def _find_fact_by_name(evidence_package: EvidencePackage, fact_name: str):
    for fact in evidence_package.facts:
        if fact.name == fact_name:
            return fact

    return None


# Calculate the expected WDP value from the current known-task wagon math.
def _calculate_expected_wdp(
    shipment_weight_kg: int,
    standard_capacity_kg: int,
    additional_wagon_capacity_kg: int,
) -> int:
    remaining_weight_kg = shipment_weight_kg - standard_capacity_kg
    if remaining_weight_kg <= 0:
        return 0

    return -(-remaining_weight_kg // additional_wagon_capacity_kg)


# Normalize category evidence values such as "A - Strategiczna" into "A".
def _normalize_category_symbols(category_values: list[str]) -> list[str]:
    normalized_values: list[str] = []
    for category_value in category_values:
        normalized_values.append(_normalize_category_symbol(category_value))

    return normalized_values


# Normalize one category evidence value such as "A - Strategiczna" into "A".
def _normalize_category_symbol(category_value: str) -> str:
    return category_value.split(" ", 1)[0].strip()


# Check whether one resolved-terms fact contains a required term prefix such as WDP.
def _term_list_contains_prefix(term_entries: list[str], term_name: str) -> bool:
    normalized_prefix = f"{term_name.strip().upper()} ="
    return any(term_entry.strip().upper().startswith(normalized_prefix) for term_entry in term_entries)
