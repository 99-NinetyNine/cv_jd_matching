from typing import List, Protocol
import os
import numpy as np
import requests
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.cache.redis_cache import redis_client
import logging

logger = logging.getLogger(__name__)

class Embedder(Protocol):
    def embed_query(self, text: str) -> List[float]:
        ...

class OllamaEmbedder:
    """
    Embedder using local Ollama instance.
    Zero-cost, privacy-preserving, but requires local resources.
    """
    def __init__(self, model: str = "nomic-embed-text", base_url: str = None):
        """
        Args:
            model: Name of the model to use (must be pulled in Ollama).
            base_url: URL of the Ollama API.
        """
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama API."""
        # Check Redis first
        import hashlib
        key = f"emb_ollama_{self.model}:{hashlib.md5(text.encode()).hexdigest()}"
        cached = redis_client.get(key)
        if cached:
            return np.frombuffer(cached, dtype=np.float64).tolist()

        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            
            # Cache it
            redis_client.set(key, np.array(embedding).tobytes(), ttl=86400)
            return embedding
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise e

class GoogleEmbedder:
    def __init__(self, model: str = "models/embedding-001"):
        self.model = model
        # Assumes GOOGLE_API_KEY is set in env
        self.client = GoogleGenerativeAIEmbeddings(model=model)

    def embed_query(self, text: str) -> List[float]:
        # Check Redis first
        import hashlib
        key = f"emb_google_{self.model}:{hashlib.md5(text.encode()).hexdigest()}"
        cached = redis_client.get(key)
        if cached:
            return np.frombuffer(cached, dtype=np.float64).tolist()
            
        try:
            embedding = self.client.embed_query(text)
            # Cache it
            redis_client.set(key, np.array(embedding).tobytes(), ttl=86400)
            return embedding
        except Exception as e:
            logger.error(f"Google embedding failed: {e}")
            raise e

class EmbeddingFactory:
    @staticmethod
    def get_embedder(provider: str = "ollama", **kwargs) -> Embedder:
        if provider == "ollama":
            return OllamaEmbedder(**kwargs)
        elif provider == "google":
            return GoogleEmbedder(**kwargs)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
