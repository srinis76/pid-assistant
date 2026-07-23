# P&ID Assistant — Demo Script

A tight, ~8-minute walkthrough. Each step pairs *what to click* with *the story it tells*.

## Setup (before the demo)

```bash
source venv/bin/activate
uvicorn api.main:app --port 8000      # → http://localhost:8000
```

Confirm `✅ Engines ready` in the terminal. Open the browser to `http://localhost:8000`.

---

## 1. The problem (30s)

> "Operators and engineers need answers from P&ID drawings — equipment specs, instrument loops, safety systems, connections — but today that means manually hunting through dense diagrams. This turns the drawing into something you can ask questions of, in plain English."

Point at the clean home screen — capability-diverse starter questions, one obvious input.

## 2. Text query → grounded answer with citations (90s)

Click **"What is V-101 and its operating conditions?"**

- Answer comes back with specs, equipment tags styled.
- Point at the citation: **"V-101 Datasheet · D-254-001 Sheet 4."**
  > "Every answer cites the drawing and sheet it came from — trust and traceability, not a black box."
- Tap the citation → the source cards.

**Story:** grounded RAG with human-readable provenance.

## 3. Hybrid retrieval (the tag-precision win) (90s)

Toggle **☰ → Display → Technical detail ON**, then ask **"What is the motor horsepower of C-104?"**

- Open the source's **"Why this source?"** → shows *rank + retrieval mode (hybrid)*.
  > "P&ID queries are tag-heavy — V-101 vs V-102. Dense embeddings blur near-identical tags; I added a BM25 lexical retriever fused with vectors via Reciprocal Rank Fusion. On this query, dense ranked the right chunk #5, keyword search #1 — fusion recovers it. My retrieval eval proves the lift: hit@1 80 → 85%."

**Story:** a data-characteristic-driven architecture choice, validated by evals.

## 4. Vision query → shows the diagram (60s)

Ask **"Show where V-101 connects downstream."**

- Router sends this to the **vision** path; the answer traces connections **and renders the actual P&ID page**.
  > "Spatial questions route to a vision model that reads the drawing image directly — and the UI shows the referenced sheet so the operator can verify."

**Story:** hybrid RAG **+** vision, with the right tool auto-selected.

## 5. Maintenance context (30s)

Ask **"Any recent maintenance on C-104?"**

- A maintenance record card surfaces inline.
  > "Operational context — open/closed tickets — surfaces alongside the technical answer."

## 6. Evaluation — the differentiator (2 min)

Go **☰ → Evaluation benchmarks**.

- Point at the **scope banner** (what data, how many questions, last run).
- Walk the three layers:
  - **Retrieval** — hit@1 85% (hybrid vs vector), deterministic vs gold chunks.
  - **Generation** — cross-model matrix: `flash-lite` wins correctness/latency/cost. *"Model choice is data-driven — I can swap any of 300+ models via one config line and the matrix re-scores."*
  - **Vision extraction** — deterministic vs ground truth, **averaged over runs** because extraction is stochastic (12, 12, then 5 equipment on identical runs — which is *why* the harness exists).

**Story:** every architectural claim is backed by an eval that targets a specific failure mode — and I know *when not* to reach for a technique (deferred reranking until multi-doc scale makes it worthwhile).

## 7. Architecture close (30s)

> "It's a FastAPI service wrapping the engines, provider-agnostic via OpenRouter, hybrid retrieval, three eval layers, and a custom UI with operator and engineer modes. The throughline: every choice is measured, and the system is model- and scale-agnostic by design."

---

## One-liners to have ready

- **Why not just bigger embeddings?** Tag precision is a lexical problem; BM25 solves it at any scale — proven by the eval, not assumed.
- **Why flash-lite?** The matrix says so — best correctness, faithfulness, latency, and near-lowest cost of the models tested.
- **Why not reranking yet?** At ~15 chunks there's nothing to rerank; its ROI appears at multi-doc scale, so it's sequenced after that — and the eval will decide if it earns its latency.
- **Multi-doc?** The next milestone; citations are already drawing/sheet-aware, so the UI is ready for it.
