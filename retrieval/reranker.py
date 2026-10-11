import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

from ingest.config import RERANKER_MODEL_NAME

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self, model_name: str = RERANKER_MODEL_NAME):
        logger.info(f"Loading Cross-Encoder reranker: {model_name}")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Prepare pairs for cross-encoder scoring
        pairs = [[query, cand["text"]] for cand in candidates]
        scores = self.model.predict(pairs)

        for idx, score in enumerate(scores):
            candidates[idx]["rerank_score"] = float(score)

        # Sort candidates descending by rerank score
        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_reranked = candidates[:top_n]
        
        logger.info(f"Cross-Encoder reranked {len(candidates)} candidates -> selected top {len(top_reranked)} chunks.")
        return top_reranked
