from __future__ import annotations

import hashlib
import logging
import os
import re
import time

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_voyageai import VoyageAIEmbeddings
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")

MODEL_NAME = "voyage-4-large"
VECTOR_DIMENSION = 2048
INITIAL_BATCH_SIZE = 8
MIN_BATCH_SIZE = 1
MAX_RETRIES = 8
# Voyage currently reports a 3-RPM unauthenticated-project limit.
# Thirty seconds keeps us below that limit with some safety margin.
REQUEST_PAUSE_SECONDS = 30

LOGGER = logging.getLogger(__name__)


def clean_pdf_text(text: str) -> str:
    """Normalize common PDF extraction artifacts before chunking."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_hazard(filename: str) -> str:
    filename = filename.lower()

    if "earthquake" in filename or "usgs" in filename or "nidm" in filename:
        return "earthquake"

    if "flood" in filename:
        return "flood"

    if "cyclone" in filename or "hurricane" in filename:
        return "cyclone"

    return "general"


def load_pdf_documents() -> list[Document]:
    """Load PDF pages through LangChain's pypdf-backed loader."""
    documents = []

    for pdf_name in sorted(os.listdir(DOCS_DIR)):
        if not pdf_name.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(DOCS_DIR, pdf_name)
        hazard = detect_hazard(pdf_name)

        for page_number, document in enumerate(
            PyPDFLoader(pdf_path).load(),
            start=1,
        ):
            text = clean_pdf_text(document.page_content)
            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": pdf_name,
                        "page": page_number,
                        "hazard": hazard,
                        "modality": "text",
                        "document_type": "pdf",
                    },
                )
            )

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
    )
    return splitter.split_documents(documents)


def add_chunk_metadata(documents: list[Document]) -> list[Document]:
    for chunk_number, document in enumerate(documents):
        document.metadata["chunk"] = chunk_number
    return documents


def _status_code(error: BaseException) -> str:
    code = getattr(error, "status_code", None)
    if code is None:
        code = getattr(error, "code", None)
    return str(code).lower()


def _is_retryable_error(error: BaseException) -> bool:
    code = _status_code(error)
    if any(value in code for value in ("408", "429", "500", "502", "503", "504")):
        return True

    error_name = type(error).__name__.lower()
    error_text = str(error).lower()
    retry_words = (
        "ratelimit",
        "rate limit",
        "too many requests",
        "resource_exhausted",
        "resourceexhausted",
        "quota exceeded",
        "temporarily unavailable",
        "service unavailable",
        "deadline exceeded",
        "timeout",
        "connection reset",
    )
    return any(word in error_name or word in error_text for word in retry_words)


def _should_shrink_batch(error: BaseException) -> bool:
    """Identify errors where fewer texts/tokens per request may help."""
    code = _status_code(error)
    error_text = str(error).lower()
    batch_words = (
        "batch",
        "too many tokens",
        "token limit",
        "context length",
        "payload too large",
        "request too large",
    )
    return code in {"400", "413"} or any(
        word in error_text for word in batch_words
    )


class VoyageEmbeddings(Embeddings):
    """Voyage embeddings with conservative adaptive batching."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("VOYAGE_API_KEY is missing")

        self.embedding_model = VoyageAIEmbeddings(
            model=MODEL_NAME,
            api_key=api_key,
            output_dimension=VECTOR_DIMENSION,
            batch_size=INITIAL_BATCH_SIZE,
            truncation=True,
        )

    @staticmethod
    def _validate_dimensions(vectors: list[list[float]]) -> list[list[float]]:
        for index, vector in enumerate(vectors):
            if len(vector) != VECTOR_DIMENSION:
                raise RuntimeError(
                    f"Voyage returned {len(vector)} dimensions for item {index}; "
                    f"expected {VECTOR_DIMENSION}"
                )
        return vectors

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        wait=wait_exponential_jitter(initial=30, max=180),
        stop=stop_after_attempt(MAX_RETRIES),
        before_sleep=before_sleep_log(LOGGER, logging.WARNING),
        reraise=True,
    )
    def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        return self._validate_dimensions(
            self.embedding_model.embed_documents(texts)
        )

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        wait=wait_exponential_jitter(initial=30, max=180),
        stop=stop_after_attempt(MAX_RETRIES),
        before_sleep=before_sleep_log(LOGGER, logging.WARNING),
        reraise=True,
    )
    def _embed_query_with_retry(self, text: str) -> list[float]:
        vector = self.embedding_model.embed_query(text)
        return self._validate_dimensions([vector])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors = []
        current_batch_size = min(INITIAL_BATCH_SIZE, len(texts))
        position = 0

        while position < len(texts):
            batch = texts[position : position + current_batch_size]

            try:
                batch_vectors = self._embed_batch_with_retry(batch)
            except Exception as error:
                if (
                    _should_shrink_batch(error)
                    and current_batch_size > MIN_BATCH_SIZE
                ):
                    new_batch_size = max(MIN_BATCH_SIZE, current_batch_size // 2)
                    LOGGER.warning(
                        "Reducing Voyage batch size from %d to %d after: %s",
                        current_batch_size,
                        new_batch_size,
                        error,
                    )
                    current_batch_size = new_batch_size
                    continue
                raise

            vectors.extend(batch_vectors)
            position += len(batch)
            LOGGER.info(
                "Embedded %d/%d chunks using batch size %d",
                position,
                len(texts),
                current_batch_size,
            )
            time.sleep(REQUEST_PAUSE_SECONDS)

        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_query_with_retry(text)


def create_chunk_id(document: Document, chunk_number: int) -> str:
    raw_value = (
        f"{document.metadata['source']}|"
        f"{document.metadata['page']}|"
        f"{chunk_number}|"
        f"{document.page_content}"
    )
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def build_document_pipeline():
    """Compose loading, splitting, and metadata stages with pipe syntax."""
    return (
        RunnableLambda(lambda _: load_pdf_documents())
        | RunnableLambda(split_documents)
        | RunnableLambda(add_chunk_metadata)
    )


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    load_dotenv(override=True)

    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX")

    if not voyage_api_key:
        raise ValueError("VOYAGE_API_KEY is missing")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is missing")
    if not pinecone_index_name:
        raise ValueError("PINECONE_INDEX is missing")
    if not os.path.exists(DOCS_DIR):
        raise FileNotFoundError(f"Docs folder not found: {DOCS_DIR}")

    chunks = build_document_pipeline().invoke(None)
    if not chunks:
        raise ValueError("No text could be extracted from the PDFs")

    print(f"Loaded and split {len(chunks)} chunks")

    embeddings = VoyageEmbeddings(api_key=voyage_api_key)
    vector_store = PineconeVectorStore(
        index_name=pinecone_index_name,
        embedding=embeddings,
        pinecone_api_key=pinecone_api_key,
    )

    ids = [create_chunk_id(document, index) for index, document in enumerate(chunks)]
    vector_store.add_documents(documents=chunks, ids=ids)
    print(f"Uploaded {len(chunks)} chunks to Pinecone")


if __name__ == "__main__":
    main()
