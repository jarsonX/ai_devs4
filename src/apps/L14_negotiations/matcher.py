# This module deterministically ranks catalog items against interpreted needs.

from __future__ import annotations

from dataclasses import dataclass

from .catalog_loader import Catalog, Item
from .normalization import extract_numeric_tokens, normalize_terms, normalize_text, tokenize
from .query_interpreter import ProductNeed


MIN_ACCEPTED_SCORE = 45
MIN_RUNNER_UP_MARGIN = 12
CATEGORY_MATCH_POINTS = 35
REQUIRED_TERM_POINTS = 12
OPTIONAL_TERM_POINTS = 4
NUMERIC_TOKEN_POINTS = 24
MISSING_NUMERIC_PENALTY = 28
CONFLICT_NUMERIC_PENALTY = 35
MISSING_DETAILS_OVERRIDE_MIN_SCORE = 60
MISSING_DETAILS_OVERRIDE_MARGIN = 24


# Represent normalized item facts used for repeatable scoring.
@dataclass(frozen=True)
class ItemFeatures:
    item: Item
    normalized_name: str
    tokens: frozenset[str]
    numeric_tokens: frozenset[str]


# Represent one scored catalog candidate.
@dataclass(frozen=True)
class ScoredCandidate:
    item: Item
    score: int
    matched_terms: tuple[str, ...]
    matched_numeric_tokens: tuple[str, ...]
    penalties: tuple[str, ...]


# Represent the final deterministic match decision.
@dataclass(frozen=True)
class MatchResult:
    need: ProductNeed
    accepted: bool
    best: ScoredCandidate | None
    runner_up: ScoredCandidate | None
    reason: str


# Allow one underspecified need only when deterministic evidence is still strong.
def can_accept_missing_details(
    need: ProductNeed,
    best: ScoredCandidate | None,
    runner_up: ScoredCandidate | None,
) -> bool:
    if best is None or not need.missing_details:
        return False
    if best.penalties:
        return False
    if not best.matched_numeric_tokens:
        return False
    if best.score < MISSING_DETAILS_OVERRIDE_MIN_SCORE:
        return False
    if runner_up and best.score - runner_up.score < MISSING_DETAILS_OVERRIDE_MARGIN:
        return False
    return True


# Build reusable normalized features for one catalog item.
def build_item_features(item: Item) -> ItemFeatures:
    return ItemFeatures(
        item=item,
        normalized_name=normalize_text(item.name),
        tokens=frozenset(tokenize(item.name)),
        numeric_tokens=frozenset(extract_numeric_tokens(item.name)),
    )


# Convert one interpreted product need into deterministic search signals.
def build_need_terms(need: ProductNeed) -> tuple[set[str], set[str], set[str]]:
    category_terms = set(normalize_terms([need.normalized_product_type, *need.aliases]))
    required_terms = set(normalize_terms(need.required_terms))
    optional_terms = set(normalize_terms(need.optional_terms))
    for attribute in need.attributes:
        required_terms.update(normalize_terms([attribute.name]))
        if attribute.unit:
            required_terms.update(normalize_terms([attribute.unit]))
    return category_terms, required_terms, optional_terms


# Extract numeric/unit tokens from product attributes and raw text.
def build_need_numeric_tokens(need: ProductNeed) -> set[str]:
    numeric_tokens = set(extract_numeric_tokens(need.raw_request_fragment))
    for attribute in need.attributes:
        if attribute.unit:
            numeric_tokens.update(
                extract_numeric_tokens(f"{attribute.value}{attribute.unit}")
            )
        else:
            numeric_tokens.update(extract_numeric_tokens(attribute.value))
    return numeric_tokens


# Score one candidate using explicit positive signals and critical penalties.
def score_candidate(need: ProductNeed, features: ItemFeatures) -> ScoredCandidate:
    category_terms, required_terms, optional_terms = build_need_terms(need)
    need_numeric_tokens = build_need_numeric_tokens(need)
    score = 0
    matched_terms: list[str] = []
    matched_numeric_tokens: list[str] = []
    penalties: list[str] = []

    for term in sorted(category_terms):
        if term in features.tokens or term in features.normalized_name:
            score += CATEGORY_MATCH_POINTS
            matched_terms.append(term)

    for term in sorted(required_terms):
        if term in features.tokens or term in features.normalized_name:
            score += REQUIRED_TERM_POINTS
            matched_terms.append(term)

    for term in sorted(optional_terms):
        if term in features.tokens or term in features.normalized_name:
            score += OPTIONAL_TERM_POINTS
            matched_terms.append(term)

    for token in sorted(need_numeric_tokens):
        if token in features.numeric_tokens:
            score += NUMERIC_TOKEN_POINTS
            matched_numeric_tokens.append(token)
        else:
            score -= MISSING_NUMERIC_PENALTY
            penalties.append(f"missing:{token}")

    # Penalize same-unit conflicts such as 48v request against a 24v item.
    for need_token in sorted(need_numeric_tokens):
        need_unit = "".join(char for char in need_token if char.isalpha())
        if not need_unit or need_token in features.numeric_tokens:
            continue
        for item_token in features.numeric_tokens:
            item_unit = "".join(char for char in item_token if char.isalpha())
            if item_unit == need_unit:
                score -= CONFLICT_NUMERIC_PENALTY
                penalties.append(f"conflict:{need_token}!={item_token}")
                break

    return ScoredCandidate(
        item=features.item,
        score=score,
        matched_terms=tuple(dict.fromkeys(matched_terms)),
        matched_numeric_tokens=tuple(matched_numeric_tokens),
        penalties=tuple(penalties),
    )


# Rank all catalog items for one interpreted product need.
def rank_candidates(
    need: ProductNeed,
    catalog: Catalog,
    limit: int = 5,
) -> list[ScoredCandidate]:
    scored = [
        score_candidate(need, build_item_features(item))
        for item in catalog.items
    ]
    scored.sort(key=lambda candidate: candidate.score, reverse=True)
    return scored[:limit]


# Choose one candidate only when the winner is strong enough and clearly ahead.
def match_need(need: ProductNeed, catalog: Catalog) -> MatchResult:
    ranked = rank_candidates(need, catalog, limit=2)
    best = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None

    if best is None:
        return MatchResult(need, False, None, None, "no_candidates")
    if best.score < MIN_ACCEPTED_SCORE:
        return MatchResult(need, False, best, runner_up, "score_too_low")
    if runner_up and best.score - runner_up.score < MIN_RUNNER_UP_MARGIN:
        return MatchResult(need, False, best, runner_up, "ambiguous")
    if need.confidence == "low":
        return MatchResult(need, False, best, runner_up, "low_interpreter_confidence")
    if need.missing_details:
        if can_accept_missing_details(need, best, runner_up):
            return MatchResult(need, True, best, runner_up, "accepted")
        return MatchResult(need, False, best, runner_up, "missing_details")

    return MatchResult(need, True, best, runner_up, "accepted")


# Match every interpreted need and preserve order for response assembly later.
def match_needs(needs: list[ProductNeed], catalog: Catalog) -> list[MatchResult]:
    return [match_need(need, catalog) for need in needs]
