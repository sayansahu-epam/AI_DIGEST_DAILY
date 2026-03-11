"""
RSS/Atom ingestion: fetch feeds and normalize entries into IngestedItem.
Structure: (a) RssAdapter implements IngestionAdapter; (b) low-level parsing
helpers are private. No storage, filtering, or deduplication.
"""

import calendar
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import feedparser

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ingestion adapter (single entry point for this source)
# ---------------------------------------------------------------------------


class RssAdapter(IngestionAdapter):
    """
    IngestionAdapter for RSS/Atom feeds. Wraps fetch_rss_items with a
    lookback window: fetches all feed entries, then keeps only items
    whose published_at is within the last hours.
    """

    def __init__(self, feed_urls: list[str]) -> None:
        self.feed_urls = feed_urls

    def fetch_items(self, hours: int) -> list[IngestedItem]:
        items = fetch_rss_items(self.feed_urls)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [item for item in items if item.published_at >= cutoff]


# ---------------------------------------------------------------------------
# Low-level RSS parsing / normalization (internal helpers)
# ---------------------------------------------------------------------------


def fetch_rss_items(feed_urls: list[str]) -> list[IngestedItem]:
    """
    Fetch and parse each feed URL, normalize entries to IngestedItem.
    Malformed feeds or entries are skipped; no exceptions are raised.
    Used by RssAdapter; may also be called directly for low-level use.
    """
    items: list[IngestedItem] = []
    for feed_url in feed_urls:
        try:
            feed_items = _fetch_one_feed(feed_url)
            items.extend(feed_items)
        except Exception as e:
            logger.warning("RSS feed failed: url=%s error=%s", feed_url, e)
    return items


def _fetch_one_feed(feed_url: str) -> list[IngestedItem]:
    """Fetch a single feed and return a list of IngestedItems. Raises on network/parse errors."""
    parsed = feedparser.parse(feed_url)
    if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
        raise ValueError(parsed.get("bozo_exception", "Parse error"))
    feed_title = (parsed.feed.get("title") or feed_url).strip() or feed_url
    items: list[IngestedItem] = []
    for entry in parsed.get("entries", []):
        try:
            item = _entry_to_ingested_item(entry, feed_title, feed_url)
            if item is not None:
                items.append(item)
        except Exception as e:
            logger.debug("Skip malformed entry: feed=%s title=%s error=%s", feed_url, entry.get("title"), e)
    return items


def _entry_to_ingested_item(entry: dict, feed_title: str, feed_url: str) -> IngestedItem | None:
    """Convert one feed entry to IngestedItem. Returns None if entry is invalid (e.g. no date)."""
    published_at = _parse_published(entry)
    if published_at is None:
        return None
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    external_id = _get_external_id(entry, link, title)
    content = _get_content(entry)
    author = entry.get("author")
    if author is not None:
        author = author.strip() or None
    return IngestedItem(
        source=feed_title,
        external_id=external_id,
        title=title,
        url=link,
        content=content,
        author=author,
        published_at=published_at,
        raw_payload=entry,
    )


def _parse_published(entry: dict) -> datetime | None:
    """Parse entry published/updated time to UTC datetime. Returns None if missing or invalid."""
    # feedparser: published_parsed / updated_parsed are time.struct_time in UTC
    raw = entry.get("published_parsed") or entry.get("updated_parsed")
    if raw is None:
        return None
    try:
        ts = calendar.timegm(raw)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, OSError, OverflowError):
        return None


def _get_external_id(entry: dict, link: str, title: str) -> str:
    """Stable external_id from entry.id, entry.guids[0], or hash(link + title)."""
    eid = entry.get("id")
    if eid and isinstance(eid, str):
        return eid.strip()
    guids = entry.get("guids", [])
    if guids:
        g = guids[0]
        gval = g.get("guid") if isinstance(g, dict) else getattr(g, "guid", None)
        if gval:
            return str(gval).strip()
    payload = (link or "") + (title or "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_content(entry: dict) -> str:
    """Prefer entry.content[0].value, else entry.summary, else empty string."""
    content_list = entry.get("content", [])
    if content_list and isinstance(content_list[0], dict):
        val = content_list[0].get("value")
        if val:
            return (val or "").strip()
    summary = entry.get("summary")
    if summary:
        return (summary or "").strip()
    return ""
