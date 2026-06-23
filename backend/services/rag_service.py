"""
RAG Service
Handles embedding user queries and searching Qdrant for relevant knowledge base chunks.
"""

import logging
import time
from typing import Optional

import google.generativeai as genai
from qdrant_client import QdrantClient

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Singleton clients
_qdrant_client: Optional[QdrantClient] = None
_gemini_initialized = False

MAX_RETRIES = 2
RETRY_DELAY = 1


def _init_gemini():
    """Initialize the Gemini API for embeddings."""
    global _gemini_initialized
    if not _gemini_initialized:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_initialized = True
        logger.info("Gemini embedding API initialized")


def _get_qdrant_client() -> QdrantClient:
    """Get or create the Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        _qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        logger.info(f"Qdrant client connected: {settings.qdrant_host}:{settings.qdrant_port}")
    return _qdrant_client


def embed_query(text: str) -> Optional[list[float]]:
    """
    Generate an embedding for a user query using Gemini.
    
    Uses task_type='retrieval_query' for optimal search performance
    (as opposed to 'retrieval_document' used during ingestion).
    
    Args:
        text: The user's message to embed
    
    Returns:
        Embedding vector, or None on failure
    """
    _init_gemini()
    settings = get_settings()

    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{settings.gemini_embedding_model}",
                content=text,
                task_type="retrieval_query",
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"Embedding attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                logger.error(f"Failed to embed query after {MAX_RETRIES} attempts")
                return None


def search_knowledge(query_text: str, top_k: int = 3) -> list[dict]:
    """
    Search the knowledge base for relevant chunks.
    
    Pipeline: embed query → search Qdrant → return top chunks
    
    Args:
        query_text: The user's message
        top_k: Number of top results to return
    
    Returns:
        List of dicts with keys: text, filename, document_type, score
        Returns empty list on any failure (bot can still respond without RAG).
    """
    # Step 1: Embed the query
    query_vector = embed_query(query_text)
    if query_vector is None:
        logger.warning("Query embedding failed — returning empty context")
        return []

    # Step 2: Search Qdrant using query_points (qdrant-client >= 1.18)
    try:
        client = _get_qdrant_client()
        settings = get_settings()

        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=top_k,
        )

        # Step 3: Extract and format results
        chunks = []
        for point in results.points:
            chunks.append({
                "text": point.payload.get("text", ""),
                "filename": point.payload.get("filename", ""),
                "document_type": point.payload.get("document_type", ""),
                "score": round(point.score, 4),
            })

        logger.info(
            f"RAG search returned {len(chunks)} chunks "
            f"(scores: {[c['score'] for c in chunks]})"
        )
        return chunks

    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        logger.warning("Returning empty context — bot will respond without RAG")
        return []
