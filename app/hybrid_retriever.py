"""
Hybrid Retriever for P&ID Assistant

Combines dense (ChromaDB vector) retrieval with sparse (BM25 lexical) retrieval
via Reciprocal Rank Fusion (RRF).

Why hybrid for P&IDs:
    P&ID queries are dominated by alphanumeric equipment/instrument tags
    (V-101, PSV-101, PIC-101A). Dense embeddings blur near-identical tags
    (V-101 vs V-102) and handle rare tokens poorly. BM25 does exact token
    matching, so it disambiguates tags regardless of corpus size. Fusing the
    two gives the semantic recall of embeddings plus the tag precision of
    lexical search.

No third-party BM25 dependency: Okapi BM25 is implemented directly here so the
retriever has zero install footprint beyond what the project already uses.
"""

import re
import math
from collections import defaultdict
from typing import List, Dict, Optional, Tuple


# ----------------------------------------------------------------------------
# Tokenization
# ----------------------------------------------------------------------------

# P&ID tag pattern: letters + hyphen + digits, optional trailing letters/suffix.
# Matches V-101, PSV-101, PIC-101A, F-104A, P-104B, F-104B&C (base part).
_TAG_RE = re.compile(r"[A-Za-z]{1,4}-\d{1,4}[A-Za-z]?")
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> List[str]:
    """
    Tag-aware tokenizer.

    Emits lowercase word tokens AND preserves P&ID tags as single tokens
    (e.g. "v-101", "psv-101"). For a tag like "PSV-101" it emits both the
    full tag token and its numeric/alpha parts, so a query for "101" or
    "psv" still overlaps while an exact "psv-101" match scores highest.
    """
    if not text:
        return []

    tokens: List[str] = []

    # 1. Preserve full tags as atomic tokens (lowercased).
    for m in _TAG_RE.finditer(text):
        tokens.append(m.group(0).lower())

    # 2. Standard word tokens (letters/digits), lowercased.
    #    This also captures the parts of tags ("psv", "101") for partial overlap.
    for m in _WORD_RE.finditer(text):
        tok = m.group(0).lower()
        if tok:
            tokens.append(tok)

    return tokens


# ----------------------------------------------------------------------------
# BM25 (Okapi)
# ----------------------------------------------------------------------------

class BM25:
    """Minimal Okapi BM25 over an in-memory corpus."""

    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_tokens = corpus_tokens
        self.N = len(corpus_tokens)
        self.doc_len = [len(doc) for doc in corpus_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0

        # Document frequency per term.
        df: Dict[str, int] = defaultdict(int)
        self.term_freqs: List[Dict[str, int]] = []
        for doc in corpus_tokens:
            freqs: Dict[str, int] = defaultdict(int)
            for tok in doc:
                freqs[tok] += 1
            self.term_freqs.append(freqs)
            for tok in freqs:
                df[tok] += 1

        # Smoothed IDF (BM25+ style, always positive).
        self.idf: Dict[str, float] = {}
        for term, freq in df.items():
            self.idf[term] = math.log(1 + (self.N - freq + 0.5) / (freq + 0.5))

    def scores(self, query_tokens: List[str]) -> List[float]:
        """BM25 score for the query against every document in the corpus."""
        scores = [0.0] * self.N
        for term in query_tokens:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i in range(self.N):
                tf = self.term_freqs[i].get(term, 0)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (tf * (self.k1 + 1)) / denom
        return scores

    def rank(self, query_tokens: List[str], top_k: Optional[int] = None) -> List[Tuple[int, float]]:
        """Return (doc_index, score) sorted by score desc, score > 0 only."""
        scored = list(enumerate(self.scores(query_tokens)))
        scored = [(i, s) for i, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k] if top_k else scored


# ----------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ----------------------------------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists: List[List[str]],
    weights: Optional[List[float]] = None,
    k: int = 60,
) -> List[Tuple[str, float]]:
    """
    Fuse multiple ranked lists of ids via weighted RRF.

    RRF score for an id = sum over lists of  weight / (k + rank).
    `k` (default 60, the standard) dampens the influence of top ranks so a
    single list can't dominate. Robust to score-scale differences between
    dense cosine similarity and BM25.

    Args:
        ranked_lists: each is an ordered list of ids (best first).
        weights: per-list weight; defaults to equal weighting.
        k: RRF constant.

    Returns:
        (id, fused_score) sorted by fused_score desc.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)

    fused: Dict[str, float] = defaultdict(float)
    for lst, w in zip(ranked_lists, weights):
        for rank, _id in enumerate(lst, start=1):
            fused[_id] += w / (k + rank)

    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


# ----------------------------------------------------------------------------
# Hybrid retriever
# ----------------------------------------------------------------------------

class HybridRetriever:
    """
    Dense + BM25 retrieval fused with RRF over a ChromaDB collection.

    The BM25 index is built once from the collection's documents (no embeddings
    required). Dense retrieval reuses a caller-supplied embedding function so
    the embedding provider stays owned by the RAG engine.
    """

    def __init__(
        self,
        collection,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
        rrf_k: int = 60,
    ):
        self.collection = collection
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        self._build_bm25_index()

    def _build_bm25_index(self):
        """Load all documents from the collection and build the BM25 index."""
        data = self.collection.get(include=["documents", "metadatas"])
        self.ids: List[str] = data["ids"]
        self.documents: List[str] = data["documents"]
        self.metadatas: List[dict] = data["metadatas"]
        self._id_to_pos = {cid: i for i, cid in enumerate(self.ids)}
        corpus_tokens = [tokenize(doc) for doc in self.documents]
        self.bm25 = BM25(corpus_tokens)

    def dense_search(self, query_embedding: List[float], top_k: int) -> List[str]:
        """Return ranked chunk ids from dense vector search."""
        res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, len(self.ids)),
            include=["distances"],
        )
        return list(res["ids"][0]) if res["ids"] and res["ids"][0] else []

    def sparse_search(self, query: str, top_k: int) -> List[str]:
        """Return ranked chunk ids from BM25 lexical search."""
        q_tokens = tokenize(query)
        ranked = self.bm25.rank(q_tokens, top_k=top_k)
        return [self.ids[idx] for idx, _ in ranked]

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 3,
        candidate_k: int = 10,
    ) -> List[Dict]:
        """
        Hybrid retrieve: pull `candidate_k` from each retriever, fuse with RRF,
        return the top_k fused results as dicts with text + metadata.

        Args:
            query: raw query string (for BM25).
            query_embedding: precomputed dense embedding (for vector search).
            top_k: number of final results.
            candidate_k: candidates to pull from each retriever before fusion.
        """
        dense_ids = self.dense_search(query_embedding, candidate_k)
        sparse_ids = self.sparse_search(query, candidate_k)

        fused = reciprocal_rank_fusion(
            [dense_ids, sparse_ids],
            weights=[self.dense_weight, self.sparse_weight],
            k=self.rrf_k,
        )

        results: List[Dict] = []
        for cid, score in fused[:top_k]:
            pos = self._id_to_pos.get(cid)
            if pos is None:
                continue
            results.append({
                "id": cid,
                "text": self.documents[pos],
                "metadata": self.metadatas[pos],
                "fusion_score": score,
                "in_dense": cid in dense_ids,
                "in_sparse": cid in sparse_ids,
            })
        return results

    def retrieve_ids(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 3,
        candidate_k: int = 10,
    ) -> List[str]:
        """Convenience: fused ranked ids only (used by eval)."""
        return [r["id"] for r in self.retrieve(query, query_embedding, top_k, candidate_k)]
