# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Workflow — CRITICAL CONSTRAINT

**NEVER commit directly to `main`.** All changes must go through a pull request:

1. Create a branch: `git checkout -b claude/<short-description>`
2. Make changes and commit to the branch
3. Push branch: `git push origin <branch-name>`
4. Raise a PR: `gh pr create --base main --head <branch-name> ...`

This applies to ALL changes — bug fixes, new files, documentation updates, everything.
The only exception is if the user explicitly says "commit directly to main".

## Project Overview

The P&ID Assistant is a Streamlit-based AI application that enables natural language queries over Piping and Instrumentation Diagrams (P&IDs) for Oil & Gas operations. It combines hybrid RAG (Retrieval Augmented Generation) with vision-enabled language models to answer both text-based and visual queries about plant equipment and systems.

**Status**: MVP complete and fully operational
**Tech Stack**: Python 3.11+, Streamlit, ChromaDB, SQLite, Gemini/GPT-4o/Claude APIs

## Frequently Used Commands

### Setup & Initialization
```bash
# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Initialize SQLite database (one-time)
python scripts/init_database.py

# Initialize ChromaDB (one-time)
python scripts/init_chromadb.py
```

### Ingestion & Processing
```bash
# Ingest P&ID PDFs (vision-based extraction → SQLite + ChromaDB)
python scripts/ingest_pdfs_v2.py

# Verify ingestion / embeddings
python scripts/verify_ingestion.py
python scripts/check_embeddings.py
```

### Running the Application
```bash
# PRIMARY: FastAPI service — serves API + frontend at http://localhost:8000
uvicorn api.main:app --port 8000

# LEGACY: Streamlit UI at http://localhost:8501
streamlit run app/main.py
```

### Evaluation (three layers)
```bash
python scripts/eval_retrieval.py --mode hybrid      # L1 retrieval: hit@K / MRR
python scripts/eval_matrix.py                       # L2 generation: cross-model LLM judge
python scripts/eval_vision_matrix.py --runs 3       # L3 vision extraction vs ground truth
# Model line-ups: config/models.json
```

### Testing
```bash
pytest tests/
pytest tests/test_ingestion.py -v
```

## High-Level Architecture

### System Flow

1. **Ingestion Pipeline** (`scripts/ingest_pdfs_v2.py`): PDFs → vision extraction → structured data + chunks + embeddings
2. **Vector Database** (ChromaDB): Stores chunk text + embeddings (both dense search and BM25 read from here)
3. **SQLite Database**: Stores equipment/instrument/connection metadata
4. **Query Router** (`app/query_router.py`): Routes queries to RAG or Vision based on keywords
5. **RAG Engine** (`app/rag_engine.py`): Retrieval + context assembly + LLM generation
6. **Hybrid Retriever** (`app/hybrid_retriever.py`): BM25 + RRF fusion; `RETRIEVAL_MODE=vector|hybrid`
7. **Vision Engine** (`app/vision_engine.py`): Image analysis for spatial/visual queries
8. **LLM Adapter** (`app/llm_adapter.py`): Multi-provider interface (Gemini, OpenAI, Claude, **OpenRouter**)
9. **API Service** (`api/main.py`): FastAPI — routes, engines, serves `static/index.html`
10. **Frontend** (`static/index.html`): fetch-driven SPA; **legacy** Streamlit at `app/main.py`

### Key Data Flows

**RAG Path** (text-only queries like "What is V-101?"):
- Query → Embedding generation (OpenAI) → Vector search (ChromaDB) → Context assembly → LLM call → Response

**Vision Path** (visual queries like "Show me where V-101 is"):
- Query → Page selection logic → Image loading → Base64 encoding → Vision LLM call → Response

**Query Routing**: Simple keyword detection in `query_router.py` (keywords: "show", "where", "display", "flow", "path", "diagram" → Vision; others → RAG)

## Critical Code Locations

### Configuration & Setup
- **Environment variables**: `.env` (template: `.env.template`)
- **Database initialization**: `scripts/init_database.py` and `scripts/init_chromadb.py`
- **SQL schema**: Defined in `scripts/init_database.py` with `documents` and `document_pages` tables

### Core Engines
- **Query routing logic**: `app/query_router.py:route_query()` — keyword-based routing
- **RAG implementation**: `app/rag_engine.py` — retrieval (vector/hybrid) + context assembly
- **Hybrid retriever**: `app/hybrid_retriever.py` — Okapi BM25 + tag-aware tokenizer + RRF fusion
- **Vision implementation**: `app/vision_engine.py` — image loading and vision API integration
- **LLM provider abstraction**: `app/llm_adapter.py` — `call_llm()` handles all providers incl. OpenRouter, with token tracking
- **Model config**: `config/models.json` — model line-ups for the eval matrices

### API & UI & Data
- **API service**: `api/main.py` (routes, engine init) + `api/schemas.py` (typed I/O)
- **Frontend**: `static/index.html` — fetch-driven SPA (primary UI)
- **Legacy Streamlit app**: `app/main.py`
- **Mock ticket data**: `app/mock_data.py` — hardcoded maintenance records
- **PDF ingestion**: `scripts/ingest_pdfs_v2.py` — vision extraction, chunking, embedding generation

### Token Tracking
- **Logging function**: `app/llm_adapter.py:log_usage()` — prints to console and writes to `logs/query_log.jsonl`
- **Cost calculation**: `app/llm_adapter.py:calculate_cost()` — provider-specific pricing

## Development Patterns

### Adding a New LLM Provider
1. Add provider config to `.env.template`
2. Implement `call_{provider}()` function in `app/llm_adapter.py`
3. Update `call_llm()` to handle new provider
4. Add pricing in `calculate_cost()`

### Adding New Query Types
1. Add keywords to `vision_keywords` in `app/query_router.py` if vision-related
2. Create specific engine logic as needed (RAG or Vision)
3. Test routing with `pytest`

### Extending Document Support (Post-MVP)
- Current design supports 1 P&ID; extend by:
  - Modifying page selection logic in `vision_engine.py:select_relevant_pages()`
  - Enhancing query router with semantic classification (ML-based)
  - Adding document filtering to RAG queries
  - Increasing ChromaDB collection capacity

## Important Implementation Details

### Vector Database (ChromaDB)
- Collection name: `pid_chunks`
- Embedding model: OpenAI `text-embedding-3-small` (1536 dimensions)
- Persistent storage at `database/vector_store/`
- Top-K retrieval: default 3 chunks per RAG query
- Metadata stored: `document_id`, `page_number`, `page_title`, `chunk_index`

### SQLite Schema
- **documents table**: file_name, file_path, document_number, total_pages, facility, upload_date
- **document_pages table**: page_number, page_type, page_title, image_path, text_content, has_equipment
- Indexes on `document_id` and `has_equipment` for performance

### Ingestion Pipeline Details
- PDF extraction uses PyMuPDF at 300 DPI for image quality
- Text chunking: simple newline/paragraph-based splitting (1000 tokens default)
- Embedding batch size: handle retries on API failures (3 attempts)
- Expected ingestion time: 60-90 seconds for 7-page PDF

### LLM Provider Costs (as of MVP)
- **Gemini Flash**: FREE tier (1,500 requests/day), ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens
- **GPT-4o mini**: ~$0.15 per 1M input, ~$0.60 per 1M output tokens
- **Claude Sonnet**: ~$3.00 per 1M input, ~$15.00 per 1M output tokens
- Vision queries cost more (~6-8K tokens) than RAG queries (~1-2K tokens)

### Token Tracking
- All LLM calls tracked via `log_usage()` in `llm_adapter.py`
- Output logged to `logs/query_log.jsonl` (JSONL format for streaming)
- Console output includes Provider, Input/Output/Total tokens, Response time, Estimated cost
- Session stats available in Streamlit sidebar

## Common Debugging Tasks

### Check Vector Store Status
```bash
python scripts/check_embeddings.py
# Shows: collections, document count, embedding dimensions
```

### Verify PDF Ingestion
```bash
python scripts/verify_ingestion.py
# Shows: pages processed, chunks created, metadata stored
```

### Test LLM Provider
```python
# In Python shell with venv activated
from app.llm_adapter import call_llm
response = call_llm("What is V-101?")
print(response)
```

### Debug Query Routing
- Check `query_router.py:route_query()` for keyword matching
- Add print statements to see which path (RAG/Vision) is selected
- Inspect `app/main.py` session state for query history

### Image Loading Issues
- Verify images exist in `data/processed/{pdf_name}/page_N.png`
- Check file paths in SQLite `document_pages.image_path`
- Ensure image files are valid PNG format (check with `file` command)

## Database Locations

- **SQLite**: `database/assets.db`
- **ChromaDB Vector Store**: `database/vector_store/` (persistent directory)
- **PDF Source Files**: `data/pdfs/`
- **Extracted Images**: `data/processed/{pdf_name}/page_N.png`
- **Query Logs**: `logs/query_log.jsonl`

## Environment Variable Reference

Critical variables in `.env`:
- `LLM_PROVIDER`: "gemini", "openai", or "claude"
- `LLM_MODEL`: Model identifier (e.g., "gemini-1.5-flash")
- `GEMINI_API_KEY`, `OPENAI_API_KEY`, `CLAUDE_API_KEY`: API credentials
- `CHUNK_SIZE`: Tokens per text chunk (default 1000)
- `EMBEDDING_MODEL`: OpenAI model for embeddings (always "text-embedding-3-small")
- `IMAGE_DPI`: Image extraction quality (default 300)
- `ENABLE_TOKEN_TRACKING`: Boolean to enable/disable logging

## Known MVP Limitations

1. **Single Document Only**: Hardcoded to 1 P&ID
2. **Simple Query Routing**: Keyword-based, not ML classification
3. **No Response Caching**: Every query hits API
4. **Mock Tickets**: Hardcoded in `app/mock_data.py`, not database-driven
5. **No Authentication**: Single-user local deployment
6. **Limited Page Selection**: Vision queries may send all pages (cost inefficient at scale)

## Testing Strategy

- **Manual testing**: 20-30 test queries covering RAG, Vision, and edge cases
- **Integration tests**: Full pipeline (PDF → ingestion → query → response)
- **Unit tests**: Available in `tests/` directory, run with `pytest`
- **Success metrics**: 90%+ accurate responses, <10s response time, cost tracking functional

## Post-MVP Roadmap

**Phase 2 (Scale)**: Multi-document support (40-50 P&IDs), response caching, ML-based routing
**Phase 3 (Production)**: Cloud deployment, authentication, PostgreSQL, monitoring
**Phase 4 (Advanced)**: SCADA integration, real-time maintenance, mobile app

## Key Files by Function

| File | Purpose |
|------|---------|
| `app/main.py` | Streamlit UI and session management |
| `app/llm_adapter.py` | LLM provider abstraction and token tracking |
| `app/query_router.py` | Query type detection (RAG vs Vision) |
| `app/rag_engine.py` | Vector search and context assembly |
| `app/vision_engine.py` | Vision query handling and image loading |
| `app/mock_data.py` | Hardcoded maintenance ticket data |
| `scripts/ingest_pdfs.py` | PDF processing pipeline |
| `scripts/init_database.py` | SQLite schema and initialization |
| `scripts/init_chromadb.py` | ChromaDB setup |
| `README.md` | User-facing setup and usage guide |
| `architecture.md` | Detailed technical architecture (47KB reference) |
