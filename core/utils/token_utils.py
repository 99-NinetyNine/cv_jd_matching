"""
Token counting and truncation utilities for LLM API calls.
Helps optimize batch processing by managing token limits.
"""

import tiktoken
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token counting and truncation for various models."""

    # Model token limits
    MODEL_LIMITS = {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "text-embedding-ada-002": 8191,
        "text-embedding-3-small": 8191,
        "text-embedding-3-large": 8191,
    }

    def __init__(self, model: str = "gpt-3.5-turbo", safety_margin: int = 100):
        """
        Initialize token manager.

        Args:
            model: Model name for token counting
            safety_margin: Safety margin to leave below max tokens
        """
        self.model = model
        self.safety_margin = safety_margin
        self.max_tokens = self.MODEL_LIMITS.get(model, 4096)

        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"Model {model} not found, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Token counting failed: {e}")
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4

    def truncate_text(self, text: str, max_tokens: Optional[int] = None) -> str:
        """
        Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens (defaults to model limit - safety margin)

        Returns:
            Truncated text
        """
        if max_tokens is None:
            max_tokens = self.max_tokens - self.safety_margin

        try:
            tokens = self.encoding.encode(text)

            if len(tokens) <= max_tokens:
                return text

            # Truncate tokens and decode
            truncated_tokens = tokens[:max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)

            logger.info(f"Truncated text from {len(tokens)} to {max_tokens} tokens")
            return truncated_text

        except Exception as e:
            logger.error(f"Truncation failed: {e}")
            # Fallback: character-based truncation
            char_limit = max_tokens * 4  # Rough estimate
            return text[:char_limit]

    def batch_items_by_tokens(
        self,
        items: List[str],
        max_batch_tokens: int = 100000,
        max_items_per_batch: int = 50000
    ) -> List[List[str]]:
        """
        Split items into batches based on token limits.

        Args:
            items: List of text items
            max_batch_tokens: Maximum tokens per batch
            max_items_per_batch: Maximum items per batch (API limit)

        Returns:
            List of batches
        """
        batches = []
        current_batch = []
        current_tokens = 0

        for item in items:
            item_tokens = self.count_tokens(item)

            # Check if adding this item would exceed limits
            if (len(current_batch) >= max_items_per_batch or
                current_tokens + item_tokens > max_batch_tokens):

                # Save current batch and start new one
                if current_batch:
                    batches.append(current_batch)
                current_batch = [item]
                current_tokens = item_tokens
            else:
                current_batch.append(item)
                current_tokens += item_tokens

        # Add final batch
        if current_batch:
            batches.append(current_batch)

        logger.info(f"Split {len(items)} items into {len(batches)} batches")
        return batches

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int = 0,
        model: Optional[str] = None
    ) -> float:
        """
        Estimate API cost for given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (defaults to self.model)

        Returns:
            Estimated cost in USD
        """
        model = model or self.model

        # Pricing as of 2024 (per 1K tokens)
        prices = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "text-embedding-ada-002": {"input": 0.0001, "output": 0},
            "text-embedding-3-small": {"input": 0.00002, "output": 0},
            "text-embedding-3-large": {"input": 0.00013, "output": 0},
        }

        if model not in prices:
            logger.warning(f"Pricing not available for {model}")
            return 0.0

        input_cost = (input_tokens / 1000) * prices[model]["input"]
        output_cost = (output_tokens / 1000) * prices[model]["output"]

        return input_cost + output_cost

    def prepare_batch_requests(
        self,
        texts: List[str],
        endpoint: str = "/v1/embeddings",
        model: Optional[str] = None,
        truncate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Prepare batch API requests with token management.

        Args:
            texts: List of texts to process
            endpoint: API endpoint
            model: Model to use
            truncate: Whether to truncate texts that exceed limits

        Returns:
            List of batch request objects
        """
        model = model or self.model
        requests = []

        for idx, text in enumerate(texts):
            # Truncate if needed
            if truncate:
                text = self.truncate_text(text)

            if endpoint == "/v1/embeddings":
                request = {
                    "custom_id": f"request-{idx}",
                    "method": "POST",
                    "url": endpoint,
                    "body": {
                        "model": model,
                        "input": text
                    }
                }
            elif endpoint == "/v1/chat/completions":
                request = {
                    "custom_id": f"request-{idx}",
                    "method": "POST",
                    "url": endpoint,
                    "body": {
                        "model": model,
                        "messages": [{"role": "user", "content": text}],
                        "max_tokens": 150
                    }
                }
            else:
                logger.warning(f"Unknown endpoint: {endpoint}")
                continue

            requests.append(request)

        return requests


# Convenience functions
def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Quick token counting function."""
    tm = TokenManager(model)
    return tm.count_tokens(text)


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
    """Quick truncation function."""
    tm = TokenManager(model)
    return tm.truncate_text(text, max_tokens)
