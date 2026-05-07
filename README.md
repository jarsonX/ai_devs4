# AI_devs

Python-based solutions and experiments developed during the AI_devs AI engineering course.

This repository is both a learning workspace and a portfolio of applied AI engineering practice. Its goal is not only to pass course assignments, but also to explore how AI-powered applications can be designed, implemented, documented, reviewed, and operated in a way that is closer to production software than to one-off scripts.

## Table Of Contents

- [About the course](#about-the-course)
- [Repository structure](#repository-structure)
- [Learning approach](#learning-approach)
- [What this repository demonstrates](#what-this-repository-demonstrates)
- [Disclaimers](#disclaimers)
  - [Course & Content](#course-content)
  - [AI Usage](#ai-usage)

## About the course

AI_devs is a hands-on course focused on building real-world applications with Large Language Models and AI APIs.

More information about the course:
https://www.aidevs.pl/

## Repository structure

Applications created to solve AI_devs course tasks are located in the `src/apps/` directory. In most cases, each task has its own dedicated application directory, for example `src/apps/L1_people`, containing the code and supporting modules created specifically for that assignment.

The repository also includes applications labeled as `EDU#`. These are not direct course tasks, but rather educational side projects and author experiments. They were usually created as simplified, focused exercises to better understand a specific concept, mechanism, or implementation detail when a topic needed additional hands-on practice.

Application documentation is kept close to the code in each app's `docs/` directory. README files describe the current purpose, workflow, configuration, run command, module structure, and verification approach for an app. Some apps also include DEV_NOTES files with working context such as implementation history, debugging lessons, trade-offs, open questions, future work, and lessons learned.

Runtime data, generated outputs, logs, cache files, downloaded references, and similar artifacts are intentionally kept outside application source directories whenever practical, usually under the repository-level `data/` directory. This keeps application code focused on implementation and documentation, while runtime artifacts remain separated by purpose.

## Learning approach

The work in this repository follows an author-directed human-AI collaboration model. The author acts as the architect, reviewer, orchestrator, and learner, while AI coding agents support implementation, refactoring, debugging, and documentation.

This is intentionally different from treating an agent as a black-box task solver. For all applications, the workflow includes explicit design discussion, architecture decisions, documentation planning, implementation review, manual code reading, debugging, and follow-up refinement. The goal is to understand the produced code and the design trade-offs behind it, even when the first implementation draft is generated with AI assistance.

The repository therefore documents not only final code, but also a way of working: using AI as an engineering partner while preserving human responsibility for direction, validation, learning, and quality. This is not presented only as a claim. In some places, the repository also includes concrete evidence of that workflow, such as [L4_sendit_MVP2_DEV_NOTES.md](src/apps/L4_sendit/L4_sendit_MVP2/docs/L4_sendit_MVP2_DEV_NOTES.md), where AI-generated implementation choices are explicitly reviewed, challenged, and refined from a developer perspective.

## What this repository demonstrates

Beyond individual course task solutions, this repository is intended to demonstrate practical skills and habits that matter in real AI application development:

- designing task-specific AI applications instead of isolated prompt scripts,
- decomposing workflows into clear modules and responsibilities,
- using configuration, environment variables, and secret-safe conventions,
- adding documentation that explains purpose, workflow, configuration, and verification,
- treating logs, runtime data, generated outputs, and cache files as separate app data,
- reviewing AI-generated code instead of accepting it uncritically,
- documenting review and refinement decisions as portfolio evidence of responsible AI-assisted development,
- learning from implementation details, bugs, trade-offs, and model behavior.

The code should be read as a learning portfolio: it shows both the resulting applications and the process of becoming more capable at building them.

## Disclaimers

### Course & Content

This repository **does not contain any course materials** that would allow someone to complete the AI_devs course without participating in it.

The repository contains **code created while working through the course tasks**.

To respect the course rules and good development practices:

- **no API keys or secrets are included** in the repository (they are managed via environment variables),
- **answers submitted to the course platform are not published**,
- **no original course content or datasets** are included.

Some solutions may be inspired by publicly discussed approaches within the course community or by examples provided during the course.

The repository is intended purely for educational and portfolio purposes.

---

### AI Usage

This project was developed with the assistance of **OpenAI Codex** as a pair-programming assistant and coding agent.

AI supported idea exploration, problem-solving, implementation, refactoring, debugging, review work, and documentation support.

No application in this repository was produced without substantial human input, review, and decision-making. Key technical and architectural decisions were either made directly by the author or implemented by the agent after the author approved the direction.

The use of AI is part of what this repository is meant to show: not autonomous code generation, but a structured workflow in which the author defines goals, evaluates trade-offs, reviews results, improves quality, and learns from the implementation.

For transparency and educational value, this repository also includes the actual instruction and workflow files used during the human-AI collaboration process while building the applications in this repository, including [AGENTS.md](AGENTS.md) and supporting documents in [`_agent/`](_agent/). They are published as real working materials that may help others develop more structured and responsible ways of working with AI tools.

The AI acted as a tool within an author-directed workflow, not as an autonomous creator.
