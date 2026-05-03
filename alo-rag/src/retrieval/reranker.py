"""Cross-encoder reranker for the ALO RAG retrieval engine.

Uses the ``BAAI/bge-reranker-base`` model from sentence-transformers to
score each (query, chunk) pair and return the top-k chunks ordered by
relevance. This model was chosen over the previous
``cross-encoder/ms-marco-MiniLM-L-6-v2`` for its significantly better
domain-specific retrieval quality on retail and policy text — see ADR-7
for the full decision rationale.

Requirements: 8.3
"""

from __future__ import annotations

import logging
from typing import Any

from src.models import RetrievedChunk

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Neural reranker using a cross-encoder model.

    The model is loaded lazily on first use to avoid heavy import-time
    overhead when the reranker is instantiated but not yet needed.

    Parameters
    ----------
    model_name:
        Hugging Face model identifier for the cross-encoder.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
    ) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 5,
        min_score: float = -3.0,
    ) -> list[RetrievedChunk]:
        """Score each *query*–chunk pair and return the top-*k* by relevance.

        Parameters
        ----------
        query:
            The user's search query.
        chunks:
            Candidate chunks to rerank (typically the fused RRF output).
        top_k:
            Number of top results to return.
        min_score:
            Minimum cross-encoder score to include a chunk. Chunks below
            this threshold are discarded even if within top_k.

        Returns
        -------
        list[RetrievedChunk]
            Up to *top_k* chunks sorted by descending cross-encoder score,
            each with ``source="reranked"``.
        """
        if not chunks:
            return []

        model = self._get_model()

        # Build (query, chunk_text) pairs for the cross-encoder
        pairs = [[query, rc.chunk.text] for rc in chunks]

        # Score all pairs in a single batch
        scores = model.predict(pairs, show_progress_bar=False)

        # Pair each chunk with its cross-encoder score
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda item: float(item[1]), reverse=True)

        reranked: list[RetrievedChunk] = []
        for rc, score in scored[:top_k]:
            if float(score) >= min_score:
                reranked.append(
                    RetrievedChunk(
                        chunk=rc.chunk,
                        score=float(score),
                        source="reranked",
                    )
                )

        logger.debug(
            "CrossEncoderReranker: %d candidates → %d passed min_score=%.1f",
            len(chunks),
            len(reranked),
            min_score,
        )
        return reranked

    def _get_model(self) -> Any:
        """Lazy-initialise and return the cross-encoder model.

        ONNX UPGRADE PATH (manual step required):
        To reduce reranker CPU latency from ~400ms to ~80ms, export the
        model to ONNX format and switch to ORTModelForSequenceClassification.

        Step 1 — export (run once in the project root):
            pip install optimum onnxruntime
            optimum-cli export onnx --model BAAI/bge-reranker-base bge_reranker_onnx/

        Step 2 — validate outputs match PyTorch outputs:
            python -c "
            from sentence_transformers import CrossEncoder
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            import numpy as np

            pairs = [['test query', 'test document']]
            pt_model = CrossEncoder('BAAI/bge-reranker-base')
            pt_score = pt_model.predict(pairs)

            tokenizer = AutoTokenizer.from_pretrained('bge_reranker_onnx/')
            ort_model = ORTModelForSequenceClassification.from_pretrained(
                'bge_reranker_onnx/', provider='CPUExecutionProvider'
            )
            inputs = tokenizer(pairs[0][0], pairs[0][1], return_tensors='pt')
            ort_score = ort_model(**inputs).logits.item()
            print('PT score:', pt_score[0], '| ORT score:', ort_score)
            print('Match:', np.isclose(pt_score[0], ort_score, atol=1e-3))
            "

        Step 3 — once validated, replace _get_model() body with:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained('bge_reranker_onnx/')
            model = ORTModelForSequenceClassification.from_pretrained(
                'bge_reranker_onnx/', provider='CPUExecutionProvider'
            )
            self._model = (tokenizer, model)
        And update predict() calls accordingly.
        """
        # TODO: ONNX export — see docstring above for manual steps
        if self._model is None:
            from sentence_transformers import CrossEncoder  # noqa: WPS433

            logger.info(
                "Loading cross-encoder model: %s", self.model_name
            )
            self._model = CrossEncoder(self.model_name)
        return self._model
