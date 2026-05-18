# Prompt construction helpers for the L6 categorize workflow.

from __future__ import annotations

from src.apps.L6_categorize.models import GoodsItem


DEFAULT_PROMPT_TEMPLATE = (
    "Return DNG only for weapons or explicit explosive/poison/radioactive/flammable danger. "
    "Reactor/fuel/cassette/core/uranium => NEU. "
    "Otherwise NEU. Reply only DNG/NEU. "
    "Item: {id} {description}"
)


# Build one short classify prompt for a single goods item.
def build_item_prompt(
    item: GoodsItem,
    template: str = DEFAULT_PROMPT_TEMPLATE,
) -> str:
    return template.format(
        id=item.item_id,
        description=item.description,
    )
