"""
Document Embedding Module
Takes chunked documents and generates embeddings using Google Gemini API.
"""

import os
import time
import logging
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
load_dotenv()  # Also check current directory

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
BATCH_SIZE = 20  # Gemini supports batching
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def initialize_gemini():
    """Initialize the Gemini API client."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not found. Set it in config/.env or as an environment variable."
        )
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info(f"Gemini API initialized with model: {GEMINI_EMBEDDING_MODEL}")


def embed_single_text(text: str, task_type: str = "retrieval_document") -> Optional[list[float]]:
    """
    Generate embedding for a single text using Gemini.
    
    Args:
        text: The text to embed
        task_type: Either 'retrieval_document' (for indexing) or 'retrieval_query' (for search)
    
    Returns:
        List of floats (768-dimensional vector) or None on failure
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{GEMINI_EMBEDDING_MODEL}",
                content=text,
                task_type=task_type,
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(
                f"Embedding attempt {attempt + 1}/{MAX_RETRIES} failed: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to embed text after {MAX_RETRIES} attempts: {e}")
                return None


def embed_batch(texts: list[str], task_type: str = "retrieval_document") -> list[Optional[list[float]]]:
    """
    Generate embeddings for a batch of texts.
    
    Args:
        texts: List of texts to embed
        task_type: Task type for the embedding
    
    Returns:
        List of embedding vectors (or None for failed ones)
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{GEMINI_EMBEDDING_MODEL}",
                content=texts,
                task_type=task_type,
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"Batch embedding attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)

    # If batch fails completely, fall back to individual embedding
    logger.warning("Batch embedding failed, falling back to individual embedding")
    return [embed_single_text(text, task_type) for text in texts]


def embed_documents(chunks: list[dict]) -> list[dict]:
    """
    Generate embeddings for all document chunks.
    
    Args:
        chunks: List of chunk dicts from chunk_documents (must have 'text' and 'metadata' keys)
    
    Returns:
        List of dicts with keys: embedding, text, metadata
        Only includes chunks that were successfully embedded.
    """
    initialize_gemini()

    embedded_chunks = []
    total = len(chunks)
    failed_count = 0

    # Process in batches
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = chunks[batch_start:batch_end]
        batch_texts = [chunk["text"] for chunk in batch]

        logger.info(
            f"Embedding batch {batch_start // BATCH_SIZE + 1}"
            f"/{(total + BATCH_SIZE - 1) // BATCH_SIZE}"
            f" (chunks {batch_start + 1}-{batch_end} of {total})"
        )

        embeddings = embed_batch(batch_texts)

        for chunk, embedding in zip(batch, embeddings):
            if embedding is not None:
                embedded_chunks.append({
                    "embedding": embedding,
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                })
            else:
                failed_count += 1
                logger.warning(
                    f"Skipping chunk {chunk['metadata']['chunk_id']} — embedding failed"
                )

        # Small delay between batches to respect rate limits
        if batch_end < total:
            time.sleep(0.5)

    logger.info(
        f"Embedding complete: {len(embedded_chunks)} successful, {failed_count} failed"
    )

    if not embedded_chunks:
        raise ValueError("No chunks were successfully embedded")

    return embedded_chunks
