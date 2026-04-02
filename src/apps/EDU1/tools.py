from __future__ import annotations

from typing import Any

from .api_client import Edu1ApiClient
from .config import AppConfig
from .data_loader import (
    extract_people_payload,
    extract_unique_cities,
    load_people_data,
)
from .models import FinalResult, Person


# This mapping groups tools by the stage of the workflow in which they are expected
# to be used. It gives developers a quick mental model of the end-to-end process:
# first load and normalize data, then select a valid city and person, and finally
# enrich that selection with the external access level and build the final result.
TOOL_STAGE_GROUPS = {
    "setup": [
        "load_people_data",
        "extract_people_payload",
        "extract_unique_cities",
    ],
    "selection": [
        "validate_selected_city",
        "find_person_by_city",
    ],
    "finalize": [
        "get_access_level",
        "build_final_result",
    ],
}


# Convert a strongly typed Person object into a plain dictionary that matches the
# JSON-like structure expected by tools and API responses. This keeps the internal
# domain model separate from the lightweight transport format used when values are
# passed between tools.
def serialize_person(person: Person) -> dict[str, Any]:
    return {
        "name": person.name,
        "surname": person.surname,
        "birthYear": person.birth_year,
        "city": person.city,
    }


# Rebuild a Person domain object from a dictionary received from a tool call or an
# intermediate result. The explicit validation here is important for learning and
# debugging: it makes invalid inputs fail close to the source instead of allowing
# partially broken data to flow deeper into the pipeline.
def deserialize_person(data: dict[str, Any]) -> Person:
    name = data.get("name")
    surname = data.get("surname")
    birth_year = data.get("birthYear")
    city = data.get("city")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Person.name must be a non-empty string.")
    if not isinstance(surname, str) or not surname.strip():
        raise ValueError("Person.surname must be a non-empty string.")
    if not isinstance(birth_year, int):
        raise ValueError("Person.birthYear must be an integer.")
    if not isinstance(city, str) or not city.strip():
        raise ValueError("Person.city must be a non-empty string.")

    return Person(
        name=name.strip(),
        surname=surname.strip(),
        birth_year=birth_year,
        city=city.strip(),
    )


# Convert the final domain result into the JSON-like structure returned to the rest
# of the application. This function mirrors serialize_person and makes the final
# output format explicit in one place, which reduces duplication and makes future
# output changes easier to reason about.
def serialize_final_result(result: FinalResult) -> dict[str, Any]:
    return {
        "selectedCity": result.selected_city,
        "person": serialize_person(result.person),
        "accessLevel": result.access_level,
    }


# Build the tool schema definitions that can be exposed to the model. The returned
# list is not the implementation itself: it is the contract that describes which
# tools exist, what each tool is for, and what arguments it accepts. The optional
# filter allows the caller to expose only a selected subset of tools when needed.
def build_tool_definitions(allowed_names: list[str] | None = None) -> list[dict[str, Any]]:
    tool_definitions = [
        # This tool starts the workflow by loading the raw EDU1 dataset from disk.
        # It intentionally has no input parameters because the file location comes
        # from application configuration, not from the model.
        {
            "type": "function",
            "name": "load_people_data",
            "description": "Load the raw EDU1 people JSON file from disk.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        # This tool extracts the actual list of people from the raw JSON structure.
        # It hides file-format details from the rest of the workflow, so later tools
        # can operate on a clean, normalized collection of person records.
        {
            "type": "function",
            "name": "extract_people_payload",
            "description": "Extract payload_sent.answer and convert it into a clean people list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rawData": {
                        "type": "object",
                    }
                },
                "required": ["rawData"],
                "additionalProperties": False,
            },
        },
        # This tool derives the set of unique cities from the people list while
        # preserving stable order. Its main role is to give the model a controlled
        # list of valid city options instead of asking it to infer them on its own.
        {
            "type": "function",
            "name": "extract_unique_cities",
            "description": "Collect unique city names from the people list in stable order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "people": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "surname": {"type": "string"},
                                "birthYear": {"type": "integer"},
                                "city": {"type": "string"},
                            },
                            "required": ["name", "surname", "birthYear", "city"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["people"],
                "additionalProperties": False,
            },
        },
        # This tool checks whether the city chosen by the model really exists in
        # the available city list. It acts as a guardrail that turns a free-form
        # model choice into a validated decision before the workflow moves on.
        {
            "type": "function",
            "name": "validate_selected_city",
            "description": (
                "Validate that the city selected by the model exists in the provided city list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selectedCity": {"type": "string"},
                    "availableCities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                },
                "required": ["selectedCity", "availableCities"],
                "additionalProperties": False,
            },
        },
        # This tool resolves the validated city to exactly one person. The schema
        # reflects an important business rule in this exercise: the selected city
        # should identify one and only one person in the dataset.
        {
            "type": "function",
            "name": "find_person_by_city",
            "description": "Find exactly one person assigned to the selected city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "people": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "surname": {"type": "string"},
                                "birthYear": {"type": "integer"},
                                "city": {"type": "string"},
                            },
                            "required": ["name", "surname", "birthYear", "city"],
                            "additionalProperties": False,
                        },
                    },
                    "city": {"type": "string"},
                },
                "required": ["people", "city"],
                "additionalProperties": False,
            },
        },
        # This tool enriches the selected person with an external access level.
        # It only asks for the identity fields needed by the API, which keeps the
        # tool focused on a single responsibility instead of passing full records.
        {
            "type": "function",
            "name": "get_access_level",
            "description": "Fetch the access level for one selected person.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "surname": {"type": "string"},
                    "birthYear": {"type": "integer"},
                },
                "required": ["name", "surname", "birthYear"],
                "additionalProperties": False,
            },
        },
        # This tool produces the final business object expected by EDU1. It gathers
        # the validated city, the selected person, and the fetched access level into
        # one explicit result so that the workflow ends with a single clear payload.
        {
            "type": "function",
            "name": "build_final_result",
            "description": "Build the final business result object for EDU1.",
            "parameters": {
                "type": "object",
                "properties": {
                    "person": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "surname": {"type": "string"},
                            "birthYear": {"type": "integer"},
                            "city": {"type": "string"},
                        },
                        "required": ["name", "surname", "birthYear", "city"],
                        "additionalProperties": False,
                    },
                    "selectedCity": {"type": "string"},
                    "accessLevel": {"type": "integer"},
                },
                "required": ["person", "selectedCity", "accessLevel"],
                "additionalProperties": False,
            },
        },
    ]

    if allowed_names is None:
        return tool_definitions

    allowed_name_set = set(allowed_names)
    return [
        tool_definition
        for tool_definition in tool_definitions
        if tool_definition["name"] in allowed_name_set
    ]


# This class is the concrete toolbox used by the EDU1 agent. It connects three
# layers: local data loading, domain validation/selection logic, and the external
# API call for access level. In practice, it is the runtime implementation behind
# the tool schemas defined above.
class Edu1Toolbox:
    # Store the application configuration and prepare the API client once, so every
    # tool method can reuse the same dependencies instead of rebuilding them.
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.api_client = Edu1ApiClient(config)

    # Load the raw people file using the configured path and wrap it in a named
    # field. Returning a dictionary keeps the shape consistent with other tool
    # outputs, which makes orchestration simpler for the calling agent.
    def load_people_data(self) -> dict[str, Any]:
        raw_data = load_people_data(self.config.data_people_path)
        return {
            "rawData": raw_data,
        }

    # Transform the raw file content into a normalized list of serialized people.
    # This method bridges the lower-level data loader and the tool interface by
    # converting domain objects into plain dictionaries safe to pass between tools.
    def extract_people_payload(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        people = extract_people_payload(raw_data)
        return {
            "people": [serialize_person(person) for person in people],
        }

    # Turn the serialized tool input back into Person objects, then derive the list
    # of unique cities. The deserialize -> process -> serialize pattern is repeated
    # throughout this file and is worth noticing because it cleanly separates tool
    # transport data from the internal domain model.
    def extract_unique_cities(self, people_data: list[dict[str, Any]]) -> dict[str, Any]:
        people = [deserialize_person(item) for item in people_data]
        cities = extract_unique_cities(people)
        return {
            "cities": cities,
        }

    # Normalize and validate the city selected by the model against the known list
    # of available cities. Instead of raising an error for an invalid choice, this
    # method returns an explicit validity flag so the calling workflow can decide
    # how to recover or ask the model to try again.
    def validate_selected_city(
        self,
        selected_city: str,
        available_cities: list[str],
    ) -> dict[str, Any]:
        cleaned_city = selected_city.strip()

        if cleaned_city in available_cities:
            return {
                "isValid": True,
                "selectedCity": cleaned_city,
            }

        return {
            "isValid": False,
            "selectedCity": None,
        }

    # Find the single person assigned to the chosen city. The method raises errors
    # when the city matches zero or multiple people because both cases violate the
    # exercise assumption that city selection should resolve to one unambiguous
    # person before the workflow can continue.
    def find_person_by_city(
        self,
        people_data: list[dict[str, Any]],
        city: str,
    ) -> dict[str, Any]:
        people = [deserialize_person(item) for item in people_data]
        matches = [person for person in people if person.city == city]

        if not matches:
            raise ValueError(f"No person found for city: {city!r}")
        if len(matches) > 1:
            raise ValueError(f"More than one person found for city: {city!r}")

        return {
            "selectedPerson": serialize_person(matches[0]),
        }

    # Ask the external EDU1 API for the access level of the selected person. This
    # method intentionally stays thin: networking details are delegated to the API
    # client so the toolbox keeps its focus on tool orchestration.
    def get_access_level(self, name: str, surname: str, birth_year: int) -> dict[str, Any]:
        access_level = self.api_client.get_access_level(name, surname, birth_year)
        return {
            "accessLevel": access_level,
        }

    # Assemble the final result object from validated inputs. The method converts
    # the incoming dictionary back to a Person, creates the FinalResult domain
    # object, and only then serializes it. That extra step keeps the final output
    # grounded in the domain model instead of stitching dictionaries together.
    def build_final_result(
        self,
        person_data: dict[str, Any],
        selected_city: str,
        access_level: int,
    ) -> dict[str, Any]:
        person = deserialize_person(person_data)
        result = FinalResult(
            selected_city=selected_city.strip(),
            person=person,
            access_level=access_level,
        )
        return {
            "result": serialize_final_result(result),
        }

    # Dispatch a tool call by name, validate the incoming arguments, and forward
    # execution to the matching method. This function is the central gateway for
    # runtime tool execution, so its validation errors are deliberately explicit:
    # they teach both developers and the agent what input shape each tool expects.
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "load_people_data":
            return self.load_people_data()

        if tool_name == "extract_people_payload":
            raw_data = arguments.get("rawData")
            if not isinstance(raw_data, dict):
                raise ValueError("Tool extract_people_payload requires object 'rawData'.")

            return self.extract_people_payload(raw_data)

        if tool_name == "extract_unique_cities":
            people = arguments.get("people")
            if not isinstance(people, list):
                raise ValueError("Tool extract_unique_cities requires list 'people'.")

            return self.extract_unique_cities(people)

        if tool_name == "validate_selected_city":
            selected_city = arguments.get("selectedCity")
            available_cities = arguments.get("availableCities")
            if not isinstance(selected_city, str):
                raise ValueError("Tool validate_selected_city requires string 'selectedCity'.")
            if not isinstance(available_cities, list) or not all(
                isinstance(city, str) for city in available_cities
            ):
                raise ValueError(
                    "Tool validate_selected_city requires string list 'availableCities'."
                )

            return self.validate_selected_city(selected_city, available_cities)

        if tool_name == "find_person_by_city":
            people = arguments.get("people")
            city = arguments.get("city")
            if not isinstance(people, list):
                raise ValueError("Tool find_person_by_city requires list 'people'.")
            if not isinstance(city, str):
                raise ValueError("Tool find_person_by_city requires string 'city'.")

            return self.find_person_by_city(people, city)

        if tool_name == "get_access_level":
            name = arguments.get("name")
            surname = arguments.get("surname")
            birth_year = arguments.get("birthYear")
            if not isinstance(name, str) or not isinstance(surname, str):
                raise ValueError(
                    "Tool get_access_level requires string 'name' and 'surname'."
                )
            if not isinstance(birth_year, int):
                raise ValueError("Tool get_access_level requires integer 'birthYear'.")

            return self.get_access_level(name, surname, birth_year)

        if tool_name == "build_final_result":
            person = arguments.get("person")
            selected_city = arguments.get("selectedCity")
            access_level = arguments.get("accessLevel")
            if not isinstance(person, dict):
                raise ValueError("Tool build_final_result requires object 'person'.")
            if not isinstance(selected_city, str):
                raise ValueError("Tool build_final_result requires string 'selectedCity'.")
            if not isinstance(access_level, int):
                raise ValueError("Tool build_final_result requires integer 'accessLevel'.")

            return self.build_final_result(person, selected_city, access_level)

        raise ValueError(f"Unsupported tool: {tool_name}")
