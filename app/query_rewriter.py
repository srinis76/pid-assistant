"""
Follow-up query rewriting for the P&ID Assistant.

Turns an elliptical / pronoun follow-up into a standalone query using recent
conversation turns, so downstream retrieval (ChromaDB + BM25) and the
keyword-based router operate on a self-contained question.

Example: "what connects to it?" + prior turn about V-101 -> "what connects to V-101?"
"""

from typing import List, Dict


REWRITE_PROMPT = """You rewrite a user's follow-up question into a standalone question \
for a P&ID (Piping & Instrumentation Diagram) assistant.

Using the conversation so far, resolve pronouns and references (it, that, they, \
the separator, etc.) into the explicit equipment tag or noun they refer to. \
Preserve the user's intent and wording as much as possible — only add the missing \
context needed to make the question answerable on its own.

If the question is already standalone, return it unchanged. Return ONLY the \
rewritten question, with no preamble, quotes, or explanation.

{history}

Follow-up question: {query}

Standalone question:"""


def rewrite_followup(query: str, turns: List[Dict], llm_adapter) -> str:
    """Rewrite `query` to standalone form using recent `turns`.

    - No turns -> returns `query` unchanged, with NO LLM call.
    - On any adapter error -> returns `query` unchanged (fail-open: memory must
      never break an otherwise-working query path).
    """
    if not turns:
        return query

    history_lines = ["Conversation so far (most recent last):"]
    for t in turns:
        history_lines.append(f"User: {t['question']}")
        history_lines.append(f"Assistant: {t['answer']}")
    history = "\n".join(history_lines)

    prompt = REWRITE_PROMPT.format(history=history, query=query)

    try:
        rewritten = llm_adapter.call_llm(prompt, images=None, query_type="rewrite")
    except Exception as e:
        print(f"⚠️  Query rewrite failed ({e}); using original query.")
        return query

    rewritten = (rewritten or "").strip()
    # Guard against an empty or degenerate rewrite.
    if not rewritten:
        return query
    return rewritten
