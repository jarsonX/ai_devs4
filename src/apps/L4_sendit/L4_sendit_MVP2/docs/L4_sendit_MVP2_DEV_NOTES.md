# Issues

## Table Of Contents

- [Issues Summary](#issues-summary)
- [Issue 1: declaration_builder](#issue-1-declaration_builder)
- [Issue 2: WDP](#issue-2-wdp)
- [Thoughts After Stage 5 Implementation](#thoughts-after-stage-5-implementation)

## Issues Summary

| Issue | Status |
|---|---|
| `declaration_builder` | <span style="color: #15803d;"><strong>Resolved</strong></span> |
| `WDP` | <span style="color: #b45309;"><strong>Not resolved</strong></span> |

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

- The issue was detected by the user during manual verification of AI-generated code.
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
***Status:*** <span style="color: #b45309;"><strong>Not resolved</strong></span>

According to `data/L4_sendit/output/task_result.json`, the current implementation still reports:

```text
WDP currently uses the physical additional wagon count for the known task.
Explicit WDP terminology evidence is not yet extracted in Stage 4.
```

WDP seems to be calculated correctly. However, it should still be verified how the model handles the `WDP` abbreviation, which according to `zalacznik-G.md` stands for `Wagony Dodatkowe Płatne`.

At the moment, this does not block the supported task flow, but it remains the main known refinement area in Stage 4 and Stage 5.

## Thoughts After Stage 5 Implementation

Stage 5 works for the current task, and the `declaration_builder` issue is now closed:

- Category A is no longer assigned inside the known task executor; it is extracted in Stage 4 as `shipment_category`.
- WDP still uses the physical number of additional wagons, without a separate terminological fact extracted in Stage 4.

This means the pipeline already works through Stage 5 for the supported task, and WDP remains the primary known refinement area before Stage 6.
