from typing import List, Protocol
from abc import ABC, abstractmethod
import os
import numpy as np
import requests
import hashlib
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.cache.redis_cache import redis_client
import logging

from core.services.embedding_utils import prepare_ollama_embedding

logger = logging.getLogger(__name__)

class Embedder(Protocol):
    def embed_query(self, text: str) -> List[float]:
        ...

 


class BaseEmbedder(ABC):
    """Base class with shared caching logic for all embedders."""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding directly."""
        return self._compute_embedding(text)
    

class OllamaEmbedder(BaseEmbedder):
    """Embedder using local Ollama instance. Zero-cost, privacy-preserving."""
    
    def __init__(self, model: str = "nomic-embed-text", base_url: str = None, **kwargs):
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
            return prepare_ollama_embedding(response.json()["embedding"])
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise


class GoogleEmbedder(BaseEmbedder):
    """Embedder using Google Generative AI."""
    
    def __init__(self, model: str = "models/embedding-001", **kwargs):
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
