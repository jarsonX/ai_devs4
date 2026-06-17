# This module normalizes Polish product text and numeric-unit tokens.

from __future__ import annotations

import re
import unicodedata


UNIT_ALIASES = {
    "metr": "m",
    "metra": "m",
    "metrow": "m",
    "metrów": "m",
    "m": "m",
    "v": "v",
    "volt": "v",
    "volty": "v",
    "w": "w",
    "wat": "w",
    "watt": "w",
    "waty": "w",
    "ah": "ah",
    "mah": "mah",
    "ohm": "ohm",
    "om": "ohm",
    "omy": "ohm",
    "kohm": "kohm",
    "uf": "uf",
    "nf": "nf",
    "pf": "pf",
    "mm": "mm",
    "mhz": "mhz",
    "ghz": "ghz",
}

WORD_ALIASES = {
    "kabla": "kabel",
    "kable": "kabel",
    "kabel": "kabel",
    "przewodu": "przewod",
    "przewod": "przewod",
    "przewód": "przewod",
    "baterii": "akumulator",
    "bateria": "akumulator",
    "battery": "akumulator",
    "akumulatora": "akumulator",
    "akumulator": "akumulator",
    "inwertera": "inwerter",
    "inverter": "inwerter",
    "falownik": "inwerter",
    "turbiny": "turbina",
    "turbina": "turbina",
    "wiatrowej": "wiatrowa",
    "rezystora": "rezystor",
    "kondensatora": "kondensator",
    "diody": "dioda",
}

STOP_WORDS = {
    "potrzebuje",
    "potrzebuję",
    "potrzebny",
    "potrzebna",
    "potrzebne",
    "chce",
    "chcę",
    "kupic",
    "kupić",
    "szukam",
    "oraz",
    "plus",
    "i",
    "a",
    "z",
    "o",
    "do",
    "dla",
    "dlugosci",
    "długości",
    "mocy",
    "napiecia",
    "napięcia",
    "pojemnosci",
    "pojemności",
}

TOKEN_RE = re.compile(r"[a-z0-9./+-]+")
NUMBER_UNIT_RE = re.compile(
    r"\b(?P<number>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-ząćęłńóśźż]+)\b",
    re.IGNORECASE,
)


# Remove Polish accents so matching can work on mixed ASCII and Unicode text.
def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


# Normalize unit spelling after a numeric value.
def normalize_number_unit_match(match: re.Match[str]) -> str:
    number = match.group("number").replace(",", ".")
    unit = strip_accents(match.group("unit").lower())
    normalized_unit = UNIT_ALIASES.get(unit, unit)
    return f"{number}{normalized_unit}"


# Normalize free-form product text into a compact searchable string.
def normalize_text(value: str) -> str:
    text = strip_accents(value).lower()
    text = NUMBER_UNIT_RE.sub(normalize_number_unit_match, text)
    text = text.replace("/", " ")
    text = re.sub(r"[^a-z0-9.+%-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Return normalized lexical tokens with aliases and stop words handled.
def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    tokens: list[str] = []
    for token in TOKEN_RE.findall(normalized):
        alias = WORD_ALIASES.get(token, token)
        if alias and alias not in STOP_WORDS:
            tokens.append(alias)
    return tokens


# Extract critical numeric/unit tokens such as 48v, 3000w, and 10m.
def extract_numeric_tokens(value: str) -> set[str]:
    normalized = normalize_text(value)
    return {
        match.group(0)
        for match in re.finditer(r"\b\d+(?:\.\d+)?(?:v|w|ah|mah|ohm|kohm|uf|nf|pf|mm|m|mhz|ghz)\b", normalized)
    }


# Normalize a short term list while preserving deterministic ordering.
def normalize_terms(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for value in values:
        for token in tokenize(value):
            if token not in seen:
                seen.add(token)
                terms.append(token)
    return terms
