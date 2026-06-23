"""
Document Chunking Module
Reads all .md files from the knowledge_base/ directory and splits them
into smaller chunks suitable for embedding and vector storage.
"""

import os
import logging
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Chunking configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Map filenames to document types for metadata
DOCUMENT_TYPE_MAP = {
    "company_overview.md": "company_overview",
    "services.md": "services",
    "faqs.md": "faqs",
    "pricing_guidelines.md": "pricing",
    "case_studies.md": "case_studies",
    "contact_information.md": "contact",
}


def get_knowledge_base_path() -> Path:
    """Get the path to the knowledge_base directory."""
    # When running from project root
    kb_path = Path(__file__).parent.parent / "knowledge_base"
    if kb_path.exists():
        return kb_path
    # Fallback: check /app/knowledge_base (Docker)
    docker_path = Path("/app/knowledge_base")
    if docker_path.exists():
        return docker_path
    raise FileNotFoundError(
        f"Knowledge base directory not found. Checked: {kb_path}, {docker_path}"
    )


def read_documents(kb_path: Path) -> list[dict]:
    """
    Read all .md files from the knowledge base directory.
    
    Returns:
        List of dicts with keys: text, filename, document_type
    """
    documents = []
    md_files = sorted(kb_path.glob("*.md"))

    if not md_files:
        logger.warning(f"No .md files found in {kb_path}")
        return documents

    for filepath in md_files:
        try:
            text = filepath.read_text(encoding="utf-8")
            filename = filepath.name
            doc_type = DOCUMENT_TYPE_MAP.get(filename, "general")

            documents.append({
                "text": text,
                "filename": filename,
                "document_type": doc_type,
            })
            logger.info(f"Read: {filename} ({len(text)} chars, type: {doc_type})")
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            continue

    logger.info(f"Total documents read: {len(documents)}")
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Split documents into smaller chunks with metadata.
    
    Args:
        documents: List of document dicts from read_documents()
    
    Returns:
        List of chunk dicts with keys: text, metadata (filename, chunk_id, document_type)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in documents:
        try:
            text_chunks = splitter.split_text(doc["text"])
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    "text": chunk_text.strip(),
                    "metadata": {
                        "filename": doc["filename"],
                        "chunk_id": f"{doc['filename']}_{i}",
                        "document_type": doc["document_type"],
                    },
                })
            logger.info(
                f"Chunked {doc['filename']}: {len(text_chunks)} chunks"
            )
        except Exception as e:
            logger.error(f"Failed to chunk {doc['filename']}: {e}")
            continue

    logger.info(f"Total chunks created: {len(chunks)}")
    return chunks


def run_chunking() -> list[dict]:
    """Main entry point: read and chunk all knowledge base documents."""
    kb_path = get_knowledge_base_path()
    logger.info(f"Knowledge base path: {kb_path}")

    documents = read_documents(kb_path)
    if not documents:
        raise ValueError("No documents found to chunk")

    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("No chunks produced from documents")

    return chunks
