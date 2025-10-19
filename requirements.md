# P&ID Digital Assistant - Requirements Specification

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-10-18 | Product Owner | Initial draft |
| 0.2 | 2025-10-18 | Product Owner | Removed containerization from MVP; relaxed non-functional requirements |
| 0.3 | 2025-10-18 | Product Owner | Expanded tech stack (Section 5.2); added PDF ingestion workflow (Section 7.4) |
| 0.4 | 2025-10-18 | Product Owner | Updated with real P&ID examples; refined database schema; added actual tag nomenclature |
| 0.5 | 2025-10-18 | Product Owner | Added critical notes: sample data is for reference only, NOT for hardcoding |
| 1.0 | 2025-10-18 | Product Owner | **SIMPLIFIED MVP**: Removed OpenAI; simplified to Claude+Gemini; minimal database schema; streamlined ingestion; 3-day delivery target |
| 1.1 | 2025-10-18 | Product Owner | Added token usage tracking requirements; model selection guidance (Sonnet vs Haiku); observability requirements |
| 1.2 | 2025-10-18 | Product Owner | **COST OPTIMIZATION**: Changed default to Gemini Flash (free tier); added GPT-4o mini fallback; updated cost estimates |

---

## 1. Executive Summary

### 1.1 Problem Statement
In Oil & Gas operations, control room engineers, field technicians, and plant managers frequently need to reference Piping and Instrumentation Diagrams (P&IDs) to understand asset configurations, tag details, and system interconnections. Currently, this process is manual — requiring users to consult physical P&ID copies or contact supervisors for clarifications, leading to inefficiency and delays in decision-making.

### 1.2 Solution Overview
The P&ID Digital Assistant is a conversational AI system that enables users to interact with P&ID data naturally through text-based queries. It combines vision-enabled language models with structured data retrieval to provide instant answers about plant assets, equipment, tags, and their interconnections.

### 1.3 Success Metrics
- **Query Response Time**: ~5-15 seconds for 90% of queries (vision API dependent)
- **Answer Accuracy**: > 90% correctness verified against source P&IDs
- **User Adoption**: Reduce manual P&ID lookups by 70%
- **Cost Efficiency**: 
  - **MVP Development**: $0-3 (using Gemini Flash free tier)
  - **Production**: Query cost < $0.50 per interaction (acceptable)
- **Delivery Timeline**: 3-day MVP development cycle

### 1.4 MVP Simplification Strategy
To achieve rapid delivery within 3 days, this MVP focuses on:
- ✅ Core value proposition: Vision-enabled + RAG hybrid P&ID queries
- ✅ Minimal viable feature set: Query, answer, basic UI
- ✅ Simplified architecture: Essential components only
- ✅ Single document: 1 P&ID for validation
- ⚠️ Deferred: Complex data extraction, advanced routing, production hardening

---

## 2. Product Overview

### 2.1 Product Vision
Become the primary digital knowledge companion for industrial plant operations, enabling engineers and technicians to instantly access and understand P&ID information through natural conversation.

### 2.2 Target Users

**Primary Persona: Control Room Engineer**
- **Role**: Monitor and control plant operations from control room
- **Pain Points**: Needs quick access to tag information, valve configurations, line connections during operations
- **Usage Context**: Desktop workstation, high-pressure time-sensitive decisions
- **Technical Proficiency**: High (familiar with P&IDs, SCADA systems)

**Secondary Persona: Field Technician** (Future)
- **Role**: Perform maintenance and troubleshooting in the field
- **Pain Points**: Needs P&ID reference while on-site, limited access to documentation
- **Usage Context**: Mobile/tablet in industrial environment (not MVP)

**Tertiary Persona: Plant Manager** (Future)
- **Role**: Oversee operations, planning, and compliance
- **Pain Points**: Needs overview of systems, historical context, maintenance records
- **Usage Context**: Office desktop, strategic decision-making (not MVP)

### 2.3 Core Value Proposition
- **Speed**: Instant answers vs. manual document search (minutes → seconds)
- **Accessibility**: Natural language vs. technical document navigation
- **Accuracy**: AI-powered understanding of complex diagrams
- **Context**: Interconnections and relationships automatically identified

### 2.4 MVP Scope and Simplifications

**MVP Focus (3-Day Timeline):**
This MVP prioritizes rapid proof-of-concept over comprehensive features. The goal is to demonstrate core value - vision-enabled P&ID querying with natural language.

**What's Included (Must-Have):**
- ✅ 1 P&ID document support
- ✅ Vision API (Gemini Flash default, Claude/GPT-4o fallback) for visual understanding
- ✅ RAG pipeline for text-based retrieval
- ✅ Simple query routing (rule-based)
- ✅ Basic Streamlit chat UI
- ✅ Mock ticket feature (hardcoded data)
- ✅ Multi-provider support (Gemini Flash, GPT-4o mini, Claude Sonnet) with manual switching
- ✅ **Cost-optimized**: Gemini Flash free tier for development ($0-5 total MVP cost)

**What's Simplified:**
- 🔶 Database: Minimal 2-3 tables (no complex equipment/tag extraction)
- 🔶 Query routing: Simple keyword matching (not ML classifier)
- 🔶 Ingestion: Basic text + image extraction (no structured parsing)
- 🔶 LLM providers: 2 options (removed OpenAI for simplicity)

**What's Deferred to Post-MVP:**
- ⏭️ Multi-document support (40-50 PDFs)
- ⏭️ Complex structured data extraction (equipment specs, tags, topology)
- ⏭️ Advanced query routing with ML classification
- ⏭️ Database-driven ticket system
- ⏭️ Production hardening (authentication, scaling, monitoring)
- ⏭️ Cloud deployment
- ⏭️ Mobile/tablet support

**Rationale:**
- Vision API + RAG can answer queries without extensive structured extraction
- Simple rules sufficient for MVP routing decisions
- Hardcoded mock data faster than database implementation
- **Gemini Flash free tier eliminates development costs** while maintaining quality
- Focus on proving core concept within aggressive timeline without budget concerns
- Premium models (Claude Sonnet) reserved for final validation and demos only

---

## 3. Functional Requirements

### 3.1 Must-Have Features (MVP)

#### FR-1: Natural Language Query Interface
**Description**: Users can ask questions about P&ID content in natural, conversational language without structured query syntax.

**User Stories**:
- As a control room engineer, I want to ask "What is XV-204?" so that I can quickly identify equipment without searching documents
- As an operator, I want to ask "Show me all valves connected to V-101" so that I can understand system configuration
- As a technician, I want to ask "What are the operating conditions for Line 2-IA-101" so that I can verify system parameters

**Acceptance Criteria**:
- System accepts free-form text queries
- Supports technical terminology and tag nomenclature
- Handles variations in phrasing (e.g., "what is", "tell me about", "show me")
- No query type restrictions (equipment, tags, lines, instruments, connections, parameters)

#### FR-2: Vision-Enabled P&ID Understanding
**Description**: System can interpret P&ID diagrams visually, understanding symbols, spatial relationships, line routing, and annotations.

**User Stories**:
- As an engineer, I want the system to understand flow direction so that I can trace upstream/downstream connections
- As a technician, I want the system to recognize instrument symbols so that I can identify equipment types
- As an operator, I want the system to see spatial layout so that I can understand physical proximity

**Acceptance Criteria**:
- Process PDF P&IDs as visual documents (images)
- Recognize standard ISA P&ID symbols (valves, vessels, instruments, lines)
- Understand spatial relationships and topology
- Interpret text annotations, tag labels, and specifications
- Support 1 PDF document in MVP (architectural design for 40-50 docs)

#### FR-3: Structured Data Retrieval
**Description**: System retrieves pre-loaded structured asset data (tags, equipment specifications, parameters) from database for fast, accurate responses.

**User Stories**:
- As an engineer, I want instant tag specifications so that I can verify equipment parameters quickly
- As a maintenance tech, I want equipment details readily available so that I don't have to call supervisors

**Acceptance Criteria**:
- Query SQLite database for tags, assets, equipment
- Return specifications, parameters, operating conditions
- Support tag lookup, equipment search, parameter queries
- Response time < 2 seconds for database queries

#### FR-4: Simple Query Routing
**Description**: System uses straightforward rule-based logic to route queries to either vision API or RAG retrieval.

**User Stories**:
- As a system, I want to identify visual queries so that I can send appropriate page images to vision API
- As a system, I want to use RAG for simple lookups so that responses are fast and cost-effective

**Acceptance Criteria**:
- **Simple routing rules**:
  * If query contains keywords: "show", "where", "flow", "path", "diagram", "layout" → Use vision API
  * If query is simple lookup: "what is [tag]", "specs for [equipment]" → Use RAG
  * Default: Use RAG first, fallback to vision if insufficient
- Route simple lookups to database/RAG
- Route visual/spatial queries to vision API  
- Log routing decisions for debugging
- **Note**: Not ML-based classification, just keyword matching for MVP

**Implementation Notes**:
- Use simple if/else or keyword matching
- No complex classifier needed for MVP
- Can enhance with better logic post-MVP

#### FR-5: Contextual Information Display
**Description**: When answering queries, provide relevant context including related equipment, connections, and recent maintenance information.

**User Stories**:
- As an engineer, I want to see related equipment when querying a tag so that I understand the broader system context
- As a technician, I want to see recent issues on an asset so that I can anticipate potential problems

**Acceptance Criteria**:
- Display tag details with upstream/downstream connections
- Show "Last Ticket" information for queried assets (mock data in MVP)
- Include resolution status for displayed tickets (mock data in MVP)
- Format: "Last Issue: [Description] | Resolved: [Date] | Solution: [Summary]"

#### FR-6: Multi-LLM Provider Support (Cost-Optimized)
**Description**: System supports multiple LLM providers with manual configuration switching via environment variables. Default setup uses free/low-cost models for development, with premium models available for final testing and production.

**User Stories**:
- As a developer, I want to use free models during development so that I can iterate without cost concerns
- As a developer, I want to manually switch to premium models so that I can validate quality before deployment
- As a developer, I want fallback options so that I can switch providers if free tier is exhausted

**Acceptance Criteria**:
- **Default Configuration** (Development):
  - Primary: **Gemini 1.5 Flash** (free tier: 1,500 requests/day)
  - Fallback: **GPT-4o mini** (if Gemini free tier exhausted or quality issues)
  - Manual flag to switch between providers via .env file
- **Premium Configuration** (Final Testing & Demos):
  - Claude Sonnet 4.5 (best quality for validation)
  - Manually enabled via .env flag change
- **Supported Providers & Models**:
  - Google Gemini: `gemini-1.5-flash` (default), `gemini-1.5-pro` (optional)
  - OpenAI: `gpt-4o-mini` (fallback), `gpt-4o` (optional premium)
  - Anthropic Claude: `claude-sonnet-4-5-20250929` (final testing only)
- Environment variable controls provider selection
- Simple adapter function routes requests to appropriate provider
- Consistent response format across providers
- Basic error handling with clear error messages

**Configuration Examples**:

**Default Development Setup** (Recommended):
```bash
# .env
LLM_PROVIDER=gemini                    # Default: Use Gemini Flash
LLM_MODEL=gemini-1.5-flash             # Free tier model
GEMINI_API_KEY=your_api_key_here
ENABLE_TOKEN_TRACKING=true
```

**Fallback to GPT-4o Mini** (If Gemini free tier exhausted):
```bash
# .env
LLM_PROVIDER=openai                    # Switch to OpenAI
LLM_MODEL=gpt-4o-mini                  # Low-cost model
OPENAI_API_KEY=your_api_key_here
ENABLE_TOKEN_TRACKING=true
```

**Premium Testing** (Day 3 final validation):
```bash
# .env
LLM_PROVIDER=claude                    # Switch to Claude
LLM_MODEL=sonnet-4.5                   # Premium model
CLAUDE_API_KEY=your_api_key_here
ENABLE_TOKEN_TRACKING=true
```

**Implementation Notes**:
- Keep implementation simple: Single function with if/else logic
- No complex adapter pattern needed for MVP
- Manual switching only (no automatic fallback)
- Developer changes .env file to switch providers
- Log which provider/model is active on startup

**Cost Impact**:
- Gemini Flash (free): $0 for up to 1,500 requests/day
- GPT-4o mini: ~$0.50-2 for 250-350 dev queries
- Claude Sonnet 4.5: ~$3-5 for final 50 validation queries
- **Total MVP cost: $0-7** (vs $15-20 with Sonnet only)

#### FR-7: Token Usage Tracking and Cost Monitoring
**Description**: System tracks and displays token usage and estimated costs for all LLM API calls to enable cost optimization and debugging.

**User Stories**:
- As a developer, I want to see token usage after each query so that I can understand cost drivers
- As a system administrator, I want session-level cost summaries so that I can monitor overall expenses
- As a developer, I want detailed logs so that I can optimize expensive queries

**Acceptance Criteria**:
- **Per-Query Tracking**:
  * Log input tokens, output tokens, total tokens after every LLM API call
  * Calculate and display estimated cost based on model pricing
  * Print to console during development/testing
  * Include provider, model, timestamp, query type
- **Session-Level Tracking**:
  * Maintain cumulative statistics: total queries, total tokens, total cost
  * Track breakdown by provider (Claude vs Gemini)
  * Track breakdown by model (Sonnet vs Haiku if using hybrid)
  * Display session summary at end or on demand
- **Logging**:
  * Write detailed logs to file for post-analysis
  * Include: timestamp, query, model, tokens, cost, response time
  * Enable/disable verbose logging via config
- **UI Display** (Optional for MVP):
  * Show token count and cost in Streamlit sidebar
  * Running total for current session

**Implementation Notes**:
```python
# Print after each API call (console)
print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 LLM API Call Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: {provider}
Model: {model}
Query Type: {query_type}
Input Tokens: {input_tokens:,}
Output Tokens: {output_tokens:,}
Total Tokens: {total_tokens:,}
Response Time: {response_time:.2f}s
Estimated Cost: ${cost:.4f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# Log to file (JSON format for analysis)
{
  "timestamp": "2025-10-18T14:30:00Z",
  "query": "What is V-101?",
  "provider": "claude",
  "model": "sonnet-4.5",
  "query_type": "simple_lookup",
  "input_tokens": 1234,
  "output_tokens": 156,
  "total_tokens": 1390,
  "response_time_seconds": 3.2,
  "estimated_cost_usd": 0.0052
}
```

**Pricing Reference (for calculations)**:
- Claude Sonnet 4.5: $3/M input, $15/M output
- Claude Haiku 3.5: $0.80/M input, $4/M output  
- Gemini Pro Vision: Check current Google AI pricing

### 3.2 Should-Have Features (Post-MVP Priority 1)

#### FR-7: Diagram Export
- Export P&ID sections as images
- Highlight queried components
- Annotation support

#### FR-8: Query History
- Save user query history
- Quick re-run of previous queries
- Export query results

#### FR-9: Multi-Document Search
- Search across multiple P&ID documents simultaneously
- Cross-reference between documents
- Document relationship mapping

### 3.3 Could-Have Features (Post-MVP Priority 2)

#### FR-10: Bulk Upload
- Upload multiple PDFs at once
- Batch processing and indexing
- Progress tracking

#### FR-11: Bookmark/Favorites
- Save frequently accessed tags/equipment
- Quick access shortcuts
- Personal workspace

#### FR-12: Advanced Filters
- Filter by system, area, equipment type
- Date-based filtering for documents
- Tag pattern matching

### 3.4 Won't-Have Features (MVP)

- SCADA real-time data integration
- Maintenance history system integration
- ERP/EAM system integration
- Mobile application
- Multi-user concurrent access
- Role-based access control (RBAC)
- Data editing capabilities
- Collaboration features

---

## 4. Non-Functional Requirements

### 4.1 Performance

**MVP Guidelines** (Local Development):

| Metric | Target | Notes |
|--------|--------|-------|
| Query Response Time (Database) | ~2-5 seconds | Aspirational; good enough for single user |
| Query Response Time (Vision API) | ~5-15 seconds | Depends on LLM provider latency |
| PDF Processing Time | < 1 minute per document | One-time setup cost |
| System Startup Time | < 10 seconds | Acceptable for local development |
| Memory Usage | < 6 GB | Hard constraint (8GB system limit) |

**Production Targets** (Future):
- Query response < 2s (95th percentile)
- High availability with SLA
- Optimized for concurrent users

### 4.2 Scalability

**MVP (Local Laptop)**:
- Single user
- 1 PDF document
- 100 queries per day expected load

**Production (Cloud)**:
- 10-50 concurrent users
- 40-50 PDF documents
- 1,000+ queries per day
- Horizontal scaling capability

**Design Principles**:
- Stateless application design
- Database connection pooling
- Async processing for heavy operations
- Simple Python application (virtual environment)
- Containerized deployment (Production only)

### 4.3 Reliability

**MVP** (Local Development):
- **Availability**: Best effort (local application, no uptime SLA)
- **Error Handling**: Graceful degradation when vision API unavailable
- **Data Integrity**: Immutable source PDFs, versioned database schema
- **Backup**: Manual backup process documented

**Production** (Future):
- 99.5% uptime SLA
- Automated failover and recovery
- Automated backup and disaster recovery

### 4.4 Usability

- **Interface**: Clean, minimal, technical aesthetic
- **Response Format**: Concise, technical, actionable information
- **Learning Curve**: < 5 minutes for technical users
- **Accessibility**: Keyboard navigation support
- **Documentation**: Inline help, query examples provided

### 4.5 Compatibility

**MVP**:
- Mac OS (M3 ARM architecture)
- Python 3.11+ (direct execution via virtual environment)
- Modern web browsers (Chrome, Safari, Firefox) if web UI

**Production** (Future):
- Cloud-agnostic (AWS/Azure/GCP)
- Docker containers for deployment
- Linux (x86_64 and ARM64)

### 4.6 Security

**MVP**:
- Local-only deployment (no network exposure)
- No authentication required (single user)
- No data encryption (local filesystem)

**Production** (Future):
- HTTPS/TLS encryption
- API key management
- User authentication (OAuth 2.0)
- Role-based access control
- Audit logging
- Data encryption at rest

### 4.7 Observability and Monitoring

**MVP Requirements**:

**Token Usage Tracking**:
- Log all LLM API calls with detailed metrics
- Track: input tokens, output tokens, model used, timestamp, cost
- Console output after each API call (for development)
- Persistent logging to file (JSON format for analysis)
- Session-level aggregation (total queries, tokens, cost)

**Query Logging**:
- Log every user query with metadata
- Include: query text, query type, routing decision, response time
- Track success/failure rates
- Enable debugging of problematic queries

**Performance Monitoring**:
- Response time tracking per query
- Breakdown by component: RAG retrieval time, LLM inference time, total time
- Identify slow queries for optimization

**Error Tracking**:
- Log all API errors with context
- Track error rates by provider/model
- Graceful degradation logging

**Log Format**:
```json
{
  "timestamp": "2025-10-18T14:30:00Z",
  "event_type": "llm_api_call",
  "provider": "claude",
  "model": "sonnet-4.5",
  "query": "What is V-101?",
  "query_type": "simple_lookup",
  "routing_decision": "rag",
  "input_tokens": 1234,
  "output_tokens": 156,
  "total_tokens": 1390,
  "response_time_seconds": 3.2,
  "estimated_cost_usd": 0.0052,
  "success": true
}
```

**Console Output** (Development):
- Verbose logging enabled by default for MVP
- Can disable via `VERBOSE_LOGGING=false` in .env
- Print token usage, costs, and timing after each query

**Session Summary**:
- Display at end of session or on-demand
- Total queries, total tokens, total cost
- Breakdown by query type (RAG vs vision)
- Average response time
- Success rate

**Production Additions** (Future):
- Real-time dashboards (Grafana)
- Alerting on high costs or error rates
- Structured logging (ELK stack)
- Distributed tracing
- Application Performance Monitoring (APM)

---

## 5. Technical Constraints

### 5.1 Hardware Constraints (MVP)
- **Platform**: Mac OS (M3 chip)
- **Memory**: 8 GB RAM total
- **Storage**: 30 GB available disk space
- **Network**: Internet connection required for LLM API calls

### 5.2 Software & Technology Stack

**Core Platform**:
- **Programming Language**: Python 3.11+
- **Package Management**: pip with `requirements.txt`
- **Environment**: Python virtual environment (`venv` or `conda`)
- **Deployment**: Direct execution - `python app.py` (no Docker for MVP)

**Databases**:
- **Structured Data**: SQLite 3.x (MVP) → PostgreSQL (Production)
- **Vector Database**: ChromaDB, FAISS, or Pinecone Lite (choose based on simplicity for local dev)

**LLM Integration**:
- **APIs**: Google Gemini API (default), OpenAI API (fallback), Claude API (premium validation)
- **Model Selection Strategy (Cost-Optimized for MVP)**:
  - **Development (Default)**: Gemini 1.5 Flash
    * FREE tier: 1,500 requests/day (likely covers entire MVP)
    * Good vision capabilities for P&ID diagrams
    * Fast responses (~2-5 seconds)
    * Cost: $0 within free tier limits
  - **Development (Fallback)**: GPT-4o mini
    * If Gemini free tier exhausted or quality issues
    * Extremely cheap: $0.15/1M input, $0.60/1M output
    * Good vision support
    * Cost: ~$0.50-2 for 250-350 queries
  - **Final Testing/Demos**: Claude Sonnet 4.5
    * Best quality for validation and presentations
    * Switch manually via .env flag on Day 3
    * Use only for final 50 validation queries
    * Cost: ~$3-5 for final testing
  - **Total MVP Cost**: $0-7 (vs $15-20 with Sonnet only)
- **Recommended Models**:
  - **Gemini 1.5 Flash** (`gemini-1.5-flash`): **DEFAULT for MVP development**
  - **GPT-4o mini** (`gpt-4o-mini`): Fallback if needed
  - **Claude Sonnet 4.5** (`claude-sonnet-4-5-20250929`): Premium for final validation
- **Configuration** (Manual switching via .env):
  ```bash
  # Day 1-2: Use Gemini Flash (FREE)
  LLM_PROVIDER=gemini
  LLM_MODEL=gemini-1.5-flash
  GEMINI_API_KEY=your_key
  
  # If needed: Switch to GPT-4o mini
  # LLM_PROVIDER=openai
  # LLM_MODEL=gpt-4o-mini
  # OPENAI_API_KEY=your_key
  
  # Day 3 final testing: Switch to Sonnet
  # LLM_PROVIDER=claude
  # LLM_MODEL=sonnet-4.5
  # CLAUDE_API_KEY=your_key
  ```
- **Orchestration Framework**: LangChain or LlamaIndex (for RAG pipeline)
  - **MVP Note**: May use lightweight direct API calls if framework adds complexity
- **Embeddings**: 
  - OpenAI `text-embedding-3-small` (or `text-embedding-ada-002`)
  - Cost: ~$0.02 per embedding run (very cheap)
  - Or open-source alternatives (sentence-transformers) if preferred

**Model Selection Rationale**:
- **Why Gemini Flash for MVP**: FREE tier covers most/all development; good quality; fast; excellent for cost-conscious iteration
- **Why GPT-4o mini as fallback**: 95% cheaper than Sonnet; good quality; widely available; easy to switch
- **Why Sonnet 4.5 for finals only**: Best quality for validation; demonstrates production capability; acceptable cost for limited final testing
- **Cost-benefit**: $15-20 saved on development; can iterate freely without worrying about costs

**PDF & Document Processing**:
- **PDF Reading**: PyMuPDF (fitz) or pdfplumber
- **OCR** (optional for scanned PDFs): pytesseract + Tesseract engine
- **Image Extraction**: PyMuPDF or pdf2image
- **Image Processing**: Pillow (PIL)

**Web Framework** (if web UI):
- **Options**: 
  - Streamlit (fastest for MVP, built-in chat UI)
  - FastAPI + React (more flexible, production-ready)
  - Gradio (simple, good for demos)
- **Recommended for MVP**: Streamlit (quickest to implement chat interface)

**Additional Libraries**:
- **Environment Variables**: python-dotenv (for API keys)
- **HTTP Clients**: httpx or requests (for API calls)
- **JSON/Config**: pydantic (data validation)
- **Async Processing**: asyncio (built-in Python)
- **Logging**: logging (built-in Python) or loguru

**Development Tools**:
- **Testing**: pytest
- **Code Quality**: black (formatter), flake8 (linter)
- **Type Checking**: mypy (optional)

**Version Constraints** (Example for MVP):
```
# Core LLM APIs (in priority order for MVP)
google-generativeai>=0.3.0     # Gemini API (DEFAULT - free tier)
openai>=1.0.0                  # For embeddings + GPT-4o mini fallback
anthropic>=0.18.0              # Claude API (final testing only)

# RAG and Vector Database
chromadb>=0.4.0                # Vector store (or use FAISS)

# PDF Processing
pymupdf>=1.23.0                # PDF text and image extraction
pillow>=10.0.0                 # Image processing

# Web Framework
streamlit>=1.30.0              # Simple chat UI (recommended for MVP)

# Utilities
python-dotenv>=1.0.0           # Environment variables (.env file)
pydantic>=2.0.0                # Data validation (optional)

# Development (optional)
pytest>=7.0.0                  # Testing
```

**Minimal MVP Stack** (if time is tight):
- google-generativeai (Gemini - FREE)
- openai (embeddings only)
- chromadb (vector store)
- pymupdf (PDF processing)
- streamlit (UI)
- python-dotenv (config)

**Can add later if time permits**:
- anthropic (Claude for finals)
- Advanced features

**API Keys Required**:
- ✅ GEMINI_API_KEY (free, no credit card)
- ✅ OPENAI_API_KEY (for embeddings, $5 credit)
- ⏭️ CLAUDE_API_KEY (optional for Day 3, $10 credit)

**Production Additions** (Future):
- Docker & Docker Compose
- PostgreSQL + pgvector
- Redis (caching)
- Nginx (reverse proxy)
- Cloud storage (S3/Azure Blob)
- Monitoring (Prometheus, Grafana)

### 5.3 Data Constraints
- **PDF Format**: Text-layer PDFs preferred, scanned images supported with OCR
- **File Size**: Individual PDFs < 20 MB
- **Total Data**: < 5 GB for MVP (1 PDF + database + indexes)

### 5.4 Architecture Constraints
- **Portability**: Must migrate from local to cloud without major code rewrite
- **Modularity**: Document processors, LLM adapters, database layer must be swappable
- **Deployment**: 
  - MVP: Direct Python execution (virtual environment, simple setup)
  - Production: Containerization (Docker) for cloud deployment

---

## 6. User Interface Requirements

### 6.1 Layout
- Chat-style interface (left sidebar: history, main area: conversation)
- Query input box (text area with submit button)
- Response area (scrollable conversation history)
- Context panel (optional, right sidebar for related info)

### 6.2 Key Interactions

**Query Submission**:
- Type natural language query
- Press Enter or click "Ask" button
- Loading indicator while processing

**Response Display**:
- Clear, formatted text responses
- Embedded diagrams/images when relevant
- "Last Ticket" info box (when applicable)
- Source references (P&ID page number, database table)

**Last Ticket Display** (Mock Data MVP):

Example for PSV-101:
```
📋 Last Ticket on PSV-101
Equipment: V-101 (High Pressure Separator)
Issue: Safety valve actuator slow response
Reported: 2025-09-15
Resolution: Actuator replaced and calibrated per manufacturer specs
Resolved: 2025-09-16
Status: ✅ Closed
Priority: High
```

Example for FT-103A:
```
📋 Last Ticket on FT-103A
Equipment: P-103 (Export Pump)
Issue: Flow transmitter reading erratic
Reported: 2025-10-01
Resolution: Transmitter recalibrated, impulse lines cleared
Resolved: 2025-10-02
Status: ✅ Closed
Priority: Medium
```

Example for V-102:
```
📋 Last Ticket on V-102
Equipment: V-102 (Low Pressure Separator)
Issue: Separator pressure relief valve set point verification
Reported: 2025-10-10
Resolution: PSV-102 tested and verified at 75 PSIG set pressure
Resolved: 2025-10-10
Status: ✅ Closed
Priority: Low
```

### 6.3 Example Queries (To Display in UI)

**Simple Queries** (Quick examples for users):
- "What is V-101?"
- "Tell me about PSV-101"
- "What are the specs for P-103?"

**Connection Queries**:
- "Show me all inflows and outflows for V-101"
- "What feeds into V-102?"
- "What's downstream of the compressor?"

**Specification Queries**:
- "What are the operating conditions for V-101?"
- "What's the design pressure of the high pressure separator?"
- "What size motor is on P-103?"

**Visual/Complex Queries**:
- "Which instruments are connected to V-101?"
- "What's upstream of the export pump?"
- "Show me the gas processing flow path"
- "How does the separation system work?"

**Maintenance Context**:
- "Has PSV-101 had any recent issues?"
- "Show me tickets for the export pump"
- "Any maintenance on V-102?"

---

## 7. Data Requirements

### 7.1 P&ID Documents
- **Format**: PDF (text-layer or scanned)
- **Quantity**: 1 document (MVP), 40-50 (production)
- **Naming Convention**: `[Plant]-[Unit]-[System]-PID-[Rev].pdf`
- **Storage**: Local filesystem (MVP), cloud storage (production)
- **Metadata**: Document title, revision, date, plant/unit/system

### 7.2 Structured Asset Data (SQLite Schema)

**CRITICAL IMPLEMENTATION NOTE:**

⚠️ **The sample data provided below is for DOCUMENTATION and UNDERSTANDING only.**

**DO NOT hardcode any equipment, tags, or specifications from the sample P&ID into the application code.**

The system MUST dynamically extract data from PDFs through the ingestion pipeline. The same ingestion script must work on:
- Different oil & gas facilities
- Different P&ID formats and layouts  
- Different tag nomenclature systems
- Different equipment types

**The sample SQL INSERT statements show:**
- ✅ What KIND of data to extract
- ✅ What the database schema looks like when populated
- ✅ Examples for testing and validation

**They are NOT:**
- ❌ Meant to be copied into code
- ❌ The only data the system will ever handle
- ❌ A substitute for proper PDF parsing/extraction

**P&ID Document Characteristics** (Based on Sample):
- Multi-page structure: Overview PFD + Legend + Detail P&IDs
- 7 pages total: Page 1 (Process Flow Diagram), Page 2 (Legend), Pages 3-7 (Detailed P&IDs)
- Equipment: V-101, V-102, P-103, C-104, H-105
- Tag nomenclature follows ISA standards
- Piping classes: A, B, D, E, F with pressure ratings

**Tables**:

**SIMPLIFIED SCHEMA FOR MVP (3-Day Timeline):**

```sql
-- Documents metadata
CREATE TABLE documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,              -- e.g., 'D-254-001_Gas_Production_Facility_Rev1.pdf'
    file_path TEXT NOT NULL,              -- Path in data/pdfs/
    document_number TEXT,                 -- e.g., 'D-254-001'
    document_title TEXT,                  -- e.g., 'Gas Production Facility'
    revision TEXT,                        -- e.g., '1'
    total_pages INTEGER,                  -- Total pages in document
    facility TEXT,                        -- e.g., 'Gas Production Facility'
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Page-level data (links text to images for hybrid approach)
CREATE TABLE document_pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,         -- 1, 2, 3...
    page_type TEXT,                       -- 'PFD', 'Legend', 'Detail_PID'
    page_title TEXT,                      -- e.g., 'High Pressure Separator'
    sheet_number TEXT,                    -- e.g., '3 OF 6'
    image_path TEXT NOT NULL,             -- Path to page image: 'data/processed/D-254-001/page_3.png'
    text_content TEXT,                    -- Extracted text from this page
    has_equipment BOOLEAN DEFAULT 0,      -- Flag if page shows major equipment
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

-- Optional: Mock tickets (can be hardcoded in code instead of DB for speed)
CREATE TABLE mock_tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_or_equipment TEXT NOT NULL,       -- e.g., 'PSV-101', 'V-101'
    issue_description TEXT,
    reported_date DATE,
    resolution TEXT,
    resolved_date DATE,
    status TEXT DEFAULT 'Closed',         -- 'Open', 'Closed', 'In Progress'
    priority TEXT                         -- 'High', 'Medium', 'Low'
);
```

**WHY SIMPLIFIED:**
- ✅ Fast to implement (2-3 tables vs 8 tables)
- ✅ RAG + Vision API can answer queries without extensive structured data
- ✅ Reduces ingestion complexity (no equipment/tag extraction needed)
- ✅ Sufficient for MVP proof-of-concept
- ✅ Can add detailed tables (equipment, tags, connections) in post-MVP phase

**DEFERRED TO POST-MVP:**
```sql
-- These tables are NOT needed for MVP:
-- ❌ equipment (detailed specs)
-- ❌ tags (instrument/valve details)  
-- ❌ piping_lines (line specifications)
-- ❌ connections (topology mapping)
-- ❌ process_streams (stream data)
```

**Rationale**: Vision API can see equipment on diagrams. RAG can retrieve text mentioning equipment. Structured extraction is a future optimization, not MVP requirement.

**Sample Data** (Based on Actual P&ID):

```sql
-- Document record (created by ingestion script)
INSERT INTO documents (file_name, file_path, document_number, document_title, revision, total_pages, facility) VALUES
('D-254-001_Gas_Production_Facility_Rev1.pdf', 'data/pdfs/D-254-001_Gas_Production_Facility_Rev1.pdf', 'D-254-001', 'Gas Production Facility', '1', 7, 'Gas Production Facility');

-- Page records (created by ingestion script)
INSERT INTO document_pages (document_id, page_number, page_type, page_title, sheet_number, image_path, has_equipment) VALUES
(1, 1, 'PFD', 'Process Flow Diagram', '1 OF 1', 'data/processed/D-254-001/page_1.png', 1),
(1, 2, 'Legend', 'Legend Sheet', '1 OF 6', 'data/processed/D-254-001/page_2.png', 0),
(1, 3, 'Detail_PID', 'High Pressure Separator', '2 OF 6', 'data/processed/D-254-001/page_3.png', 1),
(1, 4, 'Detail_PID', 'Low Pressure Separator', '3 OF 6', 'data/processed/D-254-001/page_4.png', 1),
(1, 5, 'Detail_PID', 'Pipeline Pump', '4 OF 6', 'data/processed/D-254-001/page_5.png', 1),
(1, 6, 'Detail_PID', 'Gas Compressor', '5 OF 6', 'data/processed/D-254-001/page_6.png', 1),
(1, 7, 'Detail_PID', 'Gas Compressor Utility Details', '6 OF 6', 'data/processed/D-254-001/page_7.png', 1);

-- Mock tickets (can be hardcoded in application code instead of DB for MVP speed)
INSERT INTO mock_tickets (tag_or_equipment, issue_description, reported_date, resolution, resolved_date, status, priority) VALUES
('PSV-101', 'Safety valve actuator slow response', '2025-09-15', 'Actuator replaced and calibrated per manufacturer specs', '2025-09-16', 'Closed', 'High'),
('FT-103A', 'Flow transmitter reading erratic', '2025-10-01', 'Transmitter recalibrated, impulse lines cleared', '2025-10-02', 'Closed', 'Medium'),
('V-102', 'Separator pressure relief valve set point verification', '2025-10-10', 'PSV-102 tested and verified at 75 PSIG set pressure', '2025-10-10', 'Closed', 'Low');
```

**Alternative for Mock Tickets (Hardcoded in Code - Faster for MVP):**

```python
# Can be defined directly in Python instead of database
MOCK_TICKETS = {
    "PSV-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "Safety valve actuator slow response",
        "reported": "2025-09-15",
        "resolution": "Actuator replaced and calibrated per manufacturer specs",
        "resolved": "2025-09-16",
        "status": "Closed",
        "priority": "High"
    },
    "FT-103A": {
        "equipment": "P-103 (Export Pump)",
        "issue": "Flow transmitter reading erratic",
        "reported": "2025-10-01",
        "resolution": "Transmitter recalibrated, impulse lines cleared",
        "resolved": "2025-10-02",
        "status": "Closed",
        "priority": "Medium"
    },
    "V-102": {
        "equipment": "V-102 (Low Pressure Separator)",
        "issue": "Separator pressure relief valve set point verification",
        "reported": "2025-10-10",
        "resolution": "PSV-102 tested and verified at 75 PSIG set pressure",
        "resolved": "2025-10-10",
        "status": "Closed",
        "priority": "Low"
    }
}
```

**Recommendation for MVP**: Use hardcoded dictionary approach - saves 30-60 minutes vs database implementation.

### 7.3 Vector Store (RAG)
- **Purpose**: Store document embeddings for semantic search
- **Technology**: ChromaDB, FAISS, or similar (lightweight for MVP)
- **Storage**: Local filesystem (MVP), cloud-based (production)
- **Embedding Model**: OpenAI `text-embedding-3-small` or similar

### 7.4 Data Ingestion Process

**CRITICAL DESIGN PRINCIPLE:**

⚠️ **The ingestion pipeline must be GENERIC and work with ANY P&ID document.**

**Design Requirements:**
- ✅ Parse and extract data dynamically from PDF content
- ✅ Handle different P&ID layouts, formats, and conventions
- ✅ Discover equipment, tags, and specifications at runtime
- ✅ Work on documents beyond the sample (different facilities, companies, formats)
- ✅ No hardcoded equipment IDs, tag nomenclature, or specifications

**The sample P&ID (D-254-001) is:**
- ✅ A reference for TESTING the ingestion pipeline
- ✅ An example to understand WHAT to extract
- ✅ A baseline for VALIDATION and accuracy testing

**It is NOT:**
- ❌ The only document the system will process
- ❌ A source for hardcoding data into the application
- ❌ Representative of all P&ID formats (must handle variations)

**Sample P&ID Characteristics**:
- **Facility**: Gas Production Facility
- **Document Number**: D-254-001 Rev 1
- **Structure**: Multi-page PDF
  - Page 1: Process Flow Diagram (PFD) with stream data table
  - Page 2: Legend sheet (symbols, instrument functions, piping classes)
  - Pages 3-7: Detailed P&IDs (V-101, V-102, P-103, C-104, C-104 utilities)
- **Equipment Count**: 5 major pieces (V-101, V-102, P-103, C-104, H-105)
- **Tag Count**: 50+ tags (valves, instruments, controllers)
- **Complexity**: Industrial-grade with ISA standard symbols

**Directory Structure**:
```
project-root/
├── data/
│   ├── pdfs/                           # Source P&ID PDF files
│   │   └── D-254-001_Gas_Production_Facility_Rev1.pdf
│   └── processed/                      # Extracted images per page
│       └── D-254-001/
│           ├── page_1_pfd.png         # Process flow diagram
│           ├── page_2_legend.png       # Legend and symbols
│           ├── page_3_v101.png         # High pressure separator
│           ├── page_4_v102.png         # Low pressure separator
│           ├── page_5_p103.png         # Export pump
│           ├── page_6_c104.png         # Gas compressor
│           └── page_7_c104_util.png    # Compressor utilities
├── database/
│   ├── assets.db                       # SQLite database
│   └── vector_store/                   # ChromaDB or FAISS index
│       └── [vector index files]
├── scripts/
│   └── ingest_pdfs.py                  # PDF ingestion script
├── app/
│   ├── main.py                         # Main application
│   ├── query_engine.py                 # Query processing
│   ├── llm_adapter.py                  # Multi-LLM abstraction
│   └── query_router.py                 # Hybrid routing logic
├── requirements.txt
└── README.md
```

**Two-Phase Workflow**:

**Phase 1: Data Preparation** (Offline, run once per PDF)
```bash
# Run ingestion script
python scripts/ingest_pdfs.py

# What it does:
# 1. Scans data/pdfs/ directory for PDF files
# 2. For each PDF:
#    - Extract text content per page
#    - Extract each page as high-res image (for vision API)
#    - Identify page types (PFD, Legend, Detail P&ID)
#    - Create text chunks for RAG (page-level and section-level)
#    - Generate embeddings for text chunks
#    - Store in vector database
#    - Parse and extract structured data:
#      * Equipment specifications (from text boxes)
#      * Tag nomenclature (from diagram labels)
#      * Stream data (from PFD tables)
#      * Piping specifications (from legend)
#    - Update SQLite with:
#      * Document metadata
#      * Equipment table entries
#      * Tag table entries
#      * Process stream data
# 3. Build search indexes
# 4. Generate ingestion report
```

**Phase 2: Query Runtime** (Online, main application)
```bash
# Run main application
python app/main.py

# Application:
# - Loads pre-processed databases
# - No PDF processing at runtime
# - Fast query responses from indexes
# - Sends page images to vision API only when needed
```

**Ingestion Script Requirements** (`ingest_pdfs.py`):

**Inputs**:
- PDF files in `data/pdfs/` directory
- Configuration file (embedding model, chunk size, LLM provider for extraction)

**Processing Steps**:

**SIMPLIFIED INGESTION FOR MVP (3-Day Timeline):**

1. **Document Discovery**: 
   - Scan `data/pdfs/` for PDF files
   - Extract basic metadata from filename

2. **Page-Level Processing**:
   - Extract text from each page (PyMuPDF or pdfplumber)
   - Convert each page to PNG image (300 DPI for vision quality)
   - Store images in `data/processed/[document_id]/page_N.png`

3. **Text Chunking** (Simplified):
   - **Page-level chunks**: Each page becomes one or more chunks
   - Chunk size: ~800-1200 tokens (balance context vs retrieval precision)
   - No overlap needed for MVP (saves processing time)
   - Simple split by page or by paragraph breaks

4. **Embedding Generation**:
   - Generate vector embeddings for each text chunk
   - Model: OpenAI `text-embedding-3-small` (fast, good quality)
   - Store embeddings in vector database

5. **Storage** (Minimal):
   - **Vector DB** (ChromaDB/FAISS):
     * Text chunks + embeddings
     * Metadata: page number, document ID
   - **SQLite**:
     * Document record → `documents` table
     * Page records → `document_pages` table
   - **File System**:
     * Page images → `data/processed/[document_id]/`

6. **Index Building**:
   - Create vector similarity index
   - SQLite indexes on document_id, page_number

**DEFERRED TO POST-MVP (Complex Extraction):**
- ❌ Equipment specification parsing
- ❌ Tag identification from diagram labels
- ❌ Stream table data extraction
- ❌ Piping class mapping
- ❌ Topology/connection discovery
- ❌ Symbol recognition

**Why Deferred:** Vision API can "see" equipment and tags on diagrams. RAG can retrieve text mentioning specifications. Structured extraction is optimization, not requirement for answering queries.

**Outputs**:
- Updated `database/assets.db` with:
  * Document record in `documents` table
  * Page records in `document_pages` table
- Populated `database/vector_store/` with text embeddings
- Page images in `data/processed/D-254-001/`
- Simple ingestion log:
  ```
  ✓ D-254-001_Gas_Production_Facility_Rev1.pdf
    - 7 pages processed
    - 7 images saved
    - ~15-20 text chunks generated
    - All embeddings stored successfully
  ```

**Re-run Conditions**:
- New PDF added to `data/pdfs/`
- PDF updated (new revision detected)
- Embedding model changed
- Chunking strategy modified

**Error Handling**:
- Skip corrupted PDFs with warning log
- Log failed pages but continue processing others
- Retry logic for API calls (embedding generation)
- Graceful degradation (text extraction fails → still save images)

**Performance Considerations** (MVP):
- Single PDF (7 pages): ~45-60 seconds total processing time
  * Text extraction: ~10 seconds
  * Image extraction: ~10 seconds  
  * Embedding generation: ~20-30 seconds (API latency)
  * Database writes: ~5 seconds
- Progress logging for user feedback
- Simple implementation prioritized over optimization

---

## 8. Integration Requirements

### 8.1 LLM API Integration

**Claude API**:
- Endpoint: Anthropic API
- Model: `claude-sonnet-4-5-20250929`
- Vision: Supported
- Context Window: ~200K tokens

**OpenAI API**:
- Endpoint: OpenAI API
- Model: `gpt-4-vision-preview` or later
- Vision: Supported
- Context Window: ~128K tokens

**Gemini API**:
- Endpoint: Google AI API
- Model: `gemini-pro-vision` or later
- Vision: Supported
- Context Window: Variable

**Requirements**:
- Unified adapter interface
- API key management via environment variables
- Rate limiting and retry logic
- Cost tracking per query

### 8.2 External Systems (Future)

**Out of Scope for MVP**:
- SCADA systems
- Maintenance management systems
- ERP/EAM systems
- Document management systems

---

## 9. Success Criteria

### 9.1 MVP Acceptance Criteria

The MVP will be considered successful when:

1. ✅ User can upload 1 P&ID PDF (sample document)
2. ✅ Ingestion script processes PDF successfully:
   - Extracts 7 page images
   - Extracts text and creates chunks
   - Generates embeddings
   - Populates SQLite with document/page records
3. ✅ User can ask natural language questions
4. ✅ System responds accurately to:
   - Simple tag/equipment queries (>85% accuracy via RAG)
   - Visual/spatial queries (>80% accuracy via vision API)
   - Mixed queries using hybrid approach
5. ✅ Query response time: ~5-15 seconds (acceptable for MVP)
6. ✅ System runs stably on Mac M3 with 8GB RAM
7. ✅ Mock "Last Ticket" data displays correctly for 3-5 tags
8. ✅ User can switch between Claude and Gemini via .env configuration
9. ✅ **Token usage tracking works correctly**:
   - Console prints tokens and cost after each query
   - Session summary displays at end
   - Logs written to file for analysis
10. ✅ Basic Streamlit UI allows:
   - Query input
   - Response display
   - Simple conversation history
11. ✅ System handles errors gracefully (API failures, invalid queries)

**Simplified Compared to Original:**
- ❌ No complex structured extraction required
- ❌ No multi-table database population
- ❌ No sophisticated ML routing
- ❌ No OpenAI integration
- ⏱️ 3-day delivery target vs open-ended development

**Testing Verification**:
- Run 10-20 test queries covering different types
- Verify token counts are reasonable (not excessive)
- Confirm cost tracking matches actual API usage
- Validate logs contain all required fields

### 9.2 Production Readiness Criteria (Future)

1. Supports 40-50 P&ID documents
2. Multi-user concurrent access
3. Cloud deployment operational
4. Horizontal scaling validated
5. User authentication and RBAC functional
6. Integration with at least one external system (SCADA/EAM)

---

## 10. Out of Scope

### 10.1 Explicitly Not Included in MVP

- Real-time data integration (SCADA, DCS, historians)
- Historical maintenance records from external systems
- ERP/EAM integration
- Mobile application (iOS/Android)
- Multi-user collaboration features
- Data editing/modification capabilities
- Workflow automation
- Advanced analytics and reporting
- Custom P&ID drawing tools
- Version control for P&IDs
- Compliance reporting
- Training/simulation modes

---

## 11. Future Roadmap

### Phase 2: Production Scale (3-6 months post-MVP)
- Support 40-50 P&ID documents
- Cloud deployment (AWS/Azure/GCP)
- Multi-user with authentication
- Enhanced query performance optimization
- Mobile-responsive web interface

### Phase 3: System Integration (6-12 months post-MVP)
- SCADA real-time data integration
- Maintenance history system connection
- ERP/EAM integration
- Live sensor data overlay on P&IDs

### Phase 4: Advanced Features (12+ months post-MVP)
- Predictive maintenance insights
- Anomaly detection from sensor patterns
- Automated report generation
- Multi-plant deployments
- Advanced analytics dashboards

---

## 12. Assumptions and Dependencies

### 12.1 Assumptions
- P&ID PDFs have readable text layers or are high-quality scans
- Structured asset data (tags, equipment) will be pre-populated in SQLite
- User has basic familiarity with P&IDs and industrial terminology
- Internet connection available for LLM API calls
- LLM API providers maintain service availability and pricing

### 12.2 Dependencies
- Claude API, OpenAI API, or Gemini API availability
- SQLite database engine
- Python ecosystem libraries (LangChain, vector databases, PDF processing)
- Mac OS compatibility for development tools

### 12.3 Risks

**LLM API Cost**:
- **Risk**: Vision queries can be expensive at scale with premium models
- **Mitigation**: 
  - **MVP**: Use Gemini Flash free tier (1,500 req/day) for development = $0
  - Fallback to GPT-4o mini if needed (95% cheaper than Sonnet)
  - Token usage tracking to identify expensive queries
  - Reserve Claude Sonnet only for final validation
  - Post-MVP: Hybrid routing + caching for 90%+ cost reduction
- **MVP Budget**: 
  - Gemini Flash: $0 (free tier)
  - GPT-4o mini fallback: $0.50-1
  - Claude Sonnet finals: $2-4
  - **Total: $2-5** (vs $15-20 all-Sonnet)

**Vision Accuracy**:
- **Risk**: Complex P&IDs may challenge LLM interpretation
- **Mitigation**: 
  - Use Sonnet 4.5 (best vision model) for MVP
  - Structured data fallback via RAG
  - User feedback loop for corrections
  - High-resolution page images (300 DPI)

**Performance on 8GB RAM**:
- **Risk**: Memory constraints on local machine
- **Mitigation**: 
  - Optimize embedding storage
  - Lazy loading of images
  - Efficient caching
  - Simple vector database (ChromaDB/FAISS)
  - Limit concurrent operations

**Cloud Migration Complexity**:
- **Risk**: Architecture changes during transition
- **Mitigation**: 
  - Containerization ready (post-MVP)
  - Cloud-agnostic design from start
  - Environment-based configuration
  - Database abstraction layer

**Token Usage Variability**:
- **Risk**: Token costs vary significantly by query type
- **Mitigation**:
  - Comprehensive tracking and logging
  - Identify patterns in expensive queries
  - Optimize prompts to reduce tokens
  - Post-MVP: Intelligent model routing

**Expected Token Usage** (MVP Testing Estimates):

| Query Type | Input Tokens | Output Tokens | Cost/Query (Gemini Flash) | Cost/Query (GPT-4o mini) | Cost/Query (Sonnet) | Example |
|------------|-------------|---------------|--------------------------|--------------------------|---------------------|---------|
| Simple RAG (text only) | 800-1,500 | 100-300 | **$0 (free)** | $0.0002-0.0004 | $0.003-$0.007 | "What is PSV-101?" |
| Vision (1 page) | 5,000-8,000 | 200-500 | **$0 (free)** | $0.0010-0.0017 | $0.018-$0.032 | "Show me V-101" |
| Complex (vision + reasoning) | 8,000-15,000 | 500-1,000 | **$0 (free)** | $0.0018-$0.0033 | $0.032-$0.060 | "Explain gas flow" |

**MVP Testing Budget** (350 queries with Gemini Flash default):

| Scenario | Provider Mix | Total Cost | vs All-Sonnet |
|----------|-------------|------------|---------------|
| **Best Case** (all within free tier) | 350 Gemini Flash | **$0** | Save $18-25 |
| **Typical** (some GPT-4o mini fallback) | 300 Gemini + 30 GPT-4o mini + 20 Sonnet | **$1-2** | Save $13-18 |
| **Final Testing** (switch to Sonnet Day 3) | 280 Gemini + 20 GPT-4o mini + 50 Sonnet | **$2-5** | Save $10-15 |

**Note**: Actual costs depend on query complexity and free tier availability. Token tracking provides accurate measurements.

---

## 13. Glossary

| Term | Definition |
|------|------------|
| P&ID | Piping and Instrumentation Diagram - schematic representation of process equipment and instrumentation |
| Tag | Unique identifier for equipment, instruments, or lines in a plant |
| SCADA | Supervisory Control and Data Acquisition - control system architecture |
| RAG | Retrieval Augmented Generation - AI technique combining retrieval and generation |
| EAM | Enterprise Asset Management - software for managing physical assets |
| ERP | Enterprise Resource Planning - integrated business management software |
| ISA | International Society of Automation - industry standards body |
| LLM | Large Language Model - AI model for natural language processing |
| SQLite | Lightweight embedded database engine |

---

## Appendix A: Sample User Queries

**Based on Actual P&ID: Gas Production Facility (D-254-001)**

### Tag Identification

**Equipment Tags**:
- "What is V-101?"
  - Expected: High Pressure Separator, 60" I.D. x 18'-6" S/S, Design: 1200 PSIG @ 300°F
- "Tell me about P-103"
  - Expected: Export Pump, Capacity: 100 GPM @ 2200 PSIG, Motor: 200 HP
- "Describe C-104"
  - Expected: Gas Compressor (1st Stage), 0.50 MMSCFD capacity, Suction: 50 PSIG at 70°F
- "What is H-105?"
  - Expected: Compressor Discharge Cooler, Duty: 0.12 MMBTU/HR

**Valve Tags**:
- "What is PSV-101?"
  - Expected: Pressure Safety Valve on V-101 (High Pressure Separator)
- "Tell me about SDV-102A"
  - Expected: Shutdown Valve 102A on low pressure separator system
- "What is FV-103C?"
  - Expected: Flow control valve on export pump discharge

**Instrument Tags**:
- "What is FT-103A?"
  - Expected: Flow Transmitter 103A on export pump system
- "Describe LIC-101A"
  - Expected: Level Indicator Controller for V-101 high pressure separator
- "What is PIC-101A?"
  - Expected: Pressure Indicator Controller for V-101
- "Tell me about FIC-103C"
  - Expected: Flow Indicator Controller for export pump flow control

### Connections and Topology

**Upstream/Downstream Queries**:
- "What feeds into V-101?"
  - Expected: Production header (from note 1), through line 14"-A
- "What's downstream of V-101?"
  - Expected: Gas to C-104 compressor (6"-D), Liquid to V-102 separator (4"-D)
- "Show me all inflows and outflows for V-101"
  - Expected: Inlet from production header; Gas outlet to compressor; Liquid outlet to V-102; Flare connection
- "What feeds into V-102?"
  - Expected: Liquid from V-101 via 4"-D line, Compressor spillback via 6"-A
- "What's upstream of P-103?"
  - Expected: V-102 low pressure separator liquid outlet

**Equipment Interconnections**:
- "What equipment is connected to V-101?"
  - Expected: Upstream: Production header; Downstream: V-102, C-104, Flare system
- "Show me the flow path from V-101 to C-104"
  - Expected: V-101 → 6"-D line → C-104 compressor suction
- "What connects V-102 to the export pipeline?"
  - Expected: V-102 → P-103 pump → 4"-F line → Export liquid pipeline
- "How does gas flow through the system?"
  - Expected: Production Header → V-101 → C-104 → H-105 → Export Gas Pipeline

**Line Identification**:
- "What is line 4"-D?"
  - Expected: Liquid line from V-101 to V-102, Class D piping
- "Show me all valves on line 6"-D"
  - Expected: Control valves and safety devices on gas line to compressor
- "What piping class is used for the export pump discharge?"
  - Expected: 4"-F line, Class F piping (high pressure)

### Specifications and Parameters

**Operating Conditions**:
- "What are the operating conditions for V-101?"
  - Expected: 350 PSIG (24.2 BAR) at 70°F (21°C), Liquid residence time: 3 MIN
- "What's the design pressure for V-102?"
  - Expected: Design: 75 PSIG (5.2 BAR)/FV at 300°F, Operating: 50 PSIG at 38°F
- "What are the pump specifications for P-103?"
  - Expected: 100 GPM @ 2200 PSIG, Differential pressure: 2100 PSIG, Motor: 200 HP
- "What's the capacity of C-104?"
  - Expected: 0.50 MMSCFD (14160 SCMD), Suction: 50 PSIG at 70°F, Discharge: 350 PSIG at 279°F

**Design Parameters**:
- "What's the design temperature of the high pressure separator?"
  - Expected: Design: 300°F (149°C), Operating: 70°F (21°C)
- "What size is V-102?"
  - Expected: 42" I.D. (1.07 M) x 13'-6" S/S (4.11 M)
- "What motor is on the export pump?"
  - Expected: 200 HP motor
- "What's the duty of H-105?"
  - Expected: 0.12 MMBTU/HR (35.2 KW) cooling duty

### Visual/Spatial Queries

**Layout Questions**:
- "Show me where PSV-101 is located on the diagram"
  - Expected: On V-101 vessel, flare connection (Sheet 1 and Sheet 3)
- "How is the separation system laid out?"
  - Expected: Two-stage separation: V-101 (HP) → V-102 (LP) with gas/liquid split
- "What's the flow direction from the production header?"
  - Expected: Production Header → V-101 → Split to gas (C-104) and liquid (V-102) paths
- "Show me the compressor system configuration"
  - Expected: C-104 compressor → H-105 cooler → Export gas pipeline, with anti-surge control

**Process Flow**:
- "How does liquid flow to the export pipeline?"
  - Expected: Production → V-101 → V-102 → P-103 → Export pipeline
- "What's the gas processing path?"
  - Expected: Production → V-101 → C-104 → H-105 → Export gas pipeline
- "Where does the flare system connect?"
  - Expected: Multiple connections from V-101, V-102, and pressure relief devices

### Safety and Control

**Safety Devices**:
- "What safety devices are on V-101?"
  - Expected: PSV-101, SDV-101, PSHH-101D, PSLL-101D, level switches
- "What pressure relief is on the compressor discharge?"
  - Expected: PSV-104A, PSV-104B, rupture disk
- "What shutdown valves are in the system?"
  - Expected: SDV-101, SDV-102A, SDV-102B, SDV-103, SDV-104, SDV-106

**Control Loops**:
- "What controls the level in V-101?"
  - Expected: LIC-101A with LV-101 control valve
- "How is V-101 pressure controlled?"
  - Expected: PIC-101A and PIC-101B controllers
- "What controls the export pump flow?"
  - Expected: FIC-103C with FV-103C control valve
- "What's the anti-surge control for C-104?"
  - Expected: FIC-104 with FV-104 anti-surge valve

### Contextual with Maintenance

**With Mock Ticket Data**:
- "Has PSV-101 had any recent issues?"
  - Expected: Last issue: Valve actuator slow response, Resolved: 2025-09-16, Actuator replaced
- "Show me recent maintenance on P-103"
  - Expected: FT-103A transmitter recalibrated 2025-10-02 due to erratic readings
- "Any open tickets for V-102?"
  - Expected: No open tickets, Last ticket: PSV set point verification (Closed)
- "What was the last issue with the flow transmitter on the export pump?"
  - Expected: FT-103A erratic readings, resolved by recalibration and impulse line clearing

### Complex Multi-Part Queries

**System Understanding**:
- "Explain the separation process in this facility"
  - Expected: Two-stage separation (HP and LP), gas compression, liquid export
- "What happens if V-101 pressure gets too high?"
  - Expected: PSV-101 relief to flare, PSHH-101D alarm, potential SDV-101 shutdown
- "How does the compressor protect against surge?"
  - Expected: FIC-104 anti-surge controller with spillback valve FV-104 to V-102
- "What are all the export paths from this facility?"
  - Expected: Gas export via C-104/H-105 (10"-B), Liquid export via P-103 (4"-F)

### Process Stream Data

**From PFD Table**:
- "What's the temperature at stream 1?"
  - Expected: 70°F at production header inlet
- "What's the pressure at the compressor discharge?"
  - Expected: Stream 6: 364.69 PSIA (350 PSIG) at 279.08°F
- "What's the liquid rate to the export pump?"
  - Expected: Stream 8: 73 GPM (2492 BOPD)
- "What's the gas composition at the inlet?"
  - Expected: 90% Methane, 2% each of Ethane, Propane, N-Butane, N-Pentane, N-Hexane

---

**Query Complexity Levels:**

**Level 1 - Simple Lookup** (Database only):
- "What is PSV-101?"
- "What's the capacity of P-103?"

**Level 2 - Structured Query** (Database + some reasoning):
- "What feeds into V-101?"
- "What safety devices are on V-102?"

**Level 3 - Visual Understanding** (Vision API needed):
- "Show me the flow path from V-101 to the export pipeline"
- "Where is the compressor located on the diagram?"

**Level 4 - Complex Analysis** (Hybrid: Vision + Database + Reasoning):
- "Explain the complete gas processing flow"
- "What happens during a high-pressure event in V-101?"

---

**END OF APPENDIX A**

---

## Appendix B: Reference Documents

### Sample P&ID Document

**Document**: Gas Production Facility P&ID (D-254-001 Rev 1)  
**Source**: Kenexis Consulting Corporation training sample  
**Purpose**: MVP development and testing reference

**Document Structure**:
- **Total Pages**: 7
- **Page 1**: Process Flow Diagram with stream data table
- **Page 2**: Legend sheet (symbols, instruments, piping specs)
- **Page 3**: High Pressure Separator (V-101) detail
- **Page 4**: Low Pressure Separator (V-102) detail
- **Page 5**: Pipeline Pump (P-103) detail
- **Page 6**: Gas Compressor (C-104) detail
- **Page 7**: Gas Compressor utilities detail

**Key Characteristics**:
- Industrial-grade P&ID with ISA standard symbols
- Multi-equipment system (separation, compression, pumping)
- Complete with specifications, process data, and controls
- Realistic complexity for MVP testing
- Contains 50+ tags and 5 major equipment pieces

**Usage in Development**:
- Primary test document for ingestion pipeline
- Reference for database schema validation
- Source for sample queries and test cases
- Vision API testing baseline
- Performance benchmarking reference

**⚠️ IMPORTANT**: This document is a REFERENCE SAMPLE only. The system must dynamically extract data from this and any other P&ID through the ingestion pipeline. Do NOT hardcode any data from this document into the application code.

---

**END OF REQUIREMENTS SPECIFICATION v0.4**