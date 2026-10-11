import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
db_path = str(BASE_DIR / "data" / "db" / "mediassist.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables:", tables)

for table_name in [t[0] for t in tables]:
    print(f"\n--- Schema for {table_name} ---")
    schema = cursor.execute(f"PRAGMA table_info({table_name});").fetchall()
    for col in schema:
        print(col)
    
    print(f"Sample rows from {table_name}:")
    rows = cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;").fetchall()
    for r in rows:
        print(r)

conn.close()
