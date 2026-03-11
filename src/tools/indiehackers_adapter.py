"""
Indie Hackers ingestion: fetch discussions/posts via RSS and normalize
into IngestedItem. Structure: (a) IndieHackersAdapter implements IngestionAdapter;
(b) low-level helpers are private. Uses same RSS parsing as rss_adapter.
"""

import logging
from datetime import datetime, timedelta, timezone

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter
from src.tools.rss_adapter import fetch_rss_items

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ingestion adapter (single entry point for this source)
# ---------------------------------------------------------------------------


class IndieHackersAdapter(IngestionAdapter):
    """
    IngestionAdapter for Indie Hackers. Fetches RSS feeds (same approach as
    RssAdapter), then keeps only entries within the last hours and normalizes
    with source "Indie Hackers".
    """

    def __init__(self, feed_urls: list[str]) -> None:
        self.feed_urls = [u.strip() for u in feed_urls if u.strip()]

    def fetch_items(self, hours: int) -> list[IngestedItem]:
        items = fetch_rss_items(self.feed_urls)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result: list[IngestedItem] = []
        for item in items:
            try:
                if item.published_at < cutoff:
                    continue
                result.append(_to_indie_hackers_item(item))
            except Exception as e:
                logger.debug("Skip Indie Hackers entry: id=%s error=%s", item.external_id, e)
        return result


# ---------------------------------------------------------------------------
# Low-level normalization (internal helpers)
# ---------------------------------------------------------------------------


def _to_indie_hackers_item(rss_item: IngestedItem) -> IngestedItem:
    """Normalize an RSS-sourced item to Indie Hackers: same fields, source set to 'Indie Hackers'."""
    return IngestedItem(
        source="Indie Hackers",
        external_id=rss_item.external_id,
        title=rss_item.title,
        url=rss_item.url,
        content=rss_item.content,
        author=rss_item.author,
        published_at=rss_item.published_at,
        raw_payload=rss_item.raw_payload,
    )
