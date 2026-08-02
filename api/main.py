"""
FastAPI service for the P&ID Assistant.

Wraps the existing engines (QueryRouter → RAGEngine / VisionEngine) behind HTTP
and serves the single-page frontend. The response shape matches what the
frontend already renders, so the UI only swaps canned data for a fetch().

Run:
    uvicorn api.main:app --reload --port 8000
"""

import os
import re
import time
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# Hybrid retrieval on by default for the demo (shows the tag-precision win).
os.environ.setdefault("RETRIEVAL_MODE", "hybrid")

import sys
sys.path.insert(0, str(ROOT))

from app.rag_engine import RAGEngine
from app.vision_engine import VisionEngine
from app.query_router import QueryRouter
from app.mock_data import get_ticket, format_ticket
from app.conversation_memory import ConversationMemory, DEFAULT_WINDOW
from app.query_rewriter import rewrite_followup
from api.schemas import QueryRequest, QueryResponse, Source, Ticket, Telemetry

DB_PATH = ROOT / "database" / "assets.db"
PROCESSED = ROOT / "data" / "processed"
STATIC = ROOT / "static"

TICKET_KEYWORDS = ("issue", "problem", "maintenance", "recent", "ticket", "service", "fault")

# Fallback drawing number when a document has no document_number in the DB
# (single-doc MVP; see PRODUCT_SPEC known limitations).
DEFAULT_DRAWING = "D-254-001"


def load_drawings() -> dict:
    """Map document_id -> drawing number (best-effort; single-doc MVP)."""
    drawings = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        for did, num in conn.execute("SELECT document_id, document_number FROM documents"):
            drawings[did] = num or DEFAULT_DRAWING
        conn.close()
    except Exception:
        pass
    return drawings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Engines are expensive to construct (load ChromaDB + models) — do it once.
    print("⏳ Initializing engines...")
    app.state.rag = RAGEngine()
    app.state.vision = VisionEngine()
    app.state.router = QueryRouter()
    app.state.drawings = load_drawings()
    app.state.memory = ConversationMemory(str(DB_PATH))
    print("✅ Engines ready")
    yield


app = FastAPI(title="P&ID Assistant API", version="3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _drawing_for(doc_id) -> str:
    return app.state.drawings.get(doc_id, DEFAULT_DRAWING)


def _snapshot(adapter):
    s = adapter.session_stats
    return s["total_input_tokens"], s["total_output_tokens"], s["total_cost"]


def _find_ticket(query: str):
    """Return (Ticket, raw_dict) if the query mentions equipment with a ticket."""
    tags = re.findall(r"\b[A-Z]+-\d+[A-Z]?\b", query.upper())
    for tag in tags:
        t = get_ticket(tag)
        if t:
            f = format_ticket(t)
            return Ticket(**f), f
    return None, None


@app.get("/health")
def health():
    rag = app.state.rag
    return {
        "status": "ok",
        "provider": rag.llm_adapter.provider,
        "model": rag.llm_adapter.model,
        "retrieval_mode": getattr(rag, "retrieval_mode", "vector"),
        "chunks": rag.collection.count(),
        "documents": len(app.state.drawings) or 1,
    }


@app.get("/")
def index():
    # No-cache so a frontend change is never masked by a stale cached SPA shell
    # (a cached old index.html omits conversation_id → memory silently inactive).
    return FileResponse(
        STATIC / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/pages/{page}")
def page_image(page: int):
    """Serve a rendered P&ID page image by number."""
    if PROCESSED.exists():
        for d in sorted(PROCESSED.iterdir()):
            f = d / f"page_{page}.png"
            if f.exists():
                return FileResponse(f, media_type="image/png")
    raise HTTPException(status_code=404, detail=f"Page {page} not found")


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest):
    router: QueryRouter = app.state.router
    memory: ConversationMemory = app.state.memory

    # 1. Short-term memory: recall recent turns for this conversation (opt-in).
    turns = memory.get_recent_turns(req.conversation_id, n=DEFAULT_WINDOW) \
        if req.conversation_id else []

    # 2. Resolve follow-ups ("what connects to it?") into a standalone query so
    #    routing and retrieval operate on explicit references. No turns => no-op.
    rewrite_adapter = app.state.rag.llm_adapter
    resolved = rewrite_followup(req.query, turns, rewrite_adapter) if turns else req.query
    rewritten_query = resolved if resolved != req.query else None

    route = router.route_query(resolved)

    # Maintenance ticket lookup (and optional prompt enrichment when relevant).
    ticket, ticket_raw = _find_ticket(resolved)
    prompt = resolved
    if ticket_raw and any(w in resolved.lower() for w in TICKET_KEYWORDS):
        prompt = (f"{resolved}\n\nNote: a maintenance ticket exists for this "
                  f"equipment — Issue: {ticket_raw['issue']}; "
                  f"Resolution: {ticket_raw['resolution']} ({ticket_raw['status']}).")

    history_block = memory.format_for_prompt(turns)

    engine = app.state.rag if route == "rag" else app.state.vision
    adapter = engine.llm_adapter

    before = _snapshot(adapter)
    t0 = time.time()
    try:
        if route == "rag":
            answer, meta = engine.query_rag(prompt, top_k=req.top_k, history=history_block)
        else:
            answer, meta = engine.query_vision(prompt, history=history_block)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    latency = time.time() - t0
    after = _snapshot(adapter)

    in_tok, out_tok = after[0] - before[0], after[1] - before[1]
    cost = round(after[2] - before[2], 8)

    sources, image_url, sheet = [], None, None

    if route == "rag":
        metas = meta.get("sources", [])
        rels = meta.get("relevance_scores", [])
        for i, (m, rel) in enumerate(zip(metas, rels)):
            tag = m.get("equipment_tag", "") or ""
            sources.append(Source(
                tag=tag,
                name=m.get("equipment_name") or m.get("equipment_type") or "Equipment",
                drawing=_drawing_for(m.get("document_id")),
                sheet=None,
                rank=i + 1,
                relevance=round(rel, 4) if isinstance(rel, (int, float)) else None,
                chunk_id=f"v2_equip_{tag}" if tag else None,
            ))
    else:
        # Vision: cite the referenced page image(s); show the primary one.
        paths = meta.get("image_paths") or meta.get("page_paths") or []
        doc_ids = meta.get("document_ids") or []
        pages, page_doc_ids = [], []
        for i, p in enumerate(paths):
            mo = re.search(r"page_(\d+)", str(p))
            if mo:
                pages.append(int(mo.group(1)))
                page_doc_ids.append(doc_ids[i] if i < len(doc_ids) else None)
        if pages:
            sheet = pages[0]
            image_url = f"/api/pages/{sheet}"
        for i, pg in enumerate(pages):
            sources.append(Source(
                tag="Diagram", name="Detail P&ID (image analysis)",
                drawing=_drawing_for(page_doc_ids[i]), sheet=pg, rank=i + 1, relevance=None, chunk_id=None,
            ))

    telemetry = Telemetry(
        latency_s=round(latency, 2),
        input_tokens=in_tok, output_tokens=out_tok, total_tokens=in_tok + out_tok,
        cost_usd=cost, model=adapter.model,
        retrieval_mode=getattr(engine, "retrieval_mode", "n/a"),
        rewritten_query=rewritten_query,
    )

    # Persist this turn (store the ORIGINAL user question, not the rewrite).
    if req.conversation_id:
        memory.add_turn(req.conversation_id, req.query, answer, route)

    return QueryResponse(
        answer=answer, route=route, sources=sources, ticket=ticket,
        image_url=image_url, sheet=sheet, telemetry=telemetry,
    )
