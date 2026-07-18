# AI_devs

Python-based solutions and experiments developed while completing the AI_devs AI engineering course.

This repository contains the complete set of 25 course task applications, from `L1` through `L25`. It is both a record of the completed learning journey and a portfolio of applied AI engineering practice. The work went beyond passing course assignments to explore how AI-powered applications can be designed, implemented, documented, reviewed, and operated in a way that is closer to production software than to one-off scripts.

## Table Of Contents

- [About the course](#about-the-course)
- [Repository structure](#repository-structure)
- [Applications](#applications)
- [Learning approach](#learning-approach)
  - [Human-AI collaboration](#human-ai-collaboration)
  - [Agent knowledge base availability](#agent-knowledge-base-availability)
- [What this repository demonstrates](#what-this-repository-demonstrates)
- [Disclaimers](#disclaimers)
  - [Course & Content](#course--content)
  - [AI Usage Note](#ai-usage-note)

## About the course

AI_devs is a hands-on course focused on building software applications that include AI components, such as Large Language Model workflows, AI API integrations, and model-assisted data processing.

More information about the course:
https://www.aidevs.pl/

## Repository structure

Applications created to solve AI_devs course tasks are located in the `src/apps/` directory. In most cases, each task has its own dedicated application directory, for example `src/apps/L1_people`, containing the code and supporting modules created specifically for that assignment.

The repository also includes applications labeled as `EDU#`. These are not direct course tasks, but rather educational side projects and author experiments. They were usually created as simplified, focused exercises to better understand a specific concept, mechanism, or implementation detail when a topic needed additional hands-on practice.

Application documentation is kept close to the code, usually in a `docs/` directory within the relevant application or implementation variant. README files describe the current purpose, workflow, configuration, run command, module structure, and verification approach for an app. Some apps also include DEV_NOTES files with working context such as implementation history, debugging lessons, trade-offs, open questions, future work, and lessons learned.

Runtime data, generated outputs, logs, cache files, downloaded references, and similar artifacts are intentionally kept outside application source directories whenever practical, usually under the repository-level `data/` directory. This keeps application code focused on implementation and documentation, while runtime artifacts remain separated by purpose.

## Applications

Completed course task applications:

- [`L1_people`](src/apps/L1_people/)
- [`L2_findhim`](src/apps/L2_findhim/)
- [`L3_proxy`](src/apps/L3_proxy/)
- [`L4_sendit`](src/apps/L4_sendit/)
- [`L5_railway`](src/apps/L5_railway/)
- [`L6_categorize`](src/apps/L6_categorize/)
- [`L7_electricity`](src/apps/L7_electricity/)
- [`L8_failure`](src/apps/L8_failure/)
- [`L9_mailbox`](src/apps/L9_mailbox/)
- [`L10_drone`](src/apps/L10_drone/)
- [`L11_evaluation`](src/apps/L11_evaluation/)
- [`L12_firmware`](src/apps/L12_firmware/)
- [`L13_reactor`](src/apps/L13_reactor/)
- [`L14_negotiations`](src/apps/L14_negotiations/)
- [`L15_savethem`](src/apps/L15_savethem/)
- [`L16_okoeditor`](src/apps/L16_okoeditor/)
- [`L17_windpower`](src/apps/L17_windpower/)
- [`L18_domatowo`](src/apps/L18_domatowo/)
- [`L19_filesystem`](src/apps/L19_filesystem/)
- [`L20_foodwarehouse`](src/apps/L20_foodwarehouse/)
- [`L21_radiomonitoring`](src/apps/L21_radiomonitoring/)
- [`L22_phonecall`](src/apps/L22_phonecall/)
- [`L23_shellaccess`](src/apps/L23_shellaccess/)
- [`L24_goingthere`](src/apps/L24_goingthere/)
- [`L25_timetravel`](src/apps/L25_timetravel/)

Educational side applications:

- [`EDU1`](src/apps/EDU1/)

## Learning approach

### Human-AI collaboration

This project was developed with the assistance of **OpenAI Codex** as a pair-programming assistant and coding agent. AI supported idea exploration, problem-solving, implementation, refactoring, debugging, review work, and documentation support.

The work follows an author-directed human-AI collaboration model. The author acts as the architect, reviewer, orchestrator, and learner, while AI coding agents support implementation within the direction set by the author and remain subject to author review.

This is intentionally different from treating an agent as a black-box task solver or autonomous creator. For all applications, the workflow includes explicit design discussion, architecture decisions, documentation planning, implementation review, manual code reading, debugging, and follow-up refinement. The goal is to understand the produced code and the design trade-offs behind it, even when the first implementation draft is generated with AI assistance.

The repository therefore documents not only final code, but also a way of working: using AI as an engineering partner while preserving human responsibility for direction, validation, learning, and quality. In some places, the repository also includes concrete evidence of that workflow, such as [L4_sendit_MVP2_DEV_NOTES.md](src/apps/L4_sendit/L4_sendit_MVP2/docs/L4_sendit_MVP2_DEV_NOTES.md), where AI-generated implementation choices are explicitly reviewed, challenged, and refined from a developer perspective.

For transparency and educational value, this repository includes publishable instruction and workflow files used during the human-AI collaboration process while building the applications in this repository. [AGENTS.md](AGENTS.md) is the compact always-active instruction file and router for the coding agent. More detailed conditional playbooks live in [`_agent/instructions/`](_agent/instructions/) and are loaded for specific work, such as app documentation, LLM design reviews, debugging, external API safety, or agent reference maintenance. These files are published as real working materials that may help others develop more structured and responsible ways of working with AI tools. Some private agent knowledge base materials are intentionally omitted, as explained below.

### Agent knowledge base availability

Some files used during work with AI coding agents are intentionally **not included in the public repository**. This mainly applies to parts of the agent knowledge base: curated reference notes that were built from course materials and adapted for the author's local agent workflow. In this repository, `_agent/instructions/` contains publishable operational playbooks, while `_agent/references/` may contain or point to private course-derived reference material.

Because those materials are derived from course content, they are also connected to the work and intellectual property of the course authors. To respect their rights, effort, and ownership of the original learning materials, the derived agent knowledge base is kept private even though it may be used locally while developing the repository.

As a result, documentation in this repository may contain references to agent knowledge base materials that are not available in the public version of the repo. Those references are left in place because they document the real working process, but they should be understood as pointers to private local context rather than missing setup steps required to run the applications.

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
- **answers submitted to the course platform, including course FLAGS and task completion answers, are not published**,
- **no original course content or datasets** are included.

Some solutions may be inspired by publicly discussed approaches within the course community or by examples provided during the course.

The repository is intended purely for educational and portfolio purposes.

---

### AI Usage Note

Information about AI-assisted development, coding agents, and private agent knowledge base materials is described in [Learning approach](#learning-approach), especially [Human-AI collaboration](#human-ai-collaboration) and [Agent knowledge base availability](#agent-knowledge-base-availability).

This repository also uses an intentionally unconventional and unusually detailed communication-style section in [AGENTS.md](AGENTS.md). That choice is partly practical and partly for fun: it is used to explore how a more expressive AI coding partner affects collaboration, motivation, and learning in day-to-day work.

The developer is aware that this kind of voice-heavy agent design is not necessarily a production best practice, especially when prompt size, predictability, and instruction discipline matter. It applies to chat interaction only and should not be read as a lower standard for code quality, architecture decisions, testing, or technical documentation.
