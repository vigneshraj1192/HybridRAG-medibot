import os
import glob
from pathlib import Path
import fitz # PyMuPDF

BASE_DIR = Path(__file__).resolve().parent
data_dir = str(BASE_DIR / "data")

print("--- Inspecting Markdown Files ---")
for md_file in glob.glob(os.path.join(data_dir, "**", "*.md"), recursive=True):
    print(f"\n=== File: {os.path.basename(md_file)} ===")
    with open(md_file, "r", encoding="utf-8") as f:
        print(f.read()[:500])

print("\n--- Inspecting PDF Files ---")
for pdf_file in glob.glob(os.path.join(data_dir, "**", "*.pdf"), recursive=True):
    print(f"\n=== File: {os.path.basename(pdf_file)} ===")
    doc = fitz.open(pdf_file)
    print(f"Pages: {len(doc)}")
    page_text = doc[0].get_text() if len(doc) > 0 else ""
    print("Page 1 preview:")
    print(page_text[:400])

