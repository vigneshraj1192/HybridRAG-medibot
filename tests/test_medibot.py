import pytest
from fastapi.testclient import TestClient

from backend.main import app
from sql_rag.sql_chain import sql_rag_chain, clean_sql_output

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "MediBot RAG Backend"}

def test_login_demo_users():
    users = ["dr.mehta", "nurse.priya", "billing.ravi", "tech.anand", "admin.sys"]
    for u in users:
        res = client.post("/login", json={"username": u, "password": "Password123!"})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["username"] == u

def test_collections_endpoint():
    res = client.get("/collections/doctor")
    assert res.status_code == 200
    data = res.json()
    assert "clinical" in data["accessible_collections"]
    assert "nursing" in data["accessible_collections"]
    assert "general" in data["accessible_collections"]

def test_sql_rag_cleaner():
    raw_markdown_sql = "```sql\nSELECT status, COUNT(*) FROM claims GROUP BY status;\n```"
    cleaned = clean_sql_output(raw_markdown_sql)
    assert cleaned == "SELECT status, COUNT(*) FROM claims GROUP BY status"

def test_sql_rag_execution():
    question = "How many billing claims were pending?"
    answer, sql_query, db_rows = sql_rag_chain(question)
    assert "SELECT" in sql_query.upper()
    assert "claims" in sql_query.lower()
    assert isinstance(db_rows, list)

def test_rbac_denial_for_nurse_billing_analytics():
    # Nurse requesting analytical billing metrics -> must be blocked
    res = client.post(
        "/chat",
        json={"question": "How many billing claims were escalated last month?", "role": "nurse"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "do not have permission" in data["answer"].lower()
    assert data["role"] == "nurse"
    assert len(data["sources"]) == 0
