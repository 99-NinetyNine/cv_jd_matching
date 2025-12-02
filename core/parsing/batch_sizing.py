"""
Dynamic Batch Sizing Strategy

Adapts batch size based on:
1. System resources (CPU, Memory)
2. Queue depth (how many pending CVs)
3. Time of day (lower during peak hours)
4. Historical processing times
"""

import psutil
from datetime import datetime, time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class DynamicBatchSizer:
    """Calculate optimal batch size based on system dynamics."""

    # OpenAI Batch API limits
    MAX_BATCH_SIZE = 50000  # Max requests per batch
    MIN_BATCH_SIZE = 10     # Minimum viable batch

    def __init__(self):
        self.default_size = 500  # Conservative default

    def get_optimal_batch_size(
        self,
        pending_count: int,
        task_type: str = "cv_parsing"
    ) -> int:
        """
        Calculate optimal batch size dynamically.

        Args:
            pending_count: Number of items in queue
            task_type: Type of task (cv_parsing, embedding, etc.)

        Returns:
            Optimal batch size
        """
        factors = []

        # Factor 1: Queue depth (higher queue = larger batches)
        queue_factor = self._calculate_queue_factor(pending_count)
        factors.append(queue_factor)

        # Factor 2: System resources (higher resources = larger batches)
        resource_factor = self._calculate_resource_factor()
        factors.append(resource_factor)

        # Factor 3: Time of day (off-peak = larger batches)
        time_factor = self._calculate_time_factor()
        factors.append(time_factor)

        # Factor 4: Task-specific limits
        task_limit = self._get_task_specific_limit(task_type)

        # Calculate weighted average
        weights = [0.4, 0.3, 0.3]  # Queue is most important
        weighted_factor = sum(f * w for f, w in zip(factors, weights))

        # Calculate batch size
        batch_size = int(self.default_size * weighted_factor)

        # Apply constraints
        batch_size = max(self.MIN_BATCH_SIZE, batch_size)
        batch_size = min(task_limit, batch_size)
        batch_size = min(pending_count, batch_size)  # Don't exceed available items

        logger.info(
            f"Dynamic batch sizing: pending={pending_count}, "
            f"factors={factors}, size={batch_size}"
        )

        return batch_size

    def _calculate_queue_factor(self, pending_count: int) -> float:
        """
        Calculate factor based on queue depth.

        Returns:
            Multiplier from 0.5 to 2.0
        """
        if pending_count < 50:
            return 0.5  # Small queue = smaller batches
        elif pending_count < 500:
            return 1.0  # Medium queue = default
        elif pending_count < 5000:
            return 1.5  # Large queue = larger batches
        else:
            return 2.0  # Huge queue = max batches

    def _calculate_resource_factor(self) -> float:
        """
        Calculate factor based on system resources.

        Returns:
            Multiplier from 0.5 to 1.5
        """
        try:
            # CPU usage (lower is better)
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_factor = 1.5 if cpu_percent < 50 else 1.0 if cpu_percent < 80 else 0.5

            # Memory usage (lower is better)
            memory = psutil.virtual_memory()
            mem_factor = 1.5 if memory.percent < 60 else 1.0 if memory.percent < 80 else 0.5

            # Average
            return (cpu_factor + mem_factor) / 2
        except Exception as e:
            logger.warning(f"Failed to check system resources: {e}")
            return 1.0  # Default if check fails

    def _calculate_time_factor(self) -> float:
        """
        Calculate factor based on time of day.

        Returns:
            Multiplier from 0.7 to 1.5
        """
        current_hour = datetime.now().hour

        # Off-peak hours (midnight to 6am, 10pm to midnight)
        if 0 <= current_hour < 6 or 22 <= current_hour < 24:
            return 1.5  # Larger batches during off-peak

        # Peak hours (9am to 6pm)
        elif 9 <= current_hour < 18:
            return 0.7  # Smaller batches during peak

        # Normal hours
        else:
            return 1.0

    def _get_task_specific_limit(self, task_type: str) -> int:
        """Get maximum batch size for specific task type."""
        limits = {
            "cv_parsing": 1000,      # Text extraction + parsing
            "embedding": 10000,      # Fast, can handle more
            "matching": 1000,        # Complex queries
            "explanation": 5000,     # LLM calls
        }
        return limits.get(task_type, 500)


# Usage example
def get_batch_size_for_task(pending_count: int, task_type: str) -> int:
    """Helper function to get optimal batch size."""
    sizer = DynamicBatchSizer()
    return sizer.get_optimal_batch_size(pending_count, task_type)
