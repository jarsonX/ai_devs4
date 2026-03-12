from __future__ import annotations

from .config import get_config
from .data_loader import download_people_csv, load_people
from .filters import filter_people_for_transport_check


def run_pipeline() -> None:
    config = get_config()

    csv_path = download_people_csv(config)
    people = load_people(csv_path)
    filtered_people = filter_people_for_transport_check(people)

    print(f"CSV file downloaded: {csv_path}")
    print(f"Count of records {len(people)}")
    print(f"Count of records after filtering: {len(filtered_people)}")


    if filtered_people:
        print("Example filtered record:")
        print(filtered_people[0])