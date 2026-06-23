"""
Ingestion Pipeline Orchestrator
Runs the full pipeline: chunk → embed → upload to Qdrant.

Usage:
    python -m ingestion.run_ingestion
    # or
    python ingestion/run_ingestion.py
"""

import sys
import os
import time
import logging

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.chunk_documents import run_chunking
from ingestion.embed_documents import embed_documents
from ingestion.upload_to_qdrant import upload_to_qdrant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingestion")


def run_pipeline():
    """Run the complete ingestion pipeline."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("STARTING INGESTION PIPELINE")
    logger.info("=" * 60)

    # Step 1: Chunk documents
    logger.info("")
    logger.info("STEP 1/3: Chunking documents...")
    logger.info("-" * 40)
    try:
        chunks = run_chunking()
        logger.info(f"✓ Chunking complete: {len(chunks)} chunks created")
    except Exception as e:
        logger.error(f"✗ Chunking failed: {e}")
        sys.exit(1)

    # Step 2: Generate embeddings
    logger.info("")
    logger.info("STEP 2/3: Generating embeddings...")
    logger.info("-" * 40)
    try:
        embedded_chunks = embed_documents(chunks)
        logger.info(f"✓ Embedding complete: {len(embedded_chunks)} vectors generated")
    except Exception as e:
        logger.error(f"✗ Embedding failed: {e}")
        sys.exit(1)

    # Step 3: Upload to Qdrant
    logger.info("")
    logger.info("STEP 3/3: Uploading to Qdrant...")
    logger.info("-" * 40)
    try:
        point_count = upload_to_qdrant(embedded_chunks, recreate=True)
        logger.info(f"✓ Upload complete: {point_count} points stored in Qdrant")
    except Exception as e:
        logger.error(f"✗ Upload failed: {e}")
        sys.exit(1)

    # Summary
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE COMPLETE")
    logger.info(f"  Documents processed: {len(chunks)} chunks from knowledge base")
    logger.info(f"  Vectors generated:   {len(embedded_chunks)}")
    logger.info(f"  Points in Qdrant:    {point_count}")
    logger.info(f"  Time elapsed:        {elapsed:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
