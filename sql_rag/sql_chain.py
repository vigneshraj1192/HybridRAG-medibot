import re
import sqlite3
import logging
from typing import Dict, Any, Tuple

from ingest.config import DB_PATH
from backend.llm_client import generate_llm_response

logger = logging.getLogger(__name__)

DB_SCHEMA_PROMPT = """
You are a SQLite expert for MediAssist Health Network.
Translate the user's natural language question into a valid, executable SQLite SELECT query.

Database Schema:
Table 1: `claims`
- claim_id (TEXT, Primary Key e.g. 'CLM-2024-1000')
- patient_id (TEXT)
- patient_name (TEXT)
- department (TEXT e.g. 'cardiology', 'nephrology', 'neurology')
- claim_type (TEXT e.g. 'reimbursement', 'cashless')
- diagnosis_code (TEXT e.g. 'I21.4')
- insurer (TEXT e.g. 'Bajaj Allianz', 'New India Assurance')
- claimed_amount (REAL)
- approved_amount (REAL)
- status (TEXT e.g. 'pending', 'approved', 'rejected', 'escalated')
- submitted_date (TEXT 'YYYY-MM-DD')
- resolved_date (TEXT 'YYYY-MM-DD')

Table 2: `maintenance_tickets`
- ticket_id (TEXT, Primary Key e.g. 'TKT-2024-2000')
- equipment_name (TEXT e.g. 'SterilPro 3000', 'DriveFlow IP-200')
- equipment_id (TEXT)
- category (TEXT e.g. 'sterilisation', 'infusion', 'imaging')
- campus (TEXT)
- issue_type (TEXT e.g. 'preventive_maintenance', 'sensor_failure')
- fault_code (TEXT)
- raised_by (TEXT)
- raised_date (TEXT 'YYYY-MM-DD')
- resolved_date (TEXT 'YYYY-MM-DD')
- status (TEXT e.g. 'in_progress', 'resolved', 'open', 'escalated')
- resolution_note (TEXT)

IMPORTANT RULES:
1. Return ONLY the raw SQL query. Do NOT add explanation, markdown code blocks, or commentary.
2. Use valid SQLite syntax. Use LOWER() for text comparisons if helpful.
"""

def clean_sql_output(raw_output: str) -> str:
    """
    Step 2 requirement: Clean raw LLM output to extract only the SQL statement.
    Strips ```sql ... ``` code fences, leading text, and trailing explanations.
    """
    cleaned = raw_output.strip()
    
    # Remove markdown code fences if present
    sql_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if sql_match:
        cleaned = sql_match.group(1).strip()
    
    # If there are multiple lines with extra text, extract the block starting with SELECT
    if not cleaned.upper().startswith("SELECT") and "SELECT" in cleaned.upper():
        select_idx = cleaned.upper().find("SELECT")
        cleaned = cleaned[select_idx:]
    
    # Strip any trailing semicolon or explanatory comments
    cleaned = re.sub(r";\s*$", "", cleaned)
    return cleaned

def sql_rag_chain(question: str) -> Tuple[str, str, Any]:
    """
    Component 4 Requirement: Plain Python function with 3 explicit steps:
    1. Translate natural language question into SQL using LLM.
    2. Clean raw LLM output to extract only the SQL statement.
    3. Execute SQL against database, then pass results to LLM to produce a natural language answer.
    
    Returns tuple: (natural_language_answer, executed_sql_query, raw_db_result)
    """
    logger.info(f"Executing SQL RAG Chain for question: '{question}'")
    
    # Step 1: Translate Question -> SQL Query via LLM
    sql_prompt = f"{DB_SCHEMA_PROMPT}\nUser Question: {question}\nSQL Query:"
    raw_sql_response = generate_llm_response(prompt=sql_prompt)
    
    # Step 2: Clean raw LLM output to extract ONLY the SQL statement
    cleaned_sql = clean_sql_output(raw_sql_response)
    
    # Fallback SQL if LLM API key is absent or produced invalid SQL
    if not cleaned_sql or "SELECT" not in cleaned_sql.upper():
        if "claim" in question.lower():
            cleaned_sql = "SELECT status, COUNT(*) as count, SUM(claimed_amount) as total_amount FROM claims GROUP BY status"
        else:
            cleaned_sql = "SELECT category, status, COUNT(*) as count FROM maintenance_tickets GROUP BY category, status"
    
    logger.info(f"Cleaned SQL Query: {cleaned_sql}")
    
    # Step 3: Execute SQL against Database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(cleaned_sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()
        
        db_results_str = f"Columns: {columns}\nData Rows:\n{rows}"
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        db_results_str = f"Error executing query: {e}"
        rows = []

    # Step 3 (cont): Pass SQL result back to LLM to produce natural language answer
    synthesis_prompt = f"""
You are an expert healthcare database analyst for MediAssist.
Answer the user's question clearly and accurately based on the SQL query results provided below.

User Question: {question}
Executed SQL Query: {cleaned_sql}
Database Query Results:
{db_results_str}

Provide a concise, professional, and well-structured natural language answer with summary metrics.
"""
    final_answer = generate_llm_response(prompt=synthesis_prompt)
    
    # If demo output fallback was returned by generate_llm_response, produce readable summary
    if "[Demo Output" in final_answer:
        final_answer = f"Based on MediAssist database analysis:\nExecuted SQL: `{cleaned_sql}`\nResults Found: {len(rows)} record(s).\nSummary Data: {rows[:5]}"

    return final_answer, cleaned_sql, rows
