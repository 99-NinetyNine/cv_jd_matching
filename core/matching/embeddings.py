from typing import List, Protocol
from abc import ABC, abstractmethod
import os
import numpy as np
import requests
import hashlib
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.cache.redis_cache import redis_client
import logging

logger = logging.getLogger(__name__)

class Embedder(Protocol):
    def embed_query(self, text: str) -> List[float]:
        ...

    def embed_with_id(self, text: str, entity_id: str, entity_type: str) -> List[float]:
        ...


class BaseEmbedder(ABC):
    """Base class with shared caching logic for all embedders."""
    
    def __init__(self, model: str):
        self.model = model
    
    def _get_cache_key(self, text: str = None, entity_id: str = None, entity_type: str = None) -> str:
        """Generate cache key for embedding."""
        provider = self.__class__.__name__.replace("Embedder", "").lower()
        
        if entity_id and entity_type:
            # ID-based caching for entities
            return f"emb_{provider}_{self.model}_{entity_type}:{entity_id}"
        else:
            # Content-based caching for ad-hoc queries
            hash_key = hashlib.md5(text.encode()).hexdigest()
            return f"emb_{provider}_{self.model}:{hash_key}"
    
    def _get_from_cache(self, key: str) -> List[float] | None:
        """Retrieve embedding from cache."""
        cached = redis_client.get(key)
        if cached:
            return np.frombuffer(cached, dtype=np.float64).tolist()
        return None
    
    def _save_to_cache(self, key: str, embedding: List[float], ttl: int):
        """Save embedding to cache."""
        redis_client.set(key, np.array(embedding).tobytes(), ttl=ttl)
    
    @abstractmethod
    def _compute_embedding(self, text: str) -> List[float]:
        """Compute embedding using provider-specific API. Must be implemented by subclasses."""
        pass
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding with content-based caching."""
        key = self._get_cache_key(text=text)
        cached = self._get_from_cache(key)
        if cached:
            return cached
        
        embedding = self._compute_embedding(text)
        self._save_to_cache(key, embedding, ttl=86400)  # 1 day TTL
        return embedding
    
    def embed_with_id(self, text: str, entity_id: str, entity_type: str) -> List[float]:
        """Generate embedding with ID-based caching for better cache efficiency.
        
        Args:
            text: Text to embed
            entity_id: Unique identifier (e.g., cv_id, job_id)
            entity_type: Type of entity ('cv' or 'job')
        
        Returns:
            Embedding vector
        """
        # TODO: Check database first if embeddings were computed in background batch processing
        key = self._get_cache_key(entity_id=entity_id, entity_type=entity_type)
        cached = self._get_from_cache(key)
        if cached:
            logger.info(f"Cache hit for {entity_type} {entity_id}")
            return cached
        
        logger.info(f"Computing embedding for {entity_type} {entity_id}")
        embedding = self._compute_embedding(text)
        self._save_to_cache(key, embedding, ttl=604800)  # 7 days TTL
        return embedding


class OllamaEmbedder(BaseEmbedder):
    """Embedder using local Ollama instance. Zero-cost, privacy-preserving."""
    
    def __init__(self, model: str = "nomic-embed-text", base_url: str = None):
        super().__init__(model)
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    def _compute_embedding(self, text: str) -> List[float]:
        """Compute embedding using Ollama API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise


class GoogleEmbedder(BaseEmbedder):
    """Embedder using Google Generative AI."""
    
    def __init__(self, model: str = "models/embedding-001"):
        super().__init__(model)
        self.client = GoogleGenerativeAIEmbeddings(model=model)
    
    def _compute_embedding(self, text: str) -> List[float]:
        """Compute embedding using Google API."""
        try:
            return self.client.embed_query(text)
        except Exception as e:
            logger.error(f"Google embedding failed: {e}")
            raise


class EmbeddingFactory:
    """Factory for creating embedder instances."""
    
    @staticmethod
    def get_embedder(provider: str = "ollama", **kwargs) -> Embedder:
        if provider == "ollama":
            return OllamaEmbedder(**kwargs)
        elif provider == "google":
            return GoogleEmbedder(**kwargs)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
