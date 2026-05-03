"""Hybrid retrieval engine for the ALO RAG system.

Public components:
- :class:`RRFFuser` — Reciprocal Rank Fusion
- :class:`CrossEncoderReranker` — Neural cross-encoder reranker
- :class:`HybridSearch` — Orchestrates parallel dense+sparse search with fusion and reranking
"""

from src.retrieval.fusion import RRFFuser
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.reranker import CrossEncoderReranker

__all__ = [
    "CrossEncoderReranker",
    "HybridSearch",
    "RRFFuser",
]
