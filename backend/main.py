from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.auth import authenticate_user, create_jwt_token
from backend.routers import chat, collections, health

app = FastAPI(
    title="MediBot RAG API",
    description="Backend service for MediBot with RBAC, Hybrid Search, Cross-Encoder Reranking & SQL RAG",
    version="1.0.0"
)

# Enable CORS for Next.js / React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(credentials: LoginRequest):
    user = authenticate_user(credentials.username, credentials.password)
    token = create_jwt_token(credentials.username, user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"],
        "dept": user["dept"],
        "username": credentials.username
    }

app.include_router(health.router)
app.include_router(collections.router)
app.include_router(chat.router)

if __name__ == "__main__":
    import os
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
