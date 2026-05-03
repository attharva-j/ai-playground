# Requirements Document

## Introduction

This document defines the requirements for a production-grade Retrieval-Augmented Generation (RAG) system built for ALO Yoga, a retail company. The system enables natural language querying across three knowledge domains: product knowledge, policy and operations intelligence, and customer context. It is designed as an interview case study proof-of-concept that demonstrates advanced RAG techniques including multi-strategy chunking, hybrid retrieval, query intelligence routing, and a comprehensive evaluation framework.

## Glossary

- **RAG_System**: The complete Retrieval-Augmented Generation application encompassing ingestion, retrieval, generation, and evaluation components
- **Ingestion_Pipeline**: The subsystem responsible for loading source documents, chunking them according to domain-specific strategies, computing embeddings, and storing them in the Vector_Store and BM25_Index
- **Vector_Store**: A ChromaDB-based dense vector database that stores document chunk embeddings and supports metadata-filtered similarity search
- **BM25_Index**: A sparse keyword-based retrieval index built using rank-bm25 that enables lexical matching alongside dense retrieval
- **Intent_Router**: A lightweight LLM-based classifier (Claude Haiku) that categorizes incoming queries by domain (product, policy, customer) and assigns confidence scores to determine retrieval strategy
- **HyDE_Module**: The Hypothetical Document Embeddings module that generates a hypothetical answer to a query before embedding it, improving retrieval for abstract or policy-oriented queries
- **Query_Decomposer**: The component that breaks complex multi-domain queries into independent sub-queries, each routed to the appropriate retrieval strategy
- **Retrieval_Engine**: The hybrid retrieval subsystem that executes parallel dense and sparse searches, fuses results via Reciprocal Rank Fusion, and reranks with a cross-encoder model
- **Cross_Encoder_Reranker**: A neural reranking model (ms-marco-MiniLM-L-6-v2) that scores query-chunk relevance pairs to reorder retrieval results
- **RRF_Fuser**: The Reciprocal Rank Fusion component that merges ranked lists from dense and sparse retrieval using the formula score = 1/(rank + k)
- **Generation_Engine**: The subsystem that constructs structured prompts from retrieved context and customer data, calls the LLM (Claude), and produces the final answer
- **Faithfulness_Guardrail**: A verification component that uses a second LLM call to check whether claims in the generated answer are traceable to the provided context
- **Scope_Guard**: A component that detects out-of-scope queries and returns an appropriate refusal rather than hallucinating an answer
- **Customer_Context_Injector**: The component that retrieves structured customer order data (not via embedding search) and injects it into the generation prompt
- **Evaluation_Framework**: The test harness containing 25+ test queries, retrieval metrics, generation metrics, and failure analysis tooling
- **Demo_UI**: A Streamlit-based web interface for interacting with the RAG_System, selecting customer profiles, and inspecting pipeline trace data
- **Chunk**: A segment of a source document produced by the Ingestion_Pipeline, stored with metadata in the Vector_Store
- **Domain**: One of three knowledge areas: Product (product specs, materials, sizing), Policy (returns, shipping, promos, loyalty), or Customer (order history, personal context)
- **Trace_Mode**: A diagnostic display mode in the Demo_UI that shows every pipeline decision including intent classification, retrieval scores, reranking, and generation prompt construction
- **ADR**: Architecture Decision Record — a structured document explaining key technical decisions and their rationale
- **Production_Readiness_Memo**: A document identifying top operational risks and mitigation strategies for production deployment

## Requirements

### Requirement 1: Data Ingestion — Product Knowledge Chunking

**User Story:** As a system operator, I want product catalog data chunked per-product so that each retrieval result contains complete information about a single product.

#### Acceptance Criteria

1. WHEN product catalog data is provided, THE Ingestion_Pipeline SHALL create one Chunk per product containing the product's full specifications, materials, sizing, and care instructions.
2. WHEN a product Chunk is created, THE Ingestion_Pipeline SHALL attach metadata including product_id, category, and domain="product" to the Chunk.
3. IF a product record is missing any of the required fields (product_id, name, or description), THEN THE Ingestion_Pipeline SHALL log a structured warning containing the field name that is missing and the index of the offending record, skip that record, and continue processing remaining records without halting the pipeline.
4. WHEN ingestion completes, THE Ingestion_Pipeline SHALL report a summary count of records ingested successfully and records skipped due to validation failures.

### Requirement 2: Data Ingestion — Policy Document Chunking

**User Story:** As a system operator, I want policy documents chunked by semantic sections so that conditional logic clauses (e.g., return windows, promo eligibility rules) are preserved intact within a single chunk.

#### Acceptance Criteria

1. WHEN policy documents are provided, THE Ingestion_Pipeline SHALL split them into Chunks at semantic section boundaries (headings, topic shifts) rather than at fixed token counts.
2. THE Ingestion_Pipeline SHALL preserve complete conditional logic clauses within a single Chunk so that no if/then/else rule is split across Chunks.
3. WHEN a policy Chunk is created, THE Ingestion_Pipeline SHALL attach metadata including policy_type (returns, shipping, promo, loyalty), effective_date, and domain="policy" to the Chunk.

### Requirement 3: Data Ingestion — Embedding and Indexing

**User Story:** As a system operator, I want documents embedded and indexed in both dense and sparse stores so that the system supports hybrid retrieval.

#### Acceptance Criteria

1. WHEN Chunks are produced by the Ingestion_Pipeline, THE Ingestion_Pipeline SHALL compute dense vector embeddings using the configured embedding model (voyage-3 primary, sentence-transformers/all-mpnet-base-v2 fallback).
2. WHEN Chunks are produced, THE Ingestion_Pipeline SHALL store the embeddings and metadata in the Vector_Store (ChromaDB).
3. WHEN Chunks are produced, THE Ingestion_Pipeline SHALL index the Chunk text in the BM25_Index for sparse keyword retrieval.
4. IF the primary embedding model (voyage-3) is unavailable, THEN THE Ingestion_Pipeline SHALL fall back to the secondary embedding model (all-mpnet-base-v2) and log the fallback event.
5. FOR ALL Chunks ingested, THE VectorStore SHALL expose a verify_chunk(chunk_id) method that retrieves the stored document text and compares it to the original source text; the comparison SHALL pass for every chunk immediately after ingestion (round-trip integrity check).

### Requirement 4: Customer Data Architecture

**User Story:** As a system architect, I want customer order data handled via structured lookup rather than embedding so that customer queries return precise, up-to-date results without privacy risks from embedding personal data.

#### Acceptance Criteria

1. THE Customer_Context_Injector SHALL retrieve customer order data from a structured data source (JSON/CSV) using exact-match lookups by customer_id, not via embedding similarity search.
2. WHEN a customer_id is provided with a query, THE Customer_Context_Injector SHALL return the complete order history for that customer.
3. IF a provided customer_id does not exist in the data source, THEN THE Customer_Context_Injector SHALL return an empty result set and THE Generation_Engine SHALL inform the user that no customer record was found.

### Requirement 5: Query Intent Classification

**User Story:** As a user, I want my queries automatically routed to the right knowledge domain so that I get the most relevant retrieval strategy without specifying the domain manually.

#### Acceptance Criteria

1. WHEN a query is received, THE Intent_Router SHALL classify it into one or more domains (product, policy, customer) with a confidence score between 0.0 and 1.0 for each domain.
2. THE Intent_Router SHALL return classification results within 2 seconds per query.
3. WHEN the highest confidence score for any domain is below 0.3, THE Intent_Router SHALL flag the query as "ambiguous" and THE Scope_Guard SHALL evaluate whether the query is out-of-scope.
4. WHEN a query spans multiple domains (e.g., "What's the return policy for the leggings I bought last month?"), THE Intent_Router SHALL assign confidence scores to each relevant domain and THE Query_Decomposer SHALL split the query into domain-specific sub-queries.

### Requirement 6: HyDE for Policy Queries

**User Story:** As a user asking abstract policy questions, I want the system to generate a hypothetical answer before searching so that retrieval finds the most relevant policy sections even when my question doesn't use the exact policy terminology.

#### Acceptance Criteria

1. WHEN the Intent_Router classifies a query as domain="policy" with confidence above 0.5, THE HyDE_Module SHALL generate a hypothetical answer document using the LLM.
2. THE HyDE_Module SHALL embed the hypothetical answer and use that embedding for dense retrieval instead of the raw query embedding.
3. WHEN HyDE is activated, THE RAG_System SHALL record the hypothetical document in the trace log for observability.

### Requirement 7: Multi-Query Decomposition

**User Story:** As a user asking complex questions that span multiple domains, I want the system to break my query into sub-queries so that each part is answered using the optimal retrieval strategy.

#### Acceptance Criteria

1. WHEN the Intent_Router assigns confidence scores above 0.3 to two or more domains for a single query, THE Query_Decomposer SHALL split the query into independent sub-queries, one per relevant domain.
2. THE Query_Decomposer SHALL route each sub-query to the retrieval strategy appropriate for its domain.
3. WHEN sub-query results are returned, THE Generation_Engine SHALL fuse the results into a single coherent answer.

### Requirement 8: Hybrid Retrieval and Fusion

**User Story:** As a user, I want the system to combine keyword and semantic search results so that retrieval is robust to both exact terminology matches and conceptual similarity.

#### Acceptance Criteria

1. WHEN a retrieval request is made, THE Retrieval_Engine SHALL execute a dense similarity search on the Vector_Store returning the top-12 results and a sparse BM25 search on the BM25_Index returning the top-8 results in parallel.
2. THE RRF_Fuser SHALL merge the dense and sparse result lists using Reciprocal Rank Fusion with the formula score = 1/(rank + 60).
3. THE Cross_Encoder_Reranker SHALL score each candidate chunk from the fused list and return the top-5 chunks ordered by relevance.
4. WHEN metadata filters are applicable (e.g., domain-specific filtering), THE Retrieval_Engine SHALL apply metadata post-filters to de-prioritize irrelevant chunks before reranking.

### Requirement 9: Answer Generation

**User Story:** As a user, I want accurate, well-sourced answers generated from the retrieved context so that I can trust the information provided.

#### Acceptance Criteria

1. WHEN retrieved chunks and optional customer context are available, THE Generation_Engine SHALL construct a structured prompt containing system instructions, ranked context chunks with relevance scores, and customer context (if applicable).
2. THE Generation_Engine SHALL call the LLM (Claude) with the constructed prompt and return the generated answer.
3. THE Generation_Engine SHALL include source references in the answer indicating which chunks contributed to each claim.

### Requirement 10: Faithfulness Guardrail

**User Story:** As a system operator, I want generated answers verified against the source context so that hallucinated claims are detected and flagged.

#### Acceptance Criteria

1. WHEN an answer is generated, THE Faithfulness_Guardrail SHALL make a second LLM call to verify that each factual claim in the answer is traceable to the provided context chunks.
2. WHEN a claim cannot be traced to any context chunk, THE Faithfulness_Guardrail SHALL flag that claim as unsupported and trigger one regeneration attempt using a stricter prompt that instructs the LLM to confine its answer strictly to the provided context. The regenerated answer SHALL be used as the final answer in place of the original.
3. IF the regenerated answer still contains unsupported claims, THE Faithfulness_Guardrail SHALL return it as-is with the unsupported claims flagged and the faithfulness score reflecting the remaining issues; no further regeneration attempts SHALL be made.
4. THE Faithfulness_Guardrail SHALL return a faithfulness score between 0.0 and 1.0 representing the proportion of claims that are supported by context.

### Requirement 11: Scope Guard

**User Story:** As a user, I want the system to gracefully decline queries outside its knowledge domains so that I receive an honest "I don't know" rather than a hallucinated answer.

#### Acceptance Criteria

1. WHEN the Intent_Router flags a query as "ambiguous" (all domain confidence scores below 0.3), THE Scope_Guard SHALL evaluate whether the query falls outside the system's three knowledge domains.
2. WHEN the Scope_Guard determines a query is out-of-scope, THE Generation_Engine SHALL return a polite refusal message indicating the query is outside the system's capabilities.
3. WHEN the Scope_Guard determines a query is in-scope but ambiguous, THE Scope_Guard SHALL set is_in_scope=True and populate an uncertainty_note string describing the ambiguity. THE Pipeline SHALL pass the uncertainty_note to the Generation_Engine, which SHALL append it to the generated answer so the user understands the answer may be incomplete.

### Requirement 12: Demo User Interface

**User Story:** As an interviewer or evaluator, I want a web-based demo interface so that I can interact with the RAG system, select customer profiles, and inspect the full pipeline trace.

#### Acceptance Criteria

1. THE Demo_UI SHALL provide a customer selector dropdown populated from the available customer profiles.
2. THE Demo_UI SHALL provide a text input field for entering natural language queries.
3. WHEN a query is submitted, THE Demo_UI SHALL display three panels: (a) retrieved chunks with relevance scores, (b) the generated answer, and (c) pipeline metrics (latency, retrieval scores, faithfulness score).
4. WHEN Trace_Mode is enabled, THE Demo_UI SHALL display the full pipeline decision trace including intent classification results, HyDE activation status, retrieval strategy used, reranking scores, and prompt construction details.

### Requirement 13: Evaluation Framework — Test Query Suite

**User Story:** As a system evaluator, I want a comprehensive test query suite so that I can measure system performance across varying difficulty levels and all three knowledge domains.

#### Acceptance Criteria

1. THE Evaluation_Framework SHALL contain a minimum of 25 test queries distributed across easy, medium, and hard difficulty tiers.
2. THE Evaluation_Framework SHALL include test queries covering all three domains (product, policy, customer) and cross-domain queries.
3. EACH test query SHALL have a ground-truth expected answer and a set of expected relevant chunks for retrieval evaluation.

### Requirement 14: Evaluation Framework — Retrieval Metrics

**User Story:** As a system evaluator, I want retrieval quality measured with standard IR metrics so that I can quantify how well the system finds relevant information.

#### Acceptance Criteria

1. THE Evaluation_Framework SHALL compute Recall@5 for each test query, measuring the proportion of relevant chunks appearing in the top-5 retrieved results.
2. THE Evaluation_Framework SHALL compute Mean Reciprocal Rank (MRR) across the test query suite.
3. THE Evaluation_Framework SHALL compute Context Precision measuring the proportion of retrieved chunks that are relevant.

### Requirement 15: Evaluation Framework — Generation Metrics

**User Story:** As a system evaluator, I want generation quality measured with faithfulness, relevance, and hallucination metrics so that I can quantify answer quality.

#### Acceptance Criteria

1. THE Evaluation_Framework SHALL compute a Faithfulness score for each test query using LLM-as-judge evaluation, measuring whether claims in the answer are supported by the retrieved context.
2. THE Evaluation_Framework SHALL compute an Answer Relevance score for each test query, measuring how well the answer addresses the original question.
3. THE Evaluation_Framework SHALL compute a Hallucination Rate across the test suite, defined as the proportion of answers containing at least one unsupported claim.

### Requirement 16: Evaluation Framework — Failure Analysis and Regression

**User Story:** As a system evaluator, I want automated failure analysis and a regression harness so that I can identify weak spots and detect regressions over time.

#### Acceptance Criteria

1. THE Evaluation_Framework SHALL identify and produce a detailed failure analysis for the 3 worst-performing queries based on combined retrieval and generation scores.
2. THE Evaluation_Framework SHALL provide a regression harness that re-runs the full test suite and compares results against a stored baseline.
3. THE Evaluation_Framework SHALL complete a full regression run (25+ queries with all metrics) within 5 minutes.

### Requirement 17: Architecture Decision Record

**User Story:** As an interviewer, I want a concise ADR explaining key technical decisions so that I can evaluate the candidate's reasoning and trade-off analysis.

#### Acceptance Criteria

1. THE ADR SHALL be 1-3 pages in length and cover the following decisions: chunking strategy per domain, embedding model selection, HyDE justification for policy queries, and customer data architecture (structured lookup vs. embedding).
2. EACH decision in the ADR SHALL include the context, the decision made, alternatives considered, and the rationale for the chosen approach.

### Requirement 18: Production Readiness Memo

**User Story:** As an interviewer, I want a production readiness memo identifying operational risks so that I can evaluate the candidate's understanding of production deployment concerns.

#### Acceptance Criteria

1. THE Production_Readiness_Memo SHALL identify the top operational risks for deploying the RAG_System to production.
2. THE Production_Readiness_Memo SHALL address the following topics: incremental index refresh strategy, graceful degradation when external services are unavailable, latency budget breakdown across pipeline stages, and observability (logging, metrics, alerting).
3. EACH identified risk in the Production_Readiness_Memo SHALL include a mitigation strategy.

### Requirement 19: Source Data and Synthetic Data

**User Story:** As a developer building a POC, I want realistic data for all three domains so that I can demonstrate the system's capabilities without requiring access to real ALO Yoga production data.

#### Acceptance Criteria

1. THE RAG_System SHALL use the provided ALO data package as the primary source for product and customer data. The package contains 22 real product SKUs and 8 synthetic customer profiles, which satisfies the minimum counts for customers (Req 19.3) but not for products (Req 19.1). THE developer SHALL supplement the provided 22 SKUs with at least 28 additional synthetic product records (across leggings, tops, outerwear, and accessories) to reach the minimum of 50 products total, using the same JSON schema as the provided catalog.
2. THE RAG_System SHALL include synthetic policy documents covering return policies, shipping SLAs, promotional eligibility rules, and loyalty tier logic with seasonal variations. The provided ALO data package policy files (returns_and_exchanges_policy.md, shipping_policy.md, alo_access_loyalty_program.md) satisfy this requirement and SHALL be used as-is.
3. THE RAG_System SHALL include customer order history data for at least 8 customer profiles with varying loyalty tiers, order histories, and edge cases (e.g., final-sale orders, out-of-window returns). The 8 synthetic customer profiles in the provided ALO data package satisfy this requirement.
4. THE RAG_System SHALL implement a Document_Registry: a content-addressed, SQLite-backed registry that tracks a SHA-256 hash per Chunk and enables incremental index refresh — re-embedding only Chunks whose content or metadata has changed since the last ingestion run. Unchanged Chunks SHALL be skipped entirely; removed Chunks SHALL be soft-tombstoned and filtered at query time before being hard-deleted by a periodic GC sweep.

### Requirement 20: Pipeline Observability and Tracing

**User Story:** As a developer or interviewer, I want every pipeline stage to emit structured trace data so that I can debug issues and demonstrate the system's decision-making process.

#### Acceptance Criteria

1. WHEN a query is processed, THE RAG_System SHALL record a structured trace log containing: intent classification result, retrieval strategy selected, number of chunks retrieved from each source, reranking scores, faithfulness score, and end-to-end latency.
2. THE RAG_System SHALL make the trace log accessible via the Demo_UI Trace_Mode and as a programmatic API return value.
3. WHEN any pipeline stage encounters an error, THE RAG_System SHALL log the error with the stage name, input data, and error details without halting the entire pipeline.
