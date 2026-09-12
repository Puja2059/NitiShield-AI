from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR.parent



# Folder for SQLite database files
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Folder containing original legal PDF documents
LEGAL_DOCUMENTS_DIR = BASE_DIR / "legal_documents"
LEGAL_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


# Folder for ChromaDB persistent vector storage
CHROMA_DB_PATH = BASE_DIR / "chroma_db"
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "legal_metadata.db"


APP_NAME = "NitiShield AI"

APP_ENV = os.getenv("APP_ENV", "development")


CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "legal_documents"
)

TOP_K_RESULTS = int(
    os.getenv("TOP_K_RESULTS", "5")
)


API_HOST = os.getenv("API_HOST", "127.0.0.1")

API_PORT = int(
    os.getenv("API_PORT", "8000")
)

DEBUG = os.getenv("DEBUG", "false").lower() == "true"