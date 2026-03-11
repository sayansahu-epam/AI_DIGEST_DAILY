"""Raw content item from external sources, before any processing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=False)
class IngestedItem:
    """
    A single raw item collected from an external source (RSS, HN, Reddit, etc.).
    No business logic; used only to carry data between ingestion and downstream steps.
    """

    source: str
    external_id: str
    title: str
    url: str
    content: str
    author: Optional[str]
    published_at: datetime  # UTC
    raw_payload: Any
