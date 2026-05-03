"""Vector store, BM25 index, and index builder for the ALO RAG system.

Components:
- VectorStore: ChromaDB wrapper for dense vector storage and retrieval.
- BM25Builder / BM25Index: rank-bm25 wrapper for sparse keyword retrieval.
- IndexBuilder: orchestrates building both stores from a list of chunks.

Requirements: 3.2, 3.3, 3.5
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import chromadb

from src.models import Chunk, ChunkMetadata, RetrievedChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Index build result
# ---------------------------------------------------------------------------


@dataclass
class IndexBuildResult:
    """Summary returned by :meth:`IndexBuilder.build`."""

    chunks_indexed: int
    chunks_skipped: int  # validation failures


# ---------------------------------------------------------------------------
# VectorStore — ChromaDB wrapper
# ---------------------------------------------------------------------------


class VectorStore:
    """ChromaDB wrapper for dense vector storage and retrieval.

    Supports ``add()``, ``query()`` with optional metadata filters, and
    ``verify_chunk()`` for round-trip integrity checks (R3.5).
    """

    def __init__(
        self,
        collection_name: str = "alo_rag",
        persist_directory: str | None = None,
    ) -> None:
        if persist_directory:
            self._client = chromadb.PersistentClient(path=persist_directory)
        else:
            self._client = chromadb.Client()

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_name = collection_name

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Add *chunks* with their *embeddings* to the vector store.

        Each chunk's metadata is flattened into a string-keyed dict
        suitable for ChromaDB's metadata storage.
        """
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [self._flatten_metadata(c.metadata) for c in chunks]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info("VectorStore: added %d chunks", len(chunks))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def query(
        self,
        embedding: list[float],
        n_results: int = 12,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Query the vector store and return ranked :class:`RetrievedChunk` results.

        Parameters
        ----------
        embedding:
            The query embedding vector.
        n_results:
            Maximum number of results to return.
        metadata_filter:
            Optional ChromaDB ``where`` filter dict.
        """
        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": n_results,
        }
        if metadata_filter:
            kwargs["where"] = metadata_filter

        results = self._collection.query(**kwargs)

        retrieved: list[RetrievedChunk] = []
        if not results or not results.get("ids"):
            return retrieved

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [None] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for chunk_id, doc_text, meta, distance in zip(
            ids, documents, metadatas, distances
        ):
            # ChromaDB returns cosine *distance*; convert to similarity score
            score = 1.0 - distance

            chunk = Chunk(
                chunk_id=chunk_id,
                text=doc_text or "",
                metadata=self._unflatten_metadata(meta),
                source_document=meta.get("source_document", ""),
            )
            retrieved.append(
                RetrievedChunk(chunk=chunk, score=score, source="dense")
            )

        return retrieved

    # ------------------------------------------------------------------
    # Integrity verification (R3.5)
    # ------------------------------------------------------------------

    def verify_chunk(self, chunk_id: str, expected_text: str) -> bool:
        """Round-trip integrity check.

        Retrieves the stored document text by *chunk_id* and returns
        ``True`` iff it matches *expected_text* exactly.
        """
        result = self._collection.get(ids=[chunk_id], include=["documents"])
        if not result or not result.get("documents") or not result["documents"]:
            return False

        stored_text = result["documents"][0]
        return stored_text == expected_text

    def delete(self, ids: list[str]) -> None:
        """Remove chunks from the vector store by ID."""
        try:
            self._collection.delete(ids=ids)
        except Exception:
            logger.warning("VectorStore.delete() — failed for ids=%s", ids)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_metadata(meta: ChunkMetadata) -> dict[str, str]:
        """Convert a :class:`ChunkMetadata` to a flat string dict for ChromaDB."""
        flat: dict[str, str] = {"domain": meta.domain}
        if meta.product_id is not None:
            flat["product_id"] = meta.product_id
        if meta.category is not None:
            flat["category"] = meta.category
        if meta.fabric_type is not None:
            flat["fabric_type"] = meta.fabric_type
        if meta.policy_type is not None:
            flat["policy_type"] = meta.policy_type
        if meta.effective_date is not None:
            flat["effective_date"] = meta.effective_date
        return flat

    @staticmethod
    def _unflatten_metadata(meta: dict[str, Any]) -> ChunkMetadata:
        """Reconstruct a :class:`ChunkMetadata` from a flat dict."""
        return ChunkMetadata(
            domain=meta.get("domain", ""),
            product_id=meta.get("product_id"),
            category=meta.get("category"),
            fabric_type=meta.get("fabric_type"),
            policy_type=meta.get("policy_type"),
            effective_date=meta.get("effective_date"),
        )


# ---------------------------------------------------------------------------
# BM25 Index — rank-bm25 wrapper
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


class BM25Index:
    """Wrapper around rank-bm25 for sparse keyword retrieval."""

    def __init__(
        self,
        bm25: Any,
        chunks: list[Chunk],
        tokenized_corpus: list[list[str]],
    ) -> None:
        self._bm25 = bm25
        self._chunks = chunks
        self._tokenized_corpus = tokenized_corpus

    def query(
        self,
        query_text: str,
        n_results: int = 8,
    ) -> list[RetrievedChunk]:
        """Return the top-*n_results* chunks ranked by BM25 score."""
        tokenized_query = _tokenize(query_text)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)

        # Get indices sorted by descending score
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:n_results]

        results: list[RetrievedChunk] = []
        for idx in ranked_indices:
            if scores[idx] <= 0:
                break
            results.append(
                RetrievedChunk(
                    chunk=self._chunks[idx],
                    score=float(scores[idx]),
                    source="sparse",
                )
            )

        return results


class BM25Builder:
    """Builds a :class:`BM25Index` from a list of chunks."""

    def build(self, chunks: list[Chunk]) -> BM25Index:
        """Tokenize *chunks* and construct a BM25 index."""
        from rank_bm25 import BM25Okapi  # noqa: WPS433

        tokenized_corpus = [_tokenize(c.text) for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        logger.info("BM25Builder: indexed %d chunks", len(chunks))
        return BM25Index(bm25=bm25, chunks=chunks, tokenized_corpus=tokenized_corpus)


# ---------------------------------------------------------------------------
# IndexBuilder — orchestrator
# ---------------------------------------------------------------------------


class IndexBuilder:
    """Orchestrates building both ChromaDB and BM25 indexes from chunks.

    Accepts pre-computed embeddings and delegates storage to the
    :class:`VectorStore` and :class:`BM25Builder`.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_builder: BM25Builder,
    ) -> None:
        self._vector_store = vector_store
        self._bm25_builder = bm25_builder

    def build(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> tuple[IndexBuildResult, BM25Index]:
        """Build both indexes and return ``(result, bm25_index)``.

        Parameters
        ----------
        chunks:
            The document chunks to index.
        embeddings:
            Pre-computed dense embeddings aligned with *chunks*.

        Returns
        -------
        tuple:
            A :class:`IndexBuildResult` with counts and the constructed
            :class:`BM25Index` for sparse retrieval.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must have the same length"
            )

        # Build dense index
        self._vector_store.add(chunks, embeddings)

        # Build sparse index
        bm25_index = self._bm25_builder.build(chunks)

        result = IndexBuildResult(
            chunks_indexed=len(chunks),
            chunks_skipped=0,
        )
        logger.info(
            "IndexBuilder: indexed %d chunks into vector store and BM25",
            result.chunks_indexed,
        )
        return result, bm25_index
