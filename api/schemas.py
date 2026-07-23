"""Pydantic request/response schemas for the P&ID Assistant API.

The response shape is designed to match exactly what the frontend's render
functions already expect, so the UI needs no structural changes — only a
`fetch()` in place of the canned demo data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's natural-language question")
    top_k: int = Field(3, ge=1, le=10, description="Chunks to retrieve for RAG")
    conversation_id: Optional[str] = Field(
        None, description="Opt-in short-term memory: turns are stored/recalled per id"
    )


class Source(BaseModel):
    """One retrieved source, in human-readable + technical form."""
    tag: str                      # e.g. "V-101"  (or "Diagram" for vision)
    name: str                     # e.g. "High Pressure Separator"
    drawing: str                  # e.g. "D-254-001"
    sheet: Optional[int] = None   # sheet/page number, if known
    rank: Optional[int] = None    # 1-based retrieval rank (meaningful in any mode)
    relevance: Optional[float] = None   # raw score — cosine (vector) or RRF fusion (hybrid)
    chunk_id: Optional[str] = None      # e.g. "v2_equip_V-101" (technical detail)


class Ticket(BaseModel):
    equipment: str
    issue: str
    resolution: str
    status: str
    status_emoji: str
    priority: str
    resolved: str


class Telemetry(BaseModel):
    latency_s: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    model: str
    retrieval_mode: str
    rewritten_query: Optional[str] = None   # set only when a follow-up was rewritten


class QueryResponse(BaseModel):
    answer: str
    route: str                    # "rag" | "vision"
    sources: List[Source] = []
    ticket: Optional[Ticket] = None
    image_url: Optional[str] = None   # for vision answers — the referenced page
    sheet: Optional[int] = None       # sheet number of the referenced diagram
    telemetry: Telemetry
