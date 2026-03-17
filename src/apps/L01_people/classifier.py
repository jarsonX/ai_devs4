from __future__ import annotations

import json

from openai import OpenAI

from .config import AppConfig
from .models import PersonRecord, JobClassificationResult, JobClassificationResponse
from .prompts import ALLOWED_TAGS, build_job_classification_prompt

def build_job_classification_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                        },
                        "tags": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ALLOWED_TAGS,
                            },
                        },
                    },
                    "required": ["index", "tags"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def classify_jobs(config: AppConfig, people: list[PersonRecord]) -> JobClassificationResponse:
    if not people:
        return JobClassificationResponse(results=[])  # No people = do not send the request

    client = OpenAI(api_key=config.openai_api_key)
    prompt = build_job_classification_prompt(people)
    schema = build_job_classification_schema()

    response = client.responses.create(
        model=config.openai_model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "job_classification_response",
                "schema": schema,
                "strict": True,
            }
        },
    )

    raw_json = response.output_text
    data = json.loads(raw_json)

    results = [
        JobClassificationResult(
            index=item["index"],
            tags=item["tags"],
        )
        for item in data["results"]
    ]

    return JobClassificationResponse(results=results)