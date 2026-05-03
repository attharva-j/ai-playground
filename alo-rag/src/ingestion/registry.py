"""Document registry for incremental index refresh.

A SQLite-backed, content-addressed registry that tracks a SHA-256 hash
per chunk and enables incremental index refresh — re-embedding only
chunks whose content or metadata has changed since the last ingestion
run.

Requirement: 19.4
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import sqlite3
import time
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ChunkStatus(str, Enum):
    """Lifecycle status of a chunk in the registry."""

    ACTIVE = "active"
    TOMBSTONE = "tombstone"  # soft-deleted; filtered at query time
    PENDING_GC = "pending_gc"  # scheduled for hard-deletion by GC sweep


class DocumentRegistry:
    """Tracks SHA-256 content hash per chunk for incremental refresh.

    On each ingestion run, :meth:`classify_chunk` determines whether a
    chunk is:

    - ``"unchanged"``: skip entirely (no embed call)
    - ``"modified"``:  tombstone old vectors, re-embed and re-upsert
    - ``"new"``:       embed and insert

    Chunks absent from the incoming source batch should be tombstoned
    via :meth:`tombstone`.  Tombstoned chunks are filtered at query
    time.  :meth:`gc_sweep` hard-deletes tombstones older than a
    configurable window (default 24 h).

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Defaults to
        ``"data/registry.db"``.
    """

    def __init__(self, db_path: str = "data/registry.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def _get_conn(self):
        """Yield a short-lived SQLite connection with auto-commit/rollback."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the registry table if it does not exist."""
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunk_registry (
                    chunk_id       TEXT PRIMARY KEY,
                    source_doc_id  TEXT NOT NULL,
                    content_hash   TEXT NOT NULL,
                    domain         TEXT NOT NULL,
                    metadata_json  TEXT NOT NULL DEFAULT '{}',
                    status         TEXT NOT NULL DEFAULT 'active',
                    created_at     REAL NOT NULL,
                    updated_at     REAL NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(content: str, metadata: dict) -> str:
        """Compute a SHA-256 hash over *content* + sorted metadata JSON."""
        meta_str = json.dumps(metadata, sort_keys=True, default=str)
        payload = content + meta_str
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_chunk(self, chunk_id: str, new_hash: str) -> str:
        """Classify a chunk as ``"unchanged"``, ``"modified"``, or ``"new"``."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT content_hash, status FROM chunk_registry WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()

        if row is None:
            return "new"

        existing_hash = row["content_hash"]
        status = row["status"]

        if status in (ChunkStatus.TOMBSTONE.value, ChunkStatus.PENDING_GC.value):
            return "new"

        if existing_hash == new_hash:
            return "unchanged"

        return "modified"

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert(
        self,
        chunk_id: str,
        source_doc_id: str,
        content_hash: str,
        domain: str,
        metadata: dict,
    ) -> None:
        """Insert or update a chunk record in the registry."""
        now = time.time()
        meta_json = json.dumps(metadata, sort_keys=True, default=str)

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO chunk_registry
                    (chunk_id, source_doc_id, content_hash, domain,
                     metadata_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    source_doc_id = excluded.source_doc_id,
                    content_hash  = excluded.content_hash,
                    domain        = excluded.domain,
                    metadata_json = excluded.metadata_json,
                    status        = excluded.status,
                    updated_at    = excluded.updated_at
                """,
                (
                    chunk_id,
                    source_doc_id,
                    content_hash,
                    domain,
                    meta_json,
                    ChunkStatus.ACTIVE.value,
                    now,
                    now,
                ),
            )

    def tombstone(self, chunk_id: str) -> None:
        """Soft-delete a chunk by setting its status to TOMBSTONE."""
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE chunk_registry
                SET status = ?, updated_at = ?
                WHERE chunk_id = ? AND status = ?
                """,
                (ChunkStatus.TOMBSTONE.value, now, chunk_id, ChunkStatus.ACTIVE.value),
            )

    # ------------------------------------------------------------------
    # Garbage collection
    # ------------------------------------------------------------------

    def gc_sweep(self, older_than_seconds: int = 86400) -> list[str]:
        """Hard-delete tombstoned chunks older than *older_than_seconds*."""
        cutoff = time.time() - older_than_seconds

        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT chunk_id FROM chunk_registry
                WHERE status = ? AND updated_at < ?
                """,
                (ChunkStatus.TOMBSTONE.value, cutoff),
            ).fetchall()

            deleted_ids = [row["chunk_id"] for row in rows]

            if deleted_ids:
                placeholders = ",".join("?" for _ in deleted_ids)
                conn.execute(
                    f"DELETE FROM chunk_registry WHERE chunk_id IN ({placeholders})",  # noqa: S608
                    deleted_ids,
                )
                logger.info(
                    "DocumentRegistry: gc_sweep hard-deleted %d chunks",
                    len(deleted_ids),
                )

        return deleted_ids

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_active_chunk_ids(self) -> set[str]:
        """Return the set of all chunk IDs with ACTIVE status."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT chunk_id FROM chunk_registry WHERE status = ?",
                (ChunkStatus.ACTIVE.value,),
            ).fetchall()
        return {row["chunk_id"] for row in rows}
