"""
Qdrant Upload Module
Connects to Qdrant and upserts embedded document chunks as vectors.
"""

import os
import logging
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
load_dotenv()

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "pp5_knowledge")
VECTOR_SIZE = 3072  # Gemini gemini-embedding-2 output dimension


def get_qdrant_client() -> QdrantClient:
    """Create and return a Qdrant client."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    logger.info(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    return client


def create_collection(client: QdrantClient, recreate: bool = True):
    """
    Create the vector collection in Qdrant.
    
    Args:
        client: Qdrant client instance
        recreate: If True, deletes existing collection before creating
    """
    collections = [c.name for c in client.get_collections().collections]

    if QDRANT_COLLECTION in collections:
        if recreate:
            logger.info(f"Deleting existing collection: {QDRANT_COLLECTION}")
            client.delete_collection(QDRANT_COLLECTION)
        else:
            logger.info(f"Collection {QDRANT_COLLECTION} already exists, skipping creation")
            return

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )
    logger.info(
        f"Created collection: {QDRANT_COLLECTION} "
        f"(size={VECTOR_SIZE}, distance=COSINE)"
    )


def upload_vectors(client: QdrantClient, embedded_chunks: list[dict]):
    """
    Upload embedded chunks to Qdrant.
    
    Args:
        client: Qdrant client instance
        embedded_chunks: List of dicts with keys: embedding, text, metadata
    """
    points = []
    for chunk in embedded_chunks:
        point_id = str(uuid4())
        payload = {
            "text": chunk["text"],
            "filename": chunk["metadata"]["filename"],
            "chunk_id": chunk["metadata"]["chunk_id"],
            "document_type": chunk["metadata"]["document_type"],
        }
        points.append(
            PointStruct(
                id=point_id,
                vector=chunk["embedding"],
                payload=payload,
            )
        )

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=batch,
        )
        logger.info(
            f"Uploaded batch {i // batch_size + 1}"
            f"/{(len(points) + batch_size - 1) // batch_size}"
            f" ({len(batch)} points)"
        )

    logger.info(f"Total points uploaded: {len(points)}")


def upload_to_qdrant(embedded_chunks: list[dict], recreate: bool = True):
    """
    Main entry point: create collection and upload all vectors.
    
    Args:
        embedded_chunks: List of dicts from embed_documents()
        recreate: Whether to recreate the collection from scratch
    """
    client = get_qdrant_client()
    create_collection(client, recreate=recreate)
    upload_vectors(client, embedded_chunks)

    # Verify upload
    collection_info = client.get_collection(QDRANT_COLLECTION)
    logger.info(
        f"Verification — Collection '{QDRANT_COLLECTION}' "
        f"has {collection_info.points_count} points"
    )

    return collection_info.points_count
