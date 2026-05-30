# L7 Electricity

## Table Of Contents

- [Purpose](#purpose)
- [Approach](#approach)
- [Current State](#current-state)
- [What This Task Should Teach](#what-this-task-should-teach)

## Purpose

This directory contains the application variants for the AI_devs `electricity` exercise.

The task is to read a 3x3 cable board from an image, compute deterministic tile rotations, and send them to the Hub until the puzzle is solved.

## Approach

The preferred approach in this directory is:

- use a vision model only for board perception,
- keep board solving deterministic,
- add deterministic support where the model is not stable enough on its own.

## Current State

The first target was a solution built around `gpt-5-mini`, but that path did not become stable enough in the current iteration.

A working version was then built around `gpt-5.5`, which solves the task correctly, but that solution is still considered non-ideal because `gpt-5.5` is relatively expensive.

Because of that, this directory keeps two documented tracks with different status:

- `L7_electricity_gpt_5_5/` for the working application version,
- `L7_electricity_gpt_5_mini/` for the paused experiment and design notes for a possible future return to `gpt-5-mini`.

## What This Task Should Teach

This directory is mainly about comparing solution tracks for the same AI workflow rather than treating the first model choice as final.
The important lesson is to separate the durable architecture from the model experiment: perception can change, but deterministic solving and guarded Hub interaction should stay stable.

Key learning points:

| Lesson | What it means in this directory |
|---|---|
| Keep working and experimental tracks explicit. | `L7_electricity_gpt_5_5/` holds the verified solution, while `L7_electricity_gpt_5_mini/` preserves the paused cheaper-model experiment. |
| Separate perception from solving. | Vision parsing reads the board, but ordinary code computes tile rotations. |
| Let evidence choose the model. | The stronger model became the active version because real guarded runs showed better stability. |
| Preserve failed or paused experiments usefully. | The mini track keeps design notes so future work can resume from known trade-offs instead of starting over. |
| Treat cost as a design pressure, not the only goal. | A cheaper model is valuable only if added deterministic support can make the workflow reliable enough. |

The practical pattern to remember:

```text
stable architecture -> model comparison -> verified track -> preserved experiment notes
```
