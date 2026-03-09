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

        Uses ts_rank with tsvector/tsquery for FTS on clause text.
        """
        if not self.db:
            return []

        try:
            # Build dynamic WHERE clause for filters
            where_clauses = ["con.deal_id = %s"]
            params = [deal_id]

            if filters:
                if filters.get("clause_type"):
                    where_clauses.append("c.clause_type = %s")
                    params.append(filters["clause_type"])
                if filters.get("risk_level"):
                    where_clauses.append("c.risk_level = %s")
                    params.append(filters["risk_level"])
                if filters.get("contract_type"):
                    where_clauses.append("con.contract_type = %s")
                    params.append(filters["contract_type"])

            where_sql = " AND ".join(where_clauses)

            sql = f"""
            SELECT
                c.id, c.extracted_text, c.contract_id, c.clause_type,
                c.page_number, c.risk_level, c.section_reference,
                con.filename as contract_filename,
                ts_rank(to_tsvector('english', c.extracted_text),
                        plainto_tsquery('english', %s)) AS score
            FROM clauses c
            JOIN contracts con ON con.id = c.contract_id
            WHERE {where_sql}
              AND to_tsvector('english', c.extracted_text) @@ plainto_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
            """

            # Add query parameter (appears twice - once for rank, once for filter)
            params.insert(0, query)
            params.append(query)
            params.append(self.BM25_LIMIT)

            cursor = self.db.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # Convert to list of dicts
            bm25_results = [
                {
                    "id": r[0],
                    "extracted_text": r[1],
                    "contract_id": r[2],
                    "clause_type": r[3],
                    "page_number": r[4],
                    "risk_level": r[5],
                    "section_reference": r[6],
                    "contract_filename": r[7],
                    "score": r[8] or 0.0,
                }
                for r in results
            ]

            return bm25_results

        except Exception as e:
            # Log error but don't fail the entire search
            import logging
            logging.error(f"BM25 search error: {e}")
            return []

    def _vector_search(
        self, query_embedding: list[float], deal_id: str, filters: Optional[dict] = None
    ) -> list[dict]:
        """
        pgvector HNSW approximate nearest neighbor search.
        Catches semantic equivalents: "termination for cause" matches
        "right to end agreement for material breach".

        Uses cosine distance (<=>) with HNSW index (m=16, ef_construction=128).
        Returns results ordered by vector distance, converted to similarity score.
        """
        if not self.db or not query_embedding:
            return []

        try:
            # Convert embedding to PostgreSQL vector format
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Build dynamic WHERE clause for filters
            where_clauses = ["con.deal_id = %s"]
            params = [deal_id]

            if filters:
                if filters.get("clause_type"):
                    where_clauses.append("c.clause_type = %s")
                    params.append(filters["clause_type"])
                if filters.get("risk_level"):
                    where_clauses.append("c.risk_level = %s")
                    params.append(filters["risk_level"])
                if filters.get("contract_type"):
                    where_clauses.append("con.contract_type = %s")
                    params.append(filters["contract_type"])

            where_sql = " AND ".join(where_clauses)

            sql = f"""
            SELECT
                c.id, c.extracted_text, c.contract_id, c.clause_type,
                c.page_number, c.risk_level, c.section_reference,
                con.filename as contract_filename,
                1 - (ce.embedding <=> %s::vector) AS score
            FROM clause_embeddings ce
            JOIN clauses c ON c.id = ce.clause_id
            JOIN contracts con ON con.id = c.contract_id
            WHERE {where_sql}
            ORDER BY ce.embedding <=> %s::vector ASC
            LIMIT %s
            """

            # Add vector parameter (appears twice)
            params.append(embedding_str)
            params.append(embedding_str)
            params.append(self.VECTOR_LIMIT)

            cursor = self.db.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # Convert to list of dicts
            vector_results = [
                {
                    "id": r[0],
                    "extracted_text": r[1],
                    "contract_id": r[2],
                    "clause_type": r[3],
                    "page_number": r[4],
                    "risk_level": r[5],
                    "section_reference": r[6],
                    "contract_filename": r[7],
                    "score": max(0.0, r[8]) if r[8] is not None else 0.0,  # Convert distance to similarity
                }
                for r in results
            ]

            return vector_results

        except Exception as e:
            # Log error but don't fail the entire search
            import logging
            logging.error(f"Vector search error: {e}")
            return []

    def _embed_query(self, query: str) -> list[float]:
        """
        Generate query embedding using voyage-law-2.
        Returns 1024-dimensional vector optimized for legal text retrieval.

        Uses asymmetric embedding with input_type="query" which differs from
        "document" type used for clause embeddings.
        """
        if not self.embedding_client or not query:
            # Return zero vector as fallback
            return [0.0] * 1024

        try:
            response = self.embedding_client.embed(
                texts=[query],
                model="voyage-law-2",
                input_type="query",  # Asymmetric - different from document type
            )
            if response and response.embeddings:
                return response.embeddings[0]
            else:
                return [0.0] * 1024
        except Exception as e:
            # Log error but return fallback
            import logging
            logging.error(f"Embedding error: {e}")
            return [0.0] * 1024

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

        try:
            if self.rerank_client:
                # Extract text from candidates for reranking
                documents = [c["data"]["extracted_text"] for c in candidates]

                response = self.rerank_client.rerank(
                    model="rerank-english-v3.0",
                    query=query,
                    documents=documents,
                    top_n=self.FINAL_LIMIT,
                )

                results = []
                for rerank_result in response.results:
                    candidate = candidates[rerank_result.index]
                    data = candidate["data"]
                    methods = candidate.get("methods", ["hybrid"])

                    results.append(SearchResult(
                        clause_id=data["id"],
                        contract_id=data["contract_id"],
                        contract_filename=data.get("contract_filename", ""),
                        clause_type=data.get("clause_type", ""),
                        text=data.get("extracted_text", ""),
                        page_number=data.get("page_number", 0),
                        section_reference=data.get("section_reference"),
                        risk_level=data.get("risk_level", "low"),
                        relevance_score=rerank_result.relevance_score,
                        match_method="hybrid",
                    ))
                return results
            else:
                # Fallback: convert candidates to SearchResults without reranking
                results = []
                for candidate in candidates[:self.FINAL_LIMIT]:
                    data = candidate["data"]
                    methods = candidate.get("methods", ["hybrid"])

                    results.append(SearchResult(
                        clause_id=data["id"],
                        contract_id=data["contract_id"],
                        contract_filename=data.get("contract_filename", ""),
                        clause_type=data.get("clause_type", ""),
                        text=data.get("extracted_text", ""),
                        page_number=data.get("page_number", 0),
                        section_reference=data.get("section_reference"),
                        risk_level=data.get("risk_level", "low"),
                        relevance_score=data.get("score", 0.5),
                        match_method="/".join(methods) if methods else "hybrid",
                    ))
                return results

        except Exception as e:
            # Log error but return fallback
            import logging
            logging.error(f"Reranking error: {e}")

            # Fallback: return candidates as-is
            results = []
            for candidate in candidates[:self.FINAL_LIMIT]:
                data = candidate["data"]
                results.append(SearchResult(
                    clause_id=data["id"],
                    contract_id=data["contract_id"],
                    contract_filename=data.get("contract_filename", ""),
                    clause_type=data.get("clause_type", ""),
                    text=data.get("extracted_text", ""),
                    page_number=data.get("page_number", 0),
                    section_reference=data.get("section_reference"),
                    risk_level=data.get("risk_level", "low"),
                    relevance_score=data.get("score", 0.5),
                    match_method="hybrid",
                ))
            return results
