"""The reviewed skill catalogue and per-agent registries."""

from typing import Final

SKILL_NAMES: Final[tuple[str, ...]] = (
    "product-marketing",
    "content-strategy",
    "competitor-profiling",
    "competitors",
    "marketing-ideas",
    "influencer-marketing",
    "pricing",
    "copywriting",
    "social",
    "emails",
    "ad-creative",
    "copy-editing",
)

STRATEGY_SKILL_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "product-marketing",
        "content-strategy",
        "competitor-profiling",
        "competitors",
        "marketing-ideas",
        "influencer-marketing",
        "pricing",
        "social",
    }
)

EXECUTION_SKILL_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "product-marketing",
        "competitors",
        "influencer-marketing",
        "copywriting",
        "social",
        "emails",
        "ad-creative",
        "copy-editing",
    }
)
