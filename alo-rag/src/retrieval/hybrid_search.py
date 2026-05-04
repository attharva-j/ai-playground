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
from src.models import Chunk, RetrievedChunk
from src.retrieval.fusion import RRFFuser
from src.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


_KNOWN_FABRICS = {
    "airlift": "Airlift",
    "airbrush": "Airbrush",
    "alosoft": "Alosoft",
    "softsculpt": "Alo Softsculpt",
    "conquer": "Conquer",
    "vapor": "Alo Vapor",
}

_POLICY_TAG_SIGNALS: dict[str, tuple[str, ...]] = {
    "community_discount": (
        "military discount",
        "community discount",
        "student discount",
        "healthcare discount",
        "first responder",
        "govx",
    ),
    "sale_restriction": (
        "aloversary",
        "cyber monday",
        "sale",
        "promotional event",
        "sale period",
    ),
    "promo_stacking": (
        "stack",
        "combine",
        "combined",
        "coupon",
        "discount during",
    ),
    "final_sale": (
        "final sale",
        "return sale item",
        "return discounted",
    ),
    "return_window": (
        "return window",
        "within 30 days",
        "eligible for return",
    ),
    "exchange_policy": (
        "exchange",
        "larger size",
        "smaller size",
        "different size",
        "size exchange",
    ),
}


def _detect_policy_tags(query_text: str) -> set[str]:
    q = query_text.lower()
    tags: set[str] = set()
    for tag, signals in _POLICY_TAG_SIGNALS.items():
        if any(signal in q for signal in signals):
            tags.add(tag)
    return tags

def _detect_fabrics(query_text: str) -> list[str]:
    q = query_text.lower()
    return [canonical for key, canonical in _KNOWN_FABRICS.items() if key in q]


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
        self._policy_chunks_by_tag = self._build_policy_tag_index()
    
    def _build_policy_tag_index(self) -> dict[str, list[Chunk]]:
        """Build an in-memory index from policy tag to chunks."""
        by_tag: dict[str, list[Chunk]] = {}

        for chunk in getattr(self._bm25_index, "chunks", []):
            if chunk.metadata.domain != "policy":
                continue
            for tag in chunk.metadata.policy_tags:
                by_tag.setdefault(tag, []).append(chunk)

        return by_tag

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
        
        # Fabric/entity boost for comparison queries.
        detected_fabrics = _detect_fabrics(query_text)
        if len(detected_fabrics) >= 1:
            boosted: list[RetrievedChunk] = []
            for rc in fused:
                meta = rc.chunk.metadata
                if (
                    meta.domain == "product"
                    and meta.entity_type == "fabric"
                    and meta.fabric_name in detected_fabrics
                ):
                    boosted.append(
                        RetrievedChunk(
                            chunk=rc.chunk,
                            score=rc.score + 1.0,
                            source=rc.source,
                        )
                    )
                else:
                    boosted.append(rc)

            fused = sorted(boosted, key=lambda rc: rc.score, reverse=True)

        # Add companion policy chunks for multi-clause policy questions.
        query_policy_tags = _detect_policy_tags(query_text)
        if query_policy_tags:
            existing_ids = {rc.chunk.chunk_id for rc in fused}
            companion_chunks: list[RetrievedChunk] = []

            # If a query combines community discount + sale/promo language,
            # both policy sections are needed for a complete answer.
            companion_tags = set(query_policy_tags)
            if "community_discount" in query_policy_tags:
                companion_tags.update({"sale_restriction", "promo_stacking"})
            if "sale_restriction" in query_policy_tags:
                companion_tags.update({"community_discount", "promo_stacking"})
            if "final_sale" in query_policy_tags:
                companion_tags.update({"return_window"})
            if "exchange_policy" in query_policy_tags:
                companion_tags.update({"return_window", "final_sale"})

            for tag in companion_tags:
                for chunk in self._policy_chunks_by_tag.get(tag, []):
                    if chunk.chunk_id not in existing_ids:
                        companion_chunks.append(
                            RetrievedChunk(
                                chunk=chunk,
                                score=0.25,
                                source="companion",
                            )
                        )
                        existing_ids.add(chunk.chunk_id)

            if companion_chunks:
                fused = fused + companion_chunks

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
        """Apply hard metadata filtering with a safe fallback.

        For clear single-domain queries, irrelevant-domain chunks should not
        be reranked or passed to generation. If filtering removes everything,
        fall back to the original set so the system can still attempt a low-
        confidence answer or trigger answerability handling.
        """
        matching = [
            rc for rc in chunks
            if _chunk_matches_filter(rc, metadata_filter)
        ]

        return matching if matching else chunks


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
