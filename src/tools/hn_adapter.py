"""
Hacker News ingestion: fetch recent stories via Firebase API and normalize
into IngestedItem. Structure: (a) HackerNewsAdapter implements IngestionAdapter;
(b) low-level fetch/parse helpers are private.
"""

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
NEWSTORIES_URL = f"{HN_BASE}/newstories.json"
# Cap per run to avoid hundreds of sequential requests (keeps runs responsive)
MAX_STORY_IDS = 20


# ---------------------------------------------------------------------------
# Ingestion adapter (single entry point for this source)
# ---------------------------------------------------------------------------


class HackerNewsAdapter(IngestionAdapter):
    """
    IngestionAdapter for Hacker News. Fetches new story IDs, then item details,
    and returns only stories within the last hours that have title, URL, and timestamp.
    """

    def fetch_items(self, hours: int) -> list[IngestedItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        story_ids = _fetch_story_ids()[:MAX_STORY_IDS]
        items: list[IngestedItem] = []
        for sid in story_ids:
            try:
                raw = _fetch_item(sid)
                if raw is None:
                    continue
                if not _is_valid_story(raw):
                    continue
                published_at = _parse_time(raw.get("time"))
                if published_at is None:
                    continue
                if published_at < cutoff:
                    break  # newstories is newest-first; rest are older
                item = _item_to_ingested_item(raw, published_at)
                if item is not None:
                    items.append(item)
            except Exception as e:
                logger.debug("Skip HN item: id=%s error=%s", sid, e)
        return items


# ---------------------------------------------------------------------------
# Low-level fetch / normalization (internal helpers)
# ---------------------------------------------------------------------------


def _fetch_story_ids() -> list[int]:
    """Fetch list of new story IDs from HN API. Returns empty list on failure."""
    try:
        with urllib.request.urlopen(NEWSTORIES_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("HN newstories failed: %s", e)
        return []


def _fetch_item(item_id: int) -> dict | None:
    """Fetch a single HN item by ID. Returns None on failure or invalid response."""
    try:
        url = f"{HN_BASE}/item/{item_id}.json"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug("HN item fetch failed: id=%s error=%s", item_id, e)
        return None


def _is_valid_story(raw: dict) -> bool:
    """True if item is a story with title, url, and timestamp."""
    if raw.get("type") != "story":
        return False
    if not (raw.get("title") and raw.get("url")):
        return False
    if raw.get("time") is None:
        return False
    return True


def _parse_time(ts: int | None) -> datetime | None:
    """Convert HN Unix timestamp to UTC datetime. Returns None if invalid."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, OSError, OverflowError):
        return None


def _item_to_ingested_item(raw: dict, published_at: datetime) -> IngestedItem | None:
    """Normalize HN item dict to IngestedItem. Returns None if required fields missing."""
    title = (raw.get("title") or "").strip()
    url = (raw.get("url") or "").strip()
    if not title or not url:
        return None
    content = (raw.get("text") or "").strip() if raw.get("text") else ""
    author = raw.get("by")
    if author is not None:
        author = author.strip() or None
    return IngestedItem(
        source="Hacker News",
        external_id=str(raw["id"]),
        title=title,
        url=url,
        content=content,
        author=author,
        published_at=published_at,
        raw_payload=raw,
    )
