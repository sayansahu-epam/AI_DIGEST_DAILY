"""
Common interface for all ingestion adapters (RSS, HN, Reddit, etc.).
Adapters implement fetch_items to return raw items from their source.
"""

from abc import ABC, abstractmethod

from src.models.ingested_item import IngestedItem


class IngestionAdapter(ABC):
    """
    Contract for ingestion adapters: each adapter must fetch items from its
    source and return them as a list of IngestedItem. The hours argument
    defines how far back to look (interpretation is adapter-specific).
    """

    @abstractmethod
    def fetch_items(self, hours: int) -> list[IngestedItem]:
        """Fetch items from the source for the given lookback window (hours)."""
        ...
