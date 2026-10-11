from fastapi import APIRouter
from ingest.config import ROLE_COLLECTIONS

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "app": "MediBot RAG Backend"}

@router.get("/collections/{role}")
def get_accessible_collections(role: str):
    role_lower = role.lower().strip()
    collections = ROLE_COLLECTIONS.get(role_lower, ["general"])
    return {
        "role": role_lower,
        "accessible_collections": collections
    }
