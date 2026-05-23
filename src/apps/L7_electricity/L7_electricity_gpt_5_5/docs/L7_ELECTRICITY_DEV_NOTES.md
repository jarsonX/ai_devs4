# L7 Electricity Dev Notes

## Table Of Contents

- [Purpose](#purpose)
- [Final Outcome](#final-outcome)
- [Implementation Notes](#implementation-notes)
- [Debugging Notes](#debugging-notes)
- [Lessons Learned](#lessons-learned)
- [Snapshot Folder](#snapshot-folder)
- [Future Work](#future-work)

## Purpose

This file records the practical development history behind the final working version of `L7_electricity`.
It complements the README by focusing on debugging milestones, trade-offs, and the version snapshot that solved the task.

## Final Outcome

The app now completes the exercise end to end on real services.

Confirmed successful run:

- date: `2026-05-23`,
- run id: `20260523T155302Z`,
- default vision model: `gpt-5.5`,
- planned rotations: `7`,
- executed rotations: `7`,
- completion result: final flag returned successfully.

The successful run artifacts are stored under:

- `data/L7_electricity/output/diagnostics/20260523T155302Z/`

## Implementation Notes

The final working version includes:

- deterministic board, tile, direction, and rotation logic,
- deterministic solver that builds one clockwise rotation sequence,
- Hub client for image download and per-tile rotation requests,
- masked request and response logging,
- deterministic board-rectangle isolation before tile splitting,
- light inner crop on each tile to reduce grid-border confusion,
- tile-by-tile vision parsing with bounded retry and validation,
- parser cache versioning to invalidate stale results after prompt changes,
- per-run parser snapshots for `current_before_rotations`, `solved_reference`, and `current_after_batch`.

The final default model was not chosen up front.
It was selected after direct comparison runs on the real exercise inputs.

## Debugging Notes

The main debugging milestones were:

1. TLS setup:
   - the first blocker was local HTTPS inspection,
   - this was solved by using the local CA bundle workaround,
   - TLS verification stayed enabled throughout the final solution.

2. Wrong crop source:
   - the first parser version split the full PNG as if it were already the 3x3 board,
   - real Hub images also contain title text, power-plant icons, and side labels,
   - this produced false tile crops such as the right-side label appearing in tile `3x3`.

3. Board isolation:
   - deterministic line-and-contrast detection was added,
   - the board is now isolated before any tile crop is sent to the model.

4. Tile-border confusion:
   - some parsed tiles were unstable because the model confused the grid border with cable exits,
   - a light inner crop reduced that noise.

5. Model comparison:
   - `gpt-5-mini` was good enough to reach real guarded runs,
   - `gpt-5.4-mini` was worse on this task and failed early with low confidence,
   - `gpt-5.5` gave the most stable behavior and was promoted to the default model.

## Lessons Learned

The most reusable lessons from this app are:

- deterministic preprocessing matters more than prompt cleverness when image regions are wrong,
- diagnostics that freeze `before` and `after` artifacts are essential when the same filenames are reused during a workflow,
- a stronger model can help, but only after the input pipeline is already clean,
- a deterministic solver is easy to trust once the perception layer becomes stable enough,
- "recommended default" in general model docs is not the same as "best model for this exact narrow task".

## Snapshot Folder

A source snapshot of the successful application version was created at:

- `src/apps/L7_electricity/L7_electricity_gpt_5_5/`

This folder contains the L7 application files and docs for the successful `gpt-5.5` solution run.

## Future Work

Possible next improvements, if this app is extended later:

- add a small regression harness for comparing model outputs on a frozen set of tile crops,
- persist model comparison summaries in a dedicated report file,
- reduce dependence on the vision model for the solved board by introducing a stable reference board map,
- add a lightweight command switch for explicitly choosing `guarded` versus `full` run mode.
