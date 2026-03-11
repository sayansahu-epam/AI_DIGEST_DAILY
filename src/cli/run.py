# # """
# # Minimal ingestion smoke check: run orchestration with example adapters and print results.
# # Temporary sanity check only; not the final CLI.
# # """

# # import json
# # from pathlib import Path

# # from src.tools.hn_adapter import HackerNewsAdapter
# # from src.tools.indiehackers_adapter import IndieHackersAdapter
# # from src.tools.producthunt_adapter import ProductHuntAdapter
# # from src.tools.reddit_adapter import RedditAdapter
# # from src.tools.rss_adapter import RssAdapter
# # from src.workflows.ingestion import run_ingestion

# # if __name__ == "__main__":
# #     print("Starting ingestion smoke check...", flush=True)
# #     # HN runs last (many sequential requests); others are quicker
# #     adapters = [
# #         RssAdapter(["https://feeds.bbci.co.uk/news/rss.xml", "https://www.theverge.com/rss/index.xml"]),
# #         RedditAdapter(["MachineLearning"]),
# #         ProductHuntAdapter(),
# #         IndieHackersAdapter(["https://www.indiehackers.com/feed"]),
# #         HackerNewsAdapter(),
# #     ]
# #     items = run_ingestion(adapters, hours=24)
# #     print(f"Total items ingested: {len(items)}")
# #     by_source: dict[str, int] = {}
# #     for item in items:
# #         by_source[item.source] = by_source.get(item.source, 0) + 1
# #     for source, count in sorted(by_source.items()):
# #         print(f"  {source}: {count}")

# #     # Save fetched items to a JSON file so you can view what was ingested
# #     out_path = Path(__file__).resolve().parent.parent.parent / "ingestion_results.json"
# #     rows = [
# #         {
# #             "source": item.source,
# #             "external_id": item.external_id,
# #             "title": item.title,
# #             "url": item.url,
# #             "content": item.content,
# #             "author": item.author,
# #             "published_at": item.published_at.isoformat(),
# #             "raw_payload": item.raw_payload,
# #         }
# #         for item in items
# #     ]
# #     with open(out_path, "w", encoding="utf-8") as f:
# #         json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
# #     print(f"\nSaved {len(rows)} items to: {out_path}")






# """
# Main entry point for AI Digest System.
# Runs ingestion pipeline and saves results to database.
# """

# import json
# from pathlib import Path

# from src.services.db import init_database, save_items, get_item_count
# from src.tools.hn_adapter import HackerNewsAdapter
# from src.tools.indiehackers_adapter import IndieHackersAdapter
# from src.tools.producthunt_adapter import ProductHuntAdapter
# from src.tools.reddit_adapter import RedditAdapter
# from src.tools.rss_adapter import RssAdapter
# from src.workflows.ingestion import run_ingestion


# def main():
#     """Run the full ingestion pipeline and save to database."""
    
#     print("=" * 60)
#     print("  AI DIGEST SYSTEM - Ingestion Pipeline")
#     print("=" * 60)
    
#     # Step 1: Initialize database (creates tables if needed)
#     print("\n📦 Initializing database...")
#     init_database()
#     print("   Done!")
    
#     # Step 2: Configure adapters
#     print("\n🔌 Configuring adapters...")
#     adapters = [
#         RssAdapter([
#             "https://feeds.bbci.co.uk/news/rss.xml",
#             "https://www.theverge.com/rss/index.xml"
#         ]),
#         RedditAdapter(["MachineLearning"]),
#         ProductHuntAdapter(),
#         IndieHackersAdapter(["https://www.indiehackers.com/feed"]),
#         HackerNewsAdapter(),
#     ]
#     print(f"   {len(adapters)} adapters ready")
    
#     # Step 3: Run ingestion
#     print("\n🌐 Fetching from sources...")
#     items = run_ingestion(adapters, hours=24)
#     print(f"\n   Total items fetched: {len(items)}")
    
#     # Step 4: Save to database
#     print("\n💾 Saving to database...")
#     result = save_items(items)
#     print(f"   Inserted: {result.inserted}")
#     print(f"   Updated:  {result.updated}")
#     print(f"   Total:    {result.total}")
    
#     # Step 5: Show database stats
#     print("\n📊 Database Statistics:")
#     counts = get_item_count()
#     for row in counts:
#         status = "processed" if row["is_processed"] else "pending"
#         print(f"   {row['source']}: {row['count']} ({status})")
    
#     # Step 6: Also save JSON backup (optional, can remove later)
#     print("\n📄 Saving JSON backup...")
#     out_path = Path(__file__).resolve().parent.parent.parent / "ingestion_results.json"
#     rows = [
#         {
#             "source": item.source,
#             "external_id": item.external_id,
#             "title": item.title,
#             "url": item.url,
#             "content": item.content,
#             "author": item.author,
#             "published_at": item.published_at.isoformat(),
#             "raw_payload": item.raw_payload,
#         }
#         for item in items
#     ]
#     with open(out_path, "w", encoding="utf-8") as f:
#         json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
#     print(f"   Saved to: {out_path}")
    
#     # Done!
#     print("\n" + "=" * 60)
#     print("  ✅ Ingestion Complete!")
#     print("=" * 60)


# if __name__ == "__main__":
#     main()


"""
Main entry point for AI Digest System.
One command to: Ingest → Evaluate → Generate Digest
"""

from datetime import datetime, timezone

from src.services.config import (
    PERSONA_GENAI_NEWS_ENABLED,
    PERSONA_PRODUCT_IDEAS_ENABLED,
    MAX_ITEMS_TO_EVALUATE,
    GENAI_NEWS_MIN_RELEVANCE,
    PRODUCT_IDEAS_MIN_RELEVANCE,
)
from src.services.db import init_database, save_items, get_item_count
from src.services.llm import is_ollama_running
from src.tools.hn_adapter import HackerNewsAdapter
from src.tools.indiehackers_adapter import IndieHackersAdapter
from src.tools.producthunt_adapter import ProductHuntAdapter
from src.tools.reddit_adapter import RedditAdapter
from src.tools.rss_adapter import RssAdapter
from src.tools.prefilter import Persona
from src.workflows.ingestion import run_ingestion
from src.workflows.evaluation import run_evaluation
from src.workflows.digest import generate_digest


def main():
    """Run the full AI Digest pipeline."""
    
    start_time = datetime.now(timezone.utc)
    
    print("=" * 60)
    print("  🤖 AI DIGEST SYSTEM")
    print("=" * 60)
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    # Step 0: Check Ollama
    print("\n🔍 Checking Ollama...")
    if not is_ollama_running():
        print("   ❌ Ollama is not running!")
        print("   Please start Ollama and try again.")
        return
    print("   ✅ Ollama is running!")
    
    # Step 1: Initialize database
    print("\n📦 Step 1: Initializing database...")
    init_database()
    print("   ✅ Done!")
    
    # Step 2: Run ingestion
    print("\n🌐 Step 2: Fetching from sources...")
    adapters = [
        RssAdapter([
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://www.theverge.com/rss/index.xml"
        ]),
        RedditAdapter(["MachineLearning", "LocalLLaMA"]),
        ProductHuntAdapter(),
        IndieHackersAdapter(["https://www.indiehackers.com/feed"]),
        HackerNewsAdapter(),
    ]
    items = run_ingestion(adapters, hours=24)
    
    # Step 3: Save to database
    print("\n💾 Step 3: Saving to database...")
    result = save_items(items)
    print(f"   Inserted: {result.inserted}")
    print(f"   Updated:  {result.updated}")
    
    # Step 4: Evaluate items
    print("\n🤖 Step 4: Evaluating with AI...")
    
    if PERSONA_GENAI_NEWS_ENABLED:
        run_evaluation(
            persona=Persona.GENAI_NEWS,
            limit=MAX_ITEMS_TO_EVALUATE,
            min_score=GENAI_NEWS_MIN_RELEVANCE
        )
    
    if PERSONA_PRODUCT_IDEAS_ENABLED:
        run_evaluation(
            persona=Persona.PRODUCT_IDEAS,
            limit=MAX_ITEMS_TO_EVALUATE,
            min_score=PRODUCT_IDEAS_MIN_RELEVANCE
        )
    
    # Step 5: Generate digests
    print("\n📝 Step 5: Generating digests...")
    
    digest_files = []
    
    if PERSONA_GENAI_NEWS_ENABLED:
        result = generate_digest(Persona.GENAI_NEWS)
        digest_files.append(result.file_path)
    
    if PERSONA_PRODUCT_IDEAS_ENABLED:
        result = generate_digest(Persona.PRODUCT_IDEAS)
        digest_files.append(result.file_path)
    
    # Done!
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("  ✅ AI DIGEST COMPLETE!")
    print("=" * 60)
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Digests generated:")
    for f in digest_files:
        print(f"    📄 {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()