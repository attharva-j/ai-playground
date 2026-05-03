"""Reciprocal Rank Fusion (RRF) for merging dense and sparse retrieval results.

Merges ranked lists from dense (vector) and sparse (BM25) retrieval using
the formula ``score(d) = Σ 1/(rank_i(d) + k)`` where ``rank_i(d)`` is the
1-based rank of document *d* in result list *i* and *k* is a smoothing
constant (default 60, per the original RRF paper).

Requirements: 8.2
"""

from __future__ import annotations

import logging

from src.models import RetrievedChunk

logger = logging.getLogger(__name__)


class RRFFuser:
    """Reciprocal Rank Fusion: merges ranked lists from dense and sparse retrieval.

    Parameters
    ----------
    k:
        Smoothing constant for the RRF formula.  The standard value from
        the original paper is 60.
    """

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse(
        self,
        dense_results: list[RetrievedChunk],
        sparse_results: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Merge *dense_results* and *sparse_results* using RRF.

        For each chunk appearing in either list the RRF score is computed
        as ``1 / (rank + k)`` where *rank* is 1-based.  Chunks appearing
        in both lists have their scores summed.

        Returns a list of :class:`RetrievedChunk` sorted by descending
        combined RRF score with ``source="fused"``.
        """
        # Map chunk_id → (best Chunk object, cumulative RRF score)
        scores: dict[str, float] = {}
        chunk_map: dict[str, RetrievedChunk] = {}

        # Score dense results
        for rank_0, rc in enumerate(dense_results):
            rank = rank_0 + 1  # 1-based
            rrf_score = 1.0 / (rank + self.k)
            cid = rc.chunk.chunk_id

            scores[cid] = scores.get(cid, 0.0) + rrf_score
            # Keep the first occurrence (highest-ranked) as the representative chunk
            if cid not in chunk_map:
                chunk_map[cid] = rc

        # Score sparse results
        for rank_0, rc in enumerate(sparse_results):
            rank = rank_0 + 1
            rrf_score = 1.0 / (rank + self.k)
            cid = rc.chunk.chunk_id

            scores[cid] = scores.get(cid, 0.0) + rrf_score
            if cid not in chunk_map:
                chunk_map[cid] = rc

        # Build fused result list sorted by descending RRF score
        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

        fused: list[RetrievedChunk] = []
        for cid in sorted_ids:
            original = chunk_map[cid]
            fused.append(
                RetrievedChunk(
                    chunk=original.chunk,
                    score=scores[cid],
                    source="fused",
                )
            )

        logger.debug(
            "RRFFuser: merged %d dense + %d sparse → %d fused results",
            len(dense_results),
            len(sparse_results),
            len(fused),
        )
        return fused
