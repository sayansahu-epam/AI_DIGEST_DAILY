"""
Pre-filter for content items.
Fast keyword-based filtering before expensive LLM evaluation.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Persona(Enum):
    """Content filtering personas."""
    GENAI_NEWS = "genai_news"
    PRODUCT_IDEAS = "product_ideas"


@dataclass
class PrefilterResult:
    """Result of pre-filtering."""
    passed: int
    rejected: int
    
    @property
    def total(self) -> int:
        return self.passed + self.rejected


# ---------------------------------------------------------------------------
# Keyword Definitions
# ---------------------------------------------------------------------------


GENAI_NEWS_INCLUDE = [
    # Core AI terms
    r"\bai\b", r"\bllm\b", r"\bgpt\b", r"\bllama\b", r"\bmistral\b",
    r"\bclaude\b", r"\bgemini\b", r"\bopenai\b", r"\banthropic\b",
    
    # Technical terms
    r"machine\s*learning", r"deep\s*learning", r"neural\s*network",
    r"transformer", r"embedding", r"vector\s*database", r"rag\b",
    r"fine\s*tun", r"training", r"inference", r"token",
    
    # Tools & frameworks
    r"langchain", r"ollama", r"hugging\s*face", r"pytorch", r"tensorflow",
    r"cuda", r"gpu", r"nvidia",
    
    # Concepts
    r"agent", r"chatbot", r"generative", r"diffusion", r"stable\s*diffusion",
    r"midjourney", r"prompt", r"context\s*window", r"multimodal",
    
    # Actions
    r"open\s*source", r"released", r"launched", r"benchmark",
]


GENAI_NEWS_EXCLUDE = [
    # Sports
    r"football", r"soccer", r"cricket", r"basketball", r"tennis",
    r"championship", r"league", r"match\s*result", r"score",
    
    # Entertainment
    r"celebrity", r"kardashian", r"movie\s*review", r"box\s*office",
    r"album\s*release", r"concert", r"grammy", r"oscar",
    
    # Politics (general)
    r"election", r"parliament", r"senate", r"congressman",
    
    # Lifestyle
    r"recipe", r"horoscope", r"fashion\s*week", r"weight\s*loss",
]


PRODUCT_IDEAS_INCLUDE = [
    # Launch signals
    r"launched", r"launching", r"shipped", r"shipping", r"released",
    r"built", r"building", r"created", r"introducing",
    
    # Product terms
    r"mvp", r"startup", r"saas", r"product", r"app\b", r"tool",
    r"platform", r"service", r"solution",
    
    # Indie/side project
    r"side\s*project", r"indie", r"solo\s*founder", r"bootstrapped",
    r"maker", r"hacker",
    
    # Traction signals
    r"users", r"customers", r"revenue", r"mrr", r"arr",
    r"paying", r"subscribers", r"growth",
    
    # Problem/solution
    r"problem", r"solution", r"solves", r"helps", r"automates",
]


PRODUCT_IDEAS_EXCLUDE = [
    # Job posts
    r"hiring", r"job\s*opening", r"we.re\s*hiring", r"join\s*our\s*team",
    
    # Generic news
    r"sports", r"weather", r"horoscope",
]


# ---------------------------------------------------------------------------
# Pre-filter Functions
# ---------------------------------------------------------------------------


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the regex patterns."""
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def prefilter_item(
    title: str,
    content: str,
    persona: Persona
) -> bool:
    """
    Check if an item passes the pre-filter for a given persona.
    
    Returns True if item should be sent to LLM, False if rejected.
    """
    # Combine title and content for matching
    text = f"{title} {content}".strip()
    
    if not text:
        return False
    
    # Select keyword lists based on persona
    if persona == Persona.GENAI_NEWS:
        include_patterns = GENAI_NEWS_INCLUDE
        exclude_patterns = GENAI_NEWS_EXCLUDE
    elif persona == Persona.PRODUCT_IDEAS:
        include_patterns = PRODUCT_IDEAS_INCLUDE
        exclude_patterns = PRODUCT_IDEAS_EXCLUDE
    else:
        # Unknown persona, pass through
        return True
    
    # First check exclusions (if matches, reject immediately)
    if _matches_any(text, exclude_patterns):
        logger.debug("Excluded by keyword: %s", title[:50])
        return False
    
    # Then check inclusions (must match at least one)
    if _matches_any(text, include_patterns):
        logger.debug("Included by keyword: %s", title[:50])
        return True
    
    # No match either way - reject (be conservative)
    logger.debug("No keyword match, rejecting: %s", title[:50])
    return False


def prefilter_items(
    items: list[dict],
    persona: Persona
) -> tuple[list[dict], PrefilterResult]:
    """
    Pre-filter a list of items for a given persona.
    
    Args:
        items: List of item dicts (must have 'title' and 'content' keys)
        persona: Which persona to filter for
    
    Returns:
        Tuple of (filtered_items, PrefilterResult)
    """
    passed = []
    rejected_count = 0
    
    for item in items:
        title = item.get("title", "")
        content = item.get("content", "")
        
        if prefilter_item(title, content, persona):
            passed.append(item)
        else:
            rejected_count += 1
    
    result = PrefilterResult(passed=len(passed), rejected=rejected_count)
    
    logger.info(
        "Pre-filter [%s]: passed=%d rejected=%d",
        persona.value, result.passed, result.rejected
    )
    
    return passed, result


# ---------------------------------------------------------------------------
# Quick Test (run this file directly to test)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Pre-filter")
    print("=" * 60)
    
    # Test items
    test_items = [
        {
            "title": "New GPT-5 Model Released by OpenAI",
            "content": "OpenAI announces breakthrough in AI capabilities"
        },
        {
            "title": "Football Match Results: Manchester United vs Liverpool",
            "content": "Exciting game ends in 2-1 victory"
        },
        {
            "title": "I built a SaaS in 2 weeks and got 100 paying users",
            "content": "Here's how I launched my MVP and found customers"
        },
        {
            "title": "Best Recipe for Chocolate Cake",
            "content": "Delicious homemade cake recipe"
        },
        {
            "title": "LangChain vs LlamaIndex: Which to Choose?",
            "content": "Comparing two popular LLM frameworks"
        },
        {
            "title": "We're hiring senior engineers",
            "content": "Join our team in San Francisco"
        },
    ]
    
    print("\n📰 Test Items:")
    for i, item in enumerate(test_items):
        print(f"   {i+1}. {item['title']}")
    
    # Test GENAI_NEWS filter
    print("\n" + "-" * 60)
    print("🔬 GENAI_NEWS Pre-filter:")
    print("-" * 60)
    
    passed_genai, result_genai = prefilter_items(test_items, Persona.GENAI_NEWS)
    
    print(f"\n   Passed: {result_genai.passed}")
    print(f"   Rejected: {result_genai.rejected}")
    print(f"\n   ✅ Passed items:")
    for item in passed_genai:
        print(f"      - {item['title']}")
    
    # Test PRODUCT_IDEAS filter
    print("\n" + "-" * 60)
    print("💡 PRODUCT_IDEAS Pre-filter:")
    print("-" * 60)
    
    passed_product, result_product = prefilter_items(test_items, Persona.PRODUCT_IDEAS)
    
    print(f"\n   Passed: {result_product.passed}")
    print(f"   Rejected: {result_product.rejected}")
    print(f"\n   ✅ Passed items:")
    for item in passed_product:
        print(f"      - {item['title']}")
    
    print("\n" + "=" * 60)
    print("  ✅ Pre-filter tests complete!")
    print("=" * 60)