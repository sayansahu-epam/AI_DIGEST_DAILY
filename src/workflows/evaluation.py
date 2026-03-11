"""
Evaluation workflow.
Orchestrates: DB fetch → Pre-filter → LLM Evaluation → Save results.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from src.services.db import (
    get_connection,
    get_unprocessed_items,
    mark_as_processed,
)
from src.tools.prefilter import Persona, prefilter_items
from src.tools.evaluator import (
    evaluate_genai_news,
    evaluate_product_ideas,
    GenAINewsEvaluation,
    ProductIdeasEvaluation,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of running the evaluation pipeline."""
    total_items: int
    prefilter_passed: int
    prefilter_rejected: int
    evaluated: int
    included: int
    excluded: int
    failed: int


def save_evaluation(
    item_id: int,
    persona: Persona,
    relevance_score: float,
    evaluation_data: dict
) -> bool:
    """Save an evaluation result to the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        # Insert or update evaluation
        cursor.execute("""
            INSERT INTO evaluations (item_id, persona, relevance_score, evaluation_json, evaluated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(item_id, persona) DO UPDATE SET
                relevance_score = excluded.relevance_score,
                evaluation_json = excluded.evaluation_json,
                evaluated_at = excluded.evaluated_at
        """, (
            item_id,
            persona.value,
            relevance_score,
            json.dumps(evaluation_data),
            now
        ))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error("Failed to save evaluation: %s", e)
        return False
    finally:
        conn.close()


def run_evaluation(
    persona: Persona,
    limit: int = 20,
    min_score: float = 0.6
) -> EvaluationResult:
    """
    Run the full evaluation pipeline for a persona.
    
    Args:
        persona: Which persona to evaluate for (GENAI_NEWS or PRODUCT_IDEAS)
        limit: Maximum items to process (LLM is slow!)
        min_score: Minimum relevance score to include
    
    Returns:
        EvaluationResult with statistics
    """
    print(f"\n{'='*60}")
    print(f"  Running Evaluation: {persona.value.upper()}")
    print(f"{'='*60}")
    
    # Step 1: Get unprocessed items from database
    print("\n📦 Step 1: Fetching unprocessed items from database...")
    items = get_unprocessed_items(limit=limit * 3)  # Get extra, pre-filter will reduce
    print(f"   Found: {len(items)} items")
    
    if not items:
        print("   No unprocessed items. Run ingestion first!")
        return EvaluationResult(
            total_items=0,
            prefilter_passed=0,
            prefilter_rejected=0,
            evaluated=0,
            included=0,
            excluded=0,
            failed=0
        )
    
    # Step 2: Pre-filter items
    print(f"\n🔍 Step 2: Pre-filtering for {persona.value}...")
    filtered_items, prefilter_result = prefilter_items(items, persona)
    print(f"   Passed: {prefilter_result.passed}")
    print(f"   Rejected: {prefilter_result.rejected}")
    
    # Limit to requested amount
    items_to_evaluate = filtered_items[:limit]
    print(f"   Will evaluate: {len(items_to_evaluate)} items")
    
    if not items_to_evaluate:
        print("   No items passed pre-filter!")
        return EvaluationResult(
            total_items=len(items),
            prefilter_passed=0,
            prefilter_rejected=prefilter_result.rejected,
            evaluated=0,
            included=0,
            excluded=0,
            failed=0
        )
    
    # Step 3: Evaluate each item with LLM
    print(f"\n🤖 Step 3: Evaluating with LLM (this will take a while)...")
    print(f"   Estimated time: {len(items_to_evaluate) * 10}-{len(items_to_evaluate) * 20} seconds")
    
    evaluated = 0
    included = 0
    excluded = 0
    failed = 0
    processed_ids = []
    
    for i, item in enumerate(items_to_evaluate):
        item_id = item["id"]
        title = item["title"]
        content = item.get("content", "")
        
        print(f"\n   [{i+1}/{len(items_to_evaluate)}] {title[:50]}...")
        
        # Evaluate based on persona
        if persona == Persona.GENAI_NEWS:
            result = evaluate_genai_news(title, content)
        else:
            result = evaluate_product_ideas(title, content)
        
        if result is None:
            print(f"      ❌ Failed")
            failed += 1
            continue
        
        evaluated += 1
        
        # Check decision and score
        if result.decision == "INCLUDE" and result.relevance_score >= min_score:
            print(f"      ✅ INCLUDE (score: {result.relevance_score})")
            included += 1
        else:
            print(f"      ⬜ EXCLUDE (score: {result.relevance_score})")
            excluded += 1
        
        # Save to database
        save_evaluation(
            item_id=item_id,
            persona=persona,
            relevance_score=result.relevance_score,
            evaluation_data=result.raw_response
        )
        
        processed_ids.append(item_id)
    
    # Step 4: Mark items as processed
    print(f"\n💾 Step 4: Marking {len(processed_ids)} items as processed...")
    mark_as_processed(processed_ids)
    print("   Done!")
    
    # Summary
    result = EvaluationResult(
        total_items=len(items),
        prefilter_passed=prefilter_result.passed,
        prefilter_rejected=prefilter_result.rejected,
        evaluated=evaluated,
        included=included,
        excluded=excluded,
        failed=failed
    )
    
    print(f"\n{'='*60}")
    print(f"  Evaluation Complete!")
    print(f"{'='*60}")
    print(f"   📊 Pre-filter: {result.prefilter_passed} passed, {result.prefilter_rejected} rejected")
    print(f"   🤖 Evaluated: {result.evaluated} items")
    print(f"   ✅ Included: {result.included}")
    print(f"   ⬜ Excluded: {result.excluded}")
    print(f"   ❌ Failed: {result.failed}")
    
    return result


# ---------------------------------------------------------------------------
# Quick Test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    from src.services.llm import is_ollama_running
    
    print("=" * 60)
    print("  Testing Evaluation Workflow")
    print("=" * 60)
    
    # Check Ollama
    if not is_ollama_running():
        print("\n❌ Ollama is not running! Please start Ollama.")
        exit(1)
    print("\n✅ Ollama is running!")
    
    # Run evaluation for GENAI_NEWS (just 3 items for testing)
    result = run_evaluation(
        persona=Persona.GENAI_NEWS,
        limit=3,  # Only 3 items for quick test
        min_score=0.5
    )
    
    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)