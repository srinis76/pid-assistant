"""
Tests for short-term conversation memory.

Covers the memory store, the follow-up query rewriter, and the API orchestration
that ties them together. No real LLM/embedding calls: the rewriter is tested with
a stub adapter, and the API test fakes the heavy engines so the flow is
deterministic and offline.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.conversation_memory import ConversationMemory, DEFAULT_WINDOW
from app.query_rewriter import rewrite_followup


# ─────────────────────────── ConversationMemory ───────────────────────────

def test_table_autocreated_on_fresh_db(tmp_path):
    db = tmp_path / "fresh.db"
    ConversationMemory(str(db))  # should create schema without error
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "conversation_turns" in tables


def test_add_and_fetch_ordering(tmp_path):
    mem = ConversationMemory(str(tmp_path / "m.db"))
    mem.add_turn("c1", "What is V-101?", "It is the HP separator.", "rag")
    mem.add_turn("c1", "What connects to it?", "C-104 does.", "rag")
    turns = mem.get_recent_turns("c1")
    assert [t["question"] for t in turns] == ["What is V-101?", "What connects to it?"]
    assert turns[0]["answer"] == "It is the HP separator."
    assert turns[1]["route"] == "rag"


def test_window_boundary_drops_oldest(tmp_path):
    mem = ConversationMemory(str(tmp_path / "m.db"))
    # Insert one more than the window.
    for i in range(DEFAULT_WINDOW + 1):
        mem.add_turn("c1", f"q{i}", f"a{i}", "rag")
    turns = mem.get_recent_turns("c1", n=DEFAULT_WINDOW)
    assert len(turns) == DEFAULT_WINDOW
    # Oldest (q0) dropped; window is q1..q{N}, oldest-first.
    assert turns[0]["question"] == "q1"
    assert turns[-1]["question"] == f"q{DEFAULT_WINDOW}"


def test_conversations_are_isolated(tmp_path):
    mem = ConversationMemory(str(tmp_path / "m.db"))
    mem.add_turn("c1", "q-a", "a-a", "rag")
    mem.add_turn("c2", "q-b", "a-b", "rag")
    assert [t["question"] for t in mem.get_recent_turns("c1")] == ["q-a"]
    assert [t["question"] for t in mem.get_recent_turns("c2")] == ["q-b"]


def test_empty_conversation_id_is_noop(tmp_path):
    mem = ConversationMemory(str(tmp_path / "m.db"))
    mem.add_turn("", "q", "a", "rag")          # ignored
    assert mem.get_recent_turns("") == []
    assert mem.get_recent_turns(None) == []


def test_format_for_prompt():
    turns = [
        {"question": "What is V-101?", "answer": "HP separator.", "route": "rag"},
        {"question": "What connects to it?", "answer": "C-104.", "route": "rag"},
    ]
    block = ConversationMemory.format_for_prompt(turns)
    assert "V-101" in block and "C-104" in block
    assert block.index("V-101") < block.index("C-104")  # oldest first
    assert ConversationMemory.format_for_prompt([]) == ""


# ─────────────────────────── query_rewriter ───────────────────────────

class StubAdapter:
    """Records calls; returns a canned rewrite."""
    def __init__(self, ret="what connects to V-101?", raises=False):
        self.ret = ret
        self.raises = raises
        self.calls = []

    def call_llm(self, prompt, images=None, query_type="rag"):
        self.calls.append({"prompt": prompt, "query_type": query_type})
        if self.raises:
            raise RuntimeError("simulated LLM failure")
        return self.ret


def test_rewrite_noop_without_history():
    stub = StubAdapter()
    out = rewrite_followup("what connects to it?", [], stub)
    assert out == "what connects to it?"
    assert stub.calls == []  # no LLM call when there is no history


def test_rewrite_with_history_calls_adapter():
    stub = StubAdapter(ret="what connects to V-101?")
    turns = [{"question": "What is V-101?", "answer": "HP separator.", "route": "rag"}]
    out = rewrite_followup("what connects to it?", turns, stub)
    assert out == "what connects to V-101?"
    assert len(stub.calls) == 1
    assert stub.calls[0]["query_type"] == "rewrite"
    assert "V-101" in stub.calls[0]["prompt"]      # history injected into prompt


def test_rewrite_fails_open_on_error():
    stub = StubAdapter(raises=True)
    turns = [{"question": "What is V-101?", "answer": "HP separator.", "route": "rag"}]
    out = rewrite_followup("what connects to it?", turns, stub)
    assert out == "what connects to it?"           # falls back to original


def test_rewrite_empty_response_falls_back():
    stub = StubAdapter(ret="   ")
    turns = [{"question": "What is V-101?", "answer": "HP separator.", "route": "rag"}]
    out = rewrite_followup("what connects to it?", turns, stub)
    assert out == "what connects to it?"


def test_real_adapter_log_usage_accepts_rewrite_query_type():
    """Regression: the real LLMAdapter must not KeyError on a new query_type.

    The 'rewrite' query_type is not seeded in queries_by_type; _log_usage must
    tolerate it. (Constructed via __new__ to stay offline / provider-free.)"""
    from app.llm_adapter import LLMAdapter
    adapter = LLMAdapter.__new__(LLMAdapter)
    adapter.session_stats = {
        "total_queries": 0, "total_input_tokens": 0, "total_output_tokens": 0,
        "total_cost": 0.0, "queries_by_type": {"rag": 0, "vision": 0},
    }
    adapter.verbose_logging = False
    adapter.model = "test-model"
    adapter.provider = "test"
    # Stub cost calc to avoid pricing config dependencies.
    adapter._calculate_cost = lambda tokens: 0.0
    adapter._log_usage({"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                       0.1, "rewrite")
    assert adapter.session_stats["queries_by_type"]["rewrite"] == 1


# ─────────────────────────── API orchestration ───────────────────────────

class _FakeAdapter:
    def __init__(self):
        self.model = "fake-model"
        self.session_stats = {
            "total_input_tokens": 0, "total_output_tokens": 0, "total_cost": 0.0}

    def call_llm(self, prompt, images=None, query_type="rag"):
        self.session_stats["total_input_tokens"] += 10
        self.session_stats["total_output_tokens"] += 5
        self.session_stats["total_cost"] += 0.0001
        if query_type == "rewrite":
            # Resolve the pronoun deterministically.
            return "what connects to V-101?"
        return "Canned answer."


class _FakeRAG:
    def __init__(self):
        self.llm_adapter = _FakeAdapter()
        self.retrieval_mode = "hybrid"
        self.history_seen = []

    def query_rag(self, prompt, top_k=3, history=""):
        self.history_seen.append(history)
        meta = {
            "sources": [{"equipment_tag": "V-101", "equipment_name": "HP Separator",
                         "document_id": 2}],
            "relevance_scores": [0.9],
            "retrieval_mode": "hybrid",
        }
        return f"Answer for: {prompt}", meta


class _FakeVision:
    def __init__(self):
        self.llm_adapter = _FakeAdapter()

    def query_vision(self, prompt, max_pages=3, history=""):
        return "Vision answer.", {"image_paths": [], "page_paths": []}


class _FakeRouter:
    def route_query(self, q):
        return "rag"


@pytest.fixture
def client(tmp_path, monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient

    # Point memory at a temp DB and swap heavy engines for fakes.
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "assets.db")
    monkeypatch.setattr(m, "RAGEngine", _FakeRAG)
    monkeypatch.setattr(m, "VisionEngine", _FakeVision)
    monkeypatch.setattr(m, "QueryRouter", _FakeRouter)

    with TestClient(m.app) as c:
        yield c, m


def test_two_turn_conversation_rewrites_followup(client):
    c, m = client
    cid = "conv-123"

    r1 = c.post("/api/query", json={"query": "What is V-101?", "conversation_id": cid})
    assert r1.status_code == 200
    assert r1.json()["telemetry"]["rewritten_query"] is None  # first turn, no rewrite

    r2 = c.post("/api/query",
                json={"query": "what connects to it?", "conversation_id": cid})
    assert r2.status_code == 200
    body = r2.json()
    # Follow-up was resolved to a standalone query containing the tag.
    assert body["telemetry"]["rewritten_query"] == "what connects to V-101?"
    # The engine received the resolved query, not the pronoun form.
    assert "V-101" in body["answer"]

    # Both turns persisted; the second turn stored the ORIGINAL user text.
    mem = m.ConversationMemory(str(m.DB_PATH))
    turns = mem.get_recent_turns(cid)
    assert [t["question"] for t in turns] == ["What is V-101?", "what connects to it?"]


def test_history_injected_into_engine_on_second_turn(client):
    c, m = client
    cid = "conv-hist"
    c.post("/api/query", json={"query": "What is V-101?", "conversation_id": cid})
    c.post("/api/query", json={"query": "what connects to it?", "conversation_id": cid})
    # Second call to the RAG engine should have received a non-empty history block.
    rag = m.app.state.rag
    assert rag.history_seen[0] == ""              # first turn: no history
    assert "V-101" in rag.history_seen[1]         # second turn: prior turn injected


def test_no_conversation_id_is_stateless(client):
    c, m = client
    r = c.post("/api/query", json={"query": "What is V-101?"})
    assert r.status_code == 200
    assert r.json()["telemetry"]["rewritten_query"] is None
    # Nothing was persisted.
    conn = sqlite3.connect(m.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM conversation_turns").fetchone()[0]
    conn.close()
    assert n == 0


def test_index_is_served_no_cache(client):
    """The SPA shell must not be stale-cached, or browsers keep running old JS
    after a frontend change (this masked conversation memory during testing)."""
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "").lower()
    assert "no-cache" in cc or "no-store" in cc
