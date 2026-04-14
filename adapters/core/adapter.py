"""
Base adapter orchestrator.

Composes a DatasetLoader + HarborTaskBuilder to convert any benchmark
into Harbor format. Benchmark plugins subclass this to add custom logic
(e.g., writing rubric files for GDPVal).
"""

import textwrap
from pathlib import Path
from typing import Callable, Optional

from adapters.core.models import BenchmarkTask
from adapters.core.loader import DatasetLoader
from adapters.core.builder import HarborTaskBuilder


class BenchmarkAdapter:
    """
    Base adapter that orchestrates dataset conversion.

    Subclass and override `extra_test_files()` to inject
    benchmark-specific files into each task's tests/ directory.
    """

    def __init__(
        self,
        name: str,
        loader: DatasetLoader,
        builder: HarborTaskBuilder,
        output_dir: Path,
    ):
        self._name = name
        self._loader = loader
        self._builder = builder
        self._output_dir = output_dir

    def run(
        self,
        limit: Optional[int] = None,
        filter_fn: Optional[Callable[[BenchmarkTask], bool]] = None,
    ) -> list[str]:
        """
        Convert benchmark tasks to Harbor format.

        Args:
            limit:     Max number of tasks to convert
            filter_fn: Optional predicate to filter tasks

        Returns:
            List of generated task slugs.
        """
        print(f"Loading {self._name} dataset...")
        tasks = self._loader.load()
        print(f"Loaded {len(tasks)} tasks")

        if filter_fn:
            tasks = [t for t in tasks if filter_fn(t)]
            print(f"Filtered to {len(tasks)} tasks")

        if limit:
            tasks = tasks[:limit]
            print(f"Limited to {len(tasks)} tasks")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        generated = []

        for i, task in enumerate(tasks):
            extra_files = self.extra_test_files(task)
            self._builder.build(task, self._output_dir, extra_files)
            generated.append(task.slug)
            print(f"  [{i + 1}/{len(tasks)}] {task.slug}")

        self._write_metadata(generated)
        return generated

    def extra_test_files(self, task: BenchmarkTask) -> dict[str, str]:
        """
        Override in subclass to provide extra files for tests/.

        Returns:
            Dict of {filename: content} to write into the task's tests/ dir.
        """
        return {}

    def _write_metadata(self, task_names: list[str]):
        toml = textwrap.dedent(f"""\
            [dataset]
            name = "{self._name}"
            version = "1.0"
            tasks = {len(task_names)}
        """)
        (self._output_dir / "dataset.toml").write_text(toml, encoding="utf-8")
        (self._output_dir / "tasks.txt").write_text(
            "\n".join(sorted(task_names)), encoding="utf-8"
        )
