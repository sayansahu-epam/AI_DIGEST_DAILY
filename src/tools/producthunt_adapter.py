"""
Product Hunt ingestion: fetch recent products via GraphQL and normalize
into IngestedItem. Structure: (a) ProductHuntAdapter implements IngestionAdapter;
(b) low-level fetch/parse helpers are private.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter

logger = logging.getLogger(__name__)

PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# Query as specified; do not change.
POSTS_QUERY = """
{
  posts(order: NEWEST, first: 20) {
    edges {
      node {
        id
        name
        tagline
        url
        createdAt
        makers {
          name
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Ingestion adapter (single entry point for this source)
# ---------------------------------------------------------------------------


class ProductHuntAdapter(IngestionAdapter):
    """
    IngestionAdapter for Product Hunt. Fetches newest posts via GraphQL,
    then keeps only those created within the last hours with name, url, and createdAt.
    """

    def fetch_items(self, hours: int) -> list[IngestedItem]:
        token = os.environ.get("PRODUCT_HUNT_API_TOKEN", "").strip()
        if not token:
            logger.warning("PRODUCT_HUNT_API_TOKEN not set; skipping Product Hunt")
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        items: list[IngestedItem] = []
        try:
            nodes = _fetch_posts(token)
            for node in nodes:
                try:
                    if not _is_valid_post(node):
                        continue
                    published_at = _parse_created_at(node.get("createdAt"))
                    if published_at is None or published_at < cutoff:
                        continue
                    item = _node_to_ingested_item(node, published_at)
                    if item is not None:
                        items.append(item)
                except Exception as e:
                    logger.debug("Skip Product Hunt post: id=%s error=%s", node.get("id"), e)
        except Exception as e:
            logger.warning("Product Hunt fetch failed: %s", e)
        return items


# ---------------------------------------------------------------------------
# Low-level fetch / normalization (internal helpers)
# ---------------------------------------------------------------------------


def _fetch_posts(api_token: str) -> list[dict]:
    """Execute the GraphQL query and return list of post nodes. Empty list on API error."""
    try:
        payload = {"query": POSTS_QUERY}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            PH_GRAPHQL_URL,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = json.loads(resp.read().decode())
        edges = (out.get("data") or {}).get("posts", {}).get("edges") or []
        return [e["node"] for e in edges if isinstance(e, dict) and isinstance(e.get("node"), dict)]
    except Exception as e:
        logger.debug("Product Hunt GraphQL failed: %s", e)
        return []


def _is_valid_post(node: dict) -> bool:
    """True if node has name, url, and createdAt."""
    if not node.get("name"):
        return False
    if not node.get("url"):
        return False
    if node.get("createdAt") is None:
        return False
    return True


def _parse_created_at(created_at: str | None) -> datetime | None:
    """Parse createdAt (ISO 8601) to UTC datetime. Returns None if invalid."""
    if not created_at:
        return None
    try:
        s = created_at.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _node_to_ingested_item(node: dict, published_at: datetime) -> IngestedItem | None:
    """Normalize post node to IngestedItem. Returns None if required fields missing."""
    name = (node.get("name") or "").strip()
    url = (node.get("url") or "").strip()
    if not name or not url:
        return None
    content = (node.get("tagline") or "").strip()
    author = _get_author(node)
    node_id = node.get("id")
    if node_id is None:
        return None
    return IngestedItem(
        source="Product Hunt",
        external_id=str(node_id),
        title=name,
        url=url,
        content=content,
        author=author,
        published_at=published_at,
        raw_payload=node,
    )


def _get_author(node: dict) -> str | None:
    """First maker name if available."""
    makers = node.get("makers") or []
    if makers and isinstance(makers[0], dict) and makers[0].get("name"):
        return (makers[0]["name"] or "").strip() or None
    return None
