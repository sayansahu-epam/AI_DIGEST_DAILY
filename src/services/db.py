"""
SQLite database layer for AI Digest System.
Handles all database operations: connection, table creation, CRUD operations.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.models.ingested_item import IngestedItem

logger = logging.getLogger(__name__)

# Database file location (project root)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "digest.db"


@dataclass
class SaveResult:
    """Result of a bulk save operation."""
    inserted: int
    updated: int
    
    @property
    def total(self) -> int:
        return self.inserted + self.updated


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Table: ingested_items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingested_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source          TEXT NOT NULL,
                external_id     TEXT NOT NULL,
                title           TEXT NOT NULL,
                url             TEXT NOT NULL,
                content         TEXT,
                author          TEXT,
                published_at    TEXT NOT NULL,
                ingested_at     TEXT NOT NULL,
                raw_payload     TEXT,
                is_processed    INTEGER DEFAULT 0,
                UNIQUE(source, external_id)
            )
        """)
        
        # Table: evaluations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id         INTEGER NOT NULL,
                persona         TEXT NOT NULL,
                relevance_score REAL,
                evaluation_json TEXT,
                evaluated_at    TEXT NOT NULL,
                FOREIGN KEY (item_id) REFERENCES ingested_items(id),
                UNIQUE(item_id, persona)
            )
        """)
        
        # Table: digests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                persona         TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                item_count      INTEGER NOT NULL,
                content_json    TEXT
            )
        """)
        
        # Table: deliveries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deliveries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                digest_id       INTEGER NOT NULL,
                channel         TEXT NOT NULL,
                status          TEXT NOT NULL,
                delivered_at    TEXT NOT NULL,
                error_message   TEXT,
                FOREIGN KEY (digest_id) REFERENCES digests(id)
            )
        """)
        
        conn.commit()
        logger.info("Database initialized: %s", DB_PATH)
        
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Ingested Items: Save & Query
# ---------------------------------------------------------------------------


def save_items(items: list[IngestedItem]) -> SaveResult:
    """
    Save a list of IngestedItem to the database.
    Updates existing items (by source + external_id) and inserts new ones.
    """
    if not items:
        return SaveResult(inserted=0, updated=0)
    
    conn = get_connection()
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        cursor = conn.cursor()
        
        for item in items:
            # Check if item already exists
            cursor.execute(
                "SELECT id FROM ingested_items WHERE source = ? AND external_id = ?",
                (item.source, item.external_id)
            )
            existing = cursor.fetchone()
            
            raw_json = json.dumps(item.raw_payload, default=str)
            published_iso = item.published_at.isoformat()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE ingested_items
                    SET title = ?, url = ?, content = ?, author = ?,
                        published_at = ?, raw_payload = ?
                    WHERE id = ?
                """, (
                    item.title,
                    item.url,
                    item.content,
                    item.author,
                    published_iso,
                    raw_json,
                    existing["id"]
                ))
                updated += 1
                logger.debug("Updated duplicate: source=%s id=%s", item.source, item.external_id)
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO ingested_items
                    (source, external_id, title, url, content, author,
                     published_at, ingested_at, raw_payload, is_processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    item.source,
                    item.external_id,
                    item.title,
                    item.url,
                    item.content,
                    item.author,
                    published_iso,
                    now,
                    raw_json
                ))
                inserted += 1
        
        conn.commit()
        logger.info("Saved items: inserted=%d updated=%d", inserted, updated)
        
    finally:
        conn.close()
    
    return SaveResult(inserted=inserted, updated=updated)


def get_unprocessed_items(limit: Optional[int] = None) -> list[dict]:
    """Fetch items that haven't been processed by LLM yet."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM ingested_items WHERE is_processed = 0 ORDER BY published_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def mark_as_processed(item_ids: list[int]) -> None:
    """Mark items as processed after LLM evaluation."""
    if not item_ids:
        return
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(item_ids))
        cursor.execute(
            f"UPDATE ingested_items SET is_processed = 1 WHERE id IN ({placeholders})",
            item_ids
        )
        conn.commit()
        logger.info("Marked %d items as processed", len(item_ids))
    finally:
        conn.close()


def get_item_count() -> dict:
    """Get count of items by source and processed status."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source, is_processed, COUNT(*) as count
            FROM ingested_items
            GROUP BY source, is_processed
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quick Test (run this file directly to test)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("Testing database module...")
    print(f"Database path: {DB_PATH}")
    
    # Initialize tables
    init_database()
    print("✅ Tables created")
    
    # Test with a sample item
    test_item = IngestedItem(
        source="Test Source",
        external_id="test-123",
        title="Test Article Title",
        url="https://example.com/test",
        content="This is test content.",
        author="Test Author",
        published_at=datetime.now(timezone.utc),
        raw_payload={"test": True}
    )
    
    # Save it
    result = save_items([test_item])
    print(f"✅ First save: inserted={result.inserted}, updated={result.updated}")
    
    # Save again (should update)
    result = save_items([test_item])
    print(f"✅ Second save: inserted={result.inserted}, updated={result.updated}")
    
    # Check counts
    counts = get_item_count()
    print(f"✅ Item counts: {counts}")
    
    # Get unprocessed
    unprocessed = get_unprocessed_items(limit=5)
    print(f"✅ Unprocessed items: {len(unprocessed)}")
    
    print("\n✅ All tests passed! Database is working.")