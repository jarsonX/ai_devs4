# L4 Sendit Approach

We split `L4_sendit` into two MVPs so the learning path stays readable. MVP1 is a lesson in the basic pipeline; MVP2 adds AI only after the mechanics are visible.

| Version | Goal | Rationale |
|---|---|---|
| `L4_sendit_MVP1` | Build the declaration with explicit rules, fixed local files, deterministic calculations, local validation, and saved intermediate outputs. | This is not a production app. It teaches the data flow before adding model behavior. |
| `L4_sendit_MVP2` | Add AI for natural-language command parsing, relevant-source selection, multimodal extraction from images, and uncertainty reporting. | This shows where AI improves the workflow without hiding the basic mechanics. |

MVP1 should be built as four small learning stages:

| Stage | Purpose |
|---|---|
| Static MVP | Render the first declaration from known input and explicit facts. |
| Transparent Pipeline | Save intermediate artifacts so each step can be inspected. |
| Local Validation | Check the declaration before any Hub submission. |
| AI Boundary | Mark which manual or heuristic parts will later become MVP2 AI components. |

MVP2 should teach how to insert AI as a bounded, inspectable component rather than as unexplained magic.
