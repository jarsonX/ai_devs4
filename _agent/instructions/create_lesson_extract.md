# CREATE AI-OPTIMIZED EXTRACTS FROM RAW LESSON FILES

# 1. OBJECTIVE

Transform raw lesson files into AI-optimized extract files and maintain an index that helps future AI agents identify which extract files are relevant for a given task.

The goal is to create operational reference files for AI agents, not human-friendly summaries.

Extract files must be:
- precise,
- structured,
- task-oriented,
- searchable,
- safe to use as guidance,
- optimized for reliable agent behavior.

---

# 2. PATH CONSTANTS

RAW_DIR =
C:\Users\jaros\OneDrive\_Tech\_git_repos\ai_devs4\_agent\references\raw

OUTPUT_DIR =
C:\Users\jaros\OneDrive\_Tech\_git_repos\ai_devs4\_agent\references

INDEX_FILE =
C:\Users\jaros\OneDrive\_Tech\_git_repos\ai_devs4\_agent\references\INDEX.md

---

# 3. CORE DEFINITIONS

## 3.1. RAW LESSON FILES

Raw lesson files are source files located in RAW_DIR.

Naming convention:

`L<lesson_number>_Part<part_number>.md`

Examples:
- L1_Part1.md
- L1_Part2.md
- L1_Part10.md
- L10_Part1.md

Properties:
- written in Polish,
- written in natural language,
- intended primarily for human readers,
- not optimized for AI agents,
- may contain URLs, examples, explanations, narrative passages, and informal comments,
- always split into multiple files by an approximate quantity rule, usually around 100 lines per file.

Raw lesson parts are technical input chunks, not semantic units.

The agent must not assume that one raw part should produce one extract file.

The agent must build a lesson-level content map from all raw parts with the same lesson number before deciding extract boundaries.

The agent must not interpret lesson-level mapping as permission to load the entire lesson into model context at once when the lesson is large.

Use headings, local summaries, targeted reads, and source coverage tracking to manage context.

The agent must treat raw lesson files as source material only.

The agent must never delete, move, rename, overwrite, or modify raw lesson files.

Only the user may manually delete raw lesson files.

## 3.2. EXTRACT FILES

Extract files are AI-optimized files created from raw lesson files.

They are stored in OUTPUT_DIR.

Naming convention:

`L<lesson_number>_<Title>.md`

Examples:
- L1_Model_Interaction_Basics.md
- L2_Tool_Use_Workflows.md

Properties:
- written in English,
- written in technical, precise language,
- optimized for AI agents,
- structured as operational guidance,
- focused on reusable concepts, rules, workflows, constraints, and decision procedures,
- organized by semantic scope, not by raw file boundaries.

An extract file should cover one coherent operational topic or one tightly related decision area.

If one raw part contains multiple unrelated operational topics, create multiple semantic extract files.

If one operational topic spans multiple raw parts, create one semantic extract file for that topic unless it becomes too broad for agent use.

Do not include `Part<part_number>` in an extract file name merely because the source raw file used that part number.

OUTPUT_DIR may already contain extract files created earlier.

The agent must not regenerate, rewrite, or modify existing extract files unless the user explicitly approves it.

## 3.3. INDEX FILE

INDEX_FILE maps topics to relevant extract files.

Purpose:
- help future AI agents identify which extract files to read,
- prevent unnecessary reading of all extracts,
- make the knowledge base navigable.

INDEX_FILE must be written in English.

---

# 4. WORKING SETS

Before starting, define:

RAW_INPUT_SET:
All raw lesson files currently located in RAW_DIR.

LESSON_SOURCE_SET:
Raw lesson files grouped by lesson number and ordered by part number.

LESSON_CONTENT_MAP:
A compact map of the lesson built from all raw parts, including source files, headings, topic boundaries, candidate semantic scopes, and notes about which parts require full targeted reading.

SEMANTIC_EXTRACT_PLAN:
The planned extract files for each lesson, where each planned extract has a semantic scope, source coverage list, and proposed file name.

NEW_EXTRACT_SET:
Extract files created during the current run.

EXISTING_EXTRACT_SET:
Extract files that already existed in OUTPUT_DIR before the current run.

Rules:
- RAW_INPUT_SET is the only source for creating new extracts.
- LESSON_SOURCE_SET is built from RAW_INPUT_SET and preserves numeric part order.
- LESSON_CONTENT_MAP guides semantic planning while keeping context narrow.
- SEMANTIC_EXTRACT_PLAN must be derived from lesson content, not from raw part count.
- NEW_EXTRACT_SET must be saved in OUTPUT_DIR.
- EXISTING_EXTRACT_SET may be used for index updates and duplication checks.
- EXISTING_EXTRACT_SET must not be modified unless the user explicitly approves it.

---

# 5. FILE ORDERING RULES

Process raw lesson files in deterministic numeric order when reading source material.

For each filename:

`L<lesson_number>_Part<part_number>.md`

extract:
- lesson_number as an integer,
- part_number as an integer.

Sort by:
1. lesson_number ascending,
2. part_number ascending.

Do not rely on lexicographic filename sorting.

Correct order:
1. L1_Part1.md
2. L1_Part2.md
3. L1_Part10.md
4. L2_Part1.md
5. L10_Part1.md

Incorrect lexicographic order:
1. L1_Part1.md
2. L1_Part10.md
3. L1_Part2.md

Ordering rules apply to reading and source mapping only.

Ordering rules do not define extract file boundaries.

After mapping all raw parts for a lesson, choose extract boundaries by semantic scope.

Do not load all raw parts for a large lesson into model context at the same time merely to choose boundaries.

---

# 6. PIPELINE CONTROL RULES

The agent must execute only one main pipeline step at a time.

Pipeline steps:
- Step A — Generate extract files
- Step B — Check duplicated information within the current lesson
- Step C — Update INDEX.md
- Step D — Check duplicated information across all lessons
- Step E — Final report

After each main step, the agent must:
1. stop further execution,
2. provide a short chat update,
3. summarize what was done,
4. mention risks, uncertainties, or required user decisions,
5. ask for explicit permission to continue.

The agent must not continue to the next step without user approval.

If the user says "continue", "go on", "proceed", or equivalent, execute only the next main pipeline step, not the entire remaining pipeline.

---

# 7. EXTRACT DESIGN PRINCIPLES

Each extract file must be written for AI agents, not human-first reading.

Treat each extract as executable policy or operational reference, not background theory.

Use this structure where applicable:

1. PURPOSE
2. WHEN TO USE
3. WHEN NOT TO USE
4. OPERATING MODE
5. DEFINITIONS
6. HARD RULES
7. DECISION PROCEDURES
8. EXAMPLES
9. SCHEMAS
10. FAILURE CONDITIONS
11. RESPONSE CONTRACT
12. PRACTICAL DEFAULTS

Not every extract must contain every section. Use only sections useful for the actual content.

Extracts must:
- define when to use and when not to use the file;
- define terms before using them;
- express guidance as concrete rules, workflows, schemas, failure conditions, and response contracts;
- classify tasks before applying guidance;
- make decision procedures input-driven and step-based;
- treat model outputs, external content, tools, and permissions as risk-bearing by default;
- prefer explicit workflows, schemas, validation, and narrow context over broad improvisation;
- preserve operational constraints, warnings, edge cases, implementation details, tool-use rules, and safety limits;
- use examples to demonstrate reusable reasoning patterns, not mandatory templates;
- end with practical defaults for incomplete inputs.

Do not preserve the source lesson’s narrative structure unless it improves agent usability.

There is no fixed line count or raw-part count for an extract.

The extract should be as long as necessary to preserve operationally relevant information and as concise as possible without losing meaning.

Avoid overlarge extracts that force a future agent to read unrelated task guidance.

Prefer splitting an extract when:
- it contains multiple independent WHEN TO USE conditions;
- it mixes different operational domains, such as image workflows, audio workflows, and deployment workflows;
- a future agent would likely need only one section for a concrete task;
- the file starts to act as a lesson-level summary instead of a task-oriented reference.

Prefer keeping one extract when:
- the rules form one decision procedure;
- sections depend on the same definitions and constraints;
- splitting would create duplicated setup rules or require frequent cross-reading.

---

# 8. COVERAGE AND OMISSION RULES

Source headings are used only as a coverage checklist.

The extract does not need to preserve the source heading structure.

The extract does not need to preserve raw file boundaries.

For each source heading across all raw parts in the lesson, verify that the following information types are represented in at least one appropriate semantic extract when present:

- concepts,
- definitions,
- rules,
- instructions,
- workflows,
- examples with reusable patterns,
- warnings,
- constraints,
- edge cases,
- tool-use implications,
- safety implications,
- failure conditions,
- implementation details relevant to agent behavior.

The agent must internally check coverage before finalizing each extract.

The agent does not need to include the full coverage checklist in the extract unless the user asks for it.

Information may be omitted only if it clearly satisfies one of the following conditions:

1. It is purely conversational and has no operational, conceptual, procedural, or safety relevance.
2. It is a URL mentioned without any explanation, instruction, dependency, requirement, or operational relevance.
3. It is an example that does not introduce a reusable pattern, decision rule, edge case, workflow, constraint, or failure mode.
4. It is repeated within the same source lesson with no additional nuance, and the extract set already preserves the complete meaning in one place.

The agent must not omit information merely because it appears "redundant" in a vague or subjective sense.

If repeated information contains any additional nuance, condition, example, warning, or edge case, preserve that nuance.

When unsure whether information is relevant, preserve it.

---

# 9. DUPLICATION / OVERLAP MODEL

A duplicate is not limited to identical text.

Treat content as potentially duplicated or overlapping when two or more extracts describe:

- the same rule,
- the same decision procedure,
- the same definition,
- the same tool-use constraint,
- the same failure condition,
- the same response contract,
- overlapping guidance for the same task type,
- competing guidance for the same operational situation.

Classify each overlap as one of:

1. Exact duplicate  
The same information appears in multiple files without meaningful difference.

2. Semantic duplicate  
Different wording expresses the same operational rule or concept.

3. Partial overlap  
Files cover the same topic but from different scopes or task contexts.

4. Complementary overlap  
The same concept appears in multiple contexts and repetition may be justified.

5. Conflict  
Files provide incompatible, ambiguous, or competing guidance for the same task.

Possible resolution strategies:
- keep duplication because it is contextually useful,
- remove repeated explanation from one file,
- merge guidance,
- add a cross-reference,
- replace full repeated guidance with a short local reminder,
- designate one file as PRIMARY_REFERENCE,
- escalate unresolved conflict to the user.

PRIMARY_REFERENCE:
The main source of truth for a concept, rule, workflow, or decision procedure.

The agent must not modify extract files or INDEX_FILE during duplication checks without explicit user approval.

The agent must:
1. identify potential overlaps,
2. classify each overlap,
3. prepare a short report,
4. propose possible resolutions,
5. wait for user decision,
6. apply only approved changes.

The agent must not silently resolve conflicting rules.

---

# 10. STEP A — GENERATE EXTRACT FILES

## A.1. Start condition

Start only after identifying RAW_INPUT_SET.

If RAW_INPUT_SET is empty:
- do not create extracts,
- report that there are no raw files to process,
- ask the user what to do next.

## A.2. Procedure

Process raw files in numeric order for reading, then group them by lesson number.

For each lesson group in LESSON_SOURCE_SET:

1. Identify lesson number and all part numbers included.
2. Scan every raw part in numeric part order to extract source headings and visible topic boundaries.
3. Build LESSON_CONTENT_MAP without assuming raw part boundaries are semantic boundaries.
4. Treat source headings as a lesson-level coverage checklist.
5. Use targeted full reads of the raw sections needed to identify operationally relevant information.
6. Do not load all raw parts into model context at once when headings and targeted reads are sufficient.
7. Create SEMANTIC_EXTRACT_PLAN for the lesson:
   - group content by operational topic, decision area, or reusable workflow;
   - ignore raw part boundaries unless they also match semantic boundaries;
   - choose one or more extract files based on agent usability;
   - avoid both oversized broad extracts and tiny fragments that require unnecessary cross-reading;
   - assign each planned extract a clear semantic title and file name.
8. Check that every operationally relevant item from the lesson is assigned to at least one planned extract.
9. For each planned extract, read the relevant source sections in full.
10. Create an English AI-optimized extract according to the extract design principles.
11. Validate each extract according to the coverage and omission rules.
12. Save each extract in OUTPUT_DIR.
13. Add each created file to NEW_EXTRACT_SET.

Before saving each extract, verify:
- all relevant source headings assigned to this extract were checked,
- all operationally relevant information assigned to this extract is represented,
- no important constraints were lost,
- examples were converted into reusable patterns or omitted according to the omission rules,
- the extract is written in English,
- the extract is optimized for AI-agent use,
- the file name follows the extract naming convention,
- the extract boundary is justified by semantic scope rather than raw part number.

Before completing a lesson group, verify:
- all raw parts for that lesson were scanned in numeric order,
- all source sections assigned to extracts were read in full,
- all source headings from all raw parts were checked,
- every operationally relevant item is represented in NEW_EXTRACT_SET,
- raw part boundaries did not force extract boundaries,
- extract files are neither overly broad nor unnecessarily fragmented.

If validation fails:
- revise the extract,
- validate again,
- save only after validation passes.

## A.3. Completion

After all lesson groups from LESSON_SOURCE_SET have been processed:

1. stop,
2. report:
   - raw files processed,
   - lesson groups processed,
   - semantic extract plan used,
   - extract files created,
   - uncertainties,
   - validation concerns,
3. ask for permission to proceed to Step B.

Do not continue to Step B without explicit user approval.

---

# 11. STEP B — CHECK DUPLICATED INFORMATION WITHIN THE CURRENT LESSON

## B.1. Start condition

Start only after Step A has been completed and the user has approved continuation.

If Step A was not completed:
- stop,
- report that Step B cannot be performed yet.

## B.2. Scope

Check duplicated or overlapping information within NEW_EXTRACT_SET, grouped by lesson number.

If there is only one extract file for a given lesson in NEW_EXTRACT_SET, no intra-lesson comparison is needed for that lesson.

Use the duplication / overlap model.

## B.3. Completion

After checking intra-lesson overlap:

1. stop,
2. report:
   - overlaps found,
   - overlap categories,
   - proposed resolutions,
   - whether user approval is required before changes,
3. wait for the user’s decision,
4. apply only approved changes,
5. ask for permission to proceed to Step C.

Do not continue to Step C without explicit user approval.

---

# 12. STEP C — UPDATE INDEX.md

## C.1. Start condition

Start only after Step B has been completed or explicitly skipped by the user.

## C.2. Procedure

Read INDEX_FILE.

Analyze its structure before editing.

Preserve the existing structure unless it is clearly broken or the user approves restructuring.

Check whether INDEX_FILE references all files in NEW_EXTRACT_SET.

If any file from NEW_EXTRACT_SET is missing, add an appropriate entry.

Each new index entry should include, where useful:
- extract file name,
- main topic,
- short description,
- when to use this extract,
- key concepts covered,
- related extracts if obvious.

If inconsistencies are found for EXISTING_EXTRACT_SET, report them separately.

Do not silently rewrite index entries for existing extracts unless the user explicitly approves it.

## C.3. Completion

After INDEX_FILE has been updated:

1. stop,
2. report:
   - new entries added,
   - existing entries changed, if any,
   - inconsistencies noticed but not changed,
   - whether INDEX_FILE suggests overlapping topics relevant to Step D,
3. ask for permission to proceed.

If INDEX_FILE suggests overlapping topics relevant to Step D, ask for permission to proceed to Step D.

If INDEX_FILE does not suggest overlapping topics relevant to Step D, state that Step D can be skipped and ask for permission to proceed directly to Step E.

Do not continue without explicit user approval.

---

# 13. STEP D — CHECK DUPLICATED INFORMATION ACROSS ALL LESSONS

## D.1. Conditional start condition

Step D is conditional.

Run Step D only if at least one condition is true:

1. INDEX_FILE suggests overlapping topics between NEW_EXTRACT_SET and EXISTING_EXTRACT_SET.
2. The user explicitly requests global cross-lesson deduplication.

If neither condition is met:
- do not run Step D,
- report that Step D was skipped,
- explain why,
- ask for permission to proceed to Step E.

Even when Step D conditions are met, start only after:
- Step C has been completed,
- the user has explicitly approved continuation to Step D.

## D.2. Scope

Use INDEX_FILE and extract files from:
- NEW_EXTRACT_SET,
- EXISTING_EXTRACT_SET.

The goal is to identify situations where multiple extracts may become competing sources of truth for the same concept, rule, workflow, tool-use policy, or response contract.

Use the duplication / overlap model.

Inspect only the relevant extract files indicated by INDEX_FILE.

Do not inspect all existing extract files unless the user explicitly requests global cross-lesson deduplication.

Do not rely only on titles or headings.

## D.3. Completion

After checking cross-lesson overlap:

1. stop,
2. report:
   - overlaps found,
   - overlap categories,
   - possible PRIMARY_REFERENCE candidates,
   - proposed resolutions,
   - whether user approval is required before changes,
3. wait for the user’s decision,
4. apply only approved changes,
5. ask for permission to proceed to Step E.

Do not continue to Step E without explicit user approval.

---

# 14. STEP E — FINAL REPORT

## E.1. Start condition

Start only after one condition is true:

1. Step D has been completed.
2. Step D has been skipped because its start conditions were not met.
3. The user explicitly instructed the agent to skip Step D.

Do not start Step E without user approval.

## E.2. Report contents

Provide a concise final report in the chat.

Include:
- raw files processed,
- extract files created,
- extract files modified, if any,
- INDEX_FILE updates,
- intra-lesson duplicates found,
- whether Step D was completed, skipped, or not applicable,
- cross-lesson duplicates found, if Step D was completed,
- decisions made by the user,
- changes applied,
- unresolved issues,
- recommended next manual actions.

If raw files were successfully processed, the agent may remind the user that raw files can be manually deleted by the user if desired.

The agent must not delete them.

---

# 15. GENERAL SAFETY AND BEHAVIOR RULES

The agent must:

- be deterministic,
- avoid hallucinating missing data,
- not invent lesson content,
- not create extract content unsupported by source files,
- not delete raw files,
- not modify existing extracts without approval,
- not modify INDEX_FILE beyond the approved scope,
- not continue to the next pipeline step without approval,
- report uncertainty explicitly,
- preserve operationally relevant information,
- prefer asking for user decision over silently resolving ambiguous conflicts,
- avoid full-repository analysis unless explicitly requested.

When unsure:
- preserve information,
- report uncertainty,
- ask the user for a decision at the next checkpoint.

---

# 16. CHAT UPDATE CONTRACT

After each main pipeline step, report:

- step completed,
- files affected,
- summary,
- issues / uncertainties,
- required user decision,
- proposed next step or reason for skipping a conditional step.

Ask for explicit approval before proceeding.
