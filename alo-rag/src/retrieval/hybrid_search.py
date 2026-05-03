"""Hybrid search combining dense and sparse retrieval with fusion and reranking.

Executes dense (ChromaDB) and sparse (BM25) searches in parallel, merges
results via Reciprocal Rank Fusion, applies optional metadata post-filters,
and reranks the top candidates with a cross-encoder model.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.ingestion.index_builder import BM25Index, VectorStore
from src.models import RetrievedChunk
from src.retrieval.fusion import RRFFuser
from src.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class HybridSearch:
    """Executes parallel dense + sparse search and fuses results.

    The search pipeline:
    1. Run dense similarity search (top-*dense_k*) and BM25 sparse search
       (top-*sparse_k*) in parallel threads.
    2. Merge both result lists using :class:`RRFFuser`.
    3. Optionally apply metadata post-filters to de-prioritise irrelevant
       chunks (R8.4).
    4. Rerank the top candidates with :class:`CrossEncoderReranker` and
       return the final top-*final_k* chunks.

    Parameters
    ----------
    vector_store:
        The ChromaDB vector store for dense retrieval.
    bm25_index:
        The BM25 index for sparse keyword retrieval.
    rrf_fuser:
        The RRF fusion component.
    reranker:
        The cross-encoder reranker.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        rrf_fuser: RRFFuser,
        reranker: CrossEncoderReranker,
    ) -> None:
        self._vector_store = vector_store
        self._bm25_index = bm25_index
        self._rrf_fuser = rrf_fuser
        self._reranker = reranker

    def search(
        self,
        query_embedding: list[float],
        query_text: str,
        metadata_filter: dict[str, Any] | None = None,
        dense_k: int = 12,
        sparse_k: int = 8,
        final_k: int = 5,
        rerank_min_score: float = -3.0,
    ) -> list[RetrievedChunk]:
        """Execute hybrid search and return the top-*final_k* reranked chunks.

        Parameters
        ----------
        query_embedding:
            Dense embedding of the query (or HyDE hypothetical answer).
        query_text:
            Raw query text used for BM25 sparse search and cross-encoder
            reranking.
        metadata_filter:
            Optional ChromaDB ``where`` filter applied to the dense search.
            Also used for post-filtering sparse results (R8.4).
        dense_k:
            Number of results to retrieve from the dense store.
        sparse_k:
            Number of results to retrieve from the BM25 index.
        final_k:
            Number of final results after reranking.

        Returns
        -------
        list[RetrievedChunk]
            Up to *final_k* chunks sorted by cross-encoder relevance score.
        """
        # 1. Execute dense and sparse searches in parallel
        dense_results, sparse_results = self._parallel_search(
            query_embedding=query_embedding,
            query_text=query_text,
            metadata_filter=metadata_filter,
            dense_k=dense_k,
            sparse_k=sparse_k,
        )

        logger.debug(
            "HybridSearch: dense=%d, sparse=%d results",
            len(dense_results),
            len(sparse_results),
        )

        # 2. Fuse results via RRF
        fused = self._rrf_fuser.fuse(dense_results, sparse_results)

        # 3. Apply metadata post-filters to de-prioritise irrelevant chunks
        if metadata_filter:
            fused = self._apply_metadata_post_filter(fused, metadata_filter)

        # 4. Rerank top candidates with cross-encoder
        # Feed more candidates than final_k to give the reranker a good pool
        rerank_pool_size = min(len(fused), max(final_k * 3, 15))
        reranked = self._reranker.rerank(
            query=query_text,
            chunks=fused[:rerank_pool_size],
            top_k=final_k,
            min_score=rerank_min_score,
        )

        logger.debug(
            "HybridSearch: fused=%d → reranked top-%d",
            len(fused),
            len(reranked),
        )
        return reranked

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parallel_search(
        self,
        query_embedding: list[float],
        query_text: str,
        metadata_filter: dict[str, Any] | None,
        dense_k: int,
        sparse_k: int,
    ) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
        """Run dense and sparse searches in parallel threads."""
        dense_results: list[RetrievedChunk] = []
        sparse_results: list[RetrievedChunk] = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_dense = executor.submit(
                self._vector_store.query,
                embedding=query_embedding,
                n_results=dense_k,
                metadata_filter=metadata_filter,
            )
            future_sparse = executor.submit(
                self._bm25_index.query,
                query_text=query_text,
                n_results=sparse_k,
            )

            for future in as_completed([future_dense, future_sparse]):
                try:
                    result = future.result()
                    if future is future_dense:
                        dense_results = result
                    else:
                        sparse_results = result
                except Exception:
                    logger.exception(
                        "HybridSearch: error in parallel retrieval"
                    )

        return dense_results, sparse_results

    @staticmethod
    def _apply_metadata_post_filter(
        chunks: list[RetrievedChunk],
        metadata_filter: dict[str, Any],
    ) -> list[RetrievedChunk]:
        """De-prioritise chunks that don't match the metadata filter.

        Matching chunks keep their original position; non-matching chunks
        are moved to the end of the list (rather than removed entirely)
        so the reranker still has a reasonable candidate pool.
        """
        matching: list[RetrievedChunk] = []
        non_matching: list[RetrievedChunk] = []

        for rc in chunks:
            if _chunk_matches_filter(rc, metadata_filter):
                matching.append(rc)
            else:
                non_matching.append(rc)

        return matching + non_matching


def _chunk_matches_filter(
    rc: RetrievedChunk,
    metadata_filter: dict[str, Any],
) -> bool:
    """Check whether a chunk's metadata satisfies the filter criteria.

    Supports simple equality checks on metadata fields.  ChromaDB
    ``where`` filters can be nested (``$and``, ``$or``, etc.) but for
    post-filtering we only handle flat key-value equality — the most
    common case for domain-based filtering.
    """
    meta = rc.chunk.metadata
    for key, value in metadata_filter.items():
        # Skip ChromaDB operator keys
        if key.startswith("$"):
            continue
        actual = getattr(meta, key, None)
        if actual != value:
            return False
    return True
