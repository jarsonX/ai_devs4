# Glossary

This glossary collects abbreviations and concepts found in root-level `L*.md` files in `_agent/references/`.

| Term | Description |
|---|---|
| Action surface | All actions and external effects available to a model through its tools, APIs, data access, and communication channels. A smaller action surface limits what a mistaken or compromised model can do. |
| Action-capable agent | An agent that can do something through tools, not only write an answer. For example, it may send a message, change a file, or call an API, so it needs extra safety checks. |
| Adversarial content | Content that tries to confuse the agent or change what it is supposed to do. Treat it as ordinary data, not as instructions to follow. |
| Adversarial input | Input created to bypass rules, leak data, or make the system do something unsafe. The system should check it before using it in tools or decisions. |
| Agent | A system where a model can choose steps or tools to reach a goal. It is more flexible than a fixed workflow, but also needs clearer limits. |
| Agent configuration | The settings that describe what an agent may do: instructions, tools, context, and limits. Clear configuration makes the agent easier to test and debug. |
| Agent instruction | System-level guidance that shapes an agent's role, behavior, constraints, and communication style. It helps the model understand how it should act inside a specific system. |
| Agent knowledge | Information about a specific agent, such as its behavior rules, tool-use instructions, communication rules, memories, observations, or reflections. It should be separated from user-private and public knowledge. |
| Agent loop | A repeated cycle where the model checks the situation, uses a tool, looks at the result, and decides what to do next. This is useful when the next step is not known upfront. |
| Agent settings | Relatively stable values such as an agent's name, description, tools, active modes, permissions, model choice, and availability to other agents. They describe the operating setup around the agent. |
| Agent workflow | A workflow where the model helps decide steps, tools, and the final answer. Use it when simple fixed code cannot easily cover all cases. |
| Agentic RAG | Retrieval-Augmented Generation done as a search loop. The agent searches, reads results, improves the query, checks if it has enough evidence, and then answers. |
| Agentic support | Model-driven help that improves a human or deterministic process without controlling the final irreversible action. Examples include drafting, organizing, filtering, or recommending. |
| Agentic workflow | A workflow where one or more model-driven agents choose steps, gather information, delegate work, or synthesize results from changing context. It is useful when fixed code or one simple model call is too rigid. |
| Agent-oriented knowledge base | A knowledge base organized so an agent can navigate it through entry points, links, folders, and instructions instead of guessing every search query. It is useful when documents are meant to guide agent work, not only store information. |
| AI | Artificial Intelligence. In this glossary it usually means software behavior powered by models, such as LLMs, agents, or image/audio/video models. |
| AI workflow | A workflow that combines normal application logic with one or more AI or LLM calls. It needs extra validation because it can return technically successful but incomplete or wrong results. |
| AI-assisted deployment safety | Rules for using AI help during deployment without blindly trusting it. The human or deterministic code should still control secrets, infrastructure, and risky changes. |
| AI-friendly API | An API that is easy for a model to choose and call correctly. It should have clear names, clear inputs, clear outputs, and useful error messages. |
| AI gateway | A central application layer that handles communication with AI models and providers. It keeps model choice, request settings, monitoring, streaming, and provider switching out of scattered feature code. |
| Anomaly detection | Monitoring for unusual behavior such as cost spikes, long latency, repeated failures, or abuse patterns. It helps notice when the system needs a code-level response, not only a report. |
| API | Application Programming Interface. A contract that tells software how to ask another system or component to do something. |
| API constraint audit | A review of an API before exposing it to a model. The goal is to find confusing parts, risky actions, missing limits, or places where a wrapper is needed. |
| API rate limit | Application Programming Interface rate limit. A limit on how many requests or tokens can be used in a period of time. |
| Application-induced model error | A model mistake caused by the application setup, not only by the model itself. Examples include missing tools, wrong instructions, or bad context. |
| Artifact | A durable file, content object, or structured record produced during a workflow and used by later tasks or reviewers. It should preserve enough metadata, ownership, state, and provenance to be checked independently. |
| Assertion | A concrete check used inside an eval, such as requiring valid JSON, matching a value, or asking a model to grade a rubric. Assertions turn broad quality goals into measurable checks. |
| Attachment | A file or media item included in a request, such as an image, audio file, video, PDF, or document. The system must know whether the model should inspect it or a tool should use it. |
| Attention item | A task, session, tool call, or agent state that needs human review before the system can safely continue. Examples include missing approval, expired authentication, or a blocked decision. |
| Attention queue | A visible list of attention items that need human or operator action. It helps long-running agent systems avoid hiding blocked, risky, or failed work inside chat history. |
| Augmented function calling | Giving the model extra useful context before it calls a function or tool. This helps it choose better arguments. |
| Authenticated browser profile | Saved browser state that contains an established login session. It must be protected like a credential and isolated to the intended user and domain. |
| Automation boundary | The point where model autonomy stops and deterministic code, validation, approval, or human action takes control. It should move only when evidence shows that a wider scope remains useful and safe. |
| Background agent | An agent that reacts to events and performs useful work without requiring a continuous chat. It still needs a clear way to request approval, missing information, or human help. |
| Batching | Combining several related operations into one larger operation. This can save time and reduce repeated tool calls. |
| Best-effort cleanup | Finalization work that tries to save valid partial state or release resources after any ending path. A cleanup failure must be recorded instead of being silently treated as success. |
| Blackboard topology | A multi-agent structure where agents contribute through a shared workspace or state store instead of direct messages. It needs ownership, permissions, conflict detection, and provenance. |
| Browser agent | A model-driven workflow that chooses browser actions and interprets page state when a fixed script is not reliable enough. It should still use narrow actions and validate every important result. |
| Bulk processing | Applying deterministic code to many files or records without sending each item through model context. It is useful for repeatable parsing, filtering, aggregation, and calculation. |
| Cache | Temporary information that may be reused but is not automatically trusted knowledge. Search results, scraped pages, and sandbox outputs often start as cache until validated. |
| Caching | Saving a result so the system can reuse it later instead of doing the same expensive work again. It is useful when the same input should produce the same result. |
| Canary check | A recurring test that sends known input through a workflow to see whether the output still looks acceptable. It helps catch regressions that normal uptime monitoring may miss. |
| Capability inventory | A source-checked list of actions available in an API or SDK. It helps decide which capabilities are required, optional, unnecessary, or forbidden before tools are designed. |
| Capability map | A concise description of what an agent or team can do. It helps route work without duplicating every detailed tool schema in the prompt. |
| Canonical internal API format | The application-owned request and response shape used before translating calls to a specific provider. It lets feature code stay stable while adapter code handles provider differences. |
| Checksum guard | A safety check that notices when a file changed since it was last read. It helps avoid overwriting someone else's newer changes. |
| Chunk | A smaller piece of a larger document. Search systems often use chunks because they are easier to find, rank, and place into model context. |
| Chunking strategy | The rule for splitting documents into chunks. A good strategy keeps chunks small enough to search, but large enough to keep useful meaning. |
| Circuit breaker | A runtime guard that temporarily stops calls to a failing dependency. It helps the workflow fail fast instead of wasting time, tokens, and resources on calls that are likely to fail. |
| Claim | An atomic reservation that gives one worker temporary ownership of a task. It prevents multiple workers from performing the same task at the same time. |
| Classification | Assigning input to one of several predefined categories. For example, classifying a message as `question`, `bug`, or `feedback`. |
| Classification prompt | A prompt that asks the model to choose from predefined categories. The allowed categories should be listed clearly. |
| CLI | Command Line Interface. A way to use a program by typing commands in a terminal. |
| Cloudflare Workers deployment | Running and publishing code through Cloudflare's serverless platform. In these notes, it is one possible way to publish a remote MCP server. |
| Communication degradation | The loss, compression, distortion, or reinterpretation of information as it moves between agents. Structured data, source identifiers, and explicit uncertainty fields help reduce it. |
| Completion guard | Deterministic logic that checks required state and artifacts before an agent loop may finish. It can allow exit, request missing work, pause for a human, or return a structured failure. |
| Confirmation | A clear approval step before or after a risky action. The user should see what will happen before approving it. |
| Confirmation step | A required user approval before a destructive or high-risk action. It is a guardrail for actions that affect data, money, people, or external systems. |
| Context assembly | The process of building what the model sees before it answers. It may include instructions, user input, files, tool results, and stored state. |
| Context enrichment | Adding relevant verified facts to incomplete input before making a decision or calling a tool. Enrichment gathers information, while separate validation and authorization decide whether it is correct and safe to use. |
| Context management | Choosing and organizing only the information the model needs for the current task. Good context is short enough to avoid noise but complete enough to answer well. |
| Context recall | An eval metric that checks whether the system retrieved or used the context needed to answer well. It is especially useful for RAG and search-based workflows. |
| Context selection | Picking the most relevant messages, files, tool results, or facts for the model. It helps reduce confusion and unnecessary exposure of data. |
| Context window | The maximum amount of text and output a model can handle in one request. If the input is too large, the model may have less space for the answer. |
| Control | A product or code rule that keeps important actions under user or system control. Use controls when model judgment alone is not safe enough. |
| Conversation relevance | An eval metric that checks whether a response fits the current conversation, not just a single isolated prompt. It is useful when previous messages change what counts as a good answer. |
| Conversation summarization | Replacing old conversation history with a shorter summary. This keeps important facts while reducing context size. |
| Coordinator | An agent or controller that assigns work, gathers results, tracks progress, and decides when to ask another agent, tool, or human for help. It is often the main thread that keeps a multi-agent workflow coherent. |
| Cosine similarity | A way to compare two vectors and estimate how similar they are. In search, it can suggest useful results, but it does not prove that a result is correct. |
| CRON | A time-based scheduler for running jobs at regular times or intervals. In agent systems, a CRON trigger starts a predefined task because its scheduled time has arrived. |
| Curated path | A prepared chain of files, folders, or references that leads an agent from a broad entry point to the exact context it needs. It reduces blind searching by showing the next place to look. |
| Daily Ops | A recurring update workflow that gathers information from sources such as email, calendar, tasks, notes, goals, history, and memory. It usually needs deduplication, escalation, and personalized synthesis. |
| Data exposure review | A check of what data the agent can access. The goal is to give access only to what the task really needs. |
| Data movement | Moving information from one place to another, such as from a file into an email. This can be risky if private data goes to the wrong destination. |
| Dataset | A set of examples used to test or evaluate model or agent behavior. A good dataset covers important cases, varied inputs, and balanced categories. |
| Dead letter queue | A queue or table that stores work items a system could not process after retries were exhausted. It lets the team review, alert, or reprocess failures instead of losing data. |
| Decomposed processing | Splitting one media task into smaller steps. For video, this may mean extracting audio, transcribing speech, and checking frames separately. |
| Deep Action | An iterative agent workflow that uses research-like steps to produce an action plan, code change, audit, or operational decision. It should still require approval before real side effects. |
| Deep Research | A long-running workflow where an agent clarifies a question, searches, reads, finds gaps, repeats, and writes a structured report. It is useful for broad tasks where one search is not enough. |
| Defense in depth | Using several safety layers instead of relying on one rule. If one layer fails, another may still protect the system. |
| Delegation contract | A clear agreement for sending a bounded task from a parent agent to a child agent. It should define the task, inputs, allowed tools, output format, failure behavior, and who remains accountable. |
| Destructive action | An action that can delete, overwrite, or permanently change data. It should usually require preview, confirmation, or another safety check. |
| Detail control | A tool input that lets the caller choose compact or expanded output. It avoids creating separate tools only to return different amounts of information. |
| Deterministic workflow | A workflow where code decides the steps in advance. This is best when the process is known and does not need model decisions at each step. |
| Direct audio understanding | Giving audio directly to a model that can understand sound or speech. This can preserve tone or sound details that plain transcription may miss. |
| Direct video analysis | Giving a video directly to a model or API that can inspect it. This is simpler than splitting the video into audio and frames, if the tool supports it. |
| Document representation | The form of a document used by the model or search system. It can be plain text, OCR text, page images, metadata, summaries, or a mix of these. |
| Document template | A reusable starting file for creating a document. It helps keep generated documents consistent. |
| DOCX | Office Open XML Document. A Microsoft Word-style document file that may need parsing before a model or search system can use it well. |
| Domain lock | A programmatic restriction that makes every domain except the selected one unavailable during a sensitive operation. It prevents data from another account, project, or tenant from entering the active context. |
| Domain-specific tools | Tools assigned to an agent because they match that agent's specialist area, such as calendar, email, research, music, vehicle, or image tools. They help keep specialists focused. |
| Downstream use | Anything that happens later based on model output. If code, tools, storage, or the UI uses the output, that output needs stronger checks. |
| Dry run | A preview of an action without actually changing anything. It lets you inspect what would happen before committing the action. |
| Dynamic context engineering | Choosing where information should live: in the prompt, in files, in state, in tools, or in code. The goal is to give the model the right information without overloading it. |
| Dynamic knowledge resources | A task-specific set of documents or data sources shown to the model. This avoids giving the model too much unrelated knowledge. |
| Dynamic placeholder | A value or reference filled in at runtime instead of being hard-coded. It lets prompts or documents point to changing data safely. |
| Dynamic section | Prompt content injected while the system is running, such as an agent roster, workspace state, session metadata, memory summary, permissions, or available tools. |
| Dynamic tool discovery | Finding or enabling only the tools that matter for the current task. This helps the model avoid choosing from too many tools. |
| Dynamic tool list | A task-specific list of tools available to the model. A shorter, relevant list makes tool choice safer and easier. |
| Dynamic workflow | A workflow where the model can decide the next step after seeing intermediate results. Use it when the path depends on what the system discovers. |
| Embedding | A list of numbers that represents the meaning of text, an image, or other content. Search systems compare these number lists to find items with similar meaning. |
| End frame | An image used as the desired final frame of a generated video. It helps guide where the video should end. |
| Environment snapshot | A time-bound record of changing state such as time, location, weather, device activity, or application state. It must be refreshed when a later decision depends on current conditions. |
| Eval | A structured test that scores model or agent behavior against chosen criteria. It helps measure quality, regressions, tool use, cost, or safety, but it does not guarantee correctness. |
| Eval strategy | A plan for deciding which behaviors should be evaluated, how much effort to spend, and what decision the eval should support. It keeps evals tied to product risk instead of dashboard vanity. |
| Evaluation | Checking whether something is correct, good enough, safe, or complete. It can be done by code, a model, or both. |
| Evaluation harness | The code and configuration that run eval cases, control state, capture traces, apply assertions, and report results. A reliable harness makes repeated comparisons consistent. |
| Evaluation prompt | A prompt that asks the model to judge quality, correctness, safety, or completion. It should say exactly what criteria to use. |
| Event | An application-level observation, action, or state change such as a warning, tool call, message, cost alert, or background job marker. Events help explain what happened around model calls, tool calls, agents, and workflows. |
| Event bus | A routing mechanism that sends events by topic to subscribers. It helps decouple agents or services, but it still needs schemas, duplicate handling, and review boundaries. |
| Event ingestion | The boundary that validates and converts different trigger formats into one internal event shape. Normalization makes routing consistent without pretending that every trigger needs identical handling. |
| Event topic | A named event contract such as `ticket.classified` or `user.message`. It tells publishers and subscribers what kind of payload and behavior to expect. |
| Execution bridge | A controlled interface that lets sandboxed code call selected tools or host services. The bridge must enforce its own permissions because process isolation alone does not make those calls safe. |
| Execution guard | A check that happens before the system performs an action. It can verify required inputs, permissions, confirmations, or safe routing. |
| Experiment | A controlled eval run that compares prompts, models, tool definitions, or agent versions on a dataset. It should record versions and metrics so results can be reproduced. |
| Exponential backoff | A retry strategy where the delay grows after each failed attempt. It reduces pressure on a busy or failing service compared with retrying immediately. |
| Exposure surface | Everything the agent can reach: tools, data, permissions, and actions. A smaller exposure surface usually means lower risk. |
| External context | Information loaded from outside the model, such as files, tool results, search results, messages, or attachments. It can help answer, but it may be incomplete or unsafe. |
| Extraction | Pulling specific facts from messy or unstructured input. For example, extracting name, date, and address from an email. |
| Extraction prompt | A prompt that asks the model to pull specific facts from text or media. It should name the fields the model must return. |
| False negative | An eval result where the score says the output is bad, but the output is actually good. This usually means the evaluator, expected answer, or dataset needs improvement. |
| False positive | An eval result where the score says the output is good, but the output is actually bad. This is dangerous because it can hide real system failures behind a nice metric. |
| Freshness check | A deterministic check that verifies input data is recent enough for the job or decision using it. It helps prevent old data from producing new-looking output. |
| FTS | Full-Text Search. Search based on exact words, phrases, or tokens in text. |
| FTS5 | Full-Text Search 5. SQLite's built-in full-text search feature used for keyword-style search. |
| Full-text search | Search based on words that appear in documents. It works especially well for names, IDs, filenames, and exact phrases. |
| Gap detection | The step of noticing what is still missing, weak, contradictory, or underexplored after a search or analysis pass. It helps decide whether to continue researching or produce the final output. |
| Generated image reference | A file reference returned by a tool after it creates or edits an image. Later steps can use that reference to inspect or edit the image. |
| Generated media reference | A file reference for generated media, such as an image, chart, or video. It connects the generated asset to later document or validation work. |
| Generation | One model call, including the prompt context, model settings, output, token usage, latency, and cost. In observability, generations are usually nested inside a trace. |
| Global context | Shared context that can influence many agents or sessions over time, such as memory, project notes, goals, or a knowledge base. It needs clear ownership because mistakes can spread across future work. |
| Graceful degradation | A fallback mode where the system keeps doing the safe useful parts of the workflow when one dependency is unavailable. The user or operator should see that the result is partial or delayed, not complete. |
| Graph memory | A memory layer that stores facts, entities, sources, and relationships in a graph. It can help an agent follow connections, but it needs auditing and cleanup. |
| Graph-RAG | Retrieval-Augmented Generation that combines document search with graph traversal. The agent can retrieve chunks, inspect entities, follow relationships, and answer from both text and graph evidence. |
| grep | A command-line text search tool. It is useful for finding exact words or patterns in local files before using heavier retrieval methods. |
| Guard classifier | A separate, narrowly scoped model call that classifies untrusted input before the main workflow receives or acts on it. It can reduce risk, but it can still make mistakes or be bypassed. |
| Guardrail | Runtime logic that blocks, filters, moderates, or constrains unsafe or unwanted behavior. Guardrails enforce boundaries while evals only measure behavior. |
| Hallucination | Model output that is not supported by the available information. It may sound confident even when it is wrong. |
| Heartbeat | A periodic cycle that either coordinates durable tasks or checks whether current conditions require attention. Unlike CRON, an attention heartbeat may finish successfully without taking any action. |
| Heartbeat monitoring | A monitoring pattern where a scheduled job reports that it ran and what final status it reached. If the expected report does not arrive, an external monitor can alert the operator. |
| Healthcheck | A check that proves a system, service, or scheduled job is alive or has completed a required step. For jobs, a healthcheck should distinguish success, refusal, failure, and missing runs. |
| HTML | HyperText Markup Language. The standard markup language used to structure web pages and some generated documents. |
| HTTP | HyperText Transfer Protocol. The basic protocol used by browsers, web servers, and many APIs to send requests and responses. |
| Human checkpoint | A designed pause where a person supplies missing information, resolves ambiguity, approves an action, or accepts partial work. The checkpoint should explain what is blocked and what happens after the decision. |
| Hybrid retrieval | Search that combines more than one method, often keyword search and embedding search. This can find better evidence than either method alone. |
| Image generation input | Everything given to an image model to create or edit an image. It may include a prompt, reference images, masks, templates, or settings. |
| Indexed fragment | A piece of content saved in a search index. It should keep a link back to the original source. |
| In-painting | Editing or filling a selected part of an image. For example, replacing an object inside an image while keeping the rest. |
| Input sanitization | Cleaning or checking input before the model or tools use it. This helps block unsafe, malformed, or confusing input. |
| Instruction dropout | A situation where the model misses or ignores important instructions. This can happen when the context is too long, noisy, or conflicting. |
| Instruction/data separation | Keeping instructions separate from external content. A web page, file, or tool result should not be allowed to secretly become a new instruction. |
| Interface pressure test | Using a less capable model to reveal unclear prompts, hidden assumptions, or overly complex tool contracts. The test should improve the interface, not lower the required correctness standard. |
| Item | A flexible interaction record that can represent different event types, not only a user or assistant message. Items are useful when a workflow must store tool calls, reasoning summaries, confirmations, or actions between multiple actors. |
| Jitter | Random variation added to retry delays. It prevents many workers from retrying at the same moment and making an overloaded service even worse. |
| JSON | JavaScript Object Notation. A simple text format for structured data, often used for API requests, tool arguments, and model outputs. |
| JSON prompt | JavaScript Object Notation prompt. A prompt written as structured JSON, so each part can be edited separately and precisely. |
| Latency | The time a user or system waits for a result. In AI apps, latency often comes from model calls, tool calls, retries, and large context. |
| Least privilege | Giving a system only the permissions it needs for the current task. This reduces damage if something goes wrong. |
| Lifecycle hook | Deterministic code that runs at a defined point in an agent or tool lifecycle, such as before a tool call or before finishing. It records, validates, or controls process state outside the model's narration. |
| Lightweight model | A smaller, faster, or cheaper model used for simpler tasks. It is a good fit when the task is narrow and easy to verify. |
| Live audio interface | A real-time voice interaction where the user and system can take turns quickly. It needs low latency and clear turn handling. |
| LLM | Large Language Model. A model trained to understand and generate language, often used for chat, reasoning, extraction, and tool use. |
| LLM-as-judge | A scoring method where a language model grades another model output using a rubric. It is useful for semantic quality checks, but it should not replace simple code checks when code can verify the answer directly. |
| Lockfile | A file used as a simple lock so another copy of the same job does not start while one run is already active. It should include stale-lock recovery so a crash does not block future runs forever. |
| Logging and audit | Recording what the system did and why. This helps with debugging, reviewing mistakes, and investigating unsafe behavior. |
| Lost update | A shared-state failure where two writers read the same old version, prepare different changes, and the later write overwrites the earlier one. It is common when agents rewrite the same free-text memory or file. |
| Manager agent | An agent that coordinates other agents, monitors progress, routes communication, asks the user when needed, and verifies results. It should have broad visibility only where useful and a narrow set of action tools. |
| MCP | Model Context Protocol. A standard way to connect models to tools, resources, prompts, and other capabilities. |
| MCP backend host | Model Context Protocol backend host. A backend app that owns the MCP client and coordinates MCP tools, even if users do not see it directly. |
| MCP delivery layer | Using MCP as a transport and integration layer. MCP helps deliver tools, but the tools still need good names, schemas, and safety rules. |
| MCP endpoint | Model Context Protocol endpoint. A network route used to reach a remote MCP server. |
| MCP publication | Model Context Protocol publication. The work needed to make an MCP server reachable by other hosts or clients. |
| MCP sampling | Model Context Protocol sampling. A flow where an MCP server asks the client or host to perform a model generation and return the result. The host should control credentials, limits, approval, and data exposure. |
| MCP surface | Model Context Protocol surface. Everything an MCP server exposes, such as tools, resources, prompts, apps, sampling, or elicitation. |
| MCP tools | Model Context Protocol tools. Tools exposed by an MCP server and made available to a model host or client. |
| MCPB | Model Context Protocol Bundle. A package format for distributing an MCP server and its configuration as one `.mcpb` file. |
| MCPB-compatible host | Model Context Protocol Bundle-compatible host. A host application that can import an `.mcpb` package and help the user set it up. |
| Memory Manager | A role or service that manages selected memory or context areas. It usually has broader history access and stricter write authority than ordinary worker agents. |
| Mesh topology | A multi-agent structure where agents can communicate directly with specific peer agents. It needs strong message contracts, identity, auditability, and loop prevention. |
| Metadata | Extra information about a document or chunk, such as file path, title, section, date, or source. Metadata helps search, filtering, citations, and later context interpretation. |
| Metric | A measured signal used to judge system behavior, such as accuracy, latency, trace cost, context recall, or user satisfaction. A useful metric should support a concrete decision. |
| MIME | Multipurpose Internet Mail Extensions. A standard way to label file types, such as `text/plain`, `image/png`, or `application/pdf`. |
| Model call reduction | Designing a system to use fewer model calls when possible. This can save cost and make the app faster. |
| Model self-verification | Asking a model to check an answer, sometimes its own answer. It can help find problems, but it is not proof that the answer is correct. |
| Moderation | Automatic checking for unsafe, abusive, disallowed, or out-of-scope content. It is one safety layer, not the whole safety system. |
| Monitoring | Watching how the system behaves while it runs. Monitoring helps detect failures, misuse, unusual behavior, and performance problems. |
| Multi-agent topology | The structure that defines how agents communicate, where state lives, who coordinates work, and how results are combined. Common patterns include pipeline, blackboard, orchestrator, tree, mesh, and swarm. |
| Multimodal model | A model that can work with more than one type of input or output, such as text, images, audio, or video. |
| Multi-mode tool | A tool with several named modes, such as `create`, `update`, or `delete`. The modes should be clear so the model knows which one to use. |
| MVP | Minimum Viable Product. The smallest useful version of a product that can test its most important assumptions before broader implementation. |
| Native tools | Tools built directly into the host application, not imported through MCP. They still need clear contracts and safety checks. |
| Negative constraint | A behavior an eval requires not to happen, such as avoiding every write tool in a read-only scenario. It must be checked across the relevant trace, not guessed from the final answer. |
| Neo4j | A graph database often used to store nodes and relationships. In agent workflows, it can support graph search, graph memory, and relationship traversal. |
| OAuth | Open Authorization. A common way to let an app access a user's data or services without sharing the user's password. |
| OAuth in MCP | Open Authorization in Model Context Protocol. OAuth used when an MCP system needs to act for a user or access protected user data. |
| OAuth-enabled MCP publication | Open Authorization-enabled Model Context Protocol publication. A remote MCP setup that includes authentication routes as well as the main MCP route. |
| Observability | Runtime visibility into what an LLM application or agent system did, including prompts, tool calls, traces, costs, latency, and errors. It helps debug behavior that ordinary logs or code inspection may not explain. |
| Observational Memory | A memory strategy where an agent keeps a compact log of important observations and current task state. It helps preserve continuity across long conversations or restarted sessions. |
| Observation-driven context gathering | Searching or reading in steps, where each result helps decide the next step. This is useful when the first search is incomplete. |
| Observer | A model step that updates an Observational Memory log from new unsealed messages plus the existing log. It should record useful state without inventing new facts. |
| OCR | Optical Character Recognition. A technique that turns text visible in images or scans into machine-readable text. |
| Operational dashboard | A human-facing view of running agents, sessions, tasks, tool calls, health, and attention items. It makes multi-agent activity inspectable outside a single chat window. |
| Operational file reference | A file reference that a tool can use, such as a path, file ID, URL, or asset ID. It is more useful to tools than a plain description of the file. |
| Operational oversight | The human and system processes used to observe, pause, resume, approve, repair, or reject agent activity. It is important when agents run long tasks, schedules, tools, or side effects. |
| Orchestrator | A central agent or controller that delegates tasks, collects results, decides next steps, and contacts the user when needed. It keeps a multi-agent workflow coherent, but can become a bottleneck if overloaded. |
| Orchestrator-only tools | Tools reserved for a manager or coordinator agent, such as spawning agents, managing agent status, sending notifications, or coordinating shared state. They should not automatically be given to every specialist. |
| Out-painting | Extending an image beyond its original borders. The model generates new surrounding content that should match the image. |
| Output quality monitoring | Checking whether model outputs are useful, complete, and plausible, not only whether the API responded. Useful checks include required fields, output length, topic coverage, canary checks, latency, and token usage. |
| Output token limit | The maximum amount of text a model is allowed to generate in one response. A large input can leave less room for output. |
| Output validation | Checking output before the system uses it. This can include checking that a model answer, file, report, backup, message, or record exists, has the right format, contains plausible values, and is complete enough for its purpose. |
| Partial retrieval | A search result that includes some useful information but misses other important information. It can lead to answers that are partly correct but incomplete. |
| Pass-through mapping | A provider adapter mapping where the internal request format already matches the provider closely, so little translation is needed. It is still a deliberate mapping boundary, not permission to leak provider details everywhere. |
| Paused loop | An agent execution state where the agent cannot safely continue until it receives missing information, permission, or a decision. It should be explicit so blocked work does not look complete. |
| PDF | Portable Document Format. A common document format that may need text extraction, OCR, or page-image processing before search or model use. |
| Perceived performance | How fast the system feels to the user. Progress messages or partial results can make slow work feel clearer and less frustrating. |
| Permission check | A backend check that confirms an action is allowed. The model should not be the only authority for permissions. |
| Permission review | A review of what permissions a task really needs. The goal is to avoid giving the agent too much access. |
| Persistent context | Context stored outside the active model window, such as files, databases, vector stores, graph stores, or durable logs. It can outlive one session, so read and write rules matter. |
| Phase flag | A machine-readable value that records whether a required workflow stage completed successfully. It should be set only after its evidence or output has been validated. |
| Pipeline | A task split into ordered steps, such as prepare input, call model, validate output, and save result. Pipelines make complex work easier to control. |
| Plan mode | A temporary mode focused on planning before execution. It helps decide steps and risks before making changes. |
| Policy persistence | Continued enforcement of a deterministic policy across retries, reformulated requests, and later conversation turns. An eval checks persistence, but backend code must enforce the policy. |
| Prefilling | Giving the model a starting piece of output or structure to continue from. It can guide the model, but should be used carefully. |
| Private knowledge | User-specific information, such as a person's context, preferences, private workflows, owned documents, or process notes. It should not be treated as public just because an agent can read it. |
| Proactive action | An agent action started by an event or state change instead of a new direct user request. It should require fresh evidence, permission, and a valid no-action path. |
| Progressive disclosure | Exposing only a small initial set of tools or information, then letting the agent discover more when needed. This keeps context smaller and reduces unnecessary tool exposure. |
| Progressive scope reduction | Narrowing available data, tools, and permissions as a workflow moves from broad low-risk organization toward sensitive generation or action. Each later phase receives only what it needs. |
| Promotion gate | Explicit correctness, safety, cost, latency, and rollback conditions a candidate model must meet before replacing the baseline. It prevents a good-looking average score from hiding a critical regression. |
| Prompt | The full input given to a model, including the task, context, rules, and expected output format. A good prompt says clearly what the model should do. |
| Prompt injection | A trick where external content tries to give the model new instructions. For example, a web page might say "ignore previous instructions". |
| Prompt registry | A place where prompt templates and their versions are stored. It lets traces and generations point back to the exact prompt version that produced an output. |
| Prompt rewrite | Turning a user's rough request and clarifications into a more detailed structured prompt. It is especially useful before long research or deep action workflows. |
| Prompt template | A reusable prompt with stable parts and editable fields. Templates help keep repeated model calls consistent. |
| Prompt versioning | Tracking changes to prompts and linking each version to runs, scores, costs, and outputs. This helps compare behavior and roll back bad prompt changes. |
| Primitive | A small reusable product or architecture building block that can support several more specific features. Choosing the right primitive can make an AI product easier to extend without overbuilding it. |
| Property graph | A graph model where nodes and relationships can have properties. It is the style of graph used by Neo4j in the L8 Graph-RAG reference. |
| Provenance | Information about where data came from. In search and RAG, provenance helps trace an answer back to the original file or chunk. |
| Provider abstraction | A code layer that hides details of a specific model provider. It makes it easier to switch providers or models later. |
| Provider mapper | Adapter code that converts an application's internal request into one provider's native request and converts the provider response back. It keeps provider-specific field names and quirks out of feature code. |
| Provider router | Logic that chooses which provider mapper should handle a model request. It may route by model name, explicit provider, agent configuration, tenant policy, or required capability. |
| Public knowledge | Long-term knowledge that may be shared between agents and users of a system. It needs clear write rules because many people or agents may rely on it. |
| Public MCP exposure | A Model Context Protocol server or route that can be reached by untrusted or semi-trusted users, clients, or environments. Public exposure needs stronger auth and monitoring. |
| Query enrichment | Adding helpful details to a query before running it. For example, adding known dates, IDs, language hints, or scope. |
| Query pre-processing | Work done before a deep research call, such as asking clarifying questions, narrowing scope, or rewriting the prompt. It is usually the developer's responsibility. |
| Query strategy | The plan for how to search. It may include keywords, synonyms, translations, filenames, exact phrases, or semantic queries. |
| Query transformation | Turning a user's natural-language request into a clearer query or tool-ready instruction. This helps tools receive better inputs. |
| RAG | Retrieval-Augmented Generation. A pattern where the system first retrieves relevant information, then uses it to help the model answer. |
| Rate limit | A limit on how many requests or tokens can be used in a time window. When a system hits a rate limit, it should slow down, queue, or retry later. |
| Reasoning difficulty | How hard a task is for a model to think through. More ambiguity, more steps, or more synthesis usually means higher reasoning difficulty. |
| Reciprocal Rank Fusion | A ranking method that combines several result lists by looking at result positions. It is useful when different search methods return scores that are hard to compare directly. |
| Recovery hints | Helpful instructions returned after a tool call fails. They tell the model what it can do next to recover. |
| Reference asset | A file, image, URL, or template used as input for generation, editing, or analysis. Tools usually need a real reference, not only a description. |
| Reference image | An image used to guide generation or editing. It may show style, pose, object identity, framing, or composition. |
| Reflection | A short intermediate step where the system checks intent, missing data, or the next action. It should help the workflow, not just add extra text. |
| Reflector | A model step that compresses an Observational Memory log when the log becomes too large. It should compress existing memory, not infer new facts. |
| Relevant document | A document that actually helps answer the user's task. A document can look similar to the query and still not be relevant. |
| Re-loop | A bounded return to the agent loop because required work is incomplete but still recoverable. The next attempt should name the missing phases, allowed tools, and remaining limits. |
| Remote MCP server | Model Context Protocol server exposed over a network. Because other hosts can reach it, it needs careful routing, auth, and safety choices. |
| Rendered document | A document with final visual layout, such as an HTML page, PDF, or email. It should be checked visually, not only as raw text. |
| Replay | Reconstructing a model or agent interaction from logged prompts, messages, tools, settings, and outputs so it can be rerun or compared. It is useful for debugging but may not reproduce full production behavior unless tools and state are represented safely. |
| Required inputs | Values that must be known before an action can safely run. If they are missing, the system should ask or stop instead of guessing. |
| Residual risk | Risk that remains after safeguards are applied. A classifier, sandbox, approval step, or other control may reduce danger without guaranteeing that failure is impossible. |
| Response contract | The expected shape and meaning of a response. It should explain success, failure, missing data, and possible next steps. |
| Response normalization | Converting different provider responses into one application-owned shape. It lets the rest of the system read outputs, usage, tool calls, errors, and provider metadata consistently. |
| Retrieval gap | A situation where an agent retrieves a useful-looking document but misses related context that would change the answer. It is dangerous because the agent may not know anything is missing. |
| Retry | Trying an operation again after a failure. Retries should be limited and should usually be used only for failures that may recover, such as timeouts or rate limits. |
| Reverse proxy exposure | Publishing a server through a routing layer such as `nginx`. This changes how the server is reached and what security controls are needed. |
| ripgrep | A fast command-line text search tool, usually run as `rg`. It is a strong first choice for searching small or medium local text corpora by exact terms or patterns. |
| Risk-bearing action | An action that can spend money, expose data, change state, contact someone, delete content, or create legal or business risk. It needs stronger controls. |
| RRF | Reciprocal Rank Fusion. A method for merging ranked search results from different search systems. |
| Runtime instruction injection | Adding temporary instructions while the system is running. These instructions should be narrow and removed when the task or mode ends. |
| Runtime state | Operational data stored in a database or runtime layer, such as session records, agent status, task state, schedules, or metadata. Agents may see only injected summaries of it. |
| Sandbox | A restricted environment where code or tools have limited access. It reduces what can go wrong if code behaves badly. |
| Sandboxed execution | Running generated code or tool calls inside a restricted runtime with controlled access to host functions, files, network, and output. It can reduce risk, but it still needs clear boundaries. |
| Sandboxing | Running code or tools inside a restricted environment. It limits access to files, network, or system features. |
| Schema compliance | Whether output matches the expected shape, fields, types, and allowed values. It proves the format is right, not that the content is true. |
| Schema sampling | Reading a small, representative set of records to learn a dataset's structure before processing all of it. Good sampling includes ordinary, optional, empty, and unusual cases when available. |
| Scope reduction | Replacing a broad AI goal with a smaller task, user group, data domain, action set, or decision area. This usually makes the system easier to verify and safer to operate. |
| SDK | Software Development Kit. A set of libraries, tools, and examples that help developers build with a platform or API. |
| Scheduled job | A task that runs because a scheduler, cron expression, timer, or queue delay starts it. It needs explicit timing, validation, monitoring, and overlap controls when failure would matter. |
| Sealed memory | A compact, durable record of completed work and essential state used to resume a task without replaying its full conversation. It should contain validated facts, artifacts, and remaining work. |
| Search architecture | The chosen design for finding information. It may use file search, a database, keyword search, embeddings, or a mix of methods. |
| Self-verification | Asking a model to review an answer or output. It can catch some errors, but it should not replace real validation. |
| Semantic failure | A failure where the system returns a technically valid response that is wrong, incomplete, hallucinated, or unusable for the task. It is common in AI workflows because HTTP success and valid JSON do not prove correctness. |
| Semantic plausibility | Whether an output seems reasonable for the task, not only whether it has the right format. It helps catch strange or impossible values. |
| Semantic search | Search by meaning instead of exact words. It usually compares embeddings to find content that is conceptually similar. |
| Session | A grouped user thread, chat, task, or related agent run. In observability, a session helps connect multiple traces that belong to the same ongoing work. |
| Session documents | Attachments and files created during the current session. They can be shared with agents working in that session, but should not automatically become global knowledge. |
| Session handoff | Reusing a value returned in an earlier step, such as a message ID or attachment ID, during a later step in the same scenario. Tests should verify that the real value was preserved instead of invented. |
| Session isolation | Running separate agent tasks in separate context windows while sharing only selected files or artifacts. This keeps each session focused and makes handoffs clearer. |
| Session summary injection | Adding a short summary of the session into the current context. This helps the model remember important facts without replaying everything. |
| Shared context | External information that more than one agent, session, tool, service, or human can use during work. It needs ownership, permission, and conflict rules when it can be changed. |
| Shared foundation tools | Basic tools exposed to many agents because they support collaboration, such as messaging, file reading, file searching, or file writing. They reduce handoff overhead but still need permission boundaries. |
| Shared knowledge | Information explicitly approved for use across several accounts, projects, tenants, or other isolated domains. It must be separated from private knowledge that belongs to only one domain. |
| Shared knowledge base | A shared folder or document set where multiple agents write and read intermediate knowledge for a larger workflow. It acts as the continuity layer between sessions. |
| Shared state | Memory, workspace files, queues, databases, or other external state that multiple agents can read or write. It should be treated as governed infrastructure, not as casual background text. |
| Signal convergence | The combination of several independent facts that together justify an agent action. It reduces the chance of acting on one weak or stale signal. |
| Silent degradation | A failure mode where a workflow keeps running but quietly produces worse, shorter, incomplete, slower, or less reliable results. It is dangerous because normal logs may still look successful. |
| Similar document | A document that looks close to the query by keywords or embeddings. Similar does not always mean useful for the user's real question. |
| Site instruction | Curated operating knowledge for one website, such as route patterns, selectors, navigation steps, and failure checks. It should remain separate from unreviewed lessons discovered during a run. |
| Source document | The original document that chunks or search entries come from. Keeping the source link helps verify and cite answers. |
| Source of truth | The place where the real, current data lives. Indexes, graphs, and summaries are copies or derived views, so they may become outdated. |
| Span | A timed observation for one internal operation, such as retrieval, context assembly, or tool execution. Spans help explain where time is spent inside a trace. |
| Spec-driven MCP build | Model Context Protocol build guided by a specification instead of improvised code. The spec describes tools, schemas, behavior, and review steps before implementation. |
| Specialist agent | A focused agent with narrow tools and a bounded responsibility, such as scanning mail, checking a calendar, or gathering task status. It should return structured facts rather than only prose. |
| Specialized tool | A narrow tool that delegates one bounded task to a model, API, or service with a capability different from the orchestrating model. Its input, output, validation, cost, and failure behavior should be explicit. |
| SQLite | A small database that runs inside an application or local file. It is often used for lightweight local storage and search. |
| Staged execution | Splitting work into phases that may run at different times and use newly refreshed context. It prevents an old environment snapshot from being treated as current later. |
| Stale snapshot | A copy of state that was correct when read but became outdated before the system tried to write or act on it. It can cause incorrect updates unless the system rechecks the current version. |
| Start frame | An image used as the first frame or starting point of generated video. It helps guide how the video begins. |
| State delivery decision | The choice of how to give state to the model or system. State can live in the prompt, a file, a summary, a database, or a tool. |
| State layers | The different places state can live, such as prompts, messages, files, databases, runtime metadata, and tool results. Separating them makes ownership clearer. |
| Stateful scenario | An ordered eval where several user messages, model decisions, and tool results share one session. It checks whether later steps use earlier state correctly. |
| STDIO | Standard Input/Output. A local way for a process to communicate through its input and output streams. |
| STDIO installation friction | Standard Input/Output installation friction. The setup difficulty of installing and configuring a local STDIO MCP server. |
| Streamable HTTP | A network transport that lets MCP work over HTTP. It is useful for remote or multi-user MCP systems. |
| Streamable HTTP deployment | Running a remote MCP server over HTTP. This requires network routing and usually stronger security decisions than local STDIO. |
| Strong model | A more capable model chosen for harder reasoning, ambiguity, or complex instructions. It may cost more or respond more slowly. |
| Structural guarantee | A guarantee that output has the expected format, such as valid JSON. It does not guarantee that the values inside are correct. |
| Structured output | Model output forced into a defined format or schema. It helps code read the output, but the values still need checking. |
| STT | Speech-to-text. Converting spoken audio into written text. |
| Style guide | A reusable guide for visual or document style. It helps keep generated images, pages, or documents consistent. |
| Sub-scope | A narrower access area inside one domain, such as a customer, case, role, label, or recipient group. It removes information that is valid for the domain but unnecessary for the current operation. |
| Summary artifact | A compact structured result produced from a larger dataset, such as aggregated JSON, CSV, or a validation table. It lets the model interpret results without receiving every raw record. |
| Swarm topology | A distributed multi-agent pattern where several agents explore, react, or produce candidates that are later selected or aggregated. It is risky for user-visible decisions unless observability and rejection rules are strong. |
| Synchronization layer | Code that keeps a search index up to date with the original data. Without it, search results may be stale. |
| Synthesis bottleneck | The final or near-final model call that receives many inputs and turns them into one output. It is risky because compressed context, missing evidence, or too much information can distort the result. |
| Synthetic dataset | A dataset generated or expanded by AI and then reviewed. It is a useful starting point for evals, but it still needs checks for realism, coverage, diversity, and balance. |
| Task context | A small package of information for one task or workflow step. It should include what the model needs now, not everything available. |
| Task contract | A machine-readable description of one unit of work, including its identity, dependencies, state, required capabilities, inputs, limits, and expected outputs. It lets orchestration code decide when and how the task may run. |
| Task decomposition | Breaking a complex task into smaller steps. This makes each step easier to implement, test, and validate. |
| Task list | A short progress list for multi-step work. It helps the system remember what is done and what is still pending. |
| Task-bounded tool | A tool whose actions, data access, and defaults are narrower than the source API because the agent has a limited responsibility. Narrowing the tool reduces ambiguity and unnecessary risk. |
| Template instruction files | Files that explain how to use a selected MCP template. They guide the implementation so it matches the template's intended structure. |
| Thundering herd | A failure pattern where many workers retry at the same time and overload the service they are trying to reach. Backoff and jitter help spread those retries out. |
| Timezone | A named time rule such as `Europe/Warsaw` that tells software how wall-clock time maps to UTC. Scheduled jobs should declare it explicitly so people do not have to guess what `09:00` means. |
| Token burn | Wasted token usage from too much context, repeated calls, long outputs, or loops. Token burn increases cost and latency. |
| Tool assignment | Deciding which tools, actions, integrations, or tool families each agent can access. Good assignment balances usefulness, context size, permissions, and data movement risk. |
| Tool connection risk | Risk created when an agent can move data between systems through a combination of tools. Even safe-looking tools can become risky when connected. |
| Tool consolidation | Replacing many tiny tools with a smaller number of clearer tools. This can make tool choice easier for the model. |
| Tool contract test | A stateless eval of one tool-selection or tool-call behavior without relying on earlier conversation steps. It checks the selected tool, arguments, result handling, and allowed recovery. |
| Tool family | A group of related tools that share similar names, inputs, and response style. This helps the model understand how to use them. |
| Tool grouping | Grouping related API actions into a clean tool design. It helps turn raw API operations into tools that are easier for a model to use. |
| Tool interface | The contract of a tool: name, inputs, outputs, limits, errors, and expected behavior. A clear interface helps the model call the tool correctly. |
| Tool locks | Temporary limits on which tools the model may use. They help keep the model focused and reduce accidental tool calls. |
| Tool namespace conflict | A naming conflict where different tools have similar or generic names. This can make the model choose the wrong tool. |
| Tool-use eval | An eval that checks how well an agent chooses, calls, and interprets tools. It can measure correct tool choice, forbidden tool avoidance, call count, arguments, latency, and cost. |
| Top-k context | The best `k` retrieved chunks selected for the model. These chunks should be chosen for usefulness, not only for search score. |
| Trace | A grouped record of one top-level user interaction or agent task. It connects nested model calls, tool calls, spans, events, costs, and outputs so the behavior can be understood later. |
| Transformation | Converting input into another form, structure, or wording. For example, turning notes into JSON or rewriting text in a clearer style. |
| Transformation prompt | A prompt that asks the model to convert input into another format, structure, or wording. It should define what must change and what must stay true. |
| Translated mapping | A provider adapter mapping that must rename fields, reshape messages, adjust settings, or convert streaming events because the provider API differs from the internal format. It should be explicit and tested. |
| Transient failure | A temporary failure that may succeed if tried again later, such as a timeout, network issue, overload, or rate limit. It is the main kind of failure that retry policies are meant to handle. |
| Tree topology | A multi-agent hierarchy where manager or lead roles sit between the root coordinator and worker agents. It is useful only when the extra layer reduces coordination load, enforces boundaries, or verifies work. |
| Trusted action | An action the user has allowed to run without repeated confirmation under known conditions. If the tool changes, that trust should be reviewed. |
| TTS | Text-to-speech. Converting written text into spoken audio. |
| Typed endpoint | An API endpoint with a clear business purpose and defined input and output shape. It is safer than a generic model passthrough because the application can validate the request before calling AI. |
| UI | User Interface. The part of the application the user sees and interacts with. |
| Unknown unknown | Missing information that the agent has no signal to search for. It is risky because the current context can look complete even when important related context exists elsewhere. |
| URL | Uniform Resource Locator. A web address or resource location, such as `https://example.com/page`. |
| UX | User Experience. How the product feels to use, including speed, clarity, feedback, and control. |
| Validated discovery | A site-specific lesson supported by evidence and a successful recovery or repeated observation. It remains a reviewable candidate until it is safely promoted into trusted instructions or deterministic automation. |
| Validation layer | Code that checks model output before the system uses it. It helps catch missing fields, wrong types, invalid values, or unsafe results. |
| Validation strength | How well the system can detect bad model output. Strong validation makes it safer to use model results in code or tools. |
| Value guarantee | A guarantee that the actual value is correct, not only that it has the right format. For example, a date can be valid JSON but still be the wrong date. |
| Vector store | A database or index for embeddings. It lets the system search by comparing vectors for similarity. |
| Video analysis | Asking a model or tool to inspect a video. The analysis may use frames, audio, timing, or transcript-like information. |
| Video generation | Creating a video clip with a model. The input may include text, images, a start frame, or an end frame. |
| Violation detection | Detecting unsafe, out-of-scope, abusive, policy-breaking, or product-breaking behavior in inputs or outputs. Detection can inform evals, but runtime blocking or routing needs guardrails or application logic. |
| Vision input | An image or visual file given to a model for analysis. The model or tool must actually support visual understanding. |
| VPS | Virtual Private Server. A rented server where you can run applications and manage deployment details yourself. |
| Waiting state | A non-final task state used when work cannot continue until information, permission, an artifact, or a human decision becomes available. It prevents blocked work from being mistaken for failure or completion. |
| Webhook | An event sent to an application by an external service when something changes. The receiving system should authenticate, validate, and route it before placing its data in agent context. |
| Workflow | A planned sequence of steps. In contrast to an agent loop, the order is usually known before the task starts. |
| Workflow state | The saved information about what a workflow is doing now. It can include the goal, plan, tool choices, intermediate results, and errors. |
| Workflow-level cost | The total cost of completing a workflow, including model calls, retries, validation, recovery, and paid tools or services. It is more useful for model selection than token price alone. |
| Wrapper requirement | A need to put a simpler layer around a complex API. The wrapper hides confusing details and gives the model a safer tool to call. |
| XLSX | Office Open XML Spreadsheet. A Microsoft Excel-style spreadsheet file that may need parsing before search or model use. |
