# """
# LLM-based content evaluator.
# Sends articles to Llama 3 for relevance scoring and classification.
# """

# import logging
# from dataclasses import dataclass
# from typing import Optional

# from src.services.llm import chat_json
# from src.tools.prefilter import Persona

# logger = logging.getLogger(__name__)


# # ---------------------------------------------------------------------------
# # Evaluation Results
# # ---------------------------------------------------------------------------


# @dataclass
# class GenAINewsEvaluation:
#     """Evaluation result for GENAI_NEWS persona."""
#     relevance_score: float
#     topic: str
#     why_it_matters: str
#     target_audience: str
#     decision: str  # INCLUDE or EXCLUDE
#     raw_response: dict


# @dataclass
# class ProductIdeasEvaluation:
#     """Evaluation result for PRODUCT_IDEAS persona."""
#     relevance_score: float
#     idea_type: str
#     problem_statement: str
#     solution_summary: str
#     reusability_score: float
#     decision: str  # INCLUDE or EXCLUDE
#     raw_response: dict


# # ---------------------------------------------------------------------------
# # Prompt Templates
# # ---------------------------------------------------------------------------


# GENAI_NEWS_PROMPT = """You are an AI/ML news curator for technical professionals.

# Evaluate this article for relevance to AI practitioners:

# TITLE: {title}

# CONTENT: {content}

# Respond with ONLY valid JSON (no other text):
# {{
#     "relevance_score": <float 0.0 to 1.0>,
#     "topic": "<category like 'LLM', 'Computer Vision', 'MLOps', etc>",
#     "why_it_matters": "<1-2 sentence explanation>",
#     "target_audience": "<who should read this>",
#     "decision": "<INCLUDE or EXCLUDE>"
# }}

# Scoring guide:
# - 0.9-1.0: Major breakthrough, new model release, critical update
# - 0.7-0.8: Useful tutorial, interesting research, tool announcement
# - 0.5-0.6: Tangentially related, general tech news with AI angle
# - 0.0-0.4: Not relevant to AI/ML practitioners

# Be strict. Only INCLUDE truly relevant AI/ML content."""


# PRODUCT_IDEAS_PROMPT = """You are a product analyst scanning for interesting startup/product ideas.

# Evaluate this content for product insights:

# TITLE: {title}

# CONTENT: {content}

# Respond with ONLY valid JSON (no other text):
# {{
#     "relevance_score": <float 0.0 to 1.0>,
#     "idea_type": "<SaaS, Tool, Marketplace, API, etc>",
#     "problem_statement": "<what problem does it solve>",
#     "solution_summary": "<how does it solve it>",
#     "reusability_score": <float 0.0 to 1.0 - can this idea be adapted>,
#     "decision": "<INCLUDE or EXCLUDE>"
# }}

# Scoring guide:
# - 0.9-1.0: Clear problem, validated solution, replicable idea
# - 0.7-0.8: Interesting concept, some traction signals
# - 0.5-0.6: Vague idea, unclear value proposition
# - 0.0-0.4: Not a product idea, just news/commentary

# Be selective. Only INCLUDE actionable product insights."""


# # ---------------------------------------------------------------------------
# # Evaluation Functions
# # ---------------------------------------------------------------------------


# def evaluate_genai_news(title: str, content: str) -> Optional[GenAINewsEvaluation]:
#     """
#     Evaluate an article for the GENAI_NEWS persona.
    
#     Returns GenAINewsEvaluation or None if evaluation fails.
#     """
#     prompt = GENAI_NEWS_PROMPT.format(
#         title=title[:500],  # Limit length
#         content=content[:2000]  # Limit length
#     )
    
#     response = chat_json(prompt, temperature=0.1)
    
#     if response is None:
#         logger.warning("LLM evaluation failed for: %s", title[:50])
#         return None
    
#     try:
#         return GenAINewsEvaluation(
#             relevance_score=float(response.get("relevance_score", 0.0)),
#             topic=str(response.get("topic", "Unknown")),
#             why_it_matters=str(response.get("why_it_matters", "")),
#             target_audience=str(response.get("target_audience", "")),
#             decision=str(response.get("decision", "EXCLUDE")).upper(),
#             raw_response=response
#         )
#     except (KeyError, ValueError, TypeError) as e:
#         logger.error("Failed to parse evaluation response: %s", e)
#         return None


# def evaluate_product_ideas(title: str, content: str) -> Optional[ProductIdeasEvaluation]:
#     """
#     Evaluate an article for the PRODUCT_IDEAS persona.
    
#     Returns ProductIdeasEvaluation or None if evaluation fails.
#     """
#     prompt = PRODUCT_IDEAS_PROMPT.format(
#         title=title[:500],
#         content=content[:2000]
#     )
    
#     response = chat_json(prompt, temperature=0.1)
    
#     if response is None:
#         logger.warning("LLM evaluation failed for: %s", title[:50])
#         return None
    
#     try:
#         return ProductIdeasEvaluation(
#             relevance_score=float(response.get("relevance_score", 0.0)),
#             idea_type=str(response.get("idea_type", "Unknown")),
#             problem_statement=str(response.get("problem_statement", "")),
#             solution_summary=str(response.get("solution_summary", "")),
#             reusability_score=float(response.get("reusability_score", 0.0)),
#             decision=str(response.get("decision", "EXCLUDE")).upper(),
#             raw_response=response
#         )
#     except (KeyError, ValueError, TypeError) as e:
#         logger.error("Failed to parse evaluation response: %s", e)
#         return None


# def evaluate_item(
#     title: str,
#     content: str,
#     persona: Persona
# ) -> Optional[GenAINewsEvaluation | ProductIdeasEvaluation]:
#     """
#     Evaluate an item for the given persona.
    
#     Dispatches to the appropriate evaluation function.
#     """
#     if persona == Persona.GENAI_NEWS:
#         return evaluate_genai_news(title, content)
#     elif persona == Persona.PRODUCT_IDEAS:
#         return evaluate_product_ideas(title, content)
#     else:
#         logger.error("Unknown persona: %s", persona)
#         return None


# # ---------------------------------------------------------------------------
# # Quick Test (run this file directly to test)
# # ---------------------------------------------------------------------------


# if __name__ == "__main__":
#     from src.services.llm import is_ollama_running
    
#     print("=" * 60)
#     print("  Testing Evaluator (LLM-based)")
#     print("=" * 60)
    
#     # Check Ollama first
#     print("\n🔍 Checking Ollama...")
#     if not is_ollama_running():
#         print("   ❌ Ollama is not running! Please start Ollama.")
#         exit(1)
#     print("   ✅ Ollama is running!")
    
#     # Test articles
#     test_articles = [
#         {
#             "title": "Meta Releases Llama 3.1 405B - Largest Open Source Model Ever",
#             "content": "Meta has released Llama 3.1 with 405 billion parameters, making it the largest open source language model. The model matches GPT-4 on most benchmarks and is available for commercial use."
#         },
#         {
#             "title": "I built a tool that converts Figma designs to React code",
#             "content": "After 3 months of work, I launched DesignToCode. It uses AI to analyze Figma files and generate clean React components. Already have 50 paying customers at $29/month."
#         },
#     ]
    
#     # Test GENAI_NEWS evaluation
#     print("\n" + "-" * 60)
#     print("🔬 Testing GENAI_NEWS Evaluation")
#     print("-" * 60)
    
#     article = test_articles[0]
#     print(f"\n📰 Article: {article['title']}")
#     print("   Evaluating with LLM (this may take a few seconds)...")
    
#     result = evaluate_genai_news(article["title"], article["content"])
    
#     if result:
#         print(f"\n   ✅ Evaluation Complete!")
#         print(f"   ┌─────────────────────────────────────────")
#         print(f"   │ Relevance Score:  {result.relevance_score}")
#         print(f"   │ Topic:            {result.topic}")
#         print(f"   │ Why It Matters:   {result.why_it_matters[:60]}...")
#         print(f"   │ Target Audience:  {result.target_audience}")
#         print(f"   │ Decision:         {result.decision}")
#         print(f"   └─────────────────────────────────────────")
#     else:
#         print("   ❌ Evaluation failed!")
    
#     # Test PRODUCT_IDEAS evaluation
#     print("\n" + "-" * 60)
#     print("💡 Testing PRODUCT_IDEAS Evaluation")
#     print("-" * 60)
    
#     article = test_articles[1]
#     print(f"\n📰 Article: {article['title']}")
#     print("   Evaluating with LLM (this may take a few seconds)...")
    
#     result = evaluate_product_ideas(article["title"], article["content"])
    
#     if result:
#         print(f"\n   ✅ Evaluation Complete!")
#         print(f"   ┌─────────────────────────────────────────")
#         print(f"   │ Relevance Score:  {result.relevance_score}")
#         print(f"   │ Idea Type:        {result.idea_type}")
#         print(f"   │ Problem:          {result.problem_statement[:50]}...")
#         print(f"   │ Solution:         {result.solution_summary[:50]}...")
#         print(f"   │ Reusability:      {result.reusability_score}")
#         print(f"   │ Decision:         {result.decision}")
#         print(f"   └─────────────────────────────────────────")
#     else:
#         print("   ❌ Evaluation failed!")
    
#     print("\n" + "=" * 60)
#     print("  ✅ Evaluator tests complete!")
#     print("=" * 60)


"""
LLM-based content evaluator.
Sends articles to Llama 3 for relevance scoring and classification.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.services.llm import chat_json, chat
from src.tools.prefilter import Persona

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evaluation Results
# ---------------------------------------------------------------------------


@dataclass
class GenAINewsEvaluation:
    """Evaluation result for GENAI_NEWS persona."""
    relevance_score: float
    topic: str
    why_it_matters: str
    target_audience: str
    decision: str
    raw_response: dict


@dataclass
class ProductIdeasEvaluation:
    """Evaluation result for PRODUCT_IDEAS persona."""
    relevance_score: float
    idea_type: str
    problem_statement: str
    solution_summary: str
    reusability_score: float
    decision: str
    raw_response: dict


# ---------------------------------------------------------------------------
# Prompt Templates (Simplified for better JSON compliance)
# ---------------------------------------------------------------------------


GENAI_NEWS_PROMPT = '''Evaluate this article for AI/ML relevance.

Title: {title}
Content: {content}

Reply with ONLY this JSON format, nothing else:
{{"relevance_score": 0.8, "topic": "AI", "why_it_matters": "reason here", "target_audience": "developers", "decision": "INCLUDE"}}

Rules:
- relevance_score: number between 0.0 and 1.0
- topic: short category name
- why_it_matters: one sentence
- target_audience: who should read this
- decision: either "INCLUDE" or "EXCLUDE"

JSON only, no other text:'''


PRODUCT_IDEAS_PROMPT = '''Evaluate this content for product/startup insights.

Title: {title}
Content: {content}

Reply with ONLY this JSON format, nothing else:
{{"relevance_score": 0.8, "idea_type": "SaaS", "problem_statement": "problem here", "solution_summary": "solution here", "reusability_score": 0.7, "decision": "INCLUDE"}}

Rules:
- relevance_score: number between 0.0 and 1.0
- idea_type: like "SaaS", "Tool", "API", etc
- problem_statement: what problem it solves
- solution_summary: how it solves it
- reusability_score: number between 0.0 and 1.0
- decision: either "INCLUDE" or "EXCLUDE"

JSON only, no other text:'''


# ---------------------------------------------------------------------------
# Evaluation Functions
# ---------------------------------------------------------------------------


def evaluate_genai_news(title: str, content: str) -> Optional[GenAINewsEvaluation]:
    """Evaluate an article for the GENAI_NEWS persona."""
    prompt = GENAI_NEWS_PROMPT.format(
        title=title[:300],
        content=content[:1000]
    )
    
    response = chat_json(prompt, temperature=0.1)
    
    if response is None:
        logger.warning("LLM evaluation failed for: %s", title[:50])
        return None
    
    try:
        return GenAINewsEvaluation(
            relevance_score=float(response.get("relevance_score", 0.0)),
            topic=str(response.get("topic", "Unknown")),
            why_it_matters=str(response.get("why_it_matters", "")),
            target_audience=str(response.get("target_audience", "")),
            decision=str(response.get("decision", "EXCLUDE")).upper(),
            raw_response=response
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Failed to parse evaluation response: %s", e)
        return None


def evaluate_product_ideas(title: str, content: str) -> Optional[ProductIdeasEvaluation]:
    """Evaluate an article for the PRODUCT_IDEAS persona."""
    prompt = PRODUCT_IDEAS_PROMPT.format(
        title=title[:300],
        content=content[:1000]
    )
    
    response = chat_json(prompt, temperature=0.1)
    
    if response is None:
        logger.warning("LLM evaluation failed for: %s", title[:50])
        return None
    
    try:
        return ProductIdeasEvaluation(
            relevance_score=float(response.get("relevance_score", 0.0)),
            idea_type=str(response.get("idea_type", "Unknown")),
            problem_statement=str(response.get("problem_statement", "")),
            solution_summary=str(response.get("solution_summary", "")),
            reusability_score=float(response.get("reusability_score", 0.0)),
            decision=str(response.get("decision", "EXCLUDE")).upper(),
            raw_response=response
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.error("Failed to parse evaluation response: %s", e)
        return None


def evaluate_item(
    title: str,
    content: str,
    persona: Persona
) -> Optional[GenAINewsEvaluation | ProductIdeasEvaluation]:
    """Evaluate an item for the given persona."""
    if persona == Persona.GENAI_NEWS:
        return evaluate_genai_news(title, content)
    elif persona == Persona.PRODUCT_IDEAS:
        return evaluate_product_ideas(title, content)
    else:
        logger.error("Unknown persona: %s", persona)
        return None


# ---------------------------------------------------------------------------
# Quick Test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    from src.services.llm import is_ollama_running
    
    print("=" * 60)
    print("  Testing Evaluator (LLM-based)")
    print("=" * 60)
    
    # Check Ollama first
    print("\n🔍 Checking Ollama...")
    if not is_ollama_running():
        print("   ❌ Ollama is not running! Please start Ollama.")
        exit(1)
    print("   ✅ Ollama is running!")
    
    # Test 1: Simple JSON test first
    print("\n" + "-" * 60)
    print("🧪 Test 0: Quick JSON Test")
    print("-" * 60)
    
    from src.services.llm import chat
    
    simple_prompt = 'Reply with only: {"status": "ok"}'
    response = chat(simple_prompt, temperature=0.1)
    print(f"   Raw response: {response.content}")
    
    # Test articles
    test_articles = [
        {
            "title": "Meta Releases Llama 3.1 405B",
            "content": "Meta released the largest open source language model with 405 billion parameters."
        },
        {
            "title": "I built a Figma to React converter",
            "content": "Launched my tool that converts Figma designs to React code. Got 50 paying customers."
        },
    ]
    
    # Test GENAI_NEWS
    print("\n" + "-" * 60)
    print("🔬 Testing GENAI_NEWS Evaluation")
    print("-" * 60)
    
    article = test_articles[0]
    print(f"\n📰 Article: {article['title']}")
    print("   Evaluating... (10-20 seconds)")
    
    result = evaluate_genai_news(article["title"], article["content"])
    
    if result:
        print(f"\n   ✅ Success!")
        print(f"   ┌─────────────────────────────────────")
        print(f"   │ Score:    {result.relevance_score}")
        print(f"   │ Topic:    {result.topic}")
        print(f"   │ Reason:   {result.why_it_matters[:50]}...")
        print(f"   │ Audience: {result.target_audience}")
        print(f"   │ Decision: {result.decision}")
        print(f"   └─────────────────────────────────────")
    else:
        print("   ❌ Failed!")
    
    # Test PRODUCT_IDEAS
    print("\n" + "-" * 60)
    print("💡 Testing PRODUCT_IDEAS Evaluation")
    print("-" * 60)
    
    article = test_articles[1]
    print(f"\n📰 Article: {article['title']}")
    print("   Evaluating... (10-20 seconds)")
    
    result = evaluate_product_ideas(article["title"], article["content"])
    
    if result:
        print(f"\n   ✅ Success!")
        print(f"   ┌─────────────────────────────────────")
        print(f"   │ Score:       {result.relevance_score}")
        print(f"   │ Type:        {result.idea_type}")
        print(f"   │ Problem:     {result.problem_statement[:40]}...")
        print(f"   │ Solution:    {result.solution_summary[:40]}...")
        print(f"   │ Reusability: {result.reusability_score}")
        print(f"   │ Decision:    {result.decision}")
        print(f"   └─────────────────────────────────────")
    else:
        print("   ❌ Failed!")
    
    print("\n" + "=" * 60)
    print("  Tests Complete!")
    print("=" * 60)