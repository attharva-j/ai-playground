"""FastAPI server for the ALO RAG System.

Wraps the existing RAG pipeline and exposes it as a streaming HTTP API
compatible with the Vercel AI SDK data stream protocol.

Usage (from the alo-rag/ directory):
    python -m uvicorn server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Suppress noisy polling logs for /api/trace
# ---------------------------------------------------------------------------
class _SuppressTracePolling(logging.Filter):
    """Filter out GET /api/trace access log lines to reduce noise."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "GET /api/trace" in msg:
            return False
        return True


logging.getLogger("uvicorn.access").addFilter(_SuppressTracePolling())

# ---------------------------------------------------------------------------
# Ensure the alo-rag root is on sys.path so `src.*` imports resolve.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Load environment variables from .env in the workspace root
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    # Load from the workspace root .env (one level above alo-rag/)
    load_dotenv(_PROJECT_ROOT.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; user must set env vars manually

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from src.generation.customer_context import CustomerContextInjector
from src.generation.guardrails import FaithfulnessGuardrail
from src.generation.llm_client import LLMClient
from src.generation.prompt_builder import PromptBuilder
from src.ingestion.chunkers import PolicyChunker, ProductChunker
from src.ingestion.embedders import EmbeddingService
from src.ingestion.index_builder import BM25Builder, VectorStore
from src.ingestion.loaders import PolicyLoader, ProductLoader
from src.ingestion.registry import DocumentRegistry
from src.models import FaithfulnessResult
from src.pipeline import Pipeline, PreGenerationResult, _ERROR_RESPONSE
from src.query.decomposer import QueryDecomposer
from src.query.hyde import HyDEModule
from src.query.intent_router import IntentRouter
from src.query.scope_guard import ScopeGuard
from src.retrieval.fusion import RRFFuser
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fast no-op guardrail for interactive chat (skips the second LLM call)
# ---------------------------------------------------------------------------
class _NoOpGuardrail:
    """A pass-through guardrail that skips verification for faster responses.

    The real FaithfulnessGuardrail makes a second LLM call on every
    response (~1-2s).  For interactive chat this is too slow.  This
    no-op returns a perfect score immediately.  The real guardrail is
    still used in the evaluation harness.
    """

    def verify(self, answer: str, context_chunks: list, query: str = "") -> FaithfulnessResult:
        return FaithfulnessResult(
            score=1.0,
            claims=[],
            unsupported_claims=[],
            regeneration_triggered=False,
            regenerated_answer=None,
        )

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
_DATA_DIR = _PROJECT_ROOT / "data"
_CUSTOMERS_PATH = _DATA_DIR / "customers" / "customer_order_history.json"
_PRODUCTS_PATH = _DATA_DIR / "products" / "alo_product_catalog.json"
_POLICIES_PATH = _DATA_DIR / "policies"

# ---------------------------------------------------------------------------
# App globals (populated on startup)
# ---------------------------------------------------------------------------
pipeline: Pipeline | None = None
customer_injector: CustomerContextInjector | None = None
last_trace: dict | None = None  # stores the most recent pipeline trace

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="ALO RAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup: initialise the full RAG pipeline
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event() -> None:
    """Build the full RAG pipeline on server startup."""
    global pipeline, customer_injector

    logger.info("Initialising RAG pipeline...")

    # -- Core services ----------------------------------------------------
    embedding_service = EmbeddingService()
    llm_client = LLMClient()

    # -- Load and chunk documents -----------------------------------------
    product_docs = ProductLoader().load(_PRODUCTS_PATH)
    policy_docs = PolicyLoader().load(_POLICIES_PATH)

    product_chunks, _ = ProductChunker().chunk(product_docs)
    policy_chunks = PolicyChunker().chunk(policy_docs)
    all_chunks = product_chunks + policy_chunks

    # -- Incremental ingestion via DocumentRegistry -------------------------
    vector_store = VectorStore(collection_name="alo_rag")
    registry = DocumentRegistry(db_path=str(_DATA_DIR / "registry.db"))

    chunks_to_embed = []
    for chunk in all_chunks:
        meta_dict = {
            "domain": chunk.metadata.domain,
            "policy_type": chunk.metadata.policy_type,
            "fabric_type": chunk.metadata.fabric_type,
            "category": chunk.metadata.category,
        }
        new_hash = DocumentRegistry.compute_hash(chunk.text, meta_dict)
        action = registry.classify_chunk(chunk.chunk_id, new_hash)

        # Important:
        # The server currently uses an in-memory Chroma collection. On every process
        # restart the vector store is empty, while the SQLite registry may still say
        # chunks are unchanged. In that case skipping unchanged chunks silently creates
        # an empty dense index. Only skip unchanged chunks when the vector store is
        # persistent AND the specific chunk exists in the collection.
        if action == "unchanged":
            if vector_store.is_persistent and vector_store.contains(chunk.chunk_id):
                continue
            logger.info(
                "Registry says chunk unchanged but vector missing/non-persistent; re-upserting %s",
                chunk.chunk_id,
            )
        if action == "modified":
            try:
                vector_store.delete(ids=[chunk.chunk_id])
            except Exception:
                pass  # chunk may not exist in store yet

        chunks_to_embed.append((chunk, new_hash, meta_dict))

    if chunks_to_embed:
        texts = [c.text for c, _, _ in chunks_to_embed]
        embeddings = embedding_service.embed(texts)
        chunks_only = [c for c, _, _ in chunks_to_embed]
        vector_store.add(chunks_only, embeddings)
        for chunk, new_hash, meta_dict in chunks_to_embed:
            registry.upsert(
                chunk_id=chunk.chunk_id,
                source_doc_id=chunk.source_document,
                content_hash=new_hash,
                domain=chunk.metadata.domain,
                metadata=meta_dict,
            )

    logger.info(
        "Startup ingestion: %d embedded, %d unchanged (skipped)",
        len(chunks_to_embed),
        len(all_chunks) - len(chunks_to_embed),
    )

    bm25_index = BM25Builder().build(all_chunks)

    # -- Assemble pipeline components -------------------------------------
    rrf_fuser = RRFFuser(k=60)
    reranker = CrossEncoderReranker()
    reranker._get_model()  # Eagerly load model into memory at startup
    hybrid_search = HybridSearch(
        vector_store=vector_store,
        bm25_index=bm25_index,
        rrf_fuser=rrf_fuser,
        reranker=reranker,
    )

    intent_router = IntentRouter(llm_client)
    hyde = HyDEModule(llm_client, embedding_service)
    decomposer = QueryDecomposer(llm_client)
    scope_guard = ScopeGuard(llm_client)
    prompt_builder = PromptBuilder()
    guardrail = _NoOpGuardrail()  # Skip slow LLM verification for interactive chat
    customer_injector = CustomerContextInjector(data_path=_CUSTOMERS_PATH)

    pipeline = Pipeline(
        intent_router=intent_router,
        hyde=hyde,
        decomposer=decomposer,
        scope_guard=scope_guard,
        retrieval=hybrid_search,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
        guardrail=guardrail,
        customer_injector=customer_injector,
        embedding_service=embedding_service,
    )

    logger.info("RAG pipeline initialised successfully.")


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------
def _generate_id() -> str:
    """Generate a unique message/text block ID."""
    import uuid
    return uuid.uuid4().hex


async def generate_stream_from_llm(llm_client, prompt: str, system: str):
    """Stream tokens directly from the OpenAI API via SSE.

    This produces real token-by-token streaming — each token is sent to
    the frontend as it arrives from OpenAI, giving a ChatGPT-style
    rendering experience with no artificial delays.
    """
    msg_id = _generate_id()
    text_id = _generate_id()

    # Message start
    yield f'data: {json.dumps({"type": "start", "messageId": msg_id})}\n\n'
    yield f'data: {json.dumps({"type": "start-step"})}\n\n'
    yield f'data: {json.dumps({"type": "text-start", "id": text_id})}\n\n'

    # Stream tokens directly from OpenAI
    try:
        for token in llm_client.generate_stream(prompt=prompt, system=system):
            yield f'data: {json.dumps({"type": "text-delta", "id": text_id, "delta": token})}\n\n'
    except Exception as exc:
        logger.exception("Streaming generation failed")
        yield f'data: {json.dumps({"type": "text-delta", "id": text_id, "delta": " [Error generating response]"})}\n\n'

    # Finish
    yield f'data: {json.dumps({"type": "text-end", "id": text_id})}\n\n'
    yield f'data: {json.dumps({"type": "finish-step"})}\n\n'
    yield f'data: {json.dumps({"type": "finish", "finishReason": "stop"})}\n\n'
    yield "data: [DONE]\n\n"


async def generate_stream_from_text(answer: str):
    """Stream a pre-built answer string via SSE with simulated delays.

    Used as a fallback when true LLM streaming is not available (e.g.
    error messages).
    """
    import asyncio

    msg_id = _generate_id()
    text_id = _generate_id()

    yield f'data: {json.dumps({"type": "start", "messageId": msg_id})}\n\n'
    yield f'data: {json.dumps({"type": "start-step"})}\n\n'
    yield f'data: {json.dumps({"type": "text-start", "id": text_id})}\n\n'

    words = answer.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yield f'data: {json.dumps({"type": "text-delta", "id": text_id, "delta": chunk})}\n\n'
        await asyncio.sleep(0.03)

    yield f'data: {json.dumps({"type": "text-end", "id": text_id})}\n\n'
    yield f'data: {json.dumps({"type": "finish-step"})}\n\n'
    yield f'data: {json.dumps({"type": "finish", "finishReason": "stop"})}\n\n'
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Trace serialization helper
# ---------------------------------------------------------------------------
def _serialize_trace(result) -> dict:
    """Convert a PipelineResult trace into a JSON-serializable dict."""
    trace = result.trace
    if trace is None:
        return {}

    chunks_info = []
    for rc in result.chunks:
        chunk = rc.chunk
        chunks_info.append({
            "chunk_id": chunk.chunk_id,
            "domain": chunk.metadata.domain,
            "score": round(rc.score, 4),
            "source": rc.source,
            "product_id": chunk.metadata.product_id,
            "category": chunk.metadata.category,
            "policy_type": chunk.metadata.policy_type,
            "text_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
        })

    intent = trace.intent_classification
    trace_data = {
        "intent_classification": {
            "domains": {k: round(v, 3) for k, v in intent.domains.items()},
            "primary_domain": intent.primary_domain,
            "is_ambiguous": intent.is_ambiguous,
            "is_multi_domain": intent.is_multi_domain,
        },
        "hyde_activated": trace.hyde_activated,
        "hyde_hypothetical": trace.hyde_hypothetical,
        "scope_decision": None,
        "decomposed_queries": None,
        "chunks_retrieved": len(result.chunks),
        "chunks": chunks_info,
        "faithfulness_score": result.faithfulness_score,
        "latency_ms": round(trace.latency_ms, 1),
        "stage_latencies": {k: round(v, 1) for k, v in trace.stage_latencies.items()},
    }

    if trace.scope_decision:
        sd = trace.scope_decision
        trace_data["scope_decision"] = {
            "is_in_scope": sd.is_in_scope,
            "reason": sd.reason,
            "uncertainty_note": sd.uncertainty_note,
        }

    if trace.decomposed_queries:
        trace_data["decomposed_queries"] = [
            {"text": sq.text, "target_domain": sq.target_domain}
            for sq in trace.decomposed_queries
        ]

    if trace.faithfulness_result:
        fr = trace.faithfulness_result
        trace_data["faithfulness"] = {
            "score": round(fr.score, 3),
            "total_claims": len(fr.claims),
            "unsupported_claims": len(fr.unsupported_claims),
            "regeneration_triggered": fr.regeneration_triggered,
        }

    return trace_data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/chat")
async def chat(request: Request):
    """Streaming chat endpoint — runs pipeline stages 1-7 synchronously,
    then streams the single LLM generation call to the client.
    Eliminates the redundant double generation call."""
    global last_trace
    body = await request.json()

    # Extract the latest user message
    messages = body.get("messages", [])
    user_message = ""
    conversation_history: list[dict[str, str]] = []

    # Extract all messages for conversation context
    for msg in messages:
        role = msg.get("role", "")
        text = ""
        content = msg.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    break
                elif isinstance(part, str):
                    text = part
                    break
        elif isinstance(content, str):
            text = content
        if not text:
            parts = msg.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    break
        if text and role in ("user", "assistant"):
            conversation_history.append({"role": role, "text": text})

    # The latest user message drives retrieval
    for entry in reversed(conversation_history):
        if entry["role"] == "user":
            user_message = entry["text"]
            break

    if not user_message:
        return StreamingResponse(
            generate_stream_from_text("Please provide a question."),
            media_type="text/event-stream",
            headers={"x-vercel-ai-ui-message-stream": "v1"},
        )

    customer_id = body.get("customer_id")
    if not customer_id:
        system_msg = body.get("system", "")
        if "customer_id:" in system_msg:
            customer_id = system_msg.split("customer_id:")[1].strip().split()[0]

    logger.info("Chat request — user_message=%r, customer_id=%r", user_message, customer_id)

    try:
        # Run stages 1-7 synchronously (no generation call)
        pre = pipeline.run_without_generation(
            query=user_message, customer_id=customer_id
        )

        # Build trace for the UI
        last_trace = {
            "intent_classification": {
                "domains": {k: round(v, 3) for k, v in pre.classification.domains.items()},
                "primary_domain": pre.classification.primary_domain,
                "is_ambiguous": pre.classification.is_ambiguous,
                "is_multi_domain": pre.classification.is_multi_domain,
            },
            "hyde_activated": pre.hyde_activated,
            "hyde_hypothetical": pre.hyde_hypothetical,
            "scope_decision": {
                "is_in_scope": pre.scope_decision.is_in_scope,
                "reason": pre.scope_decision.reason,
                "uncertainty_note": pre.scope_decision.uncertainty_note,
            } if pre.scope_decision else None,
            "decomposed_queries": None,
            "chunks_retrieved": len(pre.chunks),
            "chunks": [
                {
                    "chunk_id": rc.chunk.chunk_id,
                    "domain": rc.chunk.metadata.domain,
                    "score": round(rc.score, 4),
                    "source": rc.source,
                    "product_id": rc.chunk.metadata.product_id,
                    "category": rc.chunk.metadata.category,
                    "policy_type": rc.chunk.metadata.policy_type,
                    "text_preview": rc.chunk.text[:200] + "..." if len(rc.chunk.text) > 200 else rc.chunk.text,
                }
                for rc in pre.chunks
            ],
            "stage_latencies": {k: round(v, 1) for k, v in pre.stage_latencies.items()},
            "faithfulness_score": None,
            "latency_ms": round(sum(pre.stage_latencies.values()), 1),
            "customer_id": customer_id,
            "customer_injected": pre.gen_prompt is not None and pre.gen_prompt.customer_context is not None,
            "answerability": {
                "answerable": pre.answerability_decision.answerable,
                "action": pre.answerability_decision.action,
                "reason": pre.answerability_decision.reason,
                "missing_evidence": pre.answerability_decision.missing_evidence,
            } if getattr(pre, "answerability_decision", None) else None,
            "evidence_claims": [],
        }

        # Handle refused queries (out-of-scope or pipeline errors)
        if pre.is_refused:
            return StreamingResponse(
                generate_stream_from_text(pre.refusal_message or _ERROR_RESPONSE),
                media_type="text/event-stream",
                headers={"x-vercel-ai-ui-message-stream": "v1"},
            )

        # Prepend conversation history so the LLM can resolve follow-up
        # references ("it", "that order", "what about sale items?").
        # Only the last few turns are included to stay within token limits.
        prompt_text = pre.gen_prompt.rendered
        prior_turns = conversation_history[:-1]  # exclude the current user message
        if prior_turns:
            # Keep at most the last 6 turns (3 exchanges)
            recent = prior_turns[-6:]
            history_lines = ["## Conversation History\n"]
            for turn in recent:
                label = "User" if turn["role"] == "user" else "Assistant"
                # Truncate long assistant responses to save tokens
                text = turn["text"]
                if turn["role"] == "assistant" and len(text) > 300:
                    text = text[:300] + "..."
                history_lines.append(f"**{label}:** {text}\n")
            history_section = "\n".join(history_lines)
            prompt_text = history_section + "\n\n" + prompt_text
        if pre.uncertainty_note:
            prompt_text += (
                f"\n\n[SYSTEM NOTE: This query was ambiguous. "
                f"Note in your response: {pre.uncertainty_note}]"
            )

        # Stream the single generation call directly to the client
        return StreamingResponse(
            generate_stream_from_llm(
                llm_client=pipeline._llm_client,
                prompt=prompt_text,
                system=pre.gen_prompt.system_message,
            ),
            media_type="text/event-stream",
            headers={"x-vercel-ai-ui-message-stream": "v1"},
        )

    except Exception as exc:
        logger.exception("Chat endpoint — unhandled exception")
        last_trace = {"error": str(exc)}
        return StreamingResponse(
            generate_stream_from_text(
                "I'm sorry, but I encountered an issue processing your request. Please try again."
            ),
            media_type="text/event-stream",
            headers={"x-vercel-ai-ui-message-stream": "v1"},
        )


@app.get("/api/trace")
async def get_trace():
    """Return the trace data from the most recent pipeline execution."""
    if last_trace is None:
        return {"trace": None}
    return {"trace": last_trace}


@app.get("/api/customers")
async def get_customers():
    """Return the list of customer IDs and names."""
    if customer_injector is None:
        return {"customers": []}

    customer_ids = customer_injector.list_customers()
    customers = []
    for cid in customer_ids:
        profile = customer_injector.get_customer(cid)
        if profile:
            customers.append({
                "customer_id": profile.customer_id,
                "name": profile.name,
                "loyalty_tier": profile.loyalty_tier,
            })

    return {"customers": customers}
