from pathlib import Path


# Main backend directory
BASE_DIR = Path(__file__).resolve().parent

# Folder containing original legal PDFs
LEGAL_DOCUMENTS_DIR = BASE_DIR / "legal_documents"

# ChromaDB persistent storage
CHROMA_DIR = BASE_DIR / "chroma_db"

# SQLite database folder
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite database file
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