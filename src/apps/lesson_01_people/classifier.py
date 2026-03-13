from __future__ import annotations

from openai import OpenAI

from .config import AppConfig
from .models import PersonRecord
from .prompts import build_job_classification_prompt


def classify_jobs(config: AppConfig, people: list[PersonRecord]) -> str:
    if not people:
        return ""  # No people = do not send the request

    client = OpenAI(api_key=config.openai_api_key)
    prompt = build_job_classification_prompt(people)

    response = client.responses.create(
        model=config.openai_model,
        input=prompt,
    )

    return response.output_text