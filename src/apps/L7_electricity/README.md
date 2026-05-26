# L7 Electricity

## Table Of Contents

- [Purpose](#purpose)
- [Approach](#approach)
- [Current State](#current-state)

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
