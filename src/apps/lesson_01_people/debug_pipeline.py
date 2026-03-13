from __future__ import annotations

from .classifier import classify_jobs
from .config import get_config
from .data_loader import download_people_csv, load_people
from .filters import filter_people_for_transport_check


def build_debug_output(classification_result: str, filtered_people: list) -> str:
    lines = classification_result.splitlines()
    debug_lines: list[str] = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue

        number_part, _, tags_part = stripped_line.partition(":")
        if not tags_part:
            debug_lines.append(f"{stripped_line} [UNPARSED]")
            continue

        try:
            index = int(number_part.strip()) - 1
            person = filtered_people[index]
            debug_lines.append(
                f"{number_part.strip()} : {tags_part.strip()} : '{person.job}'"
            )
        except (ValueError, IndexError):
            debug_lines.append(f"{stripped_line} [MAPPING ERROR]")

    return "\n".join(debug_lines)


def run_debug_pipeline() -> None:
    config = get_config()

    csv_path = download_people_csv(config)
    people = load_people(csv_path)
    filtered_people = filter_people_for_transport_check(people)
    classification_result = classify_jobs(config, filtered_people)

    print(f"CSV file downloaded: {csv_path}")
    print(f"Count of all records: {len(people)}")
    print(f"Count of records after filtering: {len(filtered_people)}")

    if filtered_people:
        print("Example filtered record:")
        print(filtered_people[0])

    print("\nDebug model response:")
    print(build_debug_output(classification_result, filtered_people))


if __name__ == "__main__":
    run_debug_pipeline()