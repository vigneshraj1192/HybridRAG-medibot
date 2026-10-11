import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi

from ingest.config import QDRANT_PATH, COLLECTION_NAME, EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, top_k_dense: int = 25, final_top_k: int = 10):
        self.qdrant_client = QdrantClient(path=QDRANT_PATH)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.top_k_dense = top_k_dense
        self.final_top_k = final_top_k

    def retrieve(self, query: str, user_role: str) -> List[Dict[str, Any]]:
        """
        Executes metadata-filtered vector retrieval in Qdrant combined with BM25 keyword search.
        RBAC security requirement: Filter by user_role at vector store level BEFORE candidate scoring.
        """
        # 1. Compute Dense Query Vector
        query_vector = self.embedder.encode(query).tolist()

        # 2. Apply Qdrant RBAC Metadata Filter
        rbac_filter = Filter(
            must=[
                FieldCondition(
                    key="access_roles",
                    match=MatchValue(value=user_role)
                )
            ]
        )

        # 3. Dense Vector Retrieval with RBAC Filter
        try:
            res_obj = self.qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=rbac_filter,
                limit=self.top_k_dense
            )
            search_results = res_obj.points
        except AttributeError:
            search_results = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=rbac_filter,
                limit=self.top_k_dense
            )


        if not search_results:
            logger.info(f"No documents matched RBAC filter for role '{user_role}'.")
            return []

        # Convert search results to candidate dicts
        candidates = []
        corpus_texts = []
        for res in search_results:
            cand = {
                "id": res.id,
                "dense_score": res.score,
                "payload": res.payload,
                "text": res.payload.get("text", ""),
                "raw_text": res.payload.get("raw_text", ""),
                "source_document": res.payload.get("source_document", ""),
                "section_title": res.payload.get("section_title", ""),
                "collection": res.payload.get("collection", "")
            }
            candidates.append(cand)
            corpus_texts.append(cand["text"].lower().split())

        # 4. Sparse BM25 Search over RBAC-filtered candidates
        tokenized_query = query.lower().split()
        bm25 = BM25Okapi(corpus_texts)
        bm25_scores = bm25.get_scores(tokenized_query)

        max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0

        # 5. Hybrid Score Fusion (Reciprocal Rank Fusion / Normalized combination)
        for idx, cand in enumerate(candidates):
            norm_bm25 = bm25_scores[idx] / max_bm25 if max_bm25 > 0 else 0.0
            # Hybrid score weighting: 60% Dense + 40% BM25
            cand["hybrid_score"] = (0.6 * cand["dense_score"]) + (0.4 * norm_bm25)

        # Sort candidates by hybrid score
        candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_candidates = candidates[:self.final_top_k]
        
        logger.info(f"HybridRetriever fetched {len(top_candidates)} candidates for role '{user_role}'.")
        return top_candidates
