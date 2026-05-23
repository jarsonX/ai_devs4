# CREATE AI-OPTIMIZED EXTRACTS FROM RAW LESSON FILES

## Table Of Contents

- [1. Objective](#1-objective)
- [2. Path Constants](#2-path-constants)
- [3. Source And Output Types](#3-source-and-output-types)
- [4. Working Sets](#4-working-sets)
- [5. Shared Operating Rules](#5-shared-operating-rules)
- [6. Step A - Build Source Inventory](#6-step-a---build-source-inventory)
- [7. Step B - Prepare PNG Evidence](#7-step-b---prepare-png-evidence)
- [8. Step C - Build Lesson Content Map And Semantic Extract Plan](#8-step-c---build-lesson-content-map-and-semantic-extract-plan)
- [9. Step D - Write Extract Files](#9-step-d---write-extract-files)
- [10. Step E - Check Duplicated Information Within The Current Lesson](#10-step-e---check-duplicated-information-within-the-current-lesson)
- [11. Step F - Update INDEX.md](#11-step-f---update-indexmd)
- [12. Step G - Update GLOSSARY.md](#12-step-g---update-glossarymd)
- [13. Step H - Check Duplicated Information Across All Lessons](#13-step-h---check-duplicated-information-across-all-lessons)
- [14. Step I - Final Report](#14-step-i---final-report)
- [15. General Safety And Behavior Rules](#15-general-safety-and-behavior-rules)

---

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
`.\_agent\references\raw`

RAW_IMAGE_DIR =
`.\_agent\references\raw\images`

PNG_MAP_FILE_PATTERN =
`.\_agent\references\raw\images\L<lesson_number>_png_map.md`

OUTPUT_DIR =
`.\_agent\references`

INDEX_FILE =
`.\_agent\references\INDEX.md`

GLOSSARY_FILE =
`.\GLOSSARY.md`

---

# 3. SOURCE AND OUTPUT TYPES

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
- may contain URLs, PNG image references, examples, explanations, narrative passages, and informal comments,
- split into multiple files by an approximate quantity rule, usually around 100 lines per file.

Raw lesson parts are technical input chunks, not semantic units.

Use raw lesson files as source material only.

Do not delete, move, rename, overwrite, or modify raw lesson files.

## 3.2. PNG IMAGE REFERENCES AND MAPS

Raw lesson files may contain Markdown image links or direct URL references to `.png` files.

Only URLs whose path targets a `.png` file, case-insensitively, count as PNG image references.

Non-PNG URLs are ignored unless their surrounding raw text contains operationally relevant information by itself.

For each lesson, complete PNG handling before extract planning:
1. scan raw files for PNG references;
2. download discovered PNG files into RAW_IMAGE_DIR in batches of at most 5 images;
3. create or update the lesson PNG map in RAW_IMAGE_DIR using PNG_MAP_FILE_PATTERN;
4. visually inspect downloaded PNG files in batches of at most 5 images;
5. update the map with inspection findings and relevance;
6. use the map during lesson analysis and extract creation.

Do not create SEMANTIC_EXTRACT_PLAN or write extracts for a lesson until PNG discovery, download, map update, and inspection are complete for that lesson, except when unavailable PNG files have been recorded as uncertainties in the PNG map.

Downloaded PNG files in RAW_IMAGE_DIR are supporting source artifacts, not extract files.

RAW_IMAGE_DIR contents and PNG map files are temporary working artifacts. Cleanup is outside this workflow and remains a human responsibility after extract creation.

Use stable, traceable local PNG filenames that preserve the original image basename when possible and avoid overwriting unrelated images.

Each lesson PNG map must be written in English and include, for every discovered PNG reference:
- lesson number,
- source raw file,
- nearby heading or local context,
- original PNG URL,
- local PNG path in RAW_IMAGE_DIR, when download succeeds,
- download status,
- inspection status,
- concise visual findings after inspection,
- operational relevance for extract coverage,
- planned or final extract assignment, when known.

Do not treat Markdown alt text or surrounding link text as proof of image content.

Do not infer, summarize, or invent details from a PNG that was not successfully downloaded and inspected.

If a PNG cannot be downloaded or inspected, record that status in the PNG map and report it as an uncertainty at the next checkpoint.

PNG batch rule:
- A PNG download or inspection batch must contain at most 5 images.
- If a lesson contains more than 5 PNG references, split PNG handling into multiple batches.
- After each PNG batch, update the lesson PNG map before starting the next batch.
- Do not keep more than one PNG batch's visual details in active context unless the current decision requires comparison across batches.

## 3.3. EXTRACT FILES

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

Do not regenerate, rewrite, or modify existing extract files unless the user explicitly approves it.

## 3.4. INDEX FILE

INDEX_FILE maps topics to relevant extract files.

Purpose:
- help future AI agents identify which extract files to read,
- prevent unnecessary reading of all extracts,
- make the knowledge base navigable.

INDEX_FILE must be written in English.

## 3.5. GLOSSARY FILE

GLOSSARY_FILE is the repository-root human-facing glossary.

Purpose:
- help the human learner understand abbreviations and concepts found in extract files,
- provide short beginner-friendly explanations,
- map terms to related extract references.

GLOSSARY_FILE must be written in English.

GLOSSARY_FILE supports learning. It is not the primary operational reference for AI agents.

---

# 4. WORKING SETS

Define these working sets before execution:

RAW_INPUT_SET:
All raw lesson files currently located in RAW_DIR.

LESSON_SOURCE_SET:
Raw lesson files grouped by lesson number and ordered by part number.

PNG_IMAGE_REFERENCE_SET:
All `.png` image references discovered in RAW_INPUT_SET, grouped by lesson number and source raw file.

DOWNLOADED_PNG_SET:
All PNG files downloaded into RAW_IMAGE_DIR during the current run, grouped by lesson number and source raw file.

PNG_REFERENCE_MAP_SET:
Lesson PNG map files created or updated in RAW_IMAGE_DIR using PNG_MAP_FILE_PATTERN.

LESSON_CONTENT_MAP:
A compact lesson-level map built from raw headings, targeted reads, PNG map findings, topic boundaries, candidate semantic scopes, and source coverage notes.

SEMANTIC_EXTRACT_PLAN:
The planned extract files for each lesson, where each planned extract has a semantic scope, source coverage list, and proposed file name.

CURRENT_LESSON_GROUP:
The single lesson group currently being processed through PNG handling, semantic planning, extract writing, and lesson-local duplication checks.

NEW_EXTRACT_SET:
Extract files created during the current run.

EXISTING_EXTRACT_SET:
Extract files that already existed in OUTPUT_DIR before the current run.

GLOSSARY_CANDIDATE_SET:
Abbreviations and concepts discovered in NEW_EXTRACT_SET during the current run that may need to be added to GLOSSARY_FILE.

GLOSSARY_EXISTING_TERM_SET:
Terms already present in the Term column of GLOSSARY_FILE before the current glossary update step.

Working set rules:
- RAW_INPUT_SET is the only source for creating new extracts.
- LESSON_SOURCE_SET preserves deterministic numeric order.
- PNG_IMAGE_REFERENCE_SET contains only PNG references found in RAW_INPUT_SET.
- DOWNLOADED_PNG_SET contains local PNG files saved in RAW_IMAGE_DIR.
- PNG_REFERENCE_MAP_SET contains PNG map files saved in RAW_IMAGE_DIR.
- LESSON_CONTENT_MAP guides semantic planning while keeping context narrow.
- SEMANTIC_EXTRACT_PLAN must be derived from lesson content, not raw part count.
- CURRENT_LESSON_GROUP must contain only one lesson number at a time.
- NEW_EXTRACT_SET must be saved in OUTPUT_DIR.
- EXISTING_EXTRACT_SET may be used for index updates and duplication checks.
- EXISTING_EXTRACT_SET must not be modified unless the user explicitly approves it.
- GLOSSARY_CANDIDATE_SET must be derived from NEW_EXTRACT_SET, not from a full glossary rebuild by default.
- GLOSSARY_EXISTING_TERM_SET should be built by reading only the Term column of GLOSSARY_FILE whenever possible.

---

# 5. SHARED OPERATING RULES

## 5.1. FILE ORDERING

Process raw lesson files in deterministic numeric order.

For each filename matching `L<lesson_number>_Part<part_number>.md`, extract:
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

Ordering rules apply to reading and source mapping only.

Ordering rules do not define extract file boundaries.

## 5.2. CONTEXT MANAGEMENT

Build a lesson-level content map from all raw parts with the same lesson number before deciding extract boundaries.

Do not load all raw parts for a large lesson into model context at once when headings, local summaries, targeted reads, and source coverage tracking are sufficient.

Choose extract boundaries by semantic scope, not by raw part boundaries.

## 5.3. PIPELINE GATES

The agent must execute only one main pipeline step at a time.

Pipeline steps:
- Step A - Build source inventory
- Step B - Prepare PNG evidence
- Step C - Build lesson content map and semantic extract plan
- Step D - Write extract files
- Step E - Check duplicated information within the current lesson
- Step F - Update INDEX.md
- Step G - Update GLOSSARY.md
- Step H - Check duplicated information across all lessons
- Step I - Final report

The agent must not combine PNG preparation, semantic extract planning, and extract writing in a single main pipeline step.

Large lesson safety rules:
- Process one lesson group at a time after Step A.
- Process PNG references in batches of at most 5 images.
- Build heading maps and source coverage notes before targeted full-section reads.
- Write at most one planned extract before validating coverage for that extract.
- If a lesson contains many raw parts or many PNG references, stop after each completed batch or lesson-scoped substep and report progress, uncertainties, and the proposed next batch or substep.

After each main step, stop and report:
- step completed,
- files affected,
- summary,
- issues or uncertainties,
- required user decision,
- proposed next step or reason for skipping a conditional step.

Ask for explicit permission before proceeding to the next main step.

If the user says "continue", "go on", "proceed", or equivalent, execute only the next main pipeline step, not the entire remaining pipeline.

Steps B through F are lesson-scoped and may be repeated for additional lesson groups after the current lesson group is complete.

## 5.4. EXTRACT DESIGN

Each extract file must be written for AI agents, not human-first reading.

Treat each extract as executable policy or operational reference, not background theory.

Use this structure where useful:
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

Not every extract must contain every section. Use only sections that improve agent usability for the actual content.

Extracts must:
- define when to use and when not to use the file,
- define terms before using them,
- express guidance as concrete rules, workflows, schemas, failure conditions, and response contracts,
- classify tasks before applying guidance,
- make decision procedures input-driven and step-based,
- treat model outputs, external content, tools, and permissions as risk-bearing by default,
- prefer explicit workflows, schemas, validation, and narrow context over broad improvisation,
- preserve operational constraints, warnings, edge cases, implementation details, tool-use rules, and safety limits,
- use examples to demonstrate reusable reasoning patterns, not mandatory templates,
- end with practical defaults for incomplete inputs.

Do not preserve the source lesson's narrative structure unless it improves agent usability.

There is no fixed line count or raw-part count for an extract.

The extract should be as long as necessary to preserve operationally relevant information and as concise as possible without losing meaning.

Prefer splitting an extract when:
- it contains multiple independent WHEN TO USE conditions,
- it mixes different operational domains, such as image workflows, audio workflows, and deployment workflows,
- a future agent would likely need only one section for a concrete task,
- the file starts to act as a lesson-level summary instead of a task-oriented reference.

Prefer keeping one extract when:
- the rules form one decision procedure,
- sections depend on the same definitions and constraints,
- splitting would create duplicated setup rules or require frequent cross-reading.

## 5.5. COVERAGE AND OMISSION

Source headings are used as a coverage checklist, not as a required extract structure.

For each source heading across all raw parts in the lesson, verify that the following information types are represented in at least one appropriate semantic extract when present:
- concepts,
- definitions,
- rules,
- instructions,
- workflows,
- examples with reusable patterns, including PNG image examples,
- warnings,
- constraints,
- edge cases,
- tool-use implications,
- safety implications,
- failure conditions,
- implementation details relevant to agent behavior.

Information may be omitted only if it clearly satisfies one of these conditions:
1. It is purely conversational and has no operational, conceptual, procedural, or safety relevance.
2. It is a non-PNG URL mentioned without any explanation, instruction, dependency, requirement, or operational relevance.
3. It is an example that does not introduce a reusable pattern, decision rule, edge case, workflow, constraint, or failure mode.
4. It is repeated within the same source lesson with no additional nuance, and the extract set already preserves the complete meaning in one place.

PNG image references are not covered by the generic URL omission rule. Apply section 3.2 before deciding whether image content can be omitted.

Do not omit information merely because it appears redundant in a vague or subjective sense.

If repeated information contains any additional nuance, condition, example, warning, or edge case, preserve that nuance.

When unsure whether information is relevant, preserve it and report the uncertainty at the next checkpoint.

## 5.6. DUPLICATION AND OVERLAP MODEL

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

Do not modify extract files or INDEX_FILE during duplication checks without explicit user approval.

Do not silently resolve conflicting rules.

---

# 6. STEP A - BUILD SOURCE INVENTORY

## A.1. START CONDITION

Start by identifying RAW_INPUT_SET.

If RAW_INPUT_SET is empty:
- do not create extracts,
- report that there are no raw files to process,
- ask the user what to do next.

## A.2. PROCEDURE

1. Process raw file names in deterministic numeric order.
2. Group raw files by lesson number.
3. For each lesson group, identify all included part numbers.
4. Identify EXISTING_EXTRACT_SET from OUTPUT_DIR.
5. Report any filename that does not match the raw lesson naming convention.

In Step A, do not:
- scan raw files for PNG references,
- download or inspect PNG files,
- build LESSON_CONTENT_MAP,
- create SEMANTIC_EXTRACT_PLAN,
- write extract files,
- update INDEX_FILE.

## A.3. COMPLETION

After LESSON_SOURCE_SET has been built, stop and report:
- raw files discovered,
- lesson groups discovered,
- included part numbers per lesson,
- existing extract files noticed,
- filename anomalies, if any,
- uncertainties.

Ask for permission to proceed to Step B for one selected lesson group.

---

# 7. STEP B - PREPARE PNG EVIDENCE

## B.1. START CONDITION

Start only after Step A has been completed and the user has approved continuation for one CURRENT_LESSON_GROUP.

If CURRENT_LESSON_GROUP is not selected:
- stop,
- list available lesson groups from LESSON_SOURCE_SET,
- ask the user which lesson group to process.

If Step A was not completed:
- stop,
- report that Step B cannot be performed yet.

## B.2. PROCEDURE

For CURRENT_LESSON_GROUP only:

1. Scan every raw part in numeric part order for:
   - source headings,
   - visible topic boundaries,
   - Markdown image links and direct URL references to `.png` files.
2. Build PNG_IMAGE_REFERENCE_SET for the lesson.
3. Create or update the lesson PNG map file in RAW_IMAGE_DIR using PNG_MAP_FILE_PATTERN.
4. Record discovered references, source files, nearby headings, and local context in the PNG map before downloading images.
5. If no PNG references are found, record that result in the PNG map or report it as a no-PNG lesson finding.
6. If PNG references are found, split them into batches of at most 5 images.
7. For each PNG batch:
   - download each PNG into RAW_IMAGE_DIR,
   - update the PNG map with local paths, download status, and unavailable references,
   - visually inspect each successfully downloaded PNG,
   - update the PNG map with inspection status, concise visual findings, preliminary operational relevance, and source context.

Do not use surrounding Markdown alt text as a substitute for visual inspection.

Do not create SEMANTIC_EXTRACT_PLAN or write extracts in Step B.

Do not proceed to Step C for this lesson until PNG handling is complete or unavailable PNG references have been recorded as uncertainties.

## B.3. BATCH CHECKPOINTS

If a lesson has more than 5 PNG references, a Step B invocation may process only the next PNG batch.

After each PNG batch, stop when needed to protect context and report:
- lesson number,
- batch size,
- PNG references processed,
- PNG references remaining,
- PNG map file updated,
- download or inspection failures,
- uncertainties,
- proposed next PNG batch.

If Step B stops after a PNG batch and PNG references remain, Step B is not complete. The next user continuation resumes Step B for the next PNG batch, not Step C.

## B.4. COMPLETION

After all PNG references for CURRENT_LESSON_GROUP have been handled, stop and report:
- raw parts scanned,
- PNG references discovered,
- PNG map file created or updated,
- PNG files downloaded,
- unavailable PNG references, if any,
- inspection uncertainties,
- whether Step C is unblocked.

Ask for permission to proceed to Step C for the same CURRENT_LESSON_GROUP.

---

# 8. STEP C - BUILD LESSON CONTENT MAP AND SEMANTIC EXTRACT PLAN

## C.1. START CONDITION

Start only after Step B has been completed for CURRENT_LESSON_GROUP and the user has approved continuation.

If Step B was not completed for CURRENT_LESSON_GROUP:
- stop,
- report that Step C cannot be performed yet.

## C.2. PROCEDURE

For CURRENT_LESSON_GROUP only:

1. Build LESSON_CONTENT_MAP from:
   - source headings,
   - visible topic boundaries,
   - targeted reads of relevant raw sections,
   - relevant inspected PNG findings from the PNG map.
2. Treat source headings and relevant PNG findings as the lesson-level coverage checklist.
3. Do not assume raw part boundaries are semantic boundaries.
4. Do not load all raw parts into model context at once when headings, local summaries, targeted reads, and source coverage tracking are sufficient.
5. Group content by operational topic, decision area, or reusable workflow.
6. Choose one or more extract files based on agent usability.
7. Avoid both oversized broad extracts and tiny fragments that require unnecessary cross-reading.
8. Assign each planned extract a clear semantic title and file name.
9. Assign every operationally relevant item, including relevant inspected PNG findings, to at least one planned extract.
10. Update the lesson PNG map with planned extract assignments for relevant PNG findings.

Do not write extract files in Step C.

## C.3. PLAN VALIDATION CHECKLIST

Before completing Step C, verify:
- all raw parts for CURRENT_LESSON_GROUP were scanned in numeric order,
- the lesson PNG map was saved in RAW_IMAGE_DIR before extract planning began,
- PNG references for the lesson were either downloaded and inspected or recorded as unavailable,
- non-PNG URLs were ignored unless surrounding raw text was operationally relevant by itself,
- all source headings from all raw parts were considered,
- every operationally relevant item has a planned extract assignment,
- raw part boundaries did not force extract boundaries,
- planned extract files are neither overly broad nor unnecessarily fragmented.

If validation fails:
- revise LESSON_CONTENT_MAP or SEMANTIC_EXTRACT_PLAN,
- validate again,
- complete Step C only after validation passes.

## C.4. COMPLETION

After SEMANTIC_EXTRACT_PLAN has been created for CURRENT_LESSON_GROUP, stop and report:
- lesson content map summary,
- semantic extract plan,
- planned extract files,
- source coverage notes,
- PNG findings assigned to planned extracts,
- uncertainties,
- validation concerns.

Ask for permission to proceed to Step D for the same CURRENT_LESSON_GROUP.

---

# 9. STEP D - WRITE EXTRACT FILES

## D.1. START CONDITION

Start only after Step C has been completed for CURRENT_LESSON_GROUP and the user has approved continuation.

If SEMANTIC_EXTRACT_PLAN is missing or not approved:
- stop,
- report that Step D cannot be performed yet.

## D.2. PROCEDURE

For CURRENT_LESSON_GROUP only:

1. Select the next planned extract from SEMANTIC_EXTRACT_PLAN.
2. Read the relevant source sections in full.
3. Use the lesson PNG map to return to relevant local PNG files and findings.
4. Create an English AI-optimized extract according to section 5.4.
5. Validate the extract according to sections 5.5 and D.3.
6. Save the extract in OUTPUT_DIR.
7. Add the created file to NEW_EXTRACT_SET.
8. Update source coverage tracking for CURRENT_LESSON_GROUP.

By default, write one planned extract per Step D invocation. Multiple extracts may be written in one invocation only when the planned extracts are small, tightly related, and the user explicitly approved that batch.

Do not update INDEX_FILE in Step D.

## D.3. EXTRACT VALIDATION CHECKLIST

Before saving each extract, verify:
- all relevant source headings assigned to this extract were checked,
- relevant PNG references assigned to this extract were inspected or recorded as unavailable,
- the lesson PNG map contains local paths, inspection findings, and extract assignment notes needed to trace image evidence,
- all operationally relevant information assigned to this extract is represented,
- no important constraints were lost,
- examples were converted into reusable patterns or omitted according to section 5.5,
- the extract is written in English,
- the extract is optimized for AI-agent use,
- the file name follows the extract naming convention,
- the extract boundary is justified by semantic scope rather than raw part number.

Before completing all extract writing for CURRENT_LESSON_GROUP, verify:
- all planned extracts were created,
- all source sections assigned to extracts were read in full,
- all source headings from all raw parts were checked,
- every operationally relevant item is represented in NEW_EXTRACT_SET,
- raw part boundaries did not force extract boundaries,
- extract files are neither overly broad nor unnecessarily fragmented.

If validation fails:
- revise the extract,
- validate again,
- save only after validation passes.

## D.4. COMPLETION

After each Step D invocation, stop and report:
- extract files created,
- planned extracts remaining, if any,
- source coverage completed,
- PNG evidence used,
- uncertainties,
- validation concerns.

If planned extracts remain, ask for permission to continue Step D for the next planned extract.

If all planned extracts for CURRENT_LESSON_GROUP have been written, ask for permission to proceed to Step E for the same CURRENT_LESSON_GROUP.

---

# 10. STEP E - CHECK DUPLICATED INFORMATION WITHIN THE CURRENT LESSON

## E.1. START CONDITION

Start only after Step D has been completed for CURRENT_LESSON_GROUP and the user has approved continuation.

If Step D was not completed for CURRENT_LESSON_GROUP:
- stop,
- report that Step E cannot be performed yet.

## E.2. SCOPE

Check duplicated or overlapping information within NEW_EXTRACT_SET for CURRENT_LESSON_GROUP.

If there is only one extract file for CURRENT_LESSON_GROUP in NEW_EXTRACT_SET, no intra-lesson comparison is needed for that lesson.

Use the duplication and overlap model from section 5.6.

Do not modify extract files during Step E without explicit user approval.

## E.3. COMPLETION

After checking intra-lesson overlap, stop and report:
- overlaps found,
- overlap categories,
- proposed resolutions,
- whether user approval is required before changes.

Wait for the user's decision.

Apply only approved changes.

Ask for permission to proceed to Step F.

---

# 11. STEP F - UPDATE INDEX.md

## F.1. START CONDITION

Start only after Step E has been completed or explicitly skipped by the user.

## F.2. PROCEDURE

1. Read INDEX_FILE.
2. Analyze its structure before editing.
3. Preserve the existing structure unless it is clearly broken or the user approves restructuring.
4. Check whether INDEX_FILE references all files created for CURRENT_LESSON_GROUP in NEW_EXTRACT_SET.
5. Add an appropriate entry for each missing file created for CURRENT_LESSON_GROUP.
6. Report inconsistencies found for EXISTING_EXTRACT_SET separately.

Each new index entry should include, where useful:
- extract file name,
- main topic,
- short description,
- when to use this extract,
- key concepts covered,
- related extracts if obvious.

Do not silently rewrite index entries for existing extracts unless the user explicitly approves it.

## F.3. COMPLETION

After INDEX_FILE has been updated, stop and report:
- new entries added,
- existing entries changed, if any,
- inconsistencies noticed but not changed,
- whether INDEX_FILE suggests overlapping topics relevant to Step H,
- unprocessed lesson groups remaining, if any.

If unprocessed lesson groups remain, ask whether to proceed to Step B for the next lesson group or move toward final cross-lesson checks.

Ask for permission to proceed to Step G.

---

# 12. STEP G - UPDATE GLOSSARY.md

## G.1. START CONDITION

Start only after Step F has been completed for CURRENT_LESSON_GROUP and the user has approved continuation.

If GLOSSARY_FILE does not exist:
- create it at repository root,
- write it as a human-facing Markdown glossary,
- include a concise Table Of Contents near the beginning when useful for navigation.

## G.2. SCOPE

Update GLOSSARY_FILE from NEW_EXTRACT_SET for CURRENT_LESSON_GROUP only.

GLOSSARY_FILE is intended primarily for the human learner, not as the main operational reference for AI agents.

Do not create temporary checklist files for routine glossary updates unless the user explicitly requests them.

Do not scan all extract files by default. Scan only NEW_EXTRACT_SET unless:
- the user explicitly requests a full glossary rebuild,
- the glossary structure is broken,
- a term conflict cannot be resolved without checking existing references.

## G.3. PROCEDURE

1. Read only the Term column of GLOSSARY_FILE whenever possible to build GLOSSARY_EXISTING_TERM_SET.
2. Preserve the existing glossary table structure unless it is clearly broken or the user approves restructuring.
3. Scan each file in NEW_EXTRACT_SET for abbreviations and important concepts.
4. For each discovered abbreviation or concept:
   - if the term already exists in GLOSSARY_FILE, do not duplicate the row;
   - read only the existing row for that term when its Description or Related references must be checked or updated;
   - add the new extract file to `Related references` if it is not already listed;
   - if the term is new, add a new row.
5. Write or update `Description` for each new or materially changed term.
6. Keep descriptions short: 1-3 beginner-friendly sentences.
7. For abbreviations, start the description with the expanded form of the abbreviation. The expansion does not count toward the 1-3 sentence limit.
8. Use language understandable to a beginner in programming and AI.
9. Avoid unexplained jargon. If a technical word is necessary, explain it simply.
10. Keep the table sorted alphabetically by the term column.
11. Keep `Related references` as extract file names in backticks.

## G.4. GLOSSARY STYLE RULES

GLOSSARY_FILE must be:
- written in English,
- human-facing,
- beginner-friendly,
- concise,
- accurate to the extract files,
- useful for learning vocabulary before reading the detailed agent references.

A glossary description should explain what the term means in practice, not only give a formal definition.

Do not use GLOSSARY_FILE to store operational instructions that belong in extract files.

Do not add secrets, real API URLs, credentials, tokens, or internal endpoints.

## G.5. COMPLETION

After GLOSSARY_FILE has been updated, stop and report:
- new terms added,
- existing terms updated,
- related references added to existing terms,
- terms considered but skipped,
- uncertainties,
- whether Step H is recommended or can be skipped.

If INDEX_FILE suggests relevant cross-lesson overlap and the user wants cross-lesson deduplication now, ask for permission to proceed to Step H.

If INDEX_FILE does not suggest relevant cross-lesson overlap, state that Step H can be skipped and ask for permission to proceed directly to Step I.

---

# 13. STEP H - CHECK DUPLICATED INFORMATION ACROSS ALL LESSONS

## H.1. CONDITIONAL START CONDITION

Run Step H only if at least one condition is true:
1. INDEX_FILE suggests overlapping topics between NEW_EXTRACT_SET and EXISTING_EXTRACT_SET.
2. The user explicitly requests global cross-lesson deduplication.

If neither condition is met:
- do not run Step H,
- report that Step H was skipped,
- explain why,
- ask for permission to proceed to Step I.

Even when Step H conditions are met, start only after:
- Step G has been completed for the relevant new extract files,
- the user has explicitly approved continuation to Step H.

## H.2. SCOPE

Use INDEX_FILE and extract files from:
- NEW_EXTRACT_SET,
- EXISTING_EXTRACT_SET.

The goal is to identify situations where multiple extracts may become competing sources of truth for the same concept, rule, workflow, tool-use policy, or response contract.

Use the duplication and overlap model from section 5.6.

Inspect only the relevant extract files indicated by INDEX_FILE.

Do not inspect all existing extract files unless the user explicitly requests global cross-lesson deduplication.

Do not rely only on titles or headings.

## H.3. COMPLETION

After checking cross-lesson overlap, stop and report:
- overlaps found,
- overlap categories,
- possible PRIMARY_REFERENCE candidates,
- proposed resolutions,
- whether user approval is required before changes.

Wait for the user's decision.

Apply only approved changes.

Ask for permission to proceed to Step I.

---

# 14. STEP I - FINAL REPORT

## I.1. START CONDITION

Start only after one condition is true:
1. Step H has been completed.
2. Step H has been skipped because its start conditions were not met.
3. The user explicitly instructed the agent to skip Step H.

## I.2. REPORT CONTENTS

Provide a concise final report in the chat.

Include:
- raw files processed,
- lesson groups processed,
- extract files created,
- extract files modified, if any,
- INDEX_FILE updates,
- GLOSSARY_FILE updates,
- intra-lesson duplicates found,
- whether Step H was completed, skipped, or not applicable,
- cross-lesson duplicates found, if Step H was completed,
- decisions made by the user,
- changes applied,
- unresolved issues,
- recommended next manual actions.

If raw files were successfully processed, the agent may remind the user that raw files can be manually deleted by the user if desired.

If PNG files or PNG maps were created in RAW_IMAGE_DIR, the agent may remind the user that RAW_IMAGE_DIR and PNG map cleanup is a manual user responsibility after extract creation.

Do not delete raw files, downloaded PNG files, or PNG map files.

---

# 15. GENERAL SAFETY AND BEHAVIOR RULES

The agent must:
- be deterministic,
- avoid hallucinating missing data,
- not invent lesson content,
- not create extract content unsupported by source files,
- not modify existing extracts without approval,
- not modify INDEX_FILE beyond the approved scope,
- not use GLOSSARY_FILE as a substitute for agent-oriented extract files,
- keep GLOSSARY_FILE beginner-friendly because it is intended primarily for the human learner,
- report uncertainty explicitly,
- preserve operationally relevant information,
- prefer asking for user decision over silently resolving ambiguous conflicts,
- avoid full-repository analysis unless explicitly requested.

When unsure:
- preserve information,
- report uncertainty,
- ask the user for a decision at the next checkpoint.
