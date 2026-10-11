import os
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

BASE_DIR = Path(__file__).resolve().parent
pdf_path = str(BASE_DIR / "data" / "billing" / "billing_codes.pdf")

converter = DocumentConverter()
result = converter.convert(pdf_path)
doc = result.document

chunker = HybridChunker()
chunks = list(chunker.chunk(doc))

print(f"Total chunks created: {len(chunks)}")
for i, chunk in enumerate(chunks[:3]):
    print(f"\n--- Chunk {i+1} ---")
    print("Text:", chunk.text[:300])
    if hasattr(chunk, 'meta'):
        print("Meta:", chunk.meta)
