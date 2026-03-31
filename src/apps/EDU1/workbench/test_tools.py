from __future__ import annotations

from pprint import pprint

from ..config import get_config
from ..tools import Edu1Toolbox


def main() -> None:
    toolbox = Edu1Toolbox(get_config())

    raw = toolbox.load_people_data()
    raw_data = raw["rawData"].copy()
    payload_sent = dict(raw_data.get("payload_sent", {}))
    if "apikey" in payload_sent:
        payload_sent["apikey"] = "***REDACTED***"
    raw_data["payload_sent"] = payload_sent

    print("load_people_data:")
    pprint({"rawData": raw_data})
    print()

    people = toolbox.extract_people_payload(raw["rawData"])
    print("extract_people_payload:")
    pprint(people)
    print()

    cities = toolbox.extract_unique_cities(people["people"])
    print("extract_unique_cities:")
    pprint(cities)
    print()

    valid = toolbox.validate_selected_city("Katowice", cities["cities"])
    print("validate_selected_city:")
    pprint(valid)
    print()

    person = toolbox.find_person_by_city(people["people"], valid["selectedCity"])
    print("find_person_by_city:")
    pprint(person)
    print()

    access = toolbox.get_access_level(
        person["selectedPerson"]["name"],
        person["selectedPerson"]["surname"],
        person["selectedPerson"]["birthYear"],
    )
    print("get_access_level:")
    pprint(access)
    print()

    result = toolbox.build_final_result(
        person["selectedPerson"],
        valid["selectedCity"],
        access["accessLevel"],
    )
    print("build_final_result:")
    pprint(result)
    print()


if __name__ == "__main__":
    main()
