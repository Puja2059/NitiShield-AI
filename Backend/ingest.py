import re
from pathlib import Path

import chromadb
import pymupdf

from sentence_transformers import SentenceTransformer

from config import (
    LEGAL_DOCUMENTS_DIR,
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

from database import (
    initialize_database,
    add_document,
    add_chunk,
)


# Load embedding model once
print("Loading embedding model...")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Embedding model loaded.")


# Create persistent ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    metadata={
        "description": "Nepal legal documents for NitiShield chatbot"
    },
)


def clean_text(text):
    """
    Clean unnecessary spaces and line breaks.
    """

    text = text.replace("\x00", " ")

    # Replace repeated whitespace with one space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def detect_section(text):
    """
    Try to identify a section heading.

    This is a simple detector.
    It may need improvement depending on the PDF format.
    """

    patterns = [
        r"(Section\s+\d+)",
        r"(SECTION\s+\d+)",
        r"(दफा\s+\d+)",
        r"(परिच्छेद\s+\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1)

    return "Not detected"


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split long text into overlapping chunks.

    Example:
    Chunk 1: characters 0-1000
    Chunk 2: characters 850-1850
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size - 1")

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def extract_pdf_pages(pdf_path):
    """
    Extract text from each page of a PDF.

    Returns:
        [
            {
                "page_number": 1,
                "text": "..."
            }
        ]
    """

    pages = []

    with pymupdf.open(pdf_path) as pdf:
        for page_index in range(pdf.page_count):
            page = pdf.load_page(page_index)
            raw_text = page.get_text()
            cleaned = clean_text(raw_text)

            if cleaned:
                pages.append(
                    {
                        "page_number": page_index + 1,
                        "text": cleaned,
                    }
                )

    return pages


def process_pdf(pdf_path):
    """
    Process one legal PDF.
    """

    print(f"\nProcessing: {pdf_path.name}")

    # You can customize this later using a metadata file.
    law_name = pdf_path.stem.replace("_", " ").title()

    source = "Official Nepal legal source"

    document_id = add_document(
        file_name=pdf_path.name,
        law_name=law_name,
        source=source,
        document_version="Not specified",
    )

    pages = extract_pdf_pages(pdf_path)

    total_chunks = 0

    for page in pages:
        page_number = page["page_number"]
        page_text = page["text"]

        page_chunks = split_text(page_text)

        for chunk_index, chunk_text in enumerate(page_chunks):
            chunk_id = (
                f"{pdf_path.stem}"
                f"_page_{page_number}"
                f"_chunk_{chunk_index}"
            )

            section_name = detect_section(chunk_text)

            # Create vector embedding
            embedding = embedding_model.encode(
                chunk_text
            ).tolist()

            metadata = {
                "document_id": str(document_id),
                "file_name": pdf_path.name,
                "law_name": law_name,
                "section_name": section_name,
                "page_number": page_number,
                "source": source,
            }

            # Store vector and text in ChromaDB
            collection.upsert(
                ids=[chunk_id],
                documents=[chunk_text],
                embeddings=[embedding],
                metadatas=[metadata],
            )

            # Store searchable metadata and text in SQLite
            add_chunk(
                document_id=document_id,
                chunk_id=chunk_id,
                law_name=law_name,
                section_name=section_name,
                page_number=page_number,
                chunk_text=chunk_text,
            )

            total_chunks += 1

    print(
        f"Completed: {pdf_path.name} "
        f"({total_chunks} chunks created/updated)"
    )


def main():
    """
    Process every PDF in legal_documents/.
    """

    initialize_database()

    pdf_files = sorted(Path(LEGAL_DOCUMENTS_DIR).glob("*.pdf"))

    if not pdf_files:
        print(
            "No PDF files found.\n"
            f"Please place PDFs inside: {LEGAL_DOCUMENTS_DIR}"
        )
        return

    print(f"Found {len(pdf_files)} PDF file(s).")

    for pdf_path in pdf_files:
        process_pdf(pdf_path)

    print("\nAll legal documents have been processed.")
    print("ChromaDB and SQLite database are ready.")


if __name__ == "__main__":
    main()