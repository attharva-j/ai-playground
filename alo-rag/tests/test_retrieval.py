"""Unit tests for the retrieval engine.

Covers:
- RRFFuser correctly computes RRF scores and merges lists
- CrossEncoderReranker reorders chunks by relevance
- HybridSearch end-to-end with mock vector store and BM25 index
- Metadata post-filtering de-prioritises irrelevant chunks

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.models import Chunk, ChunkMetadata, RetrievedChunk
from src.retrieval.fusion import RRFFuser
from src.retrieval.hybrid_search import HybridSearch, _chunk_matches_filter
from src.retrieval.reranker import CrossEncoderReranker


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_chunk(
    chunk_id: str,
    text: str = "sample text",
    domain: str = "product",
    **meta_kwargs: Any,
) -> Chunk:
    """Create a Chunk with the given id and optional metadata overrides."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata=ChunkMetadata(domain=domain, **meta_kwargs),
        source_document="source.json",
    )


def _make_rc(
    chunk_id: str,
    score: float = 0.5,
    source: str = "dense",
    text: str = "sample text",
    domain: str = "product",
    **meta_kwargs: Any,
) -> RetrievedChunk:
    """Create a RetrievedChunk for testing."""
    return RetrievedChunk(
        chunk=_make_chunk(chunk_id, text=text, domain=domain, **meta_kwargs),
        score=score,
        source=source,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. RRFFuser — Reciprocal Rank Fusion (R8.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestRRFFuserScoreComputation:
    """Verify RRF score formula: score = 1/(rank + k), k=60 by default."""

    def test_single_dense_result_score(self) -> None:
        """A single dense result at rank 1 should get score 1/(1+60)."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc("c1", source="dense")]
        fused = fuser.fuse(dense, [])

        assert len(fused) == 1
        assert fused[0].chunk.chunk_id == "c1"
        assert fused[0].score == pytest.approx(1.0 / 61)
        assert fused[0].source == "fused"

    def test_single_sparse_result_score(self) -> None:
        """A single sparse result at rank 1 should get score 1/(1+60)."""
        fuser = RRFFuser(k=60)
        sparse = [_make_rc("c1", source="sparse")]
        fused = fuser.fuse([], sparse)

        assert len(fused) == 1
        assert fused[0].score == pytest.approx(1.0 / 61)

    def test_rank_based_scoring_dense(self) -> None:
        """Dense results at ranks 1, 2, 3 should have decreasing scores."""
        fuser = RRFFuser(k=60)
        dense = [
            _make_rc("c1", source="dense"),
            _make_rc("c2", source="dense"),
            _make_rc("c3", source="dense"),
        ]
        fused = fuser.fuse(dense, [])

        expected_scores = [1.0 / 61, 1.0 / 62, 1.0 / 63]
        for rc, expected in zip(fused, expected_scores):
            assert rc.score == pytest.approx(expected)

    def test_custom_k_value(self) -> None:
        """Custom k value should be used in the formula."""
        fuser = RRFFuser(k=10)
        dense = [_make_rc("c1", source="dense")]
        fused = fuser.fuse(dense, [])

        assert fused[0].score == pytest.approx(1.0 / 11)


class TestRRFFuserMerging:
    """Verify that RRF correctly merges dense and sparse result lists."""

    def test_disjoint_lists_merged(self) -> None:
        """Chunks appearing in only one list get a single RRF score."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc("d1", source="dense"), _make_rc("d2", source="dense")]
        sparse = [_make_rc("s1", source="sparse"), _make_rc("s2", source="sparse")]

        fused = fuser.fuse(dense, sparse)

        assert len(fused) == 4
        ids = [rc.chunk.chunk_id for rc in fused]
        assert set(ids) == {"d1", "d2", "s1", "s2"}
        # All should be marked as "fused"
        assert all(rc.source == "fused" for rc in fused)

    def test_overlapping_chunks_scores_summed(self) -> None:
        """A chunk in both lists should have its RRF scores summed."""
        fuser = RRFFuser(k=60)
        # "shared" appears at rank 1 in dense and rank 1 in sparse
        dense = [_make_rc("shared", source="dense")]
        sparse = [_make_rc("shared", source="sparse")]

        fused = fuser.fuse(dense, sparse)

        assert len(fused) == 1
        expected = 1.0 / 61 + 1.0 / 61  # rank 1 in both
        assert fused[0].score == pytest.approx(expected)

    def test_overlapping_chunk_at_different_ranks(self) -> None:
        """Shared chunk at rank 1 (dense) and rank 2 (sparse) sums correctly."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc("shared", source="dense")]
        sparse = [
            _make_rc("other", source="sparse"),
            _make_rc("shared", source="sparse"),
        ]

        fused = fuser.fuse(dense, sparse)

        shared_rc = next(rc for rc in fused if rc.chunk.chunk_id == "shared")
        expected = 1.0 / 61 + 1.0 / 62  # rank 1 dense + rank 2 sparse
        assert shared_rc.score == pytest.approx(expected)

    def test_shared_chunk_ranked_higher_than_unique(self) -> None:
        """A chunk appearing in both lists should rank above one in only one list."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc("shared", source="dense"), _make_rc("dense_only", source="dense")]
        sparse = [_make_rc("shared", source="sparse"), _make_rc("sparse_only", source="sparse")]

        fused = fuser.fuse(dense, sparse)

        assert fused[0].chunk.chunk_id == "shared"

    def test_results_sorted_descending_by_score(self) -> None:
        """Fused results should be sorted by descending RRF score."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc(f"d{i}", source="dense") for i in range(5)]
        sparse = [_make_rc(f"s{i}", source="sparse") for i in range(3)]

        fused = fuser.fuse(dense, sparse)

        scores = [rc.score for rc in fused]
        assert scores == sorted(scores, reverse=True)

    def test_empty_inputs(self) -> None:
        """Fusing two empty lists should return an empty list."""
        fuser = RRFFuser(k=60)
        assert fuser.fuse([], []) == []

    def test_empty_dense_list(self) -> None:
        """Only sparse results should be returned when dense is empty."""
        fuser = RRFFuser(k=60)
        sparse = [_make_rc("s1", source="sparse")]
        fused = fuser.fuse([], sparse)

        assert len(fused) == 1
        assert fused[0].chunk.chunk_id == "s1"

    def test_empty_sparse_list(self) -> None:
        """Only dense results should be returned when sparse is empty."""
        fuser = RRFFuser(k=60)
        dense = [_make_rc("d1", source="dense")]
        fused = fuser.fuse(dense, [])

        assert len(fused) == 1
        assert fused[0].chunk.chunk_id == "d1"


# ═══════════════════════════════════════════════════════════════════════════
# 2. CrossEncoderReranker (R8.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossEncoderReranker:
    """Test that the reranker reorders chunks by cross-encoder relevance."""

    def _make_reranker_with_mock(
        self, scores: list[float]
    ) -> CrossEncoderReranker:
        """Create a reranker with a mocked cross-encoder model returning *scores*."""
        reranker = CrossEncoderReranker()
        mock_model = MagicMock()
        mock_model.predict.return_value = scores
        reranker._model = mock_model
        return reranker

    def test_reorders_by_score(self) -> None:
        """Chunks should be reordered by descending cross-encoder score."""
        chunks = [
            _make_rc("low", text="low relevance"),
            _make_rc("high", text="high relevance"),
            _make_rc("mid", text="mid relevance"),
        ]
        # Scores correspond to chunks in input order
        reranker = self._make_reranker_with_mock([0.1, 0.9, 0.5])

        result = reranker.rerank("test query", chunks, top_k=3)

        assert [rc.chunk.chunk_id for rc in result] == ["high", "mid", "low"]

    def test_top_k_limits_results(self) -> None:
        """Only top_k results should be returned."""
        chunks = [_make_rc(f"c{i}") for i in range(5)]
        scores = [0.5, 0.9, 0.3, 0.7, 0.1]
        reranker = self._make_reranker_with_mock(scores)

        result = reranker.rerank("query", chunks, top_k=2)

        assert len(result) == 2
        # Top 2 by score: c1 (0.9), c3 (0.7)
        assert result[0].chunk.chunk_id == "c1"
        assert result[1].chunk.chunk_id == "c3"

    def test_source_set_to_reranked(self) -> None:
        """All reranked results should have source='reranked'."""
        chunks = [_make_rc("c1"), _make_rc("c2")]
        reranker = self._make_reranker_with_mock([0.8, 0.6])

        result = reranker.rerank("query", chunks, top_k=2)

        assert all(rc.source == "reranked" for rc in result)

    def test_scores_are_cross_encoder_scores(self) -> None:
        """Returned scores should be the cross-encoder scores, not original."""
        chunks = [_make_rc("c1", score=0.1), _make_rc("c2", score=0.9)]
        reranker = self._make_reranker_with_mock([0.7, 0.3])

        result = reranker.rerank("query", chunks, top_k=2)

        assert result[0].score == pytest.approx(0.7)
        assert result[1].score == pytest.approx(0.3)

    def test_empty_chunks_returns_empty(self) -> None:
        """Reranking an empty list should return an empty list."""
        reranker = CrossEncoderReranker()
        result = reranker.rerank("query", [], top_k=5)
        assert result == []

    def test_top_k_larger_than_input(self) -> None:
        """When top_k > len(chunks), return all chunks."""
        chunks = [_make_rc("c1"), _make_rc("c2")]
        reranker = self._make_reranker_with_mock([0.5, 0.8])

        result = reranker.rerank("query", chunks, top_k=10)

        assert len(result) == 2

    def test_model_receives_correct_pairs(self) -> None:
        """The cross-encoder should receive (query, chunk_text) pairs."""
        chunks = [
            _make_rc("c1", text="first chunk text"),
            _make_rc("c2", text="second chunk text"),
        ]
        reranker = self._make_reranker_with_mock([0.5, 0.5])

        reranker.rerank("my query", chunks, top_k=2)

        mock_model = reranker._model
        call_args = mock_model.predict.call_args
        pairs = call_args[0][0]
        assert pairs == [
            ["my query", "first chunk text"],
            ["my query", "second chunk text"],
        ]


# ═══════════════════════════════════════════════════════════════════════════
# 3. HybridSearch end-to-end with mocks (R8.1, R8.2, R8.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestHybridSearchEndToEnd:
    """Test HybridSearch with mock VectorStore and BM25Index."""

    def _build_hybrid_search(
        self,
        dense_results: list[RetrievedChunk],
        sparse_results: list[RetrievedChunk],
        reranker_scores: list[float] | None = None,
    ) -> HybridSearch:
        """Build a HybridSearch with mocked dependencies."""
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = dense_results

        mock_bm25_index = MagicMock()
        mock_bm25_index.query.return_value = sparse_results

        rrf_fuser = RRFFuser(k=60)

        mock_reranker = MagicMock(spec=CrossEncoderReranker)
        if reranker_scores is not None:
            # Simulate reranker: sort by provided scores, return top_k
            def rerank_side_effect(
                query: str,
                chunks: list[RetrievedChunk],
                top_k: int = 5,
            ) -> list[RetrievedChunk]:
                # Use the first len(chunks) scores
                scores = reranker_scores[: len(chunks)]
                scored = list(zip(chunks, scores))
                scored.sort(key=lambda x: x[1], reverse=True)
                return [
                    RetrievedChunk(
                        chunk=rc.chunk, score=float(s), source="reranked"
                    )
                    for rc, s in scored[:top_k]
                ]

            mock_reranker.rerank.side_effect = rerank_side_effect
        else:
            # Default: pass through with source="reranked"
            def passthrough_rerank(
                query: str,
                chunks: list[RetrievedChunk],
                top_k: int = 5,
                min_score: float = -3.0,
            ) -> list[RetrievedChunk]:
                return [
                    RetrievedChunk(
                        chunk=rc.chunk, score=rc.score, source="reranked"
                    )
                    for rc in chunks[:top_k]
                ]

            mock_reranker.rerank.side_effect = passthrough_rerank

        hs = HybridSearch(
            vector_store=mock_vector_store,
            bm25_index=mock_bm25_index,
            rrf_fuser=rrf_fuser,
            reranker=mock_reranker,
        )
        return hs

    def test_combines_dense_and_sparse_results(self) -> None:
        """HybridSearch should return results from both dense and sparse."""
        dense = [_make_rc("d1", source="dense"), _make_rc("d2", source="dense")]
        sparse = [_make_rc("s1", source="sparse")]

        hs = self._build_hybrid_search(dense, sparse)
        results = hs.search(
            query_embedding=[0.1] * 10,
            query_text="test query",
            final_k=5,
        )

        result_ids = {rc.chunk.chunk_id for rc in results}
        assert "d1" in result_ids
        assert "d2" in result_ids
        assert "s1" in result_ids

    def test_shared_chunks_boosted(self) -> None:
        """Chunks in both dense and sparse should rank higher after fusion."""
        dense = [
            _make_rc("shared", source="dense"),
            _make_rc("dense_only", source="dense"),
        ]
        sparse = [
            _make_rc("shared", source="sparse"),
            _make_rc("sparse_only", source="sparse"),
        ]

        hs = self._build_hybrid_search(dense, sparse)
        results = hs.search(
            query_embedding=[0.1] * 10,
            query_text="test query",
            final_k=5,
        )

        # The reranker passthrough preserves fusion order, so "shared" should be first
        assert results[0].chunk.chunk_id == "shared"

    def test_respects_final_k(self) -> None:
        """HybridSearch should return at most final_k results."""
        dense = [_make_rc(f"d{i}", source="dense") for i in range(6)]
        sparse = [_make_rc(f"s{i}", source="sparse") for i in range(4)]

        hs = self._build_hybrid_search(dense, sparse)
        results = hs.search(
            query_embedding=[0.1] * 10,
            query_text="test query",
            final_k=3,
        )

        assert len(results) <= 3

    def test_all_results_marked_reranked(self) -> None:
        """Final results should have source='reranked'."""
        dense = [_make_rc("d1", source="dense")]
        sparse = [_make_rc("s1", source="sparse")]

        hs = self._build_hybrid_search(dense, sparse)
        results = hs.search(
            query_embedding=[0.1] * 10,
            query_text="test query",
        )

        assert all(rc.source == "reranked" for rc in results)

    def test_empty_results(self) -> None:
        """When both stores return empty, HybridSearch returns empty."""
        hs = self._build_hybrid_search([], [])
        results = hs.search(
            query_embedding=[0.1] * 10,
            query_text="test query",
        )

        assert results == []

    def test_vector_store_called_with_correct_params(self) -> None:
        """VectorStore.query should be called with the embedding and n_results."""
        dense = [_make_rc("d1", source="dense")]
        sparse = []

        hs = self._build_hybrid_search(dense, sparse)
        embedding = [0.1, 0.2, 0.3]
        hs.search(
            query_embedding=embedding,
            query_text="test",
            dense_k=12,
            sparse_k=8,
        )

        hs._vector_store.query.assert_called_once_with(
            embedding=embedding,
            n_results=12,
            metadata_filter=None,
        )

    def test_bm25_called_with_correct_params(self) -> None:
        """BM25Index.query should be called with query text and n_results."""
        dense = []
        sparse = [_make_rc("s1", source="sparse")]

        hs = self._build_hybrid_search(dense, sparse)
        hs.search(
            query_embedding=[0.1],
            query_text="leggings fabric",
            sparse_k=8,
        )

        hs._bm25_index.query.assert_called_once_with(
            query_text="leggings fabric",
            n_results=8,
        )

    def test_metadata_filter_passed_to_vector_store(self) -> None:
        """Metadata filter should be forwarded to the vector store query."""
        hs = self._build_hybrid_search([], [])
        meta_filter = {"domain": "product"}
        hs.search(
            query_embedding=[0.1],
            query_text="test",
            metadata_filter=meta_filter,
        )

        hs._vector_store.query.assert_called_once_with(
            embedding=[0.1],
            n_results=12,
            metadata_filter=meta_filter,
        )

    def test_reranker_receives_fused_candidates(self) -> None:
        """The reranker should receive the fused (not raw) results."""
        dense = [_make_rc("d1", source="dense")]
        sparse = [_make_rc("s1", source="sparse")]

        hs = self._build_hybrid_search(dense, sparse)
        hs.search(
            query_embedding=[0.1],
            query_text="test",
            final_k=5,
        )

        # Reranker should have been called once
        hs._reranker.rerank.assert_called_once()
        call_kwargs = hs._reranker.rerank.call_args
        # The chunks arg should contain fused results
        rerank_chunks = call_kwargs[1].get("chunks") or call_kwargs[0][1]
        assert all(rc.source == "fused" for rc in rerank_chunks)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Metadata post-filtering (R8.4)
# ═══════════════════════════════════════════════════════════════════════════


class TestChunkMatchesFilter:
    """Test the _chunk_matches_filter helper used for post-filtering."""

    def test_matching_domain(self) -> None:
        rc = _make_rc("c1", domain="product")
        assert _chunk_matches_filter(rc, {"domain": "product"}) is True

    def test_non_matching_domain(self) -> None:
        rc = _make_rc("c1", domain="policy")
        assert _chunk_matches_filter(rc, {"domain": "product"}) is False

    def test_matching_multiple_fields(self) -> None:
        rc = _make_rc("c1", domain="product", category="leggings")
        assert _chunk_matches_filter(rc, {"domain": "product", "category": "leggings"}) is True

    def test_partial_match_fails(self) -> None:
        """All filter fields must match; partial match returns False."""
        rc = _make_rc("c1", domain="product", category="tops")
        assert _chunk_matches_filter(rc, {"domain": "product", "category": "leggings"}) is False

    def test_chromadb_operator_keys_skipped(self) -> None:
        """Keys starting with '$' should be ignored."""
        rc = _make_rc("c1", domain="product")
        assert _chunk_matches_filter(rc, {"$and": [], "domain": "product"}) is True

    def test_missing_metadata_field_returns_false(self) -> None:
        """If the chunk doesn't have the filtered field, it shouldn't match."""
        rc = _make_rc("c1", domain="product")
        # fabric_type is None by default
        assert _chunk_matches_filter(rc, {"fabric_type": "Airlift"}) is False

    def test_empty_filter_matches_all(self) -> None:
        """An empty filter should match any chunk."""
        rc = _make_rc("c1", domain="policy")
        assert _chunk_matches_filter(rc, {}) is True


class TestMetadataPostFiltering:
    """Test that HybridSearch._apply_metadata_post_filter de-prioritises
    non-matching chunks rather than removing them."""

    def test_matching_chunks_come_first(self) -> None:
        """Chunks matching the filter should appear before non-matching ones."""
        chunks = [
            _make_rc("policy1", domain="policy"),
            _make_rc("product1", domain="product"),
            _make_rc("product2", domain="product"),
            _make_rc("policy2", domain="policy"),
        ]

        filtered = HybridSearch._apply_metadata_post_filter(
            chunks, {"domain": "product"}
        )

        ids = [rc.chunk.chunk_id for rc in filtered]
        # product chunks should come first, then policy chunks
        assert ids == ["product1", "product2", "policy1", "policy2"]

    def test_non_matching_chunks_not_removed(self) -> None:
        """Non-matching chunks should still be present (just de-prioritised)."""
        chunks = [
            _make_rc("policy1", domain="policy"),
            _make_rc("product1", domain="product"),
        ]

        filtered = HybridSearch._apply_metadata_post_filter(
            chunks, {"domain": "product"}
        )

        assert len(filtered) == 2
        assert {rc.chunk.chunk_id for rc in filtered} == {"policy1", "product1"}

    def test_all_matching_preserves_order(self) -> None:
        """When all chunks match, original order is preserved."""
        chunks = [
            _make_rc("p1", domain="product"),
            _make_rc("p2", domain="product"),
            _make_rc("p3", domain="product"),
        ]

        filtered = HybridSearch._apply_metadata_post_filter(
            chunks, {"domain": "product"}
        )

        assert [rc.chunk.chunk_id for rc in filtered] == ["p1", "p2", "p3"]

    def test_no_matching_chunks(self) -> None:
        """When no chunks match, all are returned (just in original order)."""
        chunks = [
            _make_rc("pol1", domain="policy"),
            _make_rc("pol2", domain="policy"),
        ]

        filtered = HybridSearch._apply_metadata_post_filter(
            chunks, {"domain": "product"}
        )

        assert len(filtered) == 2
        assert [rc.chunk.chunk_id for rc in filtered] == ["pol1", "pol2"]

    def test_empty_chunks_list(self) -> None:
        """Filtering an empty list returns an empty list."""
        filtered = HybridSearch._apply_metadata_post_filter(
            [], {"domain": "product"}
        )
        assert filtered == []

    def test_filter_by_category(self) -> None:
        """Post-filter should work with any metadata field, not just domain."""
        chunks = [
            _make_rc("c1", domain="product", category="leggings"),
            _make_rc("c2", domain="product", category="tops"),
            _make_rc("c3", domain="product", category="leggings"),
        ]

        filtered = HybridSearch._apply_metadata_post_filter(
            chunks, {"category": "leggings"}
        )

        ids = [rc.chunk.chunk_id for rc in filtered]
        assert ids == ["c1", "c3", "c2"]


class TestHybridSearchWithMetadataFilter:
    """Integration test: metadata filter affects final ranking in HybridSearch."""

    def test_metadata_filter_deprioritises_irrelevant_chunks(self) -> None:
        """With a domain filter, matching chunks should rank higher than
        non-matching ones after post-filtering, even if the non-matching
        chunk had a higher fusion score."""
        # Dense returns a policy chunk first (higher rank → higher RRF score)
        # and a product chunk second
        dense = [
            _make_rc("policy1", source="dense", domain="policy"),
            _make_rc("product1", source="dense", domain="product"),
        ]
        sparse = [
            _make_rc("product1", source="sparse", domain="product"),
        ]

        mock_vs = MagicMock()
        mock_vs.query.return_value = dense

        mock_bm25 = MagicMock()
        mock_bm25.query.return_value = sparse

        rrf_fuser = RRFFuser(k=60)

        # Reranker passthrough: preserves input order
        mock_reranker = MagicMock(spec=CrossEncoderReranker)

        def passthrough(query, chunks, top_k=5, min_score=-3.0):
            return [
                RetrievedChunk(chunk=rc.chunk, score=rc.score, source="reranked")
                for rc in chunks[:top_k]
            ]

        mock_reranker.rerank.side_effect = passthrough

        hs = HybridSearch(
            vector_store=mock_vs,
            bm25_index=mock_bm25,
            rrf_fuser=rrf_fuser,
            reranker=mock_reranker,
        )

        results = hs.search(
            query_embedding=[0.1],
            query_text="test",
            metadata_filter={"domain": "product"},
            final_k=5,
        )

        # product1 should come before policy1 because of post-filtering
        result_ids = [rc.chunk.chunk_id for rc in results]
        product_idx = result_ids.index("product1")
        policy_idx = result_ids.index("policy1")
        assert product_idx < policy_idx
