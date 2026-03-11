import logging

from src.models.ingested_item import IngestedItem
from src.tools.ingestion_base import IngestionAdapter

logger = logging.getLogger(__name__)


def run_ingestion(adapters: list[IngestionAdapter], hours: int) -> list[IngestedItem]:
    """
    Run ingestion adapters sequentially.
    One slow or failing adapter is logged and skipped.
    This is intentional for early-stage reliability.
    """
    result: list[IngestedItem] = []
    print(f"Running ingestion (lookback={hours}h, adapters={len(adapters)})...", flush=True)

    for adapter in adapters:
        name = type(adapter).__name__
        print(f"  {name}...", end=" ", flush=True)
        try:
            items = adapter.fetch_items(hours)
            result.extend(items)
            print(f"{len(items)} items", flush=True)
        except Exception as e:
            logger.warning(
                "Ingestion adapter failed: adapter=%s error=%s",
                name,
                e,
            )
            print(f"failed ({e})", flush=True)

    return result
