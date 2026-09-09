from pathlib import Path
import hashlib
import os
import re
import time
from typing import List

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore


# ============================================================
# Project paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[3]
DOCS_DIR = ROOT_DIR / "docs"


# ============================================================
# OpenRouter / NVIDIA Nemotron Embedding Model
# ============================================================

MODEL_NAME = "nvidia/llama-nemotron-embed-vl-1b-v2:free"

# NVIDIA documents 2048-dimensional output for this model.
VECTOR_DIMENSION = 2048

API_URL = "https://openrouter.ai/api/v1/embeddings"


# ============================================================
# API / batching configuration
# ============================================================

# Keep this conservative for the free endpoint.
BATCH_SIZE = 8

MAX_RETRIES = 8

INITIAL_BACKOFF = 5
MAX_BACKOFF = 60


# ============================================================
# Text cleaning
# ============================================================

def clean_pdf_text(text: str) -> str:
    """
    Clean common PDF extraction artefacts without aggressively
    changing the actual document meaning.
    """

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Fix words broken across a line:
    # "fright-\nened" -> "frightened"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Replace remaining single newlines inside sentences with spaces.
    # Keep paragraph breaks.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Collapse excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# OpenRouter LangChain Embeddings wrapper
# ============================================================

class NemotronVLEmbeddings(Embeddings):

    API_URL = API_URL

    def __init__(self, api_key: str):

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is missing"
            )

        self.api_key = api_key

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Sentinel RAG",
        }

    # --------------------------------------------------------
    # Low-level embedding request
    # --------------------------------------------------------

    def _embed_batch(
        self,
        texts: List[str],
        input_type: str,
    ) -> List[List[float]]:

        if not texts:
            return []

        payload = {
            "model": MODEL_NAME,
            "input": texts,
            "input_type": input_type,
            "dimensions": VECTOR_DIMENSION,
            "encoding_format": "float",
        }

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                response = requests.post(
                    self.API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                )

                # --------------------------------------------
                # Success
                # --------------------------------------------

                if response.status_code == 200:

                    body = response.json()

                    data = body.get("data")

                    if not data:
                        raise RuntimeError(
                            "OpenRouter returned no embedding data."
                        )

                    # Preserve original order
                    data.sort(
                        key=lambda item: item["index"]
                    )

                    vectors = [
                        item["embedding"]
                        for item in data
                    ]

                    # Defensive dimension check
                    for i, vector in enumerate(vectors):

                        if len(vector) != VECTOR_DIMENSION:
                            raise RuntimeError(
                                f"Unexpected embedding dimension "
                                f"for item {i}: "
                                f"expected {VECTOR_DIMENSION}, "
                                f"got {len(vector)}"
                            )

                    return vectors

                # --------------------------------------------
                # Rate limit
                # --------------------------------------------

                if response.status_code == 429:

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after:

                        try:
                            wait_time = float(retry_after)
                        except ValueError:
                            wait_time = INITIAL_BACKOFF

                    else:

                        wait_time = min(
                            INITIAL_BACKOFF * (2 ** (attempt - 1)),
                            MAX_BACKOFF,
                        )

                    print(
                        f"[429 Rate Limited] "
                        f"Attempt {attempt}/{MAX_RETRIES}. "
                        f"Waiting {wait_time:.1f}s..."
                    )

                    time.sleep(wait_time)
                    continue

                # --------------------------------------------
                # Server-side errors
                # --------------------------------------------

                if response.status_code >= 500:

                    wait_time = min(
                        INITIAL_BACKOFF * (2 ** (attempt - 1)),
                        MAX_BACKOFF,
                    )

                    print(
                        f"[{response.status_code} Server Error] "
                        f"Attempt {attempt}/{MAX_RETRIES}. "
                        f"Waiting {wait_time:.1f}s..."
                    )

                    time.sleep(wait_time)
                    continue

                # --------------------------------------------
                # Other errors
                # --------------------------------------------

                try:
                    error_body = response.json()
                except Exception:
                    error_body = response.text

                raise RuntimeError(
                    f"OpenRouter API error "
                    f"{response.status_code}: "
                    f"{error_body}"
                )

            except requests.RequestException as exc:

                wait_time = min(
                    INITIAL_BACKOFF * (2 ** (attempt - 1)),
                    MAX_BACKOFF,
                )

                print(
                    f"[Network Error] {exc}. "
                    f"Attempt {attempt}/{MAX_RETRIES}. "
                    f"Waiting {wait_time:.1f}s..."
                )

                time.sleep(wait_time)

        raise RuntimeError(
            f"Failed after {MAX_RETRIES} attempts."
        )

    # --------------------------------------------------------
    # Documents = search_document
    # --------------------------------------------------------

    def embed_documents(
        self,
        texts: List[str],
    ) -> List[List[float]]:

        if not texts:
            return []

        all_vectors = []

        total_batches = (
            len(texts) + BATCH_SIZE - 1
        ) // BATCH_SIZE

        for batch_number, start in enumerate(
            range(0, len(texts), BATCH_SIZE),
            start=1,
        ):

            batch = texts[
                start:start + BATCH_SIZE
            ]

            print(
                f"Embedding document batch "
                f"{batch_number}/{total_batches} "
                f"({len(batch)} chunks)"
            )

            vectors = self._embed_batch(
                batch,
                input_type="search_document",
            )

            all_vectors.extend(vectors)

        return all_vectors

    # --------------------------------------------------------
    # Query = search_query
    # --------------------------------------------------------

    def embed_query(
        self,
        text: str,
    ) -> List[float]:

        vectors = self._embed_batch(
            [text],
            input_type="search_query",
        )

        return vectors[0]


# ============================================================
# Hazard detection
# ============================================================

def detect_hazard(filename: str) -> str:

    filename = filename.lower()

    if (
        "earthquake" in filename
        or "usgs" in filename
        or "nidm" in filename
    ):
        return "earthquake"

    if "flood" in filename:
        return "flood"

    if (
        "cyclone" in filename
        or "hurricane" in filename
    ):
        return "cyclone"

    return "general"


# ============================================================
# Load PDFs
# ============================================================

def load_pdf_documents() -> List[Document]:

    documents = []

    for pdf_path in sorted(
        DOCS_DIR.glob("*.pdf")
    ):

        print(
            f"Reading PDF: {pdf_path.name}"
        )

        reader = PdfReader(
            str(pdf_path)
        )

        hazard = detect_hazard(
            pdf_path.name
        )

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            raw_text = page.extract_text()

            if not raw_text:
                continue

            text = clean_pdf_text(
                raw_text
            )

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,

                    metadata={
                        "source": pdf_path.name,
                        "page": page_number,
                        "hazard": hazard,
                        "modality": "text",
                        "document_type": "pdf",
                    },
                )
            )

    return documents


# ============================================================
# Stable chunk ID
# ============================================================

def create_chunk_id(
    document: Document,
    chunk_number: int,
) -> str:

    raw_value = (
        f"{document.metadata['source']}|"
        f"{document.metadata['page']}|"
        f"{chunk_number}|"
        f"{document.page_content}"
    )

    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Load environment
    # --------------------------------------------------------

    load_dotenv(
        override=True
    )

    openrouter_api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    pinecone_api_key = os.getenv(
        "PINECONE_API_KEY"
    )

    pinecone_index_name = os.getenv(
        "PINECONE_INDEX"
    )

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if not openrouter_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is missing"
        )

    if not pinecone_api_key:
        raise ValueError(
            "PINECONE_API_KEY is missing"
        )

    if not pinecone_index_name:
        raise ValueError(
            "PINECONE_INDEX is missing"
        )

    if not DOCS_DIR.exists():
        raise FileNotFoundError(
            f"Docs folder not found: {DOCS_DIR}"
        )

    # ========================================================
    # STEP 1 — Load PDF pages
    # ========================================================

    print("\n========================================")
    print("STEP 1: Loading PDFs")
    print("========================================")

    page_documents = (
        load_pdf_documents()
    )

    if not page_documents:

        raise ValueError(
            "No text could be extracted from the PDFs."
        )

    print(
        f"Loaded {len(page_documents)} PDF pages"
    )

    # ========================================================
    # STEP 2 — Split into semantic-ish chunks
    # ========================================================

    print("\n========================================")
    print("STEP 2: Creating chunks")
    print("========================================")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
            ", ",
            " ",
            "",
        ],
    )

    chunks = splitter.split_documents(
        page_documents
    )

    for index, document in enumerate(
        chunks
    ):
        document.metadata["chunk"] = index

    print(
        f"Created {len(chunks)} chunks"
    )

    # ========================================================
    # STEP 3 — Initialize embeddings
    # ========================================================

    print("\n========================================")
    print("STEP 3: Initializing Nemotron VL")
    print("========================================")

    embeddings = (
        NemotronVLEmbeddings(
            api_key=openrouter_api_key
        )
    )

    # ========================================================
    # STEP 4 — Connect to Pinecone
    # ========================================================

    print("\n========================================")
    print("STEP 4: Connecting to Pinecone")
    print("========================================")

    vector_store = PineconeVectorStore(
        index_name=pinecone_index_name,
        embedding=embeddings,
        pinecone_api_key=pinecone_api_key,
    )

    # ========================================================
    # STEP 5 — Generate stable IDs
    # ========================================================

    ids = [
        create_chunk_id(
            document,
            index,
        )
        for index, document
        in enumerate(chunks)
    ]

    # ========================================================
    # STEP 6 — Upload
    # ========================================================

    print("\n========================================")
    print(
        f"STEP 5: Uploading {len(chunks)} chunks"
    )
    print("========================================")

    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )

    print("\n========================================")
    print("SUCCESS")
    print("========================================")
    print(
        f"Uploaded {len(chunks)} chunks "
        f"to Pinecone."
    )


if __name__ == "__main__":
    main()