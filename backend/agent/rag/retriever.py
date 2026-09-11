from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

try:
    # Works when imported as backend.agent.rag.retriever
    from .ingest import VoyageEmbeddings
except ImportError:
    # Works when this file is run directly
    from ingest import VoyageEmbeddings


ROOT_DIR = Path(__file__).resolve().parents[3]


# ============================================================
# Settings
# ============================================================

def _settings() -> tuple[str, str, str]:
    """Load and validate shared environment settings."""

    load_dotenv(override=True)

    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX")
    voyage_api_key = os.getenv("VOYAGE_API_KEY")

    if not pinecone_api_key:
        raise RuntimeError(
            "PINECONE_API_KEY is missing"
        )

    if not pinecone_index_name:
        raise RuntimeError(
            "PINECONE_INDEX is missing"
        )

    if not voyage_api_key:
        raise RuntimeError(
            "VOYAGE_API_KEY is missing"
        )

    return (
        pinecone_api_key,
        pinecone_index_name,
        voyage_api_key,
    )


# ============================================================
# Vector store
# ============================================================

def get_vector_store() -> PineconeVectorStore:
    """Return a LangChain vector store connected to Pinecone."""

    pinecone_api_key, index_name, voyage_api_key = (
        _settings()
    )

    embeddings = VoyageEmbeddings(
        api_key=voyage_api_key
    )

    return PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        pinecone_api_key=pinecone_api_key,
    )


# ============================================================
# Hazard normalization
# ============================================================

def _normalize_hazard(
    hazard: Optional[str],
) -> Optional[str]:

    if hazard is None:
        return None

    hazard = hazard.strip().lower()

    if not hazard:
        return None

    allowed = {
        "earthquake",
        "flood",
        "cyclone",
        "general",
    }

    if hazard not in allowed:
        raise ValueError(
            f"Invalid hazard '{hazard}'. "
            f"Expected one of: {sorted(allowed)}"
        )

    return hazard


# ============================================================
# Retrieve guidance
# ============================================================

def retrieve_guidance(
    query: str,
    *,
    hazard: Optional[str] = None,
    k: int = 4,
    fetch_k: int = 15,
    lambda_mult: float = 0.7,
) -> list[Document]:
    """
    Retrieve relevant safety guidance using MMR.

    MMR helps avoid returning multiple highly similar chunks
    from the same page/document.
    """

    if not query or not query.strip():
        raise ValueError(
            "query must not be empty"
        )

    if k < 1:
        raise ValueError(
            "k must be at least 1"
        )

    if fetch_k < k:
        raise ValueError(
            "fetch_k must be greater than or equal to k"
        )

    if not 0.0 <= lambda_mult <= 1.0:
        raise ValueError(
            "lambda_mult must be between 0 and 1"
        )

    hazard = _normalize_hazard(hazard)

    vector_store = get_vector_store()

    metadata_filter = None

    if hazard:
        metadata_filter = {
            "hazard": {
                "$eq": hazard
            }
        }

    return vector_store.max_marginal_relevance_search(
        query=query,
        k=k,
        fetch_k=fetch_k,
        lambda_mult=lambda_mult,
        filter=metadata_filter,
    )


# ============================================================
# Retrieve with scores
# ============================================================

def retrieve_guidance_with_scores(
    query: str,
    *,
    hazard: Optional[str] = None,
    k: int = 4,
) -> list[tuple[Document, float]]:
    """
    Retrieve documents with their Pinecone similarity scores.

    Note:
    This uses similarity search rather than MMR because LangChain's
    MMR result doesn't directly expose standard similarity scores.
    """

    if not query or not query.strip():
        raise ValueError(
            "query must not be empty"
        )

    if k < 1:
        raise ValueError(
            "k must be at least 1"
        )

    hazard = _normalize_hazard(hazard)

    vector_store = get_vector_store()

    metadata_filter = None

    if hazard:
        metadata_filter = {
            "hazard": {
                "$eq": hazard
            }
        }

    return vector_store.similarity_search_with_score(
        query=query,
        k=k,
        filter=metadata_filter,
    )


# ============================================================
# Build LLM context
# ============================================================

def build_context(
    documents: list[Document],
) -> str:
    """Format retrieved chunks for the LLM."""

    if not documents:
        return (
            "No relevant safety guidance was found."
        )

    sections = []

    for number, document in enumerate(
        documents,
        start=1,
    ):

        metadata = document.metadata

        source = metadata.get(
            "source",
            "unknown source",
        )

        page = metadata.get(
            "page",
            "unknown page",
        )

        hazard = metadata.get(
            "hazard",
            "general",
        )

        chunk = metadata.get(
            "chunk",
            "unknown",
        )

        sections.append(
            f"[Source {number}: "
            f"{source}, "
            f"page {page}, "
            f"hazard {hazard}, "
            f"chunk {chunk}]\n"
            f"{document.page_content.strip()}"
        )

    return "\n\n".join(sections)


# ============================================================
# Testing
# ============================================================

if __name__ == "__main__":

    query = (
        "What should an elderly person do during an earthquake?"
    )

    results = retrieve_guidance(
        query,
        hazard="earthquake",
        k=3,
        fetch_k=15,
        lambda_mult=0.7,
    )

    print("\n" + "=" * 70)
    print("RETRIEVAL RESULTS")
    print("=" * 70)

    for index, document in enumerate(
        results,
        start=1,
    ):

        print(
            f"\n[Source {index}: "
            f"{document.metadata.get('source')}, "
            f"page {document.metadata.get('page')}, "
            f"hazard {document.metadata.get('hazard')}]"
        )

        print(
            document.page_content
        )

    print("\n" + "=" * 70)
