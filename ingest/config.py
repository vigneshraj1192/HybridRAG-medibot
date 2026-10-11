import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
QDRANT_PATH = str(BASE_DIR / "qdrant_db")
COLLECTION_NAME = "medibot_chunks"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Role permissions mapping per document collection
COLLECTION_ROLES = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "doctor", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"]
}

# Role accessible collections mapping
ROLE_COLLECTIONS = {
    "doctor": ["clinical", "nursing", "general"],
    "nurse": ["nursing", "general"],
    "billing_executive": ["billing", "general"],
    "technician": ["equipment", "general"],
    "admin": ["clinical", "nursing", "billing", "equipment", "general"]
}

# SQLite DB Path
DB_PATH = str(DATA_DIR / "db" / "mediassist.db")

# Demo users
DEMO_USERS = {
    "dr.mehta": {"password": "Password123!", "role": "doctor", "name": "Dr. Mehta", "dept": "Clinical"},
    "nurse.priya": {"password": "Password123!", "role": "nurse", "name": "Nurse Priya", "dept": "Nursing"},
    "billing.ravi": {"password": "Password123!", "role": "billing_executive", "name": "Ravi Kumar", "dept": "Billing"},
    "tech.anand": {"password": "Password123!", "role": "technician", "name": "Anand Sharma", "dept": "Biomedical"},
    "admin.sys": {"password": "Password123!", "role": "admin", "name": "System Admin", "dept": "IT / Executive"}
}

JWT_SECRET = os.getenv("JWT_SECRET", "medibot_super_secret_jwt_key_2026")
JWT_ALGORITHM = "HS256"
