# P&ID Assistant

A conversational AI system that enables natural language queries over Piping and Instrumentation Diagrams (P&IDs) for Oil & Gas operations.

## Overview

The P&ID Assistant combines Retrieval Augmented Generation (RAG) with vision-enabled language models to provide instant answers about plant assets, equipment, tags, and their interconnections.

### Key Features

- Natural language query interface
- Vision-enabled P&ID understanding
- Hybrid RAG + Vision API architecture
- Multi-LLM provider support (Gemini Flash, GPT-4o mini, Claude Sonnet)
- Token usage tracking and cost monitoring
- Mock maintenance ticket display

## Technology Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit |
| Backend | Python 3.11+ |
| LLM | Gemini Flash (default), GPT-4o mini, Claude Sonnet |
| Vector DB | ChromaDB |
| Database | SQLite |
| PDF Processing | PyMuPDF |
| Embeddings | OpenAI API |

## Project Structure

```
pid-assistant/
├── data/
│   ├── pdfs/                     # Source P&ID PDF files
│   └── processed/                # Extracted page images
├── database/
│   ├── assets.db                 # SQLite database
│   └── vector_store/             # ChromaDB directory
├── logs/
│   └── query_log.jsonl           # Query and cost logs
├── scripts/
│   ├── init_database.py          # Database initialization
│   ├── init_chromadb.py          # ChromaDB initialization
│   └── ingest_pdfs.py            # PDF ingestion script
├── app/
│   ├── main.py                   # Streamlit UI entry point
│   ├── query_router.py           # Query routing logic
│   ├── rag_engine.py             # RAG implementation
│   ├── vision_engine.py          # Vision query handling
│   ├── llm_adapter.py            # LLM provider abstraction
│   ├── mock_data.py              # Mock ticket data
│   └── utils.py                  # Shared utilities
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
LLM_PROVIDER=gemini                    # Options: gemini, openai, claude
LLM_MODEL=gemini-1.5-flash             # Model name

# API Keys
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here    # For embeddings
CLAUDE_API_KEY=your_claude_key_here    # Optional for finals

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
python scripts/ingest_pdfs.py
```

This will:
- Extract text from each PDF page
- Extract page images (300 DPI PNG)
- Chunk text content
- Generate embeddings
- Store in ChromaDB and SQLite

Expected time: ~60-90 seconds for a 7-page PDF

### 9. Start Application

```bash
streamlit run app/main.py
```

The application will open in your browser at `http://localhost:8501`

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

To switch LLM providers, edit `.env`:

**Default (Free) - Gemini Flash:**
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
```

**Fallback - GPT-4o mini:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

**Premium Testing - Claude Sonnet:**
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4-5-20250929
```

Restart the application after changing providers.

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

## MVP Limitations

- **Single Document**: Supports 1 P&ID (extensible design)
- **Simple Routing**: Keyword-based, not ML classification
- **No Caching**: Every query hits API (cost inefficient)
- **Local Only**: No cloud deployment
- **Mock Tickets**: Hardcoded data, not database-driven

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

**Last Updated**: 2025-10-19
**Version**: 1.0 MVP
