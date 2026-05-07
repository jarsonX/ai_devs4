# Issues

## Table Of Contents

- [Issues Summary](#issues-summary)
- [Issue 1: declaration_builder](#issue-1-declaration_builder)
- [Issue 2: WDP](#issue-2-wdp)
- [Completion Notes](#completion-notes)

## Issues Summary

| Issue | Status |
|---|---|
| `declaration_builder` | <span style="color: #15803d;"><strong>Resolved</strong></span> |
| `WDP` | <span style="color: #15803d;"><strong>Resolved</strong></span> |

## Issue 1: declaration_builder
***Status:*** <span style="color: #15803d;"><strong>Resolved</strong></span>

### Original problem

This issue was identified during manual review of AI-generated code by the developer. That review caught a design flaw which the pipeline itself did not expose at the time.

The previous implementation contained the following executor-local category rule:

```python
def _resolve_known_task_category(
    contents: str,
    route_status: str,
    disabled_route_exception: str,
) -> tuple[str, str]:
    normalized_contents = contents.lower()
    normalized_route_status = route_status.lower()
    normalized_exception = disabled_route_exception.lower()

    # === KNOWN_TASK: spk_transport_declaration ===============================
    # The currently supported course task uses reactor fuel cassettes. MVP1 and
    # local validation established category A as the accepted interpretation.
    # Keep this course-specific rule explicit so future tasks can replace it
    # with their own documented executor logic.
    # =========================================================================
    if (
        "reaktor" in normalized_contents
        and "paliw" in normalized_contents
        and "wy" in normalized_route_status
    ):
        return (
            "A",
            (
                "Known task executor treats reactor fuel cassettes as category A to satisfy "
                "the disabled-route exception documented for Żarnowiec routes."
            ),
        )

    raise ValueError("Known declaration executor cannot resolve the shipment category from current evidence.")
```

This rule assigned category `A` based on local string matching in the executor. That was a poor design because:

- it hid category interpretation inside Stage 5 instead of exposing it as evidence,
- it would not generalize to other valid category-A cases,
- it made validation weaker because the final result did not depend on an explicit evidence-backed category fact.

### Root cause

- The issue was detected by the developer during manual verification of AI-generated code.
- The code was proposed by an AI agent (AI responsibility).
- The earlier app design did not define clearly enough that shipment classification should be extracted before task execution (human responsibility).

### Implemented solution

- Stage 4 now extracts `shipment_category` from the selected `category rules` source as an evidence-backed fact.
- Stage 5 no longer assigns category with a hard-coded keyword rule in `declaration_builder.py`.
- `task_result.category` now links to `shipment_category` in `evidence_links`.
- The executor preserves Stage 4 uncertainty notes and confidence context instead of hiding interpretation inside local deterministic code.

### Implementation notes

- `fact_extractor.py` now requires `shipment_category` for the `category rules` documentation need.
- `validator.py` now validates that `shipment_category` uses a supported symbol and comes from a source selected for `category rules`.
- A deterministic markdown quote-repair step was added in Stage 4 to recover exact `evidence_quote` text when the model returns a close paraphrase instead of a literal substring.

### Verification

- A real OpenAI-powered end-to-end run completed successfully after the refinement was implemented.
- The resulting `data/L4_sendit/output/evidence_package.json` contains validated `shipment_category` evidence.
- The resulting `data/L4_sendit/output/task_result.json` links `category` to `shipment_category` instead of the old local rule.

### Remaining caveat

- The current category decision is still interpretive for `kasety z paliwem do reaktora`. The source text mentions `ogniwa paliwowe`, not the exact shipment phrase, so the model reports uncertainty and non-maximal confidence.
- In a production application, category-A assignment should likely require a human approval step or an additional business-side safeguard.

## Issue 2: WDP
***Status:*** <span style="color: #15803d;"><strong>Resolved</strong></span>

### Original problem

`wdp` was already calculated correctly as the physical number of additional wagons, but the result field still lacked explicit terminology evidence showing what the declaration abbreviation meant.

That gap mattered because:

- the output field used an SPK abbreviation rather than a self-explanatory long name,
- the executor depended on implicit developer knowledge that `WDP` meant `Wagony Dodatkowe Płatne`,
- the evidence trail was weaker than it should be for a format-sensitive declaration output.

### Proposed solution

- Do not add a WDP-only fact such as `wdp_term_meaning`.
- Treat this as a broader terminology problem, not as a single abbreviation exception.
- Add a new documentation-need concept such as `declaration terminology` or equivalent terminology/glossary need when the identified task requires interpreting abbreviations used in the output contract or reference package.
- In Stage 3, allow source selection to include glossary or abbreviation sources such as `zalacznik-G.md` when the current task requires terminology resolution.
- In Stage 4, extract terminology evidence in a reusable form for task-relevant terms rather than hard-coding `WDP` as a one-off case.
- In Stage 5, keep `wdp` calculation deterministic exactly as it is now, but allow the result to link not only to capacity facts but also to the terminology evidence that explains what the output field means.

### Design rationale

- A WDP-specific fact would overfit the workflow to one declaration field and one known command shape.
- The application should not assume that every supported command requires WDP.
- The same design gap can appear for other abbreviations in SPK documentation and declaration fields, so the solution should generalize to task-relevant terminology.
- This keeps the app aligned with the command-driven design: only tasks that actually require terminology resolution should trigger that part of the documentation workflow.

### Implemented solution

- Stage 3 now supports a terminology-oriented documentation need for tasks that require abbreviation resolution in the output contract.
- Stage 3 source selection can now include terminology sources such as `zalacznik-G.md` without introducing a `WDP`-specific source type or fact name.
- Stage 4 now extracts a generic `resolved_terms` fact whose `value` contains task-relevant entries shaped as `TERM = expansion`.
- Stage 5 still calculates `wdp` deterministically from validated wagon-capacity evidence, but it now also requires terminology evidence and links `wdp` to `resolved_terms`.
- The validator now treats terminology evidence as part of the evidence contract for terminology-dependent outputs.

### Implementation notes

- `task_registry.py` now declares `declaration terminology` as a documentation need for the known declaration task.
- `source_selector.py` now allows Stage 3 to satisfy task needs from both Stage 1 documentation needs and task-supported documentation needs, which is how terminology sources can be selected when the task requires them.
- `fact_extractor.py` now supports `resolved_terms` and instructs Stage 4 to extract only task-relevant terminology entries instead of a full glossary dump.
- `declaration_builder.py` still computes `wdp` with deterministic arithmetic, but now requires `resolved_terms` evidence that includes `WDP`.
- `validator.py` now validates the `resolved_terms` shape, source provenance, and required terminology presence for the known declaration task.

### Verification

- Local deterministic verification passed after the refinement was implemented.
- The mock-driven Stage 3 and Stage 4 flow can now carry `declaration terminology` and validated `resolved_terms` evidence.
- The resulting `task_result.json` can link `wdp` to `standard_capacity_kg`, `additional_wagon_capacity_kg`, and `resolved_terms`.
- A real OpenAI-powered end-to-end run completed successfully after the remaining Stage 3 and Stage 4 blockers were corrected.
- The resulting `selected_sources.json` now assigns `zalacznik-G.md` to `declaration terminology`.
- The resulting `evidence_package.json` now contains validated `resolved_terms` evidence and literal markdown quotes accepted by the deterministic validator.

### Remaining caveat

- The terminology refinement is now confirmed by a real OpenAI-powered run, but shipment category assignment still remains interpretive rather than explicit for the current cargo wording.

### Follow-up fix

- The first real OpenAI-powered run after the terminology refinement exposed two non-input blockers:
- Stage 4 accepted semantically correct facts, but the model returned two markdown `evidence_quote` values in a form that deterministic quote validation could not accept.
- Stage 3 selected `zalacznik-G.md`, but did not initially assign the `declaration terminology` documentation need.
- `fact_extractor.py` was then updated so markdown quote repair can recover short contiguous multi-line spans when one fact is supported by more than one adjacent line.
- `source_selector.py` was then updated with stricter terminology guidance and a lightweight deterministic correction for clearly terminology-oriented sources.

## Completion Notes

The implementation is now complete for the currently supported task:

- Stage 1 through Stage 7 are implemented.
- Stage 6 renders the final declaration text deterministically from validated data and template evidence.
- Stage 7 writes a masked verification payload for every run and performs Hub submission only behind `--submit`.
- A real OpenAI-powered `--submit` run completed successfully and the Hub accepted the generated declaration.

The final architecture keeps the intended division of responsibility:

- AI handles command understanding, source selection, evidence extraction, and interpretive uncertainty.
- Deterministic code handles validation, arithmetic, rendering, artifact writing, and guarded submission.

The most reusable lesson from MVP2 is that the app became reliable only after the evidence contract was treated as a first-class boundary:

- Stage 5 stopped hiding business interpretation inside executor-local code.
- Stage 4 gained enough repair/normalization logic to tolerate minor model variability without weakening validation.
- Stage 6 and Stage 7 remained deterministic, which made final rendering and submission auditable and safe.
