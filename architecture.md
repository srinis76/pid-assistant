# P&ID Digital Assistant - System Architecture

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-18 | Architect | Initial architecture design |

---

## 1. Executive Summary

### 1.1 Architecture Overview

The P&ID Digital Assistant is a hybrid AI system combining Retrieval Augmented Generation (RAG) with vision-enabled language models to provide natural language query capabilities over P&ID documents. The architecture is designed for rapid MVP development (3 days) on local hardware (Mac M3) with a clear migration path to cloud production.

**Core Architecture Pattern**: Hybrid RAG + Vision API with simple rule-based query routing

**Key Design Principles**:
- **Simplicity First**: Minimal components for 3-day delivery
- **Cost-Optimized**: Free-tier models (Gemini Flash) for development
- **Portable**: Easy migration from local to cloud
- **Modular**: Swappable components (LLM providers, databases, document processors)

### 1.2 Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | Streamlit | Chat interface |
| **Backend** | Python 3.11+ | Application logic |
| **LLM** | Gemini Flash (default) | Vision + text understanding |
| **Vector DB** | ChromaDB | Semantic search |
| **Database** | SQLite | Document metadata |
| **PDF Processing** | PyMuPDF | Text + image extraction |
| **Embeddings** | OpenAI API | Text vectorization |

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                      (Streamlit Web App)                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Chat Input   │  │ Response     │  │ Token/Cost   │        │
│  │ Box          │  │ Display      │  │ Display      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                           │
│                      (Python Backend)                           │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Query Processing Engine                    │   │
│  │                                                         │   │
│  │  1. Query Router (keyword-based)                       │   │
│  │     ├─ "show", "where", "flow" → VISION               │   │
│  │     └─ Simple lookups → RAG                            │   │
│  │                                                         │   │
│  │  2. RAG Path                    3. Vision Path         │   │
│  │     ├─ Vector Search               ├─ Page Selector    │   │
│  │     ├─ Context Assembly            ├─ Image Loader     │   │
│  │     └─ LLM Call (text)             └─ LLM Call (vision)│   │
│  │                                                         │   │
│  │  4. Response Handler                                   │   │
│  │     ├─ Token Tracking                                  │   │
│  │     ├─ Cost Calculation                                │   │
│  │     └─ Logging                                         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              LLM Adapter Layer                          │   │
│  │                                                         │   │
│  │  def call_llm(query, context, images=None):            │   │
│  │      provider = get_provider()  # from .env            │   │
│  │      if provider == "gemini":                          │   │
│  │          return gemini_client.generate(...)            │   │
│  │      elif provider == "openai":                        │   │
│  │          return openai_client.chat(...)                │   │
│  │      elif provider == "claude":                        │   │
│  │          return claude_client.messages(...)            │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Vector DB    │  │ SQLite DB    │  │ File System  │        │
│  │ (ChromaDB)   │  │              │  │              │        │
│  │              │  │ - documents  │  │ - PDFs       │        │
│  │ - Text       │  │ - pages      │  │ - Images     │        │
│  │   chunks     │  │ - tickets    │  │              │        │
│  │ - Embeddings │  │   (mock)     │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Gemini API   │  │ OpenAI API   │  │ Claude API   │        │
│  │ (Flash FREE) │  │ (Embeddings) │  │ (Finals)     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagrams

#### **Ingestion Flow** (One-time Setup)

```
PDF File (D-254-001.pdf)
    ↓
┌─────────────────────────────────────┐
│   ingest_pdfs.py                   │
│                                     │
│  1. Extract text per page          │
│     (PyMuPDF)                       │
│          ↓                          │
│  2. Extract images per page        │
│     (300 DPI PNG)                   │
│          ↓                          │
│  3. Chunk text                      │
│     (800-1200 tokens/chunk)         │
│          ↓                          │
│  4. Generate embeddings             │
│     (OpenAI API)                    │
│          ↓                          │
│  5. Store in databases              │
└─────────────────────────────────────┘
    ↓           ↓           ↓
    │           │           │
    ▼           ▼           ▼
┌────────┐  ┌────────┐  ┌────────┐
│Vector  │  │SQLite  │  │Files   │
│DB      │  │        │  │        │
│        │  │docs    │  │.png    │
│chunks  │  │pages   │  │images  │
└────────┘  └────────┘  └────────┘
```

#### **Query Flow - RAG Path** (Text-only)

```
User Query: "What is V-101?"
    ↓
┌─────────────────────────────────────┐
│  Query Router                      │
│  → No visual keywords detected     │
│  → Route to: RAG                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  1. Generate query embedding       │
│     (OpenAI API)                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. Vector similarity search        │
│     (ChromaDB)                      │
│     → Top 3 relevant chunks         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. Assemble context                │
│     Chunks + metadata               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  4. LLM API call                    │
│     Provider: Gemini Flash (default)│
│     Input: Context + Query (text)   │
│     Output: Answer                  │
│                                     │
│  5. Track tokens & cost             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  6. Display response                │
│     + Token count                   │
│     + Cost estimate                 │
└─────────────────────────────────────┘
```

#### **Query Flow - Vision Path** (Image-based)

```
User Query: "Show me where V-101 is on the diagram"
    ↓
┌─────────────────────────────────────┐
│  Query Router                      │
│  → "show" keyword detected         │
│  → Route to: VISION                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  1. Identify relevant pages         │
│     - Search mentions of "V-101"    │
│     - Or send all pages (MVP)       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. Load page images                │
│     - Read PNG from filesystem      │
│     - Encode as base64              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. LLM API call (vision)           │
│     Provider: Gemini Flash (default)│
│     Input: Image(s) + Query         │
│     Output: Answer with spatial info│
│                                     │
│  4. Track tokens & cost             │
│     (Higher cost: ~6-8K tokens)     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  5. Display response                │
│     + Token count                   │
│     + Cost estimate                 │
└─────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Ingestion Pipeline (`scripts/ingest_pdfs.py`)

**Purpose**: Process PDF documents and prepare data for querying

**Inputs**:
- PDF files in `data/pdfs/` directory
- Configuration from environment variables

**Outputs**:
- Text chunks with embeddings in ChromaDB
- Document/page metadata in SQLite
- Page images in `data/processed/` directory

**Core Functions**:

```python
def ingest_pdf(pdf_path: str) -> None:
    """
    Main ingestion function
    
    Steps:
    1. Extract document metadata
    2. Process each page (text + image)
    3. Chunk text content
    4. Generate embeddings
    5. Store in databases
    6. Log results
    """
    pass

def extract_page_text(pdf_path: str, page_num: int) -> str:
    """Extract text from a single page using PyMuPDF"""
    pass

def extract_page_image(pdf_path: str, page_num: int, dpi: int = 300) -> str:
    """
    Extract page as PNG image
    Returns: path to saved image
    """
    pass

def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks
    Simple approach: split on paragraphs/newlines
    """
    pass

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI API"""
    pass

def store_in_vector_db(chunks: List[str], embeddings: List, metadata: dict) -> None:
    """Store chunks and embeddings in ChromaDB"""
    pass

def store_in_sqlite(doc_metadata: dict, pages_metadata: List[dict]) -> None:
    """Store document and page records in SQLite"""
    pass
```

**Error Handling**:
- Skip corrupted pages, continue processing
- Log errors to file
- Retry embedding generation on API failures (3 attempts)
- Validate all outputs before committing

**Performance**:
- Expected: 60-90 seconds for 7-page PDF
- Progress logging for user feedback
- No parallel processing (MVP simplicity)

---

### 3.2 Query Router (`app/query_router.py`)

**Purpose**: Decide whether to route query to RAG or Vision path

**Implementation**:

```python
from typing import Literal

QueryType = Literal["rag", "vision"]

def route_query(query: str) -> QueryType:
    """
    Simple keyword-based routing for MVP
    
    Args:
        query: User's natural language query
        
    Returns:
        "vision" if visual query, "rag" otherwise
    """
    query_lower = query.lower()
    
    # Visual keywords trigger vision path
    vision_keywords = [
        "show", "display", "where", "locate", 
        "flow", "path", "diagram", "layout",
        "picture", "image", "visual"
    ]
    
    for keyword in vision_keywords:
        if keyword in query_lower:
            return "vision"
    
    # Default to RAG (cheaper, faster)
    return "rag"
```

**Future Enhancement** (Post-MVP):
- ML-based classification
- Confidence scoring
- Hybrid queries (use both paths)

---

### 3.3 RAG Engine (`app/rag_engine.py`)

**Purpose**: Retrieve relevant context and generate answers using text-only LLM

**Core Functions**:

```python
from typing import List, Dict

def query_rag(query: str, top_k: int = 3) -> str:
    """
    Main RAG query function
    
    Args:
        query: User question
        top_k: Number of chunks to retrieve
        
    Returns:
        LLM-generated answer
    """
    # 1. Generate query embedding
    query_embedding = generate_query_embedding(query)
    
    # 2. Search vector DB
    results = search_vector_db(query_embedding, top_k)
    
    # 3. Assemble context
    context = assemble_context(results)
    
    # 4. Call LLM
    answer = call_llm_text(query, context)
    
    return answer

def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for query using OpenAI API"""
    import openai
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return response.data[0].embedding

def search_vector_db(embedding: List[float], top_k: int) -> List[Dict]:
    """
    Search ChromaDB for similar chunks
    
    Returns: List of {text, metadata, distance}
    """
    import chromadb
    client = chromadb.PersistentClient(path="database/vector_store")
    collection = client.get_collection("pid_chunks")
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    
    return results

def assemble_context(results: List[Dict]) -> str:
    """
    Format retrieved chunks into context string
    
    Include: chunk text, page number, document name
    """
    context_parts = []
    for i, result in enumerate(results):
        context_parts.append(
            f"[Source {i+1} - Page {result['metadata']['page_num']}]\n"
            f"{result['text']}\n"
        )
    return "\n---\n".join(context_parts)

def call_llm_text(query: str, context: str) -> str:
    """
    Call LLM with text-only input
    Uses provider from environment variable
    """
    from app.llm_adapter import call_llm
    
    prompt = f"""You are a technical assistant helping with P&ID documents.

Context from P&ID documentation:
{context}

User question: {query}

Provide a clear, technical answer based on the context above."""

    return call_llm(prompt, images=None)
```

---

### 3.4 Vision Engine (`app/vision_engine.py`)

**Purpose**: Process visual queries using vision-enabled LLMs

**Core Functions**:

```python
from typing import List
import base64

def query_vision(query: str) -> str:
    """
    Main vision query function
    
    Args:
        query: User question requiring visual understanding
        
    Returns:
        LLM-generated answer with visual context
    """
    # 1. Identify relevant pages
    page_paths = select_relevant_pages(query)
    
    # 2. Load and encode images
    images = load_images(page_paths)
    
    # 3. Call LLM with vision
    answer = call_llm_vision(query, images)
    
    return answer

def select_relevant_pages(query: str, max_pages: int = 3) -> List[str]:
    """
    Determine which P&ID pages to send to vision API
    
    MVP: Simple heuristics
    - Search for equipment mentions in query
    - Look up which pages contain that equipment
    - Or default to sending all pages (for small docs)
    
    Returns: List of image file paths
    """
    # For MVP with 1 PDF (7 pages), can afford to send all
    # Filter to equipment-related pages if possible
    
    import sqlite3
    conn = sqlite3.connect("database/assets.db")
    cursor = conn.cursor()
    
    # Get all page images
    cursor.execute("""
        SELECT image_path, page_number, page_title 
        FROM document_pages 
        WHERE has_equipment = 1
        ORDER BY page_number
    """)
    
    pages = cursor.fetchall()
    conn.close()
    
    # For MVP: return first max_pages equipment pages
    return [page[0] for page in pages[:max_pages]]

def load_images(image_paths: List[str]) -> List[str]:
    """
    Load images and encode as base64
    
    Returns: List of base64-encoded image strings
    """
    encoded_images = []
    for path in image_paths:
        with open(path, 'rb') as f:
            image_data = f.read()
            encoded = base64.b64encode(image_data).decode('utf-8')
            encoded_images.append(encoded)
    return encoded_images

def call_llm_vision(query: str, images: List[str]) -> str:
    """
    Call LLM with vision capability
    Uses provider from environment variable
    """
    from app.llm_adapter import call_llm
    
    # Vision-specific prompt
    prompt = f"""You are analyzing P&ID (Piping and Instrumentation Diagram) documents.

User question: {query}

Examine the P&ID diagram(s) provided and answer the question based on what you see. 
Be specific about locations, connections, and equipment shown in the diagrams."""

    return call_llm(prompt, images=images)
```

---

### 3.5 LLM Adapter (`app/llm_adapter.py`)

**Purpose**: Abstract LLM provider differences, enable easy switching

**Implementation**:

```python
import os
from typing import List, Optional, Dict
import logging

def call_llm(prompt: str, images: Optional[List[str]] = None) -> str:
    """
    Unified LLM calling function
    
    Args:
        prompt: Text prompt
        images: Optional list of base64-encoded images
        
    Returns:
        LLM response text
    """
    provider = os.getenv("LLM_PROVIDER", "gemini")
    
    # Track token usage
    start_time = time.time()
    
    if provider == "gemini":
        response, tokens = call_gemini(prompt, images)
    elif provider == "openai":
        response, tokens = call_openai(prompt, images)
    elif provider == "claude":
        response, tokens = call_claude(prompt, images)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Log usage
    elapsed = time.time() - start_time
    log_usage(provider, tokens, elapsed)
    
    return response

def call_gemini(prompt: str, images: Optional[List[str]]) -> tuple[str, Dict]:
    """Call Gemini API"""
    import google.generativeai as genai
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    # Prepare content
    if images:
        # Vision query
        import PIL.Image
        import io
        
        content = []
        for img_b64 in images:
            img_bytes = base64.b64decode(img_b64)
            img = PIL.Image.open(io.BytesIO(img_bytes))
            content.append(img)
        content.append(prompt)
    else:
        # Text-only query
        content = prompt
    
    response = model.generate_content(content)
    
    # Extract token usage (if available)
    tokens = {
        "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
        "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
        "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
    }
    
    return response.text, tokens

def call_openai(prompt: str, images: Optional[List[str]]) -> tuple[str, Dict]:
    """Call OpenAI API (GPT-4o mini)"""
    import openai
    
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Prepare messages
    if images:
        # Vision query
        content = [{"type": "text", "text": prompt}]
        for img_b64 in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })
        messages = [{"role": "user", "content": content}]
    else:
        # Text-only
        messages = [{"role": "user", "content": prompt}]
    
    response = client.chat.completions.create(
        model=model_name,
        messages=messages
    )
    
    tokens = {
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
    
    return response.choices[0].message.content, tokens

def call_claude(prompt: str, images: Optional[List[str]]) -> tuple[str, Dict]:
    """Call Claude API"""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")
    
    # Prepare content
    if images:
        # Vision query
        content = []
        for img_b64 in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            })
        content.append({"type": "text", "text": prompt})
    else:
        # Text-only
        content = prompt
    
    response = client.messages.create(
        model=model_name,
        max_tokens=2048,
        messages=[{"role": "user", "content": content}]
    )
    
    tokens = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
    }
    
    return response.content[0].text, tokens

def log_usage(provider: str, tokens: Dict, elapsed: float) -> None:
    """
    Log token usage and cost
    Print to console and write to log file
    """
    # Calculate cost based on provider
    cost = calculate_cost(provider, tokens)
    
    # Console output
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 LLM API Call Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: {provider}
Input Tokens: {tokens['input_tokens']:,}
Output Tokens: {tokens['output_tokens']:,}
Total Tokens: {tokens['total_tokens']:,}
Response Time: {elapsed:.2f}s
Estimated Cost: ${cost:.4f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)
    
    # Write to log file (JSON)
    import json
    from datetime import datetime
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "tokens": tokens,
        "cost": cost,
        "response_time": elapsed
    }
    
    with open("logs/query_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def calculate_cost(provider: str, tokens: Dict) -> float:
    """Calculate estimated cost based on provider pricing"""
    pricing = {
        "gemini": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        "openai": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
        "claude": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000}
    }
    
    if provider not in pricing:
        return 0.0
    
    cost = (
        tokens["input_tokens"] * pricing[provider]["input"] +
        tokens["output_tokens"] * pricing[provider]["output"]
    )
    
    return cost
```

---

### 3.6 Mock Ticket Display (`app/mock_data.py`)

**Purpose**: Provide hardcoded maintenance ticket data for MVP

**Implementation**:

```python
from typing import Optional, Dict

# Hardcoded mock ticket data
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
    },
    "V-101": {
        "equipment": "V-101 (High Pressure Separator)",
        "issue": "High-level alarm testing and calibration",
        "reported": "2025-09-20",
        "resolution": "LSHH-101B tested and calibrated, alarm set at 85% level",
        "resolved": "2025-09-21",
        "status": "Closed",
        "priority": "Medium"
    },
    "C-104": {
        "equipment": "C-104 (Gas Compressor)",
        "issue": "Vibration sensor alarm during startup",
        "reported": "2025-09-28",
        "resolution": "False alarm, sensor recalibrated, no mechanical issues found",
        "resolved": "2025-09-29",
        "status": "Closed",
        "priority": "High"
    }
}

def get_ticket(tag_or_equipment: str) -> Optional[Dict]:
    """
    Get mock ticket for a tag or equipment
    
    Args:
        tag_or_equipment: Tag ID (e.g., "PSV-101") or equipment ID (e.g., "V-101")
        
    Returns:
        Ticket dict or None if not found
    """
    return MOCK_TICKETS.get(tag_or_equipment.upper())

def format_ticket(ticket: Dict) -> str:
    """
    Format ticket for display
    
    Returns:
        Formatted string for UI display
    """
    status_emoji = "✅" if ticket["status"] == "Closed" else "⚠️"
    
    return f"""
📋 Last Ticket on {ticket['equipment']}
Issue: {ticket['issue']}
Reported: {ticket['reported']}
Resolution: {ticket['resolution']}
Resolved: {ticket['resolved']}
Status: {status_emoji} {ticket['status']}
Priority: {ticket['priority']}
    """
```

---

## 4. Database Design

### 4.1 SQLite Schema

**File**: `database/assets.db`

```sql
-- Documents table
CREATE TABLE documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    document_number TEXT,
    document_title TEXT,
    revision TEXT,
    total_pages INTEGER,
    facility TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document pages table
CREATE TABLE document_pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    page_type TEXT,  -- 'PFD', 'Legend', 'Detail_PID'
    page_title TEXT,
    sheet_number TEXT,
    image_path TEXT NOT NULL,
    text_content TEXT,
    has_equipment BOOLEAN DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(document_id)
);

-- Indexes for performance
CREATE INDEX idx_pages_document ON document_pages(document_id);
CREATE INDEX idx_pages_equipment ON document_pages(has_equipment);
```

### 4.2 Vector Database (ChromaDB)

**Collection**: `pid_chunks`

**Schema**:
```python
{
    "ids": ["chunk_1", "chunk_2", ...],
    "embeddings": [[0.1, 0.2, ...], ...],  # 1536-dim vectors
    "metadatas": [
        {
            "document_id": 1,
            "page_number": 3,
            "page_title": "High Pressure Separator",
            "chunk_index": 0
        },
        ...
    ],
    "documents": ["chunk text content", ...]
}
```

**Initialization**:
```python
import chromadb

client = chromadb.PersistentClient(path="database/vector_store")

collection = client.create_collection(
    name="pid_chunks",
    metadata={"description": "P&ID document chunks with embeddings"}
)
```

---

## 5. File Structure

```
pid-assistant/
├── .env                          # Environment variables (NOT in git)
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── README.md                     # Setup and usage instructions
│
├── data/                         # Data directory
│   ├── pdfs/                     # Source PDF files
│   │   └── D-254-001_Gas_Production_Facility_Rev1.pdf
│   └── processed/                # Extracted page images
│       └── D-254-001/
│           ├── page_1.png
│           ├── page_2.png
│           └── ...
│
├── database/                     # Database files
│   ├── assets.db                 # SQLite database
│   └── vector_store/             # ChromaDB directory
│       └── [chromadb files]
│
├── logs/                         # Log files
│   └── query_log.jsonl           # Query and cost logs
│
├── scripts/                      # Utility scripts
│   └── ingest_pdfs.py            # PDF ingestion script
│
├── app/                          # Main application
│   ├── __init__.py
│   ├── main.py                   # Streamlit UI entry point
│   ├── query_router.py           # Query routing logic
│   ├── rag_engine.py             # RAG implementation
│   ├── vision_engine.py          # Vision query handling
│   ├── llm_adapter.py            # LLM provider abstraction
│   ├── mock_data.py              # Mock ticket data
│   └── utils.py                  # Shared utilities
│
└── tests/                        # Tests (optional for MVP)
    └── test_ingestion.py
```

---

## 6. Environment Configuration

### 6.1 `.env` File Template

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
IMAGE_DPI=300                          # Image extraction quality

# Database Paths
SQLITE_DB_PATH=database/assets.db
VECTOR_DB_PATH=database/vector_store

# Ingestion Settings
CHUNK_SIZE=1000                        # Tokens per chunk
EMBEDDING_MODEL=text-embedding-3-small
```

### 6.2 `requirements.txt`

```
# Core LLM APIs
google-generativeai>=0.3.0
openai>=1.0.0
anthropic>=0.18.0

# Vector Database
chromadb>=0.4.0

# PDF Processing
pymupdf>=1.23.0
pillow>=10.0.0

# Web UI
streamlit>=1.30.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0

# Development
pytest>=7.0.0
```

---

## 7. Deployment Architecture

### 7.1 MVP Deployment (Local Mac M3)

```
┌─────────────────────────────────────────┐
│         Mac M3 Laptop (8GB RAM)         │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Streamlit App                    │ │
│  │  (localhost:8501)                 │ │
│  └───────────────────────────────────┘ │
│                ↓                        │
│  ┌───────────────────────────────────┐ │
│  │  Python Backend                   │ │
│  │  - Query processing               │ │
│  │  - LLM adapter                    │ │
│  │  - RAG/Vision engines             │ │
│  └───────────────────────────────────┘ │
│                ↓                        │
│  ┌───────────────────────────────────┐ │
│  │  Local Storage                    │ │
│  │  - SQLite (metadata)              │ │
│  │  - ChromaDB (vectors)             │ │
│  │  - Filesystem (PDFs, images)      │ │
│  └───────────────────────────────────┘ │
│                                         │
│         ↓ (Internet)                    │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│         External APIs                   │
│  - Gemini API (vision + text)           │
│  - OpenAI API (embeddings)              │
│  - Claude API (optional)                │
└─────────────────────────────────────────┘
```

**Startup Commands**:
```bash
# 1. Run ingestion (one-time)
python scripts/ingest_pdfs.py

# 2. Start application
streamlit run app/main.py
```

### 7.2 Production Deployment (Future)

```
┌────────────────────────────────────────────┐
│              Load Balancer                 │
└────────────────────────────────────────────┘
                  ↓
┌────────────────────────────────────────────┐
│         Application Tier (K8s)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ App Pod  │  │ App Pod  │  │ App Pod  │ │
│  │  1       │  │  2       │  │  3       │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└────────────────────────────────────────────┘
                  ↓
┌────────────────────────────────────────────┐
│            Data Tier                       │
│  ┌─────────────┐  ┌─────────────┐         │
│  │ PostgreSQL  │  │ Pinecone/   │         │
│  │ (metadata)  │  │ Weaviate    │         │
│  └─────────────┘  └─────────────┘         │
│                                            │
│  ┌─────────────┐  ┌─────────────┐         │
│  │ S3/Blob     │  │ Redis       │         │
│  │ (PDFs/imgs) │  │ (cache)     │         │
│  └─────────────┘  └─────────────┘         │
└────────────────────────────────────────────┘
```

---

## 8. Implementation Roadmap

### Day 1: Data Pipeline (6-8 hours)

**Morning** (4 hours):
1. Project setup (30 min)
   - Create directory structure
   - Initialize git repository
   - Setup virtual environment
   - Install dependencies

2. Database setup (1 hour)
   - Create SQLite schema
   - Initialize ChromaDB
   - Write database utility functions

3. Ingestion script - Part 1 (2.5 hours)
   - PDF text extraction
   - PDF image extraction
   - Test with sample P&ID

**Afternoon** (4 hours):
4. Ingestion script - Part 2 (4 hours)
   - Text chunking implementation
   - Embedding generation (OpenAI API)
   - Store in ChromaDB
   - Store metadata in SQLite
   - End-to-end ingestion test
   - Verify: All 7 pages processed correctly

---

### Day 2: Query Engine (8 hours)

**Morning** (4 hours):
1. LLM Adapter (2 hours)
   - Implement Gemini Flash integration
   - Token tracking and logging
   - Test with simple prompts

2. RAG Engine (2 hours)
   - Vector search implementation
   - Context assembly
   - Test text-only queries

**Afternoon** (4 hours):
3. Vision Engine (2 hours)
   - Page selection logic
   - Image loading and encoding
   - Vision API integration
   - Test visual queries

4. Query Router (1 hour)
   - Keyword-based routing
   - Integration with RAG and Vision

5. Testing & Integration (1 hour)
   - Test 10-15 queries (both types)
   - Verify responses are accurate
   - Check token costs

---

### Day 3: UI & Polish (8 hours)

**Morning** (4 hours):
1. Streamlit UI (3 hours)
   - Chat interface setup
   - Query input and response display
   - Token/cost display sidebar
   - Mock ticket integration

2. Testing (1 hour)
   - End-to-end user flow
   - Test with all query types

**Afternoon** (4 hours):
3. Bug Fixes (2 hours)
   - Fix any issues found
   - Edge case handling
   - Error message improvements

4. Switch to Claude Sonnet (30 min)
   - Change .env to Claude
   - Re-test critical queries
   - Verify quality improvement

5. Final Testing & Demo Prep (1.5 hours)
   - Create 10-15 demo queries
   - Practice demo flow
   - Document known limitations
   - Generate session summary report

---

## 9. Testing Strategy

### 9.1 Test Categories

**Unit Tests** (Optional for MVP):
- LLM adapter provider switching
- Query router keyword detection
- Embedding generation

**Integration Tests** (Recommended):
- Full ingestion pipeline
- RAG query flow end-to-end
- Vision query flow end-to-end

**Manual Tests** (Critical):
- 20-30 queries covering:
  - Simple tag lookups
  - Equipment specifications
  - Visual/spatial queries
  - Connection/topology questions
  - Mock ticket display

### 9.2 Test Queries

**RAG Path Tests**:
1. "What is V-101?"
2. "What are the specs for P-103?"
3. "What's the design pressure of V-102?"
4. "Tell me about PSV-101"
5. "What's the capacity of C-104?"

**Vision Path Tests**:
1. "Show me where V-101 is on the diagram"
2. "What equipment is connected to V-101?"
3. "Show me the flow path from V-101 to C-104"
4. "Where is the gas compressor located?"
5. "Display the complete separation system"

**Mock Ticket Tests**:
1. Query "PSV-101" → Should show recent ticket
2. Query "V-102" → Should show ticket info
3. Query unknown tag → Should handle gracefully

### 9.3 Success Criteria

- [ ] 90% of test queries return accurate answers
- [ ] Average response time < 10 seconds
- [ ] Token tracking works for all queries
- [ ] Cost estimates are reasonable ($2-5 total)
- [ ] UI is functional and usable
- [ ] No crashes or unhandled errors

---

## 10. Observability & Monitoring

### 10.1 Logging Strategy

**Console Logs** (Development):
- Every API call with tokens/cost
- Query routing decisions
- Error messages with stack traces

**File Logs** (`logs/query_log.jsonl`):
```json
{
  "timestamp": "2025-10-18T14:30:00Z",
  "query": "What is V-101?",
  "query_type": "rag",
  "provider": "gemini",
  "model": "gemini-1.5-flash",
  "tokens": {
    "input": 1234,
    "output": 156,
    "total": 1390
  },
  "cost": 0.00,
  "response_time": 3.2,
  "success": true
}
```

### 10.2 Cost Tracking

**Per-Session Summary**:
- Total queries
- Total tokens
- Total cost
- Breakdown by provider
- Breakdown by query type (RAG vs Vision)

**Display in UI Sidebar**:
```
📊 Session Stats
━━━━━━━━━━━━━━━
Queries: 12
Tokens: 45.2K
Cost: $0.85
Provider: Gemini
```

---

## 11. Security Considerations

### 11.1 MVP (Local Deployment)

**Current Security Posture**:
- ✅ Local-only (no network exposure)
- ✅ API keys in .env (not committed to git)
- ✅ No authentication needed (single user)
- ✅ No sensitive data (sample P&IDs only)

**Risks**:
- ⚠️ API keys in plaintext on disk
- ⚠️ No encryption of local data

**Mitigations**:
- Keep .env in .gitignore
- Don't share API keys
- Acceptable for MVP development

### 11.2 Production (Future)

**Required**:
- OAuth 2.0 authentication
- API key encryption (AWS Secrets Manager, etc.)
- HTTPS/TLS for all connections
- Role-based access control
- Audit logging
- Data encryption at rest

---

## 12. Performance Optimization

### 12.1 Current Bottlenecks

1. **Vision API calls** (~5-10 seconds)
   - Mitigation: Caching, reduce image resolution for dev

2. **Embedding generation** (~1-2 seconds per query)
   - Mitigation: Cache query embeddings

3. **Image loading** (~1 second per page)
   - Mitigation: Lazy loading, compress images

### 12.2 Optimization Opportunities (Post-MVP)

1. **Response Caching**:
   ```python
   cache = {}
   cache_key = hash(query)
   if cache_key in cache:
       return cache[cache_key]
   ```

2. **Embedding Caching**:
   - Cache common queries
   - Semantic similarity matching

3. **Image Pre-loading**:
   - Load all images at startup
   - Keep in memory for faster access

4. **Async Processing**:
   - Parallel API calls when possible
   - Background embedding generation

---

## 13. Known Limitations (MVP)

1. **Single Document**: Only supports 1 P&ID (extensible design)
2. **No Multi-Page Context**: Vision queries limited to selected pages
3. **Simple Routing**: Keyword-based, not ML classification
4. **No Caching**: Every query hits API (cost inefficient)
5. **No Authentication**: Single user only
6. **Mock Data**: Tickets are hardcoded, not dynamic
7. **No Editing**: Read-only system
8. **English Only**: No multi-language support

---

## 14. Migration Path (MVP → Production)

### Phase 1: Scale Data (Week 1-2)
- [ ] Support 40-50 P&ID documents
- [ ] Optimize vector storage
- [ ] Add document management UI

### Phase 2: Optimize Cost (Week 2-3)
- [ ] Implement response caching
- [ ] Add Haiku for simple queries
- [ ] Smart model routing

### Phase 3: Production Hardening (Week 3-4)
- [ ] Add authentication
- [ ] Deploy to cloud (Docker + K8s)
- [ ] Set up monitoring/alerting
- [ ] Production database (PostgreSQL)

### Phase 4: Feature Expansion (Month 2+)
- [ ] SCADA integration
- [ ] Maintenance history
- [ ] Mobile support
- [ ] Multi-user collaboration

---

**END OF ARCHITECTURE SPECIFICATION v1.0**