"""
Hybrid Search - Reference Implementation
Combines BM25 keyword search with vector semantic search and Cohere reranking.
Achieves 91% accuracy vs. 72% vector-only vs. 58% BM25-only (see DEC-005).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    clause_id: str
    contract_id: str
    contract_filename: str
    clause_type: str
    text: str
    page_number: int
    section_reference: Optional[str]
    risk_level: str
    relevance_score: float
    match_method: str  # bm25, vector, hybrid


class HybridSearch:
    """
    Three-stage search pipeline:
    1. BM25 keyword search (PostgreSQL full-text) - catches exact legal terms
    2. Vector semantic search (pgvector HNSW) - catches conceptual equivalents
    3. Reciprocal Rank Fusion + Cohere Rerank - merges and reorders results

    Why hybrid over vector-only:
    Legal text requires BOTH exact term matching ("force majeure") AND
    semantic matching ("events beyond reasonable control"). Neither approach
    alone achieves acceptable recall for legal professionals.
    """

    RRF_K = 60  # Reciprocal Rank Fusion constant (standard value)
    BM25_LIMIT = 50
    VECTOR_LIMIT = 50
    RERANK_INPUT = 20  # Send top 20 to Cohere for reranking
    FINAL_LIMIT = 10   # Return top 10 to user

    def __init__(self, db_connection=None, embedding_client=None, rerank_client=None):
        self.db = db_connection
        self.embedding_client = embedding_client
        self.rerank_client = rerank_client

    def search(
        self,
        query: str,
        deal_id: str,
        filters: Optional[dict] = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Execute hybrid search across all clauses in a deal.

        Args:
            query: Natural language search query
            deal_id: Scope search to this deal
            filters: Optional filters (contract_type, risk_level, clause_type)
            limit: Number of results to return

        Returns:
            Reranked list of matching clauses with relevance scores
        """
        # Stage 1: Parallel BM25 + vector search
        bm25_results = self._bm25_search(query, deal_id, filters)
        query_embedding = self._embed_query(query)
        vector_results = self._vector_search(query_embedding, deal_id, filters)

        # Stage 2: Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(bm25_results, vector_results)

        # Stage 3: Cohere Rerank on top candidates
        reranked = self._rerank(query, fused_results[: self.RERANK_INPUT])

        return reranked[:limit]

    def _bm25_search(
        self, query: str, deal_id: str, filters: Optional[dict] = None
    ) -> list[dict]:
        """
        PostgreSQL full-text search using GIN index on clause text.
        Catches exact legal terms like "force majeure", "indemnification",
        "Section 14.2".
        """
        # In production:
        # SELECT
        #     c.id, c.extracted_text, c.contract_id, c.clause_type,
        #     c.page_number, c.risk_level,
        #     ts_rank(to_tsvector('english', c.extracted_text),
        #             plainto_tsquery($1)) AS score
        # FROM clauses c
        # JOIN contracts con ON con.id = c.contract_id
        # WHERE con.deal_id = $2
        #   AND to_tsvector('english', c.extracted_text) @@ plainto_tsquery($1)
        # ORDER BY score DESC
        # LIMIT 50

        return []

    def _vector_search(
        self, query_embedding: list[float], deal_id: str, filters: Optional[dict] = None
    ) -> list[dict]:
        """
        pgvector HNSW approximate nearest neighbor search.
        Catches semantic equivalents: "termination for cause" matches
        "right to end agreement for material breach".

        Uses cosine distance with HNSW index (m=16, ef_construction=128).
        """
        # In production:
        # SELECT
        #     c.id, c.extracted_text, c.contract_id, c.clause_type,
        #     c.page_number, c.risk_level,
        #     1 - (ce.embedding <=> $1::vector) AS score
        # FROM clause_embeddings ce
        # JOIN clauses c ON c.id = ce.clause_id
        # JOIN contracts con ON con.id = c.contract_id
        # WHERE con.deal_id = $2
        # ORDER BY ce.embedding <=> $1::vector
        # LIMIT 50

        return []

    def _embed_query(self, query: str) -> list[float]:
        """
        Generate query embedding using voyage-law-2.
        Returns 1024-dimensional vector optimized for legal text retrieval.
        """
        # In production:
        # response = self.embedding_client.embed(
        #     texts=[query],
        #     model="voyage-law-2",
        #     input_type="query",  # Different from "document" - asymmetric embedding
        # )
        # return response.embeddings[0]

        return [0.0] * 1024  # Placeholder

    def _reciprocal_rank_fusion(
        self,
        bm25_results: list[dict],
        vector_results: list[dict],
    ) -> list[dict]:
        """
        Merge BM25 and vector results using Reciprocal Rank Fusion (RRF).

        RRF formula: score = sum(1 / (k + rank_i)) for each result list
        where k is a constant (60 is standard).

        RRF advantages over score normalization:
        - Doesn't require calibrating score distributions between BM25 and vector
        - Robust to outlier scores
        - Well-studied in information retrieval literature
        """
        rrf_scores = {}

        # Score BM25 results by rank
        for rank, result in enumerate(bm25_results):
            clause_id = result.get("id")
            rrf_scores[clause_id] = rrf_scores.get(clause_id, {
                "score": 0.0, "data": result, "methods": []
            })
            rrf_scores[clause_id]["score"] += 1.0 / (self.RRF_K + rank + 1)
            rrf_scores[clause_id]["methods"].append("bm25")

        # Score vector results by rank
        for rank, result in enumerate(vector_results):
            clause_id = result.get("id")
            rrf_scores[clause_id] = rrf_scores.get(clause_id, {
                "score": 0.0, "data": result, "methods": []
            })
            rrf_scores[clause_id]["score"] += 1.0 / (self.RRF_K + rank + 1)
            rrf_scores[clause_id]["methods"].append("vector")

        # Sort by combined RRF score
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        return sorted_results

    def _rerank(self, query: str, candidates: list[dict]) -> list[SearchResult]:
        """
        Rerank top candidates using Cohere Rerank (cross-encoder model).
        Cross-encoders are more accurate than bi-encoders for final ranking
        because they process query-document pairs jointly.

        Adds ~150ms latency but significantly improves result ordering.
        """
        if not candidates:
            return []

        # In production:
        # documents = [c["data"]["extracted_text"] for c in candidates]
        # response = self.rerank_client.rerank(
        #     model="rerank-english-v3.0",
        #     query=query,
        #     documents=documents,
        #     top_n=self.FINAL_LIMIT,
        # )
        #
        # return [
        #     SearchResult(
        #         clause_id=candidates[r.index]["data"]["id"],
        #         contract_id=candidates[r.index]["data"]["contract_id"],
        #         ...
        #         relevance_score=r.relevance_score,
        #         match_method="hybrid",
        #     )
        #     for r in response.results
        # ]

        return []
