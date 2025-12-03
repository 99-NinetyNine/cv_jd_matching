"""
Embedding Utilities

Handles embeddings from different providers with varying dimensions.
Provides padding/truncation to ensure compatibility with pgvector schema.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# Target dimension for pgvector (matches models.py)
TARGET_DIMENSION = 1536

# Provider configurations
PROVIDER_DIMENSIONS = {
    "openai": {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    },
    "ollama": {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "llama2": 4096,  # If using Ollama with Llama2
    },
    "gemini": {
        "text-embedding-004": 768,
        "text-multilingual-embedding-002": 768,
    }
}


def normalize_embedding(
    embedding: List[float],
    provider: str = "openai",
    model: str = None,
    target_dim: int = TARGET_DIMENSION
) -> List[float]:
    """
    Normalize embedding to target dimension.

    Args:
        embedding: Input embedding vector
        provider: Provider name (openai, ollama, gemini)
        model: Model name (optional, for validation)
        target_dim: Target dimension (default: 1536 for OpenAI)

    Returns:
        Normalized embedding with target_dim dimensions

    Raises:
        ValueError: If embedding is invalid
    """
    if not embedding:
        print(" error padding...")
        raise ValueError("Embedding cannot be empty")
    print("padding...")
    current_dim = len(embedding)

    # Case 1: Perfect match
    if current_dim == target_dim:
        return embedding

    # Case 2: Need padding (Gemini 768 → OpenAI 1536)
    elif current_dim < target_dim:
        logger.info(f"Padding embedding from {current_dim} to {target_dim} dimensions")
        # Pad with zeros
        padded = embedding + [0.0] * (target_dim - current_dim)
        return padded

    # Case 3: Need truncation (OpenAI-large 3072 → 1536)
    else:
        logger.warning(f"Truncating embedding from {current_dim} to {target_dim} dimensions")
        # Truncate (preserves most important features in first dimensions)
        return embedding[:target_dim]


def get_expected_dimension(provider: str, model: str = None) -> int:
    """
    Get expected embedding dimension for a provider/model.

    Args:
        provider: Provider name
        model: Model name (optional)

    Returns:
        Expected dimension

    Example:
        >>> get_expected_dimension("openai", "text-embedding-3-small")
        1536
        >>> get_expected_dimension("gemini")
        768
    """
    if provider not in PROVIDER_DIMENSIONS:
        logger.warning(f"Unknown provider: {provider}. Assuming target dimension.")
        return TARGET_DIMENSION

    provider_models = PROVIDER_DIMENSIONS[provider]

    if model and model in provider_models:
        return provider_models[model]

    # Return first model's dimension as default
    return list(provider_models.values())[0]


def validate_embedding(
    embedding: List[float],
    provider: str = "openai",
    model: str = None
) -> bool:
    """
    Validate embedding dimensions match provider expectations.

    Args:
        embedding: Embedding vector
        provider: Provider name
        model: Model name

    Returns:
        True if valid, False otherwise
    """
    if not embedding:
        return False

    expected_dim = get_expected_dimension(provider, model)
    actual_dim = len(embedding)

    if actual_dim != expected_dim:
        logger.warning(
            f"Dimension mismatch: expected {expected_dim} for {provider}/{model}, "
            f"got {actual_dim}"
        )
        return False
    return True


def prepare_embedding_for_storage(
    embedding: List[float],
    provider: str = "openai",
    model: str = None,
    auto_normalize: bool = True
) -> List[float]:
    """
    Prepare embedding for storage in database.

    Validates and optionally normalizes embedding to target dimension.

    Args:
        embedding: Input embedding
        provider: Provider name
        model: Model name
        auto_normalize: Whether to auto-normalize dimensions

    Returns:
        Normalized embedding ready for storage

    Example:
        >>> # Gemini embedding (768 dims) → stored as 1536 dims
        >>> gemini_emb = [0.1] * 768
        >>> stored_emb = prepare_embedding_for_storage(gemini_emb, "gemini")
        >>> len(stored_emb)
        1536
    """
    if validate_embedding(embedding, provider, model) and auto_normalize:
        logger.info(f"Auto-normalizing {provider} embedding")
        print("normlizzing..")
        return normalize_embedding(embedding, provider, model)

    return embedding


# Convenience functions for common providers

def prepare_openai_embedding(embedding: List[float]) -> List[float]:
    """Prepare OpenAI embedding (usually no transformation needed)."""
    return prepare_embedding_for_storage(embedding, "openai")


def prepare_gemini_embedding(embedding: List[float]) -> List[float]:
    """Prepare Gemini embedding (768 → 1536 with padding)."""
    return prepare_embedding_for_storage(embedding, "gemini")


def prepare_ollama_embedding(embedding: List[float], model: str = "nomic-embed-text") -> List[float]:
    """Prepare Ollama embedding (768/1024 → 1536 with padding)."""
    return prepare_embedding_for_storage(embedding, "ollama", model)
