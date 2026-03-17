from __future__ import annotations

from .models import PersonRecord


ALLOWED_TAGS = [
    "IT",
    "transport",
    "edukacja",
    "medycyna",
    "praca z ludźmi",
    "praca z pojazdami",
    "praca fizyczna",
]


TAG_DESCRIPTIONS = {
    "IT": "Work directly related to software, programming, computer systems, IT infrastructure, cybersecurity, data engineering, data analysis, or administering digital systems. Do not use this tag for general technical, scientific, industrial, electrical, mechanical, or research work unless the description clearly involves computing or information systems.",
    "transport": "Work directly related to transporting people or goods, logistics, freight, shipping, dispatching, route planning, fleet operations, warehouse flow, or coordination of movement of goods.",
    "edukacja": "Work directly related to teaching, training, tutoring, lecturing, pedagogy, or organized transfer of knowledge. Do not use this tag only because the role requires expertise or research.",
    "medycyna": "Work directly related to healthcare, diagnosis, treatment, patient care, medicine, clinical work, laboratory diagnostics, or public health.",
    "praca z ludźmi": "Work where direct interaction with people is a core part of the role, for example clients, patients, students, interviewees, citizens, or team members.",
    "praca z pojazdami": "Work directly involving driving, operating, repairing, servicing, inspecting, or maintaining vehicles.",
    "praca fizyczna": "Work mainly based on manual, physical, installation, construction, maintenance, field, or hands-on technical labor.",
}


def build_job_classification_prompt(people: list[PersonRecord]) -> str:
    lines: list[str] = []

    for index, person in enumerate(people, start=1):
        lines.append(f"{index}. {person.job}")

    jobs_block = "\n".join(lines)

    tag_description_lines = [
        f"- {tag}: {description}"
        for tag, description in TAG_DESCRIPTIONS.items()
    ]
    tag_descriptions_block = "\n".join(tag_description_lines)

    return f"""
You classify job descriptions into predefined tags.

Available tags:
{", ".join(ALLOWED_TAGS)}

Tag definitions:
{tag_descriptions_block}

Important classification rules:
- Classify each item independently.
- Assign only tags that are explicitly supported by the job description.
- Do not invent new tags.
- Preserve input numbering.
- Return exactly one result per input item.
- Use the IT tag only for roles clearly related to software, computers, digital systems, IT infrastructure, or data/engineering work in a computing context.
- Do not use the IT tag for scientific, engineering, electrical, installation, industrial, agricultural, or research roles unless computing is clearly part of the described duties.
- Use edukacja only when teaching, training, lecturing, tutoring, or pedagogy is clearly part of the work.
- Use transport only when the role clearly involves transport, logistics, shipping, dispatching, freight, warehouse flow, or coordination of movement of goods or people.
- Prefer fewer tags over too many tags.
- If a tag is uncertain and not clearly grounded in the description, leave it out.

Examples:
1. Develops web applications, fixes software bugs, maintains backend services.
1: IT

2. Installs electrical systems and maintains industrial control units on construction sites.
2: praca fizyczna

3. Plans delivery routes, coordinates freight movement, supervises warehouse flow.
3: transport

4. Teaches mathematics in secondary school and works daily with students.
4: edukacja, praca z ludźmi

5. Conducts scientific research on new materials and publishes results.
5: edukacja

Input job descriptions:
{jobs_block}

Return a JSON response that matches the provided schema exactly.
Do not add explanations or any text outside the JSON output.
""".strip()