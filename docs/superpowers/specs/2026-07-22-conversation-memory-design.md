# Short-Term Conversation Memory — Design

**Date:** 2026-07-22
**Status:** Approved, in implementation
**Scope:** Add per-conversation short-term memory so multi-turn chats stay coherent
(e.g. "what connects to it?" resolves *it* to the equipment from a prior turn).

## Problem

Every `POST /api/query` is currently stateless. The frontend *looks* like a
continuous conversation, but each request sends only `{query, top_k}` — the LLM
has no idea what was asked before. Elliptical / pronoun follow-ups therefore
fail: "what connects to it?" retrieves nothing useful because neither ChromaDB
(dense) nor BM25 (keyword) can match "it" to a chunk, and the keyword-based
router may mis-route it.

## Non-Goals (YAGNI)

- **No long-term / cross-session memory.** This is session-scoped coherence only.
- **No vector DB for history.** ChromaDB stays exclusively for P&ID document
  chunks. Conversation turns go straight into the prompt as text.
- **No summarization (yet).** A sliding window of raw turns is enough for a
  single-doc MVP. Summarization is a clean add-on later if chats get long.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Storage | SQLite table in existing `assets.db` | Durable across restarts; DB already present. |
| Injection | Query rewrite **+** context prepend | Rewrite fixes retrieval & routing; context gives the answer LLM continuity. |
| History bound | Sliding window, N=6 turns, no summary | Predictable, bounded token cost; simplest correct thing. |
| Stored question | The **original** user text (not the rewrite) | History reads naturally; future rewrites see real phrasing. |
| Backward compat | `conversation_id` optional | Omitting it = today's stateless behavior. Nothing breaks. |

## Components

### A. `app/conversation_memory.py` (new)
`ConversationMemory` — owns all SQLite persistence for turns.
- `__init__(db_path)` — runs `CREATE TABLE IF NOT EXISTS` so existing DBs upgrade.
- `add_turn(conversation_id, question, answer, route)` — append (auto turn_index).
- `get_recent_turns(conversation_id, n=6)` — last N turns, oldest-first.
- `format_for_prompt(turns) -> str` — render turns into a plain-text block.

Depends only on the SQLite path.

### B. `app/query_rewriter.py` (new)
`rewrite_followup(query, turns, llm_adapter) -> str`
- No history → returns `query` unchanged (no LLM call).
- With history → one cheap LLM call (history + instruction, no retrieved chunks)
  producing a standalone query. On any error, falls back to the original query
  (fail-open — memory must never break a working query path).

### C. Engines (edit — additive, optional param)
`rag_engine.query_rag(query, top_k, history="")` and
`vision_engine.query_vision(query, max_pages, history="")` gain an optional
`history` string injected into their prompt templates. Default `""` keeps every
existing caller (tests, Streamlit, eval scripts) working unchanged.

### D. `api/main.py` (edit — orchestration)
See data flow below.

### E. `api/schemas.py` (edit)
- `QueryRequest.conversation_id: Optional[str] = None`
- `Telemetry.rewritten_query: Optional[str] = None` (echo when it differs, for
  transparency / demo under the existing "Technical detail" toggle).

### F. `static/index.html` (edit — minimal)
- Send `conversation_id: current?.id` in the fetch body; hoist `ensureConvo()` to
  before the fetch so the first turn is tagged.
- Under the existing tech toggle, show `rewritten_query` when it differs.

### G. `scripts/init_database.py` (edit)
Add the `conversation_turns` table for fresh installs.

## Data Model

```sql
CREATE TABLE IF NOT EXISTS conversation_turns (
    turn_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_index      INTEGER NOT NULL,   -- 0-based order within a conversation
    question        TEXT NOT NULL,      -- ORIGINAL user text, not the rewrite
    answer          TEXT NOT NULL,
    route           TEXT,               -- "rag" | "vision"
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_turns_convo
    ON conversation_turns(conversation_id, turn_index);
```

`conversation_id` is a string, matching the `Date.now()` id the frontend already
generates.

## Data Flow (per query)

```
POST /api/query { query, top_k, conversation_id? }
  1. turns = memory.get_recent_turns(conversation_id, n=6)   # [] if new/absent
  2. rewritten = rewrite_followup(query, turns, adapter) if turns else query
  3. route = router.route_query(rewritten)                   # route on RESOLVED query
     ticket lookup also uses rewritten
  4. history_block = memory.format_for_prompt(turns)
     engine.query_rag(rewritten, top_k, history=history_block)   # or query_vision
  5. if conversation_id: memory.add_turn(conversation_id, original_query, answer, route)
  6. return response (+ telemetry.rewritten_query when it differs)
```

If `conversation_id` is absent, steps 1–2 and 5 are skipped → identical to today.

## Token Impact

- Step 2 rewrite: small extra call (history + instruction only, no chunks).
- Step 4: prompt grows by `history_block`, bounded to 6 turns (~300–900 input
  tokens in practice). Output tokens unchanged.
- First turn of any conversation: no history → no rewrite → no added cost.

## Testing

`tests/test_conversation_memory.py` (pytest), using a temp SQLite DB and a stub
LLM adapter where an API call would otherwise be needed:

- **Memory unit:** add/fetch ordering; N-turn window boundary (7th drops 1st);
  isolation between two `conversation_id`s; table auto-creation on a fresh DB.
- **Rewriter unit:** no-history → query unchanged and adapter **not** called;
  with-history → adapter called with a prompt containing the prior turns;
  adapter error → falls back to original query.
- **API integration:** two-turn conversation via `POST /api/query` — turn 2
  ("what connects to it?") is rewritten to contain the turn-1 tag.
- **Regression:** request with no `conversation_id` behaves exactly as before.

Plus a manual end-to-end run against the real LLM to confirm a real follow-up
resolves, reporting the measured input-token delta.
