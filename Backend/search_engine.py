import chromadb
import numpy as np

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    VECTOR_TOP_K,
    BM25_TOP_K,
    FINAL_TOP_K,
)

from database import get_all_chunks


class LegalSearchEngine:
    """
    Hybrid legal search engine.

    Uses:
    1. ChromaDB semantic vector search
    2. BM25 keyword search
    """

    def __init__(self):
        print("Loading legal search engine...")

        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME
        )

        self.chunks = get_all_chunks()

        self.bm25 = None
        self.tokenized_documents = []

        self.build_bm25_index()

        print(
            f"Search engine ready with "
            f"{len(self.chunks)} legal chunks."
        )

    def build_bm25_index(self):
        """
        Build BM25 index from SQLite legal chunks.
        """

        if not self.chunks:
            self.bm25 = None
            return

        self.tokenized_documents = [
            row["chunk_text"].lower().split()
            for row in self.chunks
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_documents
        )

    def vector_search(self, question):
        """
        Search ChromaDB using semantic similarity.
        """

        if not isinstance(question, str) or not question.strip():
            return []

        document_count = self.collection.count()

        if document_count == 0:
            return []

        question_embedding = self.embedding_model.encode(
            question
        ).tolist()

        results = self.collection.query(
            query_embeddings=[question_embedding],
            n_results=min(VECTOR_TOP_K, document_count),
        )

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        ids = (results.get("ids") or [[]])[0]

        vector_results = []

        for index, document in enumerate(documents):
            vector_results.append(
                {
                    "chunk_id": ids[index],
                    "text": document,
                    "metadata": metadatas[index],
                    "vector_distance": distances[index],
                    "retrieval_method": "vector",
                }
            )

        return vector_results

    def bm25_search(self, question):
        """
        Search legal chunks using keyword matching.
        """

        if self.bm25 is None or not isinstance(question, str):
            return []

        question_tokens = question.strip().lower().split()

        if not question_tokens:
            return []

        scores = self.bm25.get_scores(
            question_tokens
        )

        top_indexes = np.argsort(scores)[::-1][:BM25_TOP_K]

        bm25_results = []

        for index in top_indexes:
            score = float(scores[index])

            if score <= 0:
                continue

            row = self.chunks[index]

            bm25_results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "text": row["chunk_text"],
                    "metadata": {
                        "law_name": row["law_name"],
                        "section_name": row["section_name"],
                        "page_number": row["page_number"],
                    },
                    "bm25_score": score,
                    "retrieval_method": "bm25",
                }
            )

        return bm25_results

    def hybrid_search(self, question):
        """
        Combine vector and BM25 search results.

        A chunk found by both methods receives a higher rank.
        """

        vector_results = self.vector_search(question)
        bm25_results = self.bm25_search(question)

        combined = {}

        # Add vector results
        for result in vector_results:
            chunk_id = result["chunk_id"]

            combined[chunk_id] = {
                **result,
                "combined_score": 1.0,
            }

        # Add or strengthen BM25 results
        for result in bm25_results:
            chunk_id = result["chunk_id"]

            if chunk_id in combined:
                combined[chunk_id]["combined_score"] += 1.0
                combined[chunk_id][
                    "retrieval_method"
                ] = "vector + bm25"
            else:
                combined[chunk_id] = {
                    **result,
                    "combined_score": 0.5,
                }

        final_results = sorted(
            combined.values(),
            key=lambda item: item["combined_score"],
            reverse=True,
        )

        return final_results[:FINAL_TOP_K]