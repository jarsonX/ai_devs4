# L4 Sendit MVP1 Dev Notes

## Table Of Contents

- [Implementation Notes](#implementation-notes)
- [AI Boundary](#ai-boundary)
- [Design Decisions](#design-decisions)
- [Hub Submission Notes](#hub-submission-notes)
- [Verification Notes](#verification-notes)
- [Resolved Questions](#resolved-questions)
- [Open Questions](#open-questions)
- [Future Work](#future-work)

## Implementation Notes

MVP1 is intentionally deterministic. The app parses one known command format, uses manually confirmed facts, renders the declaration, saves transparent artifacts, validates the result locally, and can submit the final declaration to the Hub when explicitly requested.

The current pipeline does not call OpenAI, OCR, vision models, or agents. The only external call in MVP1 is the guarded Hub submission behind `--submit`.

Hub submission is guarded by the explicit `--submit` flag. Without that flag, the app only writes local artifacts and does not load secret Hub configuration.

## AI Boundary

MVP1 marks future AI insertion points with visible code comments that start with:

```text
# === AI_BOUNDARY TODO ========================================================
```

These comments are intentionally louder than normal purpose comments so a reader can scan the code and immediately find deterministic steps that are useful comparison points for the AI-assisted workflow.

Current AI comparison points:

- `command_parser.py`: fixed-format parsing shows the expected command data shape for AI command understanding.
- `fact_extractor.py`: manual facts show why task-specific source selection, text extraction, image extraction, and evidence packaging are useful.
- `validator.py`: deterministic validation shows which checks should remain outside model control.

## Design Decisions

Manual facts stay in MVP1 because the learning goal is to expose the basic deterministic pipeline without model behavior. This makes the data flow easier to inspect:

```text
command.txt -> parsed command -> static facts -> declaration data -> declaration.txt
```

Stage 2 and Stage 3 artifacts make that flow visible for comparison with AI-assisted artifacts:

- `data/L4_sendit/output/parsed_command.json`
- `data/L4_sendit/output/extracted_facts.json`
- `data/L4_sendit/output/declaration_data.json`
- `data/L4_sendit/output/verification_payload.json`
- `data/L4_sendit/output/hub_response.json` when `--submit` is used
- `data/L4_sendit/output/run_report.md`

## Hub Submission Notes

`verification_payload.json` is saved with a masked API key and is safe to inspect. The real `AI_DEVS_API_KEY` is loaded only for an explicit `--submit` run and is not written to disk.

When `--submit` is used, the Hub HTTP status and decoded response body are saved to:

```text
data/L4_sendit/output/hub_response.json
```

This makes the final Hub result inspectable after the command finishes.

## Verification Notes

MVP1 was submitted to the course Hub successfully. The Hub accepted the generated declaration, which confirms the key implementation choices:

- category `A` is valid for the disabled `X-01` route in this task,
- amount due `0 PP` is valid for the selected category,
- `WDP: 4` is the correct declaration value for the `2800 kg` shipment,
- no special notes should be rendered beyond `UWAGI SPECJALNE: brak`.

## Resolved Questions

- WDP uses the physical additional wagon count. This was uncertain during implementation, but Hub verification accepted `WDP: 4`.
- Route `X-01` is manually confirmed from `trasy-wylaczone.png`. The value was sufficient for MVP1 and accepted by Hub verification.

## Open Questions

- Which MVP2 evidence extraction strategy should be used for image references: direct vision, OCR, or another inspectable extraction step?

## Future Work

- Keep MVP1 as the deterministic baseline for the known course command.
- Implement bounded AI command understanding with a schema and deterministic validation in MVP2.
- Implement task-specific source selection for local SPK references in MVP2.
- Implement multimodal evidence extraction for selected image references in MVP2.
- Keep local validation deterministic in the AI-assisted workflow.
