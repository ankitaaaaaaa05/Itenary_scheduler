"""
embedding_client.py 
"""
import os
import requests
import numpy as np
from dotenv import load_dotenv

load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT", "")
API_KEY = os.getenv("API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")



def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a single text string."""
    endpoint = API_ENDPOINT.rstrip("/") + "/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }
    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
    except Exception:
        # Return zero vector on failure (ChromaDB needs consistent dims)
        return [0.0] * 1536


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts."""
    return [get_embedding(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
