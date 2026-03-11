"""
Reddit ingestion: fetch recent posts from subreddits via public JSON and
normalize into IngestedItem. Structure: (a) RedditAdapter implements
IngestionAdapter; (b) low-level fetch/parse helpers are private.
"""

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "python:ai_intelligence_digest:v0.1"


# ---------------------------------------------------------------------------
# Ingestion adapter (single entry point for this source)
# ---------------------------------------------------------------------------


class RedditAdapter(IngestionAdapter):
    """
    IngestionAdapter for Reddit. Fetches /new.json for each configured
    subreddit and returns only posts within the last hours that have
    title, URL, and timestamp.
    """

    def __init__(self, subreddits: list[str]) -> None:
        self.subreddits = [s.strip() for s in subreddits if s.strip()]

    def fetch_items(self, hours: int) -> list[IngestedItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        items: list[IngestedItem] = []
        for subreddit in self.subreddits:
            try:
                posts = _fetch_subreddit_new(subreddit)
                for post in posts:
                    try:
                        if not _is_valid_post(post):
                            continue
                        published_at = _parse_created_utc(post.get("created_utc"))
                        if published_at is None or published_at < cutoff:
                            continue
                        item = _post_to_ingested_item(post, subreddit, published_at)
                        if item is not None:
                            items.append(item)
                    except Exception as e:
                        logger.debug("Skip Reddit post: subreddit=%s id=%s error=%s", subreddit, post.get("id"), e)
            except Exception as e:
                logger.warning("Reddit subreddit failed: subreddit=%s error=%s", subreddit, e)
        return items


# ---------------------------------------------------------------------------
# Low-level fetch / normalization (internal helpers)
# ---------------------------------------------------------------------------


def _fetch_subreddit_new(subreddit: str) -> list[dict]:
    """Fetch /r/{subreddit}/new.json. Returns list of post data dicts, or empty list on failure."""
    try:
        url = f"{REDDIT_BASE}/r/{subreddit}/new.json"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        children = (data.get("data") or {}).get("children") or []
        return [c["data"] for c in children if isinstance(c, dict) and isinstance(c.get("data"), dict)]
    except Exception as e:
        logger.debug("Reddit fetch failed: subreddit=%s error=%s", subreddit, e)
        return []


def _is_valid_post(post: dict) -> bool:
    """True if post has title, url, and created_utc."""
    if not (post.get("title") is not None and post.get("url") is not None):
        return False
    if post.get("created_utc") is None:
        return False
    return True


def _parse_created_utc(created_utc: int | float | None) -> datetime | None:
    """Convert Reddit created_utc (Unix timestamp) to UTC datetime. Returns None if invalid."""
    if created_utc is None:
        return None
    try:
        return datetime.fromtimestamp(int(created_utc), tz=timezone.utc)
    except (TypeError, OSError, OverflowError):
        return None


def _post_to_ingested_item(post: dict, subreddit: str, published_at: datetime) -> IngestedItem | None:
    """Normalize Reddit post dict to IngestedItem. Returns None if required fields missing."""
    title = (post.get("title") or "").strip()
    url = (post.get("url") or "").strip()
    if not title or not url:
        return None
    content = (post.get("selftext") or "").strip() if post.get("selftext") else ""
    author = post.get("author")
    if author is not None:
        author = author.strip() or None
    post_id = post.get("id")
    if post_id is None:
        return None
    return IngestedItem(
        source=f"Reddit/{subreddit}",
        external_id=str(post_id),
        title=title,
        url=url,
        content=content,
        author=author,
        published_at=published_at,
        raw_payload=post,
    )
