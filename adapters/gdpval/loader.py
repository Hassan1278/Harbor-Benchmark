"""
GDPVal dataset loader.

Fetches the 220-task gold subset from HuggingFace (openai/gdpval)
and converts each row into a BenchmarkTask with GDPVal-specific
metadata (sector, occupation, rubric).
"""

from datasets import load_dataset

from adapters.core.models import BenchmarkTask, ReferenceFile
from adapters.core.loader import DatasetLoader


class GDPValLoader(DatasetLoader):
    """Loads GDPVal from HuggingFace: openai/gdpval."""

    DATASET_ID = "openai/gdpval"

    def load(self) -> list[BenchmarkTask]:
        ds = load_dataset(self.DATASET_ID, split="train")
        return [self._to_task(row) for row in ds]

    @staticmethod
    def _to_task(row: dict) -> BenchmarkTask:
        ref_names = row.get("reference_files") or []
        ref_urls = row.get("reference_file_urls") or []
        refs = [
            ReferenceFile(name=n, url=u)
            for n, u in zip(ref_names, ref_urls)
            if n
        ]

        sector = row.get("sector", "unknown")
        occupation = row.get("occupation", "unknown")

        return BenchmarkTask(
            task_id=row["task_id"],
            prompt=row["prompt"],
            category=occupation,
            tags=["gdpval", sector],
            reference_files=refs,
            deliverable_files=row.get("deliverable_files") or [],
            metadata={
                "sector": sector,
                "occupation": occupation,
                "rubric_json": row.get("rubric_json", ""),
                "rubric_pretty": row.get("rubric_pretty", ""),
            },
        )
