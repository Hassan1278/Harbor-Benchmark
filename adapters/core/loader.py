"""
Abstract dataset loader.

Each benchmark implements its own loader that knows how to fetch
and parse tasks from its specific source (HuggingFace, GitHub, API, etc.).
"""

from abc import ABC, abstractmethod

from adapters.core.models import BenchmarkTask


class DatasetLoader(ABC):
    """Interface for loading benchmark tasks from any source."""

    @abstractmethod
    def load(self) -> list[BenchmarkTask]:
        """Fetch and return all tasks from the data source."""
        ...
