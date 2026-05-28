# Token budget helpers for keeping the Hub answer below the hard limit.

from __future__ import annotations

import math


# Estimate tokens conservatively when no tokenizer package is available.
def estimate_tokens(text: str) -> int:
    if not text:
        return 0

    # The exercise only needs a guard before submission. chars/3 is intentionally
    # stricter than the common chars/4 rule so borderline answers fail locally.
    return max(1, math.ceil(len(text) / 3))


# Raise a clear local error instead of submitting an oversized Hub answer.
def ensure_token_limit(text: str, token_limit: int) -> int:
    token_estimate = estimate_tokens(text)
    if token_estimate > token_limit:
        raise ValueError(
            f"Condensed logs are too large: {token_estimate} estimated tokens, "
            f"limit is {token_limit}."
        )

    return token_estimate
