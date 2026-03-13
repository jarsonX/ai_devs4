from __future__ import annotations

from .classifier import classify_jobs
from .config import get_config
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
        print("Example transport-related person:")
        print(transport_people[0][0])
        print("Assigned tags:")
        print(transport_people[0][1])