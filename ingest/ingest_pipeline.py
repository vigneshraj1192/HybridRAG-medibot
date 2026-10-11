import os
import glob
import uuid
import logging
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from ingest.config import (
    DATA_DIR,
    QDRANT_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    COLLECTION_ROLES
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_ingestion():
    logger.info("Starting MediBot Document Ingestion Pipeline...")
    
    # 1. Initialize Document Converter & Chunker
    converter = DocumentConverter()
    chunker = HybridChunker()
    
    # 2. Initialize Embeddings Model
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # 3. Initialize Qdrant Local Client
    logger.info(f"Initializing local Qdrant database at {QDRANT_PATH}")
    qdrant_client = QdrantClient(path=QDRANT_PATH)
    
    # Recreate collection to ensure fresh ingestion
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    
    points: List[PointStruct] = []
    total_docs = 0
    total_chunks = 0
    
    # Iterate through collection directories
    for collection_name, access_roles in COLLECTION_ROLES.items():
        collection_dir = DATA_DIR / collection_name
        if not collection_dir.exists():
            logger.warning(f"Directory not found: {collection_dir}")
            continue
        
        file_paths = glob.glob(str(collection_dir / "*.*"))
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in [".pdf", ".md", ".txt"]:
                continue
            
            filename = os.path.basename(file_path)
            logger.info(f"Processing document [{collection_name}]: {filename}")
            total_docs += 1
            
            try:
                # Convert document via Docling
                conversion_result = converter.convert(file_path)
                doc = conversion_result.document
                
                # Split hierarchically into chunks
                doc_chunks = list(chunker.chunk(doc))
                logger.info(f"  Extracted {len(doc_chunks)} structural chunks from {filename}")
                
                for chunk in doc_chunks:
                    chunk_raw_text = chunk.text.strip()
                    if not chunk_raw_text:
                        continue
                    
                    # Extract section heading context
                    section_title = "General"
                    if hasattr(chunk, "meta") and chunk.meta and hasattr(chunk.meta, "headings") and chunk.meta.headings:
                        section_title = " > ".join(chunk.meta.headings)
                    
                    # Determine chunk type
                    chunk_type = "text"
                    if "|" in chunk_raw_text and "\n" in chunk_raw_text:
                        chunk_type = "table"
                    elif len(chunk_raw_text.split()) < 10 and chunk_raw_text.isupper():
                        chunk_type = "heading"
                    
                    # Embed parent section context into the chunk text
                    embedded_text = f"Document: {filename}\nSection: {section_title}\n\n{chunk_raw_text}"
                    
                    # Compute dense embedding
                    vector = embedder.encode(embedded_text).tolist()
                    
                    # Payload matching required metadata schema
                    payload = {
                        "source_document": filename,
                        "collection": collection_name,
                        "access_roles": access_roles,
                        "section_title": section_title,
                        "chunk_type": chunk_type,
                        "text": embedded_text,
                        "raw_text": chunk_raw_text
                    }
                    
                    point_id = str(uuid.uuid4())
                    points.append(PointStruct(id=point_id, vector=vector, payload=payload))
                    total_chunks += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
    
    # Batch upsert into Qdrant
    if points:
        logger.info(f"Upserting {len(points)} chunks into Qdrant collection '{COLLECTION_NAME}'...")
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"Ingestion completed! Total Documents: {total_docs}, Total Chunks: {total_chunks}")
    else:
        logger.error("No chunks were generated during ingestion!")

if __name__ == "__main__":
    run_ingestion()
