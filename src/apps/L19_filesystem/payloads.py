# Deterministic filesystem payload for the L19 exercise.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


ROOT_DIRECTORIES = ("/miasta", "/osoby", "/towary")
CITY_PATHS = {
    "Brudzewo": "/miasta/brudzewo",
    "Celbowo": "/miasta/celbowo",
    "Darzlubie": "/miasta/darzlubie",
    "Domatowo": "/miasta/domatowo",
    "Karlinkowo": "/miasta/karlinkowo",
    "Mechowo": "/miasta/mechowo",
    "Opalino": "/miasta/opalino",
    "Puck": "/miasta/puck",
}

CITY_DEMANDS: dict[str, dict[str, int]] = {
    "Brudzewo": {"ryz": 55, "woda": 140, "wiertarka": 5},
    "Celbowo": {"kurczak": 40, "woda": 125, "mlotek": 6},
    "Darzlubie": {"wolowina": 25, "woda": 130, "kilof": 7},
    "Domatowo": {"makaron": 60, "woda": 150, "lopata": 8},
    "Karlinkowo": {
        "makaron": 52,
        "wolowina": 22,
        "ziemniak": 95,
        "woda": 155,
        "kilof": 6,
    },
    "Mechowo": {
        "ziemniak": 100,
        "kapusta": 70,
        "marchew": 65,
        "woda": 165,
        "lopata": 9,
    },
    "Opalino": {"chleb": 45, "woda": 120, "mlotek": 6},
    "Puck": {"chleb": 50, "ryz": 45, "woda": 175, "wiertarka": 7},
}

TRADERS_BY_CITY = {
    "Brudzewo": "Rafal Kisiel",
    "Celbowo": "Oskar Radtke",
    "Darzlubie": "Marta Frantz",
    "Domatowo": "Natan Rams",
    "Karlinkowo": "Lena Konkel",
    "Mechowo": "Eliza Redmann",
    "Opalino": "Iga Kapecka",
    "Puck": "Damian Kroll",
}

SELLERS_BY_GOOD = {
    "chleb": ("Domatowo", "Celbowo", "Brudzewo"),
    "kapusta": ("Celbowo",),
    "kilof": ("Puck", "Mechowo", "Celbowo"),
    "kurczak": ("Darzlubie",),
    "lopata": ("Brudzewo", "Puck"),
    "makaron": ("Opalino",),
    "maka": ("Brudzewo", "Mechowo"),
    "marchew": ("Puck",),
    "mlotek": ("Karlinkowo", "Mechowo"),
    "ryz": ("Darzlubie", "Opalino", "Karlinkowo"),
    "wiertarka": ("Karlinkowo", "Domatowo"),
    "wolowina": ("Opalino",),
    "ziemniak": ("Domatowo", "Darzlubie"),
}


# Represent one virtual filesystem creation operation.
@dataclass(frozen=True)
class FilesystemOperation:
    action: str
    path: str
    content: str | None = None

    # Convert the operation into the Hub API shape.
    def to_api(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "path": self.path,
        }
        if self.content is not None:
            payload["content"] = self.content
        return payload


# Return one markdown link to a city file.
def city_link(city: str) -> str:
    return f"[{city}]({CITY_PATHS[city]})"


# Convert a person name into a stable ASCII file path.
def person_path(name: str) -> str:
    return "/osoby/" + name.lower().replace(" ", "_")


# Build the city file creation operations.
def build_city_files() -> list[FilesystemOperation]:
    operations: list[FilesystemOperation] = []
    for city in sorted(CITY_DEMANDS):
        content = json.dumps(CITY_DEMANDS[city], ensure_ascii=True, sort_keys=True)
        operations.append(FilesystemOperation("createFile", CITY_PATHS[city], content))
    return operations


# Build the person file creation operations.
def build_person_files() -> list[FilesystemOperation]:
    operations: list[FilesystemOperation] = []
    for city, person in sorted(TRADERS_BY_CITY.items()):
        content = f"{person}\n{city_link(city)}"
        operations.append(FilesystemOperation("createFile", person_path(person), content))
    return operations


# Build the goods file creation operations.
def build_goods_files() -> list[FilesystemOperation]:
    operations: list[FilesystemOperation] = []
    for good, cities in sorted(SELLERS_BY_GOOD.items()):
        content = "\n".join(f"- {city_link(city)}" for city in cities)
        operations.append(FilesystemOperation("createFile", f"/towary/{good}", content))
    return operations


# Build every filesystem operation needed before the final done call.
def build_filesystem_operations() -> list[FilesystemOperation]:
    operations = [
        FilesystemOperation("createDirectory", path)
        for path in ROOT_DIRECTORIES
    ]
    operations.extend(build_city_files())
    operations.extend(build_person_files())
    operations.extend(build_goods_files())
    validate_operations(operations)
    return operations


# Convert operations into the batch answer accepted by the Hub.
def build_batch_answer() -> list[dict[str, Any]]:
    return [operation.to_api() for operation in build_filesystem_operations()]


# Return a stable local summary for dry-run output.
def build_solution_summary() -> dict[str, Any]:
    return {
        "directories": list(ROOT_DIRECTORIES),
        "cities": CITY_DEMANDS,
        "traders_by_city": TRADERS_BY_CITY,
        "sellers_by_good": SELLERS_BY_GOOD,
        "operation_count": len(build_filesystem_operations()),
    }


# Verify local assumptions before the app writes anything remotely.
def validate_operations(operations: list[FilesystemOperation]) -> None:
    paths = [operation.path for operation in operations]
    if len(paths) != len(set(paths)):
        raise ValueError("Filesystem operations contain duplicate paths.")

    for operation in operations:
        validate_ascii(operation.path, label=f"path {operation.path}")
        if operation.content is not None:
            validate_ascii(operation.content, label=f"content for {operation.path}")

    for operation in operations:
        if operation.path.startswith("/miasta/") and operation.content is not None:
            parsed = json.loads(operation.content)
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError(f"{operation.path} must contain a non-empty JSON object.")
            if not all(isinstance(value, int) for value in parsed.values()):
                raise ValueError(f"{operation.path} contains non-integer demand values.")

    linked_city_paths = set(CITY_PATHS.values())
    for operation in operations:
        if operation.path.startswith("/osoby/") or operation.path.startswith("/towary/"):
            links = set(re.findall(r"\]\((/miasta/[^)]+)\)", operation.content or ""))
            if not links:
                raise ValueError(f"{operation.path} does not contain a city markdown link.")
            unknown = links - linked_city_paths
            if unknown:
                raise ValueError(f"{operation.path} links to unknown cities: {sorted(unknown)}")


# Raise when a file path or payload text would violate the exercise ASCII rule.
def validate_ascii(value: str, *, label: str) -> None:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} contains non-ASCII text.") from exc
