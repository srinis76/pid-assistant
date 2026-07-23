"""
Conversation Memory for the P&ID Assistant.

Short-term, session-scoped memory: stores each (question, answer) turn per
conversation in SQLite and returns a bounded sliding window of recent turns so
multi-turn chats stay coherent (e.g. "what connects to it?" can be resolved
against a prior turn).

This is deliberately NOT a vector store — conversation turns go straight into
the prompt as text. ChromaDB remains exclusively for P&ID document chunks.
"""

import sqlite3
from typing import List, Dict, Optional


# Default number of recent turns to carry forward (the sliding window size).
DEFAULT_WINDOW = 6


class ConversationMemory:
    """Owns SQLite persistence for per-conversation turns."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        """Create the turns table if it doesn't exist (upgrades existing DBs)."""
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    turn_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    turn_index      INTEGER NOT NULL,
                    question        TEXT NOT NULL,
                    answer          TEXT NOT NULL,
                    route           TEXT,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_convo
                ON conversation_turns(conversation_id, turn_index)
            """)
            conn.commit()
        finally:
            conn.close()

    def add_turn(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        route: Optional[str] = None,
    ) -> None:
        """Append a turn. `question` should be the ORIGINAL user text."""
        if not conversation_id:
            return
        conn = self._connect()
        try:
            # Next turn_index = current count for this conversation.
            row = conn.execute(
                "SELECT COALESCE(MAX(turn_index) + 1, 0) FROM conversation_turns "
                "WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            next_index = row[0] if row else 0
            conn.execute(
                "INSERT INTO conversation_turns "
                "(conversation_id, turn_index, question, answer, route) "
                "VALUES (?, ?, ?, ?, ?)",
                (conversation_id, next_index, question, answer, route),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_turns(
        self,
        conversation_id: str,
        n: int = DEFAULT_WINDOW,
    ) -> List[Dict]:
        """Return the last `n` turns for a conversation, oldest-first."""
        if not conversation_id:
            return []
        conn = self._connect()
        try:
            # Grab the newest n by turn_index, then reverse to oldest-first.
            rows = conn.execute(
                "SELECT question, answer, route FROM conversation_turns "
                "WHERE conversation_id = ? "
                "ORDER BY turn_index DESC LIMIT ?",
                (conversation_id, n),
            ).fetchall()
        finally:
            conn.close()
        turns = [{"question": q, "answer": a, "route": r} for (q, a, r) in rows]
        turns.reverse()
        return turns

    @staticmethod
    def format_for_prompt(turns: List[Dict]) -> str:
        """Render turns into a plain-text block for injection into a prompt.

        Returns "" when there are no turns, so callers can inject unconditionally.
        """
        if not turns:
            return ""
        lines = ["Previous conversation (most recent last):"]
        for t in turns:
            lines.append(f"User: {t['question']}")
            lines.append(f"Assistant: {t['answer']}")
        return "\n".join(lines)
