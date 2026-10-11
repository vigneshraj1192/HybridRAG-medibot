import re
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.reranker import Reranker
from sql_rag.sql_chain import sql_rag_chain
from backend.llm_client import generate_llm_response
from ingest.config import ROLE_COLLECTIONS

logger = logging.getLogger(__name__)

router = APIRouter()

# Singletons for retriever and reranker to speed up requests
_retriever = None
_reranker = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker

class ChatRequest(BaseModel):
    question: str
    role: Optional[str] = None

class SourceItem(BaseModel):
    source_document: str
    section_title: str
    collection: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    retrieval_type: str
    role: str

ANALYTICAL_KEYWORDS = [
    "how many", "total amount", "claimed amount", "approved amount",
    "maintenance tickets", "billing claims", "escalated", "pending claims",
    "count of", "average amount", "open tickets", "fault code", "insurer", "claims across"
]

def is_analytical_question(question: str) -> bool:
    q_lower = question.lower()
    return any(kw in q_lower for kw in ANALYTICAL_KEYWORDS)

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    question = request.question.strip()
    user_role = (request.role or current_user.get("role") or "doctor").lower().strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    logger.info(f"Processing /chat request. Question: '{question}', Role: '{user_role}'")
    
    # 1. Routing logic: Check if query is an analytical/database question
    if is_analytical_question(question):
        # RBAC Security Check: SQL RAG is strictly restricted to billing_executive and admin
        if user_role not in ["billing_executive", "admin"]:
            refusal_msg = (
                f"As a {user_role.replace('_', ' ')}, you do not have permission to access analytical "
                f"billing or equipment maintenance database metrics. Database analytics are restricted to billing executives and system administrators."
            )
            return ChatResponse(
                answer=refusal_msg,
                sources=[],
                retrieval_type="sql_rag",
                role=user_role
            )
        
        # Execute SQL RAG Chain
        answer, sql_query, db_rows = sql_rag_chain(question)
        sources = [
            SourceItem(
                source_document="mediassist.db",
                section_title=f"SQL Query: {sql_query}",
                collection="relational_db"
            )
        ]
        return ChatResponse(
            answer=answer,
            sources=sources,
            retrieval_type="sql_rag",
            role=user_role
        )

    # 2. Document RAG Routing (Hybrid Search + Cross-Encoder Reranker)
    retriever = get_retriever()
    reranker = get_reranker()
    
    # Step 1: Hybrid Retrieval with Qdrant RBAC Metadata Filter
    broad_candidates = retriever.retrieve(query=question, user_role=user_role)
    
    # Handle RBAC dismissal if 0 candidates match role filter
    if not broad_candidates:
        accessible_cols = ", ".join(ROLE_COLLECTIONS.get(user_role, ["general"]))
        refusal_msg = (
            f"As a {user_role.replace('_', ' ')}, you don't have access to requested document collections. "
            f"I can only answer questions from your permitted collections ({accessible_cols})."
        )
        return ChatResponse(
            answer=refusal_msg,
            sources=[],
            retrieval_type="hybrid_rag",
            role=user_role
        )
    
    # Step 2: Cross-Encoder Reranking (Top-10 -> Top-3)
    top_chunks = reranker.rerank(query=question, candidates=broad_candidates, top_n=3)
    
    # Check if top reranked chunks match the query context
    if top_chunks and top_chunks[0].get("rerank_score", 0.0) < -10.0:
        # Very low relevance score
        accessible_cols = ", ".join(ROLE_COLLECTIONS.get(user_role, ["general"]))
        refusal_msg = (
            f"As a {user_role.replace('_', ' ')}, I could not find relevant information in your accessible collections ({accessible_cols}) to answer this query."
        )
        return ChatResponse(
            answer=refusal_msg,
            sources=[],
            retrieval_type="hybrid_rag",
            role=user_role
        )

    # Step 3: Build Prompt & Synthesize Answer via LLM
    context_str = ""
    sources_list = []
    for idx, cand in enumerate(top_chunks):
        context_str += f"\n--- Source Passage {idx+1} [{cand['source_document']} | {cand['section_title']}] ---\n{cand['text']}\n"
        sources_list.append(
            SourceItem(
                source_document=cand["source_document"],
                section_title=cand["section_title"],
                collection=cand["collection"]
            )
        )
    
    system_prompt = (
        "You are MediBot, an intelligent medical and administrative assistant for MediAssist Health Network. "
        "Answer the user's question accurately using ONLY the provided source passages below. "
        "Always cite specific document names and section titles where appropriate."
    )
    user_prompt = f"User Question: {question}\n\nRetrieved Passages:\n{context_str}\n\nAnswer:"
    
    answer = generate_llm_response(prompt=user_prompt, system_instruction=system_prompt)
    
    # Fallback formatting if API keys missing
    if "[Demo Output" in answer:
        top_doc = sources_list[0].source_document if sources_list else "handbook"
        top_sec = sources_list[0].section_title if sources_list else "General"
        answer = f"Based on {top_doc} ({top_sec}):\n{top_chunks[0]['raw_text']}"

    return ChatResponse(
        answer=answer,
        sources=sources_list,
        retrieval_type="hybrid_rag",
        role=user_role
    )
