# LLM App Optimization Checklist

Use this checklist to review a completed LLM application and decide whether it is well optimized.

Mark each item as:
- `YES` if the rule is clearly satisfied,
- `NO` if it is missing,
- `N/A` if this checklist item does not apply to the current application under review.

For every item, add a short evidence note:
- mention the file, component, workflow step, metric, or behavior that supports the answer,
- do not answer with `YES`, `NO`, or `N/A` alone.

## 1. Task Design

- [ ] The app solves a clearly defined task with a concrete expected output.
- [ ] The task is split into smaller steps when a single model call would mix multiple responsibilities.
- [ ] The workflow uses deterministic code for stable logic and reserves LLM calls for language or reasoning tasks.
- [ ] The system avoids asking the model to do multiple unrelated jobs in one step.
- [ ] The workflow is simple enough to explain step by step without hidden or unnecessary branches.

## 2. Model Usage

- [ ] Each LLM step has an explicit reason for using the selected model.
- [ ] Stronger and more expensive models are used only in steps that require stronger reasoning or better output quality.
- [ ] The app does not call the model when ordinary code, rules, or lookups would be enough.
- [ ] Repeated model calls are explained by the workflow and are not caused by avoidable retries or weak step design.

## 3. Prompt Quality

- [ ] Each prompt has a clear instruction, relevant context, constraints, and expected output format.
- [ ] Prompts include only information needed for the current step.
- [ ] The app avoids passing irrelevant history, data, or examples into prompts.
- [ ] Ambiguous user requests are clarified, transformed, or decomposed before execution.

## 4. Context Control

- [ ] Only the context needed for the current step is sent to the model.
- [ ] Old conversation history is summarized or dropped when full detail is no longer needed.
- [ ] Tool results are filtered before being added to the next model call.
- [ ] The app treats context as a limited and expensive resource.

## 5. Tool And Workflow Efficiency

- [ ] The tool list exposed to the model is limited to the tools needed for the current step.
- [ ] The workflow prefers fewer, higher-value tool calls over many small calls.
- [ ] Related operations are batched when possible.
- [ ] Repeated external calls use caching when freshness requirements allow it.
- [ ] Each workflow step has a clear purpose and there are no obvious steps that can be removed without changing the result.

## 6. Output Stability

- [ ] The model returns structured output whenever the result is consumed by code.
- [ ] Output schemas are defined before execution.
- [ ] Model responses are validated before they are used downstream.
- [ ] The app treats model output as untrusted input until validation passes.

## 7. Cost And Latency

- [ ] The number of LLM calls is intentionally minimized.
- [ ] The number of tool calls is intentionally minimized.
- [ ] Large prompts are avoided because they increase token usage, latency, and noise.
- [ ] The app has clear places where cost, latency, retries, or token usage can be measured or logged.
- [ ] Expensive steps are easy to identify during debugging or review.

## 8. Safety And Control

- [ ] The model is responsible for interpretation and planning, not final authorization.
- [ ] Sensitive or risky actions are protected by backend checks, not by model judgment alone.
- [ ] Retrieved or user-provided content is not mixed with system instructions in an unsafe way.
- [ ] The workflow stops or asks for missing required inputs instead of guessing important values.

## 9. Review Validation

- [ ] There is no obvious LLM call that can be replaced with ordinary code without reducing required quality.
- [ ] There is no obvious workflow step that can be removed without changing the result or reducing reliability.
- [ ] There is no obvious context block that can be removed without making the current step weaker or less safe.
- [ ] The current workflow would still be understandable and maintainable if the application becomes larger.

## Quick Rule Of Thumb

Prefer:
- smaller context,
- fewer calls,
- shorter workflows,
- stronger validation,
- simpler responsibilities per step.

Avoid:
- one huge prompt for everything,
- passing full history by default,
- exposing all tools all the time,
- repeating the same calls without caching or batching,
- using the model where normal code is enough.
