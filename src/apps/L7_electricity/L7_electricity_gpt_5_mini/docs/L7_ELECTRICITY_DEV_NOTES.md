# L7 Electricity Dev Notes

## Table Of Contents

- [Purpose](#purpose)
- [Deterministic Support Ideas](#deterministic-support-ideas)
- [Candidate 1: Solved Reference Map](#candidate-1-solved-reference-map)
- [Candidate 2: Regression Harness](#candidate-2-regression-harness)
- [Candidate 3: Two-Stage Tile Classification](#candidate-3-two-stage-tile-classification)
- [Candidate 4: Extra Validation Heuristics](#candidate-4-extra-validation-heuristics)
- [Open Questions](#open-questions)
- [Next Starting Point](#next-starting-point)

## Purpose

This file records the first deterministic support ideas for the `gpt-5-mini` experiment track.

The working hypothesis is simple:

- `gpt-5-mini` may be good enough,
- but only if we narrow the perception problem and add stronger deterministic guardrails.

## Deterministic Support Ideas

The current shortlist of supports is:

1. deterministic solved reference map,
2. small regression harness on frozen tile crops,
3. two-stage tile classification,
4. extra validation heuristics on before/after parse changes.

These ideas are intentionally ordered from the most immediately useful to the most experimental.

## Candidate 1: Solved Reference Map

Idea:

- stop parsing the solved board with the model,
- store one trusted deterministic target board map,
- compare the parsed current board directly against that fixed reference.

Why it helps:

- removes half of the vision work,
- reduces the number of model calls,
- removes one entire source of current-versus-solved parse mismatch,
- makes debugging much easier because only one side of the comparison stays probabilistic.

Likely implementation direction:

- store the solved target map in code or in a tiny reference JSON,
- validate it once against the manually confirmed solved board,
- reuse it in solver input without calling the vision model.

Risk:

- we must be sure the solved reference image really is stable for this exercise.

## Candidate 2: Regression Harness

Idea:

- build a small frozen dataset of difficult tile crops,
- run both `gpt-5-mini` and `gpt-5.5` against the same crops,
- compare shape and orientation accuracy.

Why it helps:

- replaces guesswork with evidence,
- shows exactly which tile families are hard for `gpt-5-mini`,
- gives us a repeatable benchmark after every prompt or validation change.

Likely dataset content:

- 20 to 30 tile crops,
- especially T-junctions,
- straight versus corner edge cases,
- tiles that changed unexpectedly in earlier diagnostics.

Risk:

- benchmark quality depends on careful labeling,
- a tiny dataset may overfit our intuition if we are not careful.

## Candidate 3: Two-Stage Tile Classification

Idea:

- do not ask the model for full exits immediately,
- first ask for tile shape family:
  - `straight`
  - `corner`
  - `t-junction`
- then ask for orientation only inside that family.

Why it helps:

- each model call becomes a smaller classification problem,
- validation can reject impossible combinations earlier,
- orientation prompts can be more specific once shape family is known.

Likely implementation direction:

- keep both stages schema-constrained,
- allow bounded retry only inside the current tile,
- avoid turning this into an open-ended multi-step agent loop.

Risk:

- doubles model interactions unless we batch or optimize carefully,
- may require a new scoped LLM design review if the workflow changes materially.

## Candidate 4: Extra Validation Heuristics

Idea:

- add deterministic checks that compare expected and observed board changes,
- especially on tiles that were not rotated.

Examples:

- if tile `1x2` was rotated once, its orientation should change in a locally plausible way,
- if tile `3x3` was not rotated, a sudden unrelated shape-family change is suspicious,
- if a straight tile becomes a T-junction in a post-batch parse, the parse should be rejected.

Why it helps:

- catches unstable vision output after the fact,
- protects the workflow from blindly trusting one inconsistent parse,
- makes guarded runs safer and more informative.

Risk:

- heuristics can become too strict and reject valid parses if designed poorly,
- they reduce damage from bad parses but do not fix the root cause by themselves.

## Open Questions

- Should the solved reference map live in Python code or in a reference JSON file?
- Should the regression harness be part of app code or a separate experiment utility?
- Does the two-stage classifier stay inside the already approved LLM design boundary?
- Should this track reuse `data/L7_electricity/...` or get its own experiment data directory?

## Next Starting Point

The most practical next move is:

1. define the deterministic solved reference map,
2. assemble a first difficult tile-crop benchmark from existing diagnostics,
3. compare `gpt-5-mini` with `gpt-5.5` on that dataset before changing parser architecture.

That order keeps the early work measurable and avoids premature complexity.
