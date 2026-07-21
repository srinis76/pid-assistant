# P&ID Assistant

A conversational AI system that enables natural language queries over Piping and Instrumentation Diagrams (P&IDs) for Oil & Gas operations.

## Overview

The P&ID Assistant combines Retrieval Augmented Generation (RAG) with vision-enabled language models to provide instant answers about plant assets, equipment, tags, and their interconnections.

### Key Features

- Natural language query interface with source citations (drawing + sheet)
- **Hybrid retrieval** — dense vectors + BM25 lexical, fused with Reciprocal Rank Fusion (tag-precise for P&ID identifiers like `V-101`, `PSV-101`)
- Vision-enabled P&ID understanding (renders the referenced diagram in the answer)
- **Provider-agnostic LLMs via OpenRouter** — swap across 300+ models with a one-line config change
- **Three-layer evaluation harness** — retrieval (hit@K), generation (LLM-judge), and vision extraction (deterministic vs ground truth)
- FastAPI service with a custom single-page UI (operator + engineer modes)
- Token/latency/cost telemetry per query
- Maintenance ticket surfacing

## Technology Stack

| Layer | Technology |
|-------|------------|
| API / UI | FastAPI + custom single-page frontend (`static/index.html`) |
| Backend | Python 3.11+ |
| Retrieval | Hybrid — ChromaDB (dense) + in-house BM25, fused via RRF |
| LLM | OpenRouter (any model); native Gemini / OpenAI / Claude also supported |
| Vector DB | ChromaDB |
| Database | SQLite |
| PDF / Vision | PyMuPDF + vision LLM extraction |
| Embeddings | OpenAI (`text-embedding-3-small`) |

> A legacy Streamlit UI (`app/main.py`) is retained; the FastAPI service (`api/main.py`) is the primary interface.

## Project Structure

```
pid-assistant/
├── api/                          # FastAPI service (primary interface)
│   ├── main.py                   # App, routes, engine init, serves the UI
│   └── schemas.py                # Typed request/response models
├── static/
│   └── index.html                # Single-page frontend (fetch-driven)
├── config/
│   └── models.json               # Model line-ups for the eval matrices
├── data/
│   ├── pdfs/                     # Source P&ID PDF files
│   └── processed/                # Extracted page images
├── database/
│   ├── assets.db                 # SQLite (equipment, instruments, connections)
│   └── vector_store/             # ChromaDB directory
├── scripts/
│   ├── init_database.py          # SQLite schema
│   ├── init_chromadb.py          # ChromaDB init
│   ├── ingest_pdfs_v2.py         # Vision-based ingestion pipeline
│   ├── eval_retrieval.py         # Layer 1 — retrieval hit@K / MRR (--mode vector|hybrid)
│   ├── eval_matrix.py            # Layer 2 — cross-model generation matrix (LLM judge)
│   └── eval_vision_matrix.py     # Layer 3 — vision extraction vs ground truth (--runs N)
├── app/
│   ├── rag_engine.py             # Retrieval + generation
│   ├── hybrid_retriever.py       # BM25 + RRF fusion over ChromaDB
│   ├── vision_engine.py          # Vision query handling
│   ├── vision_extractor.py       # Structured extraction from P&ID images
│   ├── query_router.py           # RAG vs Vision routing
│   ├── llm_adapter.py            # Multi-provider LLM abstraction (incl. OpenRouter)
│   ├── mock_data.py              # Maintenance ticket data
│   └── main.py                   # Legacy Streamlit UI
├── requirements.txt              # Python dependencies
└── .env                          # Environment variables (NOT in git)
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- Internet connection for LLM API calls
- API keys for:
  - Gemini API (free tier available)
  - OpenAI API (for embeddings)
  - Claude API (optional for final testing)

### 2. Clone Repository

```bash
git clone <repository-url>
cd pid-assistant
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
# OR
venv\Scripts\activate     # On Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file from the template:

```bash
cp .env.template .env
```

Edit `.env` and add your API keys:

```bash
# LLM Provider Configuration
LLM_PROVIDER=gemini                    # gemini, openai, claude, or openrouter
LLM_MODEL=gemini-2.5-flash             # model name (or OpenRouter slug)

# API Keys
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here    # For embeddings (always OpenAI)
CLAUDE_API_KEY=your_claude_key_here    # Optional
OPENROUTER_API_KEY=your_openrouter_key # Unified access to 300+ models

# Retrieval
RETRIEVAL_MODE=hybrid                  # vector (dense only) or hybrid (dense + BM25 via RRF)
HYBRID_CANDIDATE_K=10                  # candidates per retriever before fusion
HYBRID_DENSE_WEIGHT=1.0
HYBRID_SPARSE_WEIGHT=1.0
HYBRID_RRF_K=60

# Application Settings
ENABLE_TOKEN_TRACKING=true
VERBOSE_LOGGING=true
IMAGE_DPI=300

# Database Paths
SQLITE_DB_PATH=database/assets.db
VECTOR_DB_PATH=database/vector_store

# Ingestion Settings
CHUNK_SIZE=1000
EMBEDDING_MODEL=text-embedding-3-small
```

### 6. Initialize Databases

```bash
# Initialize SQLite database
python scripts/init_database.py

# Initialize ChromaDB
python scripts/init_chromadb.py
```

### 7. Add P&ID Documents

Place your P&ID PDF files in the `data/pdfs/` directory.

For testing, use the sample document:
- `D-254-001_Gas_Production_Facility_Rev1.pdf`

### 8. Run Ingestion Pipeline

```bash
python scripts/ingest_pdfs_v2.py
```

This will:
- Extract page images (300 DPI PNG)
- Run vision-based extraction of equipment, instruments, and connections
- Build equipment-centric chunks and generate embeddings
- Store structured data in SQLite and chunks in ChromaDB

Expected time: ~60-90 seconds for a 7-page PDF

### 9. Start the Application

**FastAPI service (primary):**
```bash
uvicorn api.main:app --port 8000
```
Open `http://localhost:8000`.

**Legacy Streamlit UI (optional):**
```bash
streamlit run app/main.py     # http://localhost:8501
```

## Usage

### Query Examples

**Simple Lookups** (RAG path):
- "What is V-101?"
- "What are the specs for P-103?"
- "Tell me about PSV-101"

**Visual Queries** (Vision API path):
- "Show me where V-101 is on the diagram"
- "What equipment is connected to V-101?"
- "Display the flow path from V-101 to C-104"

**Maintenance Context**:
- "Has PSV-101 had any recent issues?"
- "Show me tickets for the export pump"

### Model Switching

**Recommended — OpenRouter** (one interface, 300+ models). Edit `.env`:
```bash
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash-lite   # or openai/gpt-4o-mini, anthropic/claude-sonnet-4-5, ...
```
Switching models is a single-line change — no code changes.

**Native providers** are also supported directly:
```bash
LLM_PROVIDER=gemini   LLM_MODEL=gemini-2.5-flash
LLM_PROVIDER=openai   LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=claude   LLM_MODEL=claude-sonnet-4-5-20250929
```

Restart the application after changing providers.

## Evaluation

The system ships with a three-layer evaluation harness — each layer targets a different failure mode:

```bash
# Layer 1 — Retrieval: hit@K / MRR vs gold chunks (compare vector vs hybrid)
python scripts/eval_retrieval.py --mode hybrid

# Layer 2 — Generation: cross-model quality/latency/cost (LLM-as-judge)
python scripts/eval_matrix.py

# Layer 3 — Vision extraction: tag recall / field coverage vs ground truth
python scripts/eval_vision_matrix.py --runs 3
```

Model line-ups for the matrices are defined in `config/models.json`. Retrieval scoring is deterministic (gold chunks / ground truth); generation is scored by a fixed LLM judge held constant across models.

## Cost Considerations

### Default Configuration (Development)
- **Gemini Flash**: FREE tier (1,500 requests/day)
- **Cost**: $0 within free tier limits

### Fallback Configuration
- **GPT-4o mini**: ~$0.0002-0.0004 per simple query
- **Cost**: ~$0.50-2 for 250-350 queries

### Premium Configuration (Final Testing)
- **Claude Sonnet 4.5**: ~$0.003-0.060 per query
- **Cost**: ~$3-5 for 50 validation queries


## Development

### Running Tests

```bash
pytest tests/
```

### Linting and Formatting

```bash
# Install dev tools
pip install black flake8

# Format code
black app/ scripts/

# Lint code
flake8 app/ scripts/
```

## Troubleshooting

### Issue: "No module named 'chromadb'"
**Solution**: Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "API key not found"
**Solution**: Check that `.env` file exists and contains valid API keys.

### Issue: "Database not found"
**Solution**: Run database initialization scripts:
```bash
python scripts/init_database.py
python scripts/init_chromadb.py
```

### Issue: Slow query responses
**Solution**:
- Vision API queries take 5-15 seconds (normal)
- Check internet connection
- Verify API service status

## Current Limitations

- **Single Document**: operates on 1 P&ID drawing (multi-document is the next milestone)
- **Simple Routing**: keyword-based RAG-vs-Vision, not ML classification
- **No Caching**: every query hits the API
- **Local Only**: no cloud deployment or auth yet
- **Mock Tickets**: maintenance records are hardcoded, not database-driven

Delivered since MVP: hybrid retrieval, OpenRouter model-agnosticism, a three-layer eval harness, and a FastAPI service with a custom UI.

## Roadmap

### Phase 2: Production Scale
- Support 40-50 P&ID documents
- Cloud deployment (AWS/Azure/GCP)
- Multi-user authentication
- Response caching

### Phase 3: System Integration
- SCADA real-time data integration
- Maintenance history connection
- ERP/EAM integration

### Phase 4: Advanced Features
- Predictive maintenance insights
- Anomaly detection
- Multi-plant deployments

## License

[Your License Here]

## Support

For issues and questions, please contact [Your Contact Info]

---

**Last Updated**: 2026-07-20
**Version**: 3.0
