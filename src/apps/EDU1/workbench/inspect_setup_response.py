from __future__ import annotations

from pprint import pprint

from ..agent import run_deterministic_setup
from ..config import get_config
from ..tools import Edu1Toolbox


def main() -> None:
    config = get_config()
    toolbox = Edu1Toolbox(config)
    state: dict[str, object] = {}

    run_deterministic_setup(toolbox, state)

    print("setup mode:")
    print("deterministic application code")
    print()

    print("prepared state keys:")
    pprint(sorted(state.keys()))
    print()

    print("people count:")
    print(len(state["people"]))
    print()

    print("cities:")
    pprint(state["cities"])
    print()

    print("first person:")
    pprint(state["people"][0])
    print()


if __name__ == "__main__":
    main()
