from pathlib import Path
import os


CHROMA_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = CHROMA_DIR.parent



# Folder for SQLite database files
DATA_DIR = CHROMA_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Folder containing original legal PDF documents
LEGAL_DOCUMENTS_DIR = CHROMA_DIR / "legal_documents"
LEGAL_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


# Folder for ChromaDB persistent vector storage
CHROMA_DB_PATH = CHROMA_DIR / "chroma_db"
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "legal_metadata.db"

# ChromaDB collection name
CHROMA_COLLECTION_NAME = "nepal_legal_documents"

# Embedding model
# This multilingual model is suitable for an initial English/Nepali prototype.
EMBEDDING_MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Chunk settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Number of results retrieved from each search method
VECTOR_TOP_K = 8
BM25_TOP_K = 8

# Final number of combined results
FINAL_TOP_K = 5