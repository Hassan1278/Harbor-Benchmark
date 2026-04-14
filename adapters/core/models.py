"""
Domain models for benchmark tasks.

These are abstract enough to represent tasks from ANY benchmark,
not just GDPVal. Benchmark-specific fields belong in subclasses.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenceFile:
    """A file the agent can read to complete the task."""
    name: str
    url: str = ""


@dataclass
class BenchmarkTask:
    """
    Base representation of a benchmark task.

    Subclass this to add benchmark-specific fields (e.g., rubric for GDPVal,
    patch for SWE-Bench, statute for LawBench).
    """
    task_id: str
    prompt: str
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    reference_files: list[ReferenceFile] = field(default_factory=list)
    deliverable_files: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Filesystem-safe short identifier. Override for custom naming."""
        cat_part = (
            self.category.lower()
            .replace(" ", "-")
            .replace(",", "")[:30]
        )
        return f"{cat_part}-{self.task_id[:8]}"
