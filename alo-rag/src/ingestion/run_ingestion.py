"""Ingestion runner script for the ALO RAG system.

Loads product, policy, and customer data, chunks them using domain-specific
chunkers, computes embeddings, builds ChromaDB + BM25 indexes, and registers
all chunks in the DocumentRegistry for incremental refresh.

Usage:
    python -m src.ingestion.run_ingestion [--data-dir DATA_DIR] [--persist-dir PERSIST_DIR]

Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 19.4
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
import time
from pathlib import Path

from src.ingestion.chunkers import PolicyChunker, ProductChunker
from src.ingestion.embedders import EmbeddingService
from src.ingestion.index_builder import BM25Builder, IndexBuilder, VectorStore
from src.ingestion.loaders import CustomerLoader, PolicyLoader, ProductLoader
from src.ingestion.registry import DocumentRegistry

logger = logging.getLogger(__name__)


def _metadata_to_dict(meta: object) -> dict:
    """Convert a dataclass metadata object to a plain dict, dropping None values."""
    return {k: v for k, v in dataclasses.asdict(meta).items() if v is not None}


def run_ingestion(
    data_dir: Path,
    persist_dir: Path | None = None,
    registry_db_path: str | None = None,
) -> dict:
    """Execute the full ingestion pipeline.

    Parameters
    ----------
    data_dir:
        Root directory containing ``products/``, ``policies/``, and
        ``customers/`` subdirectories.
    persist_dir:
        Optional directory for persisting the ChromaDB vector store.
        When ``None``, an in-memory store is used.
    registry_db_path:
        Optional path for the SQLite document registry database.
        Defaults to ``<data_dir>/registry.db``.

    Returns
    -------
    dict:
        Summary statistics of the ingestion run.
    """
    start_time = time.time()

    products_path = data_dir / "products" / "alo_product_catalog.json"
    policies_path = data_dir / "policies"
    customers_path = data_dir / "customers" / "customer_order_history.json"

    if registry_db_path is None:
        registry_db_path = str(data_dir / "registry.db")

    # ------------------------------------------------------------------
    # 1. Load raw data
    # ------------------------------------------------------------------
    logger.info("=== Step 1: Loading raw data ===")

    product_loader = ProductLoader()
    policy_loader = PolicyLoader()
    customer_loader = CustomerLoader()

    product_docs = product_loader.load(products_path)
    policy_docs = policy_loader.load(policies_path)
    customer_profiles = customer_loader.load(customers_path)

    logger.info(
        "Loaded: %d product docs, %d policy docs, %d customer profiles",
        len(product_docs),
        len(policy_docs),
        len(customer_profiles),
    )

    # ------------------------------------------------------------------
    # 2. Chunk products and policies
    # ------------------------------------------------------------------
    logger.info("=== Step 2: Chunking documents ===")

    product_chunker = ProductChunker()
    policy_chunker = PolicyChunker()

    product_chunks, product_summary = product_chunker.chunk(product_docs)
    policy_chunks = policy_chunker.chunk(policy_docs)

    all_chunks = product_chunks + policy_chunks

    logger.info(
        "Chunking complete: %d product chunks (ingested=%d, skipped=%d), "
        "%d policy chunks, %d total",
        len(product_chunks),
        product_summary.ingested,
        product_summary.skipped,
        len(policy_chunks),
        len(all_chunks),
    )

    # ------------------------------------------------------------------
    # 3. Register chunks in DocumentRegistry for incremental refresh
    # ------------------------------------------------------------------
    logger.info("=== Step 3: Registering chunks in DocumentRegistry ===")

    registry = DocumentRegistry(db_path=registry_db_path)

    # Track which chunk IDs are in the current batch for tombstoning
    current_chunk_ids: set[str] = set()
    new_count = 0
    modified_count = 0
    unchanged_count = 0

    for chunk in all_chunks:
        current_chunk_ids.add(chunk.chunk_id)
        meta_dict = _metadata_to_dict(chunk.metadata)
        content_hash = DocumentRegistry.compute_hash(chunk.text, meta_dict)
        classification = registry.classify_chunk(chunk.chunk_id, content_hash)

        if classification == "new":
            new_count += 1
        elif classification == "modified":
            modified_count += 1
        else:
            unchanged_count += 1

        # Upsert regardless — updates the hash and timestamp for active chunks
        registry.upsert(
            chunk_id=chunk.chunk_id,
            source_doc_id=chunk.source_document,
            content_hash=content_hash,
            domain=chunk.metadata.domain,
            metadata=meta_dict,
        )

    # Tombstone chunks that were previously active but are no longer present
    previously_active = registry.get_active_chunk_ids()
    removed_ids = previously_active - current_chunk_ids
    for chunk_id in removed_ids:
        registry.tombstone(chunk_id)

    logger.info(
        "Registry: new=%d, modified=%d, unchanged=%d, tombstoned=%d",
        new_count,
        modified_count,
        unchanged_count,
        len(removed_ids),
    )

    # ------------------------------------------------------------------
    # 4. Compute embeddings
    # ------------------------------------------------------------------
    logger.info("=== Step 4: Computing embeddings ===")

    # For correctness, this CLI rebuilds the full local index every run.
    # Incremental registry state is recorded for production/persistent index
    # refresh workflows, but the local Chroma index is rebuilt from all active
    # chunks so registry/vector-store drift cannot silently degrade retrieval.
    chunks_to_embed = all_chunks
    embedding_service = EmbeddingService()
    texts_to_embed = [chunk.text for chunk in chunks_to_embed]
    embeddings = embedding_service.embed(texts_to_embed)

    logger.info("Computed %d embeddings", len(embeddings))

    # ------------------------------------------------------------------
    # 5. Build ChromaDB + BM25 indexes
    # ------------------------------------------------------------------
    logger.info("=== Step 5: Building indexes ===")

    vector_store = VectorStore(
        collection_name="alo_rag",
        persist_directory=str(persist_dir) if persist_dir else None,
    )
    bm25_builder = BM25Builder()
    index_builder = IndexBuilder(vector_store=vector_store, bm25_builder=bm25_builder)

    build_result, bm25_index = index_builder.build(chunks_to_embed, embeddings)

    logger.info(
        "Index build complete: %d chunks indexed, %d skipped",
        build_result.chunks_indexed,
        build_result.chunks_skipped,
    )

    # ------------------------------------------------------------------
    # 6. Run GC sweep on old tombstones
    # ------------------------------------------------------------------
    gc_deleted = registry.gc_sweep()
    if gc_deleted:
        logger.info("GC sweep: hard-deleted %d old tombstoned chunks", len(gc_deleted))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time

    summary = {
        "products_loaded": len(product_docs),
        "products_ingested": product_summary.ingested,
        "products_skipped": product_summary.skipped,
        "policies_loaded": len(policy_docs),
        "policy_chunks_created": len(policy_chunks),
        "product_chunks_created": len(product_chunks),
        "total_chunks": len(all_chunks),
        "customers_loaded": len(customer_profiles),
        "embeddings_computed": len(embeddings),
        "chunks_indexed": build_result.chunks_indexed,
        "registry_new": new_count,
        "registry_modified": modified_count,
        "registry_unchanged": unchanged_count,
        "registry_tombstoned": len(removed_ids),
        "gc_deleted": len(gc_deleted),
        "elapsed_seconds": round(elapsed, 2),
    }

    _print_summary(summary)
    return summary


def _print_summary(summary: dict) -> None:
    """Print a human-readable ingestion summary to stdout."""
    print("\n" + "=" * 60)
    print("  ALO RAG Ingestion Summary")
    print("=" * 60)
    print(f"  Products loaded:          {summary['products_loaded']}")
    print(f"  Products ingested:        {summary['products_ingested']}")
    print(f"  Products skipped:         {summary['products_skipped']}")
    print(f"  Product chunks created:   {summary['product_chunks_created']}")
    print(f"  Policies loaded:          {summary['policies_loaded']}")
    print(f"  Policy chunks created:    {summary['policy_chunks_created']}")
    print(f"  Total chunks:             {summary['total_chunks']}")
    print(f"  Customers loaded:         {summary['customers_loaded']}")
    print(f"  Embeddings computed:      {summary['embeddings_computed']}")
    print(f"  Chunks indexed:           {summary['chunks_indexed']}")
    print("-" * 60)
    print(f"  Registry — new:           {summary['registry_new']}")
    print(f"  Registry — modified:      {summary['registry_modified']}")
    print(f"  Registry — unchanged:     {summary['registry_unchanged']}")
    print(f"  Registry — tombstoned:    {summary['registry_tombstoned']}")
    print(f"  GC deleted:               {summary['gc_deleted']}")
    print("-" * 60)
    print(f"  Elapsed time:             {summary['elapsed_seconds']}s")
    print("=" * 60 + "\n")


def main() -> None:
    """CLI entry point for the ingestion runner."""
    parser = argparse.ArgumentParser(
        description="Run the ALO RAG ingestion pipeline",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Root data directory (default: data)",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="ChromaDB persistence directory (default: in-memory)",
    )
    parser.add_argument(
        "--registry-db",
        type=str,
        default=None,
        help="Path to the SQLite registry database (default: <data-dir>/registry.db)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run_ingestion(
        data_dir=args.data_dir,
        persist_dir=args.persist_dir,
        registry_db_path=args.registry_db,
    )


if __name__ == "__main__":
    main()
