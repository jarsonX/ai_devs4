from __future__ import annotations

import requests

from .classifier import classify_jobs
from .config import get_config, AppConfig
from .data_loader import download_people_csv, load_people
from .filters import filter_people_for_transport_check
from .models import PersonRecord, JobClassificationResponse


def select_transport_people(
    filtered_people: list[PersonRecord],
    classification_response: JobClassificationResponse,
) -> list[tuple[PersonRecord, list[str]]]:
    transport_people: list[tuple[PersonRecord, list[str]]] = []

    for result in classification_response.results:
        if "transport" not in result.tags:
            continue

        person = filtered_people[result.index - 1]
        transport_people.append((person, result.tags))

    return transport_people


def build_answer_payload(
    config: AppConfig,
    transport_people: list[tuple[PersonRecord, list[str]]],
) -> dict:
    answer = []

    for person, tags in transport_people:
        birth_year = int(person.birth_date[:4])

        answer.append(
            {
                "name": person.name,
                "surname": person.surname,
                "gender": person.gender,
                "born": birth_year,
                "city": person.birth_place,
                "tags": tags,
            }
        )

    payload = {
        "apikey": config.ai_devs_api_key,
        "task": config.task_name,
        "answer": answer,
    }

    return payload


def send_answer(config: AppConfig, payload: dict) -> dict:
    verify_url = f"{config.hub_base_url}/verify"

    response = requests.post(verify_url, json=payload, timeout=30)
    response.raise_for_status()

    return response.json()


def run_pipeline() -> None:
    config = get_config()

    csv_path = download_people_csv(config)
    people = load_people(csv_path)
    filtered_people = filter_people_for_transport_check(people)
    classification_response = classify_jobs(config, filtered_people)
    transport_people = select_transport_people(filtered_people, classification_response)

    print(f"CSV file downloaded: {csv_path}")
    print(f"Count of all records: {len(people)}")
    print(f"Count of records after filtering: {len(filtered_people)}")
    print(f"Count of transport-related people: {len(transport_people)}")

    if transport_people:
        print("\nExample transport-related person:")
        print(transport_people[0][0])
        print("Assigned tags:")
        print(transport_people[0][1])

    payload = build_answer_payload(config, transport_people)
    #print("\nPayload to send:")
    #print(payload)
    verification_result = send_answer(config, payload)

    print("\nVerification result:")
    print(verification_result)