"""
Harbor Adapter Core Framework

A general-purpose framework for converting any external benchmark dataset
into Harbor task format. Benchmark-specific logic lives in plugins (e.g.,
adapters/gdpval/), not here.

Usage:
    1. Subclass BenchmarkTask with your benchmark's fields
    2. Implement DatasetLoader to fetch tasks from your source
    3. Optionally customize VerifierConfig for your judge strategy
    4. Wire them together in a BenchmarkAdapter

See adapters/gdpval/ for a complete example.
"""

from adapters.core.models import BenchmarkTask, ReferenceFile
from adapters.core.loader import DatasetLoader
from adapters.core.builder import HarborTaskBuilder, FileDownloader
from adapters.core.verifier import VerifierConfig
from adapters.core.adapter import BenchmarkAdapter

__all__ = [
    "BenchmarkTask",
    "ReferenceFile",
    "DatasetLoader",
    "HarborTaskBuilder",
    "FileDownloader",
    "VerifierConfig",
    "BenchmarkAdapter",
]
