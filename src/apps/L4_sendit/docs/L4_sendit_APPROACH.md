# L4 Sendit Approach

## Table Of Contents

- [MVP Split](#mvp-split)
- [MVP1 Learning Stages](#mvp1-learning-stages)
- [MVP2 Learning Goal](#mvp2-learning-goal)

## MVP Split

`L4_sendit` uses two MVPs so the learning path stays readable. MVP1 is a deterministic baseline for the known course task. MVP2 is an AI-assisted command-driven workflow that identifies the requested task, selects relevant local documentation, extracts evidence, executes the task, and validates the final output.

| Version | Goal | Rationale |
|---|---|---|
| `L4_sendit_MVP1` | Build the declaration with explicit rules, fixed local files, deterministic calculations, local validation, and saved intermediate outputs. | This is not a production app. It teaches the data flow without model behavior. |
| `L4_sendit_MVP2` | Use AI for command understanding, task-specific source selection, evidence extraction, and uncertainty reporting while deterministic code owns validation, rendering, persistence, and guarded submission. | This shows how to build a bounded AI workflow without hiding the stable mechanics. |

## MVP1 Learning Stages

MVP1 should be built as four small learning stages:

| Stage | Purpose |
|---|---|
| Static MVP | Render the first declaration from known input and explicit facts. |
| Transparent Pipeline | Save intermediate artifacts so each step can be inspected. |
| Local Validation | Check the declaration before any Hub submission. |
| AI Boundary | Mark manual or heuristic parts that are useful comparison points for the AI-assisted workflow. |

## MVP2 Learning Goal

MVP2 should teach how to design AI as bounded, inspectable workflow stages. The model helps with language-heavy, ambiguous, or multimodal work; deterministic code keeps file access, schemas, validation, rendering, and external submission controlled.
