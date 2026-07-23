# P&ID Assistant — Product Specification

**Version**: 1.0  
**Status**: Initial Phase  
**Last Updated**: 2026-07-22

---

## 1. Executive Summary

The P&ID Assistant is a conversational AI product for Oil & Gas operations teams. It enables engineers, operators, and maintenance personnel to ask natural language questions about Piping and Instrumentation Diagrams (P&IDs) and receive accurate, grounded answers — without needing to manually search dense engineering drawings.

The product combines hybrid retrieval (semantic + keyword) with vision-enabled language models to handle two fundamentally different query types: knowledge questions about equipment and instruments ("What is V-101 and what does it connect to?") and spatial/visual questions about layout and flow paths ("Show me the pressure relief path from V-101"). This dual-mode design is central to the product's value proposition: P&IDs are both structured data sources and visual documents, and a useful assistant must handle both.

The initial phase targets single-facility deployments and is architected to scale toward multi-facility, multi-document, and eventually real-time SCADA-integrated deployments in later phases.

---

## 2. Problem Statement

P&IDs are the authoritative reference for how a plant is wired — every valve, vessel, instrument, and connection is defined there. Yet they are notoriously hard to use:

- A single P&ID sheet can contain hundreds of tagged components with small, overlapping symbols
- Finding a specific instrument or tracing a process line requires visual scanning that takes an expert minutes and a newcomer much longer
- When a maintenance event occurs, the engineer needs to cross-reference the diagram, the tag database, and the maintenance history — typically across three different tools
- Training new operators on plant layout is slow because the knowledge lives in the drawings, not in a queryable system

The result is that tribal knowledge accumulates in experienced engineers, onboarding is slow, and routine questions ("is there a bypass valve on this line?") consume time that could be spent on higher-value work.

**The opportunity**: Modern vision-capable LLMs can now read and reason over engineering diagrams. Combined with hybrid retrieval over structured extraction from those same diagrams, it becomes possible to build a system that answers these questions accurately, cheaply, and in natural language.

---

## 3. Target Users

### Primary: Plant Engineer / Process Engineer
Needs to quickly look up equipment specs, tag relationships, and process flow paths during design review, incident investigation, or MOC (Management of Change) processes. Values accuracy and source transparency — needs to know which page and diagram the answer came from.

### Secondary: Maintenance Technician / Field Operator
Working from a mobile interface or control room terminal. Asks short, specific questions: "What type of valve is XV-201?", "Is there a bypass around P-301?". Needs fast, confident answers. Does not want to open a 15MB PDF to find one instrument.

### Tertiary: New Employee / Trainee
Learning plant layout and equipment. Uses the assistant as a study aid and reference. Benefits from complete, explanatory answers and the ability to ask follow-up questions.

---

## 4. Product Goals

### Initial Phase Goals
1. Answer natural language questions about a P&ID with ≥90% accuracy on factual queries
2. Support both knowledge queries (text-based RAG) and visual queries (vision model) from a single conversational interface
3. Ingest a P&ID PDF in under 2 minutes and make it immediately queryable
4. Track LLM usage and cost per query so the operator can monitor spend
5. Run entirely locally with no cloud infrastructure dependency (API keys aside)

### Business Goals (Product Trajectory)
- Reduce time-to-answer for routine P&ID questions from ~5 minutes (manual search) to <15 seconds
- Reduce onboarding time for new engineers on a facility by providing always-available diagram knowledge
- Create a product that can be licensed per-facility to Oil & Gas operators, EPCs, and plant maintenance teams

---

## 5. Non-Goals (Initial Phase)

These are explicitly out of scope for the initial phase and will be addressed in later phases:

- **Multi-document support**: The initial phase ingests and queries one P&ID at a time. Cross-document queries ("compare V-101 on Sheet 3 with the version on Sheet 7") are Phase 2.
- **Authentication and multi-user**: The initial phase is a single-user deployment. User accounts, roles, and audit logging are Phase 3.
- **Real-time data integration**: The system answers questions about the static P&ID. Live plant data (sensor readings, alarm states) are Phase 4.
- **SCADA / DCS connectivity**: Out of scope until Phase 4.
- **Response caching**: Each query makes a fresh LLM call. Caching for repeat queries is a Phase 2 performance optimization.
- **Mobile-native app**: The web frontend is responsive but not a native mobile app. Native mobile is Phase 3.

---

## 6. Functional Requirements

### 6.1 Document Ingestion
- The system must accept a P&ID in PDF format as input
- Ingestion must extract structured data (equipment tags, instruments, piping connections, page titles) using a vision-capable LLM
- Extracted content must be stored in two complementary stores: a relational database (equipment metadata and relationships) and a vector store (semantic chunks for retrieval)
- Ingestion must render each PDF page as a high-resolution image and store it for later vision queries
- Ingestion must complete within 2 minutes for a 10-page P&ID

### 6.2 Query Interface
- The system must accept natural language queries over a chat-style web interface
- The interface must display the query, the answer, and — where applicable — which page(s) of the P&ID the answer references
- The interface must support follow-up questions within a session (conversational context)

### 6.3 Query Routing
- The system must automatically classify each query as either a knowledge query (→ RAG path) or a visual/spatial query (→ Vision path)
- Users should not need to specify which mode to use; routing should be transparent
- Routing decisions must be explainable: the system should surface the path taken (RAG or Vision) so engineers can build trust in the system

### 6.4 RAG Path (Knowledge Queries)
- Retrieval must use a hybrid strategy: dense vector search (semantic similarity) fused with BM25 (keyword matching) using Reciprocal Rank Fusion
- The retriever must be tag-aware: equipment tags (e.g. "V-101", "XV-201") must be preserved as atomic tokens during indexing and retrieval
- The system must assemble relevant context from retrieved chunks and pass it to an LLM to generate a grounded answer
- Answers must be grounded in retrieved context; the system should not speculate beyond what the document contains

### 6.5 Vision Path (Spatial/Visual Queries)
- The system must select the most relevant P&ID page(s) for a given visual query
- Selected page images must be passed to a vision-capable LLM for analysis
- The system must return both the LLM's answer and indicate which page was used

### 6.6 LLM Provider Abstraction
- The system must support multiple LLM providers (Gemini, OpenAI, Anthropic, OpenRouter) through a unified adapter
- The active provider and model must be configurable via environment variables without code changes
- The system must support OpenRouter as a gateway for cross-provider model comparison

### 6.7 Cost and Usage Tracking
- Every LLM call must log: provider, model, input tokens, output tokens, response time, and estimated cost
- Session-level cost summaries must be available in the UI
- Logs must be written in a structured format (JSONL) for downstream analysis

### 6.8 Evaluation Framework
- The system must include a three-layer evaluation framework:
  - **L1 (Retrieval)**: Hit@K and MRR metrics against a ground truth query set
  - **L2 (Generation)**: LLM-as-judge scoring across models for accuracy, faithfulness, and relevance
  - **L3 (Extraction)**: Vision extraction quality vs ground truth equipment inventory
- Evaluation must be runnable without modifying production code

---

## 7. System Architecture

### 7.1 Design Principles

**Separation of ingestion and query**: The ingestion pipeline and query engines are fully decoupled. Ingestion populates the databases; query time reads from them. This means the document can be re-ingested with a better model without changing the query layer, and vice versa.

**Dual storage for dual query modes**: A relational database (SQLite) stores structured equipment metadata with relationship integrity. A vector store (ChromaDB) stores semantic text chunks for fuzzy retrieval. Both are populated at ingestion time from the same source. The RAG engine reads the vector store; the Vision engine reads the image files written to disk.

**Provider-agnostic LLM layer**: No query engine calls a specific LLM directly. All LLM calls go through a single adapter (`llm_adapter.py`) that handles provider routing, token logging, and cost calculation. This makes provider switching a config change, not a code change, and enables the cross-model evaluation matrix.

**API-first, UI-agnostic**: The query engines are exposed as a FastAPI service. The web frontend is a static single-page application that communicates via REST. This means the frontend can be replaced (or a CLI, mobile app, or Slack bot added) without touching the backend.

### 7.2 Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Ingestion Pipeline                   │
│  PDF → PyMuPDF (300 DPI images) → Vision LLM extract   │
│       → SQLite (equipment/instruments/connections)       │
│       → ChromaDB (text chunks + embeddings)              │
│       → Disk (page images for vision queries)           │
└─────────────────────────────────────────────────────────┘
                            │
                    populated once
                            │
┌─────────────────────────────────────────────────────────┐
│                      Query Layer                         │
│                                                         │
│   User Query → Query Router                             │
│                    │                                    │
│          ┌─────────┴──────────┐                        │
│          ▼                    ▼                        │
│    RAG Engine           Vision Engine                   │
│  (Hybrid Retriever      (Page selector +               │
│   BM25 + Vector +        Vision LLM call)              │
│   RRF fusion)                                          │
│          │                    │                        │
│          └─────────┬──────────┘                        │
│                    ▼                                    │
│             LLM Adapter                                 │
│    (Gemini | OpenAI | Claude | OpenRouter)             │
│                    │                                    │
│                 Response                               │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    API Service (FastAPI)                  │
│              REST endpoints + static frontend            │
└─────────────────────────────────────────────────────────┘
```

### 7.3 Query Routing Logic

The query router classifies each incoming query before dispatching it. The initial phase uses keyword detection on spatial/visual terms ("show", "where", "display", "flow path", "diagram", "locate"). Queries matching these terms route to the Vision engine; all others route to the RAG engine.

This design is intentionally simple for the initial phase. The routing logic is isolated in a single module (`query_router.py`) so it can be replaced with an ML classifier in Phase 2 without changing the engines it dispatches to.

### 7.4 Hybrid Retrieval

The RAG engine uses a two-stage hybrid retrieval strategy:

1. **Dense retrieval**: Query is embedded using `text-embedding-3-small` (1536 dimensions) and compared against the ChromaDB vector store using cosine similarity
2. **BM25 retrieval**: The same query is tokenized using a tag-aware tokenizer (which preserves equipment tags like "V-101" as single tokens) and scored against a BM25 index built over the same corpus
3. **Fusion**: Results from both stages are merged using Reciprocal Rank Fusion (RRF), which produces a single ranked list without requiring score normalization between the two systems

This hybrid approach outperforms pure vector search on exact tag lookups (BM25 advantage) while maintaining semantic coverage for paraphrased questions (dense advantage).

---

## 8. Data Model

### SQLite (Relational)

**documents**: Stores one record per ingested P&ID.  
Fields: `id`, `file_name`, `file_path`, `document_number`, `total_pages`, `facility`, `upload_date`

**document_pages**: Stores one record per page per document.  
Fields: `id`, `document_id`, `page_number`, `page_type`, `page_title`, `image_path`, `text_content`, `has_equipment`

Indexes on `document_id` and `has_equipment` for query performance.

### ChromaDB (Vector)

**Collection**: `pid_chunks`  
**Embedding model**: `text-embedding-3-small` (1536 dimensions)  
**Metadata per chunk**: `document_id`, `page_number`, `page_title`, `chunk_index`  
**Chunking strategy**: Paragraph/newline-based splitting at ~1000 tokens

### File System

**Page images**: `data/processed/{pdf_name}/page_N.png` — 300 DPI PNG renders of each PDF page, used by the Vision engine at query time.

**Query logs**: `logs/query_log.jsonl` — one JSON line per LLM call, written by the adapter.

---

## 9. API Design

The FastAPI service exposes the following endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Submit a natural language query; returns answer + metadata |
| POST | `/ingest` | Trigger ingestion of a new P&ID PDF |
| GET | `/status` | System health: ingestion state, document count, vector store size |
| GET | `/documents` | List ingested documents |
| GET | `/` | Serve the SPA frontend |

**Query request schema**:
```json
{
  "query": "string",
  "provider": "gemini | openai | claude | openrouter (optional, uses env default)",
  "model": "string (optional, uses env default)"
}
```

**Query response schema**:
```json
{
  "answer": "string",
  "route": "rag | vision",
  "source_pages": ["int"],
  "tokens": { "input": "int", "output": "int" },
  "cost_usd": "float",
  "latency_ms": "int"
}
```

---

## 10. Technology Stack and Rationale

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.11+ | Dominant in ML/AI tooling; best LLM SDK support |
| **Web framework** | FastAPI | Async, typed, auto-docs; appropriate for AI service patterns |
| **Vector store** | ChromaDB | Embedded (no infra), persistent, well-documented Python API |
| **Relational DB** | SQLite | Zero-infra for initial phase; schema migrates to PostgreSQL in Phase 3 |
| **PDF rendering** | PyMuPDF | Fast, high-quality raster output; 300 DPI sufficient for vision models |
| **Embeddings** | OpenAI `text-embedding-3-small` | Best cost/quality ratio at 1536 dims; widely benchmarked |
| **LLM (default)** | Gemini Flash (via OpenRouter) | Free tier for dev; fast; vision-capable; cost-efficient for initial phase |
| **Frontend** | Vanilla JS SPA | Zero framework overhead; ships as single HTML file; no build step |
| **Evaluation** | LLM-as-judge (cross-model) | No labeled answer dataset needed; scales to new query sets easily |

### Alternatives Considered

**Vector store**: Pinecone and Weaviate were considered but require cloud accounts and add operational complexity inappropriate for local deployments in the initial phase. ChromaDB runs in-process.

**Relational DB**: PostgreSQL was considered as the production database. SQLite is used for the initial phase to avoid requiring a running database service. The schema is designed to migrate without changes.

**LLM routing**: A dedicated classification model (e.g. fine-tuned BERT) was considered for query routing. Keyword detection was chosen for the initial phase because it requires no additional model, is fully inspectable, and handles the query distribution well in practice. The routing module is isolated for easy replacement.

---

## 11. Evaluation Strategy

The system is evaluated across three layers to catch failure modes at different points in the pipeline:

**L1 — Retrieval Quality**: Measures whether the right chunks are retrieved before generation. Metrics: Hit@1, Hit@3, MRR. Evaluated against a fixed set of (query, expected_chunk_id) pairs in `tests/ground_truth.json`. Failure here means the LLM has no chance of answering correctly regardless of its capability.

**L2 — Generation Quality**: Measures the quality of the final answer given retrieved context. An LLM judge scores each answer on accuracy, faithfulness (does it stay grounded in the context?), and relevance. Run across multiple model/provider combinations to surface cost-quality tradeoffs. Script: `scripts/eval_matrix.py`.

**L3 — Extraction Quality**: Measures how accurately the ingestion pipeline extracts structured data from the P&ID. Metrics: tag recall, field coverage, connection accuracy. Evaluated against a hand-verified ground truth. Script: `scripts/eval_vision_matrix.py`. Failure here propagates to both L1 and L2.

This three-layer structure separates retrieval failures from generation failures from extraction failures — which are otherwise indistinguishable from the end user's perspective.

---

## 12. Cost Model

| Provider | Path | Typical tokens/query | Estimated cost/query |
|----------|------|----------------------|----------------------|
| Gemini Flash | RAG | ~1–2K input, ~300 output | ~$0.0002 |
| Gemini Flash | Vision | ~6–8K input, ~500 output | ~$0.0008 |
| GPT-4o mini | RAG | ~1–2K input, ~300 output | ~$0.0004 |
| GPT-4o mini | Vision | ~6–8K input, ~500 output | ~$0.0016 |
| Claude Sonnet | RAG | ~1–2K input, ~300 output | ~$0.012 |

Cost tracking is built into every LLM call so operators can monitor spend without instrumenting anything separately. Vision queries cost 3–4× more than RAG queries due to image token overhead — this is a known and accepted trade-off for the initial phase; page pre-selection will reduce this in Phase 2.

---

## 13. Non-Functional Requirements

**Latency**: RAG queries should return in <5 seconds. Vision queries should return in <15 seconds. Both measured from query submission to first character of response.

**Accuracy**: ≥90% of factual queries (equipment type, tag lookup, connection tracing) should return a correct answer as evaluated by L2 eval.

**Ingestion throughput**: A 10-page P&ID should ingest in under 2 minutes on a standard development machine.

**Reliability**: The system should handle LLM API failures gracefully with retry logic (3 attempts with backoff) and surface a clear error message rather than a silent failure.

**Observability**: Every query and every LLM call is logged to `logs/query_log.jsonl` in structured JSONL. This log is the basis for offline debugging and cost analysis.

---

## 14. Phasing and Roadmap

### Initial Phase (Current)
- Single P&ID ingestion and querying
- Dual-mode query routing (RAG + Vision)
- Multi-provider LLM support
- Three-layer evaluation framework
- Local deployment, no authentication required
- FastAPI service + SPA frontend

### Phase 2 — Scale
- Multi-document support (40–50 P&IDs per facility)
- ML-based query routing (replaces keyword heuristic)
- Response caching for repeat queries
- Cross-document query support ("which documents reference V-101?")
- Semantic page pre-selection for vision queries (reduce per-query cost)

### Phase 3 — Production
- Cloud deployment (containerized, deployable to AWS/Azure/GCP)
- User authentication and role-based access
- PostgreSQL (migrated from SQLite)
- Audit logging for regulatory compliance contexts
- Native mobile interface

### Phase 4 — Real-Time Integration
- SCADA / DCS data integration (live sensor values)
- Real-time maintenance ticket linkage
- Alarm contextualization ("is there an active alarm on V-101?")
- Change detection (flag when P&ID revision changes existing answers)

---

## 15. Open Questions and Known Constraints

**Legend page handling**: P&ID symbol legends are extracted but not yet injected as context into per-page extraction prompts. This means instrument function codes may not always be resolved correctly. Planned fix in the next iteration.

**Cross-page connections**: Sheet references ("SHT 3", "SHT 5") are extracted but not yet used to follow connections across pages. Connections that cross pages may be incomplete.

**Query routing boundary cases**: Queries that are both factual and spatial ("What is the pressure rating of the valve shown in the relief path?") currently route to Vision. The correct answer may require both paths. Hybrid routing is a Phase 2 capability.

**Ground truth maintenance**: The evaluation ground truth (`tests/ground_truth.json`) was created from a single P&ID. It must be extended for each new document added to the system.

**LLM schema adherence**: More capable models (e.g. Gemini Pro) return explicit `null` for uncertain fields rather than hallucinating values. The data model handles this explicitly — null fields are coerced to empty strings, and null connections are filtered rather than stored. This is a deliberate trade-off: accuracy over completeness.
