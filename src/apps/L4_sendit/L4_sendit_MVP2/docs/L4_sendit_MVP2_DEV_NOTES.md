# Needs further work

## declaration_builder
```
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

This should be determined by inference rather than key words.

## WDP
According to task_result.json: "Explicit WDP terminology evidence is not yet extracted in Stage 4".

WDP seems to be calculated correctly. However, it should be verified how the model handles "WDP" abbreviation, which actually means 'Wagony Dodatkowe Płatne' based on zalacznik-G.md.

## Thoguths after Stage 5 implementation

Stage 5 works for the current task, but it leaves two uncertainties:
* Category A is currently an explicit interpretation of the known task executor.
* WDP still uses the physical number of additional wagons, without a separate terminological fact from Stage 4 (see WDP above).

This means the pipeline already works up to Stage 5, but these two areas are exactly the points worth refining before Stage 6.