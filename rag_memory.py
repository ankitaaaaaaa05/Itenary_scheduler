"""
rag_memory.py — ChromaDB-based RAG memory for itineraries and preferences
"""
import chromadb
from chromadb.config import Settings
import json
import uuid
from embedding_client import get_embedding

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="travel_memory",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def store_itinerary_memory(itin_id: int, user_id: int, plan_text: str, metadata: dict = None):
    """Store itinerary in ChromaDB for RAG retrieval."""
    col = _get_collection()
    doc_id = f"itin_{itin_id}_{user_id}"
    meta = {
        "itin_id": str(itin_id),
        "user_id": str(user_id),
        "type": "itinerary",
    }
    if metadata:
        meta.update({k: str(v) for k, v in metadata.items()})
    try:
        embedding = get_embedding(plan_text[:2000])
        col.upsert(
            ids=[doc_id],
            documents=[plan_text[:3000]],
            embeddings=[embedding],
            metadatas=[meta],
        )
    except Exception as e:
        print(f"[RAG] Store error: {e}")


def retrieve_similar(query: str, user_id: int = None, n_results: int = 3) -> list[dict]:
    """Retrieve similar past itineraries."""
    col = _get_collection()
    try:
        embedding = get_embedding(query)
        where = {"user_id": str(user_id)} if user_id else None
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        results = col.query(**kwargs)
        docs = []
        for i, doc in enumerate(results.get("documents", [[]])[0]):
            docs.append({
                "document": doc,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 1.0,
            })
        return docs
    except Exception as e:
        print(f"[RAG] Retrieve error: {e}")
        return []