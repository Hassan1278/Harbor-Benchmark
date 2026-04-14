"""
GDPVal → Harbor Adapter

Converts the GDPVal dataset into Harbor task format using the core framework.
The only GDPVal-specific logic here is:
  1. Loading from HuggingFace via GDPValLoader
  2. Injecting rubric.json into each task's tests/ directory
  3. Using Gemini 3.1 Pro as judge (via template/tests/test.sh)

References:
    Paper:     https://arxiv.org/abs/2510.04374
    Dataset:   https://huggingface.co/datasets/openai/gdpval
    GDPVal-AA: https://artificialanalysis.ai/evaluations/gdpval-aa

Usage:
    python -m adapters.gdpval.adapter --limit 5
    python -m adapters.gdpval.adapter --sector "Professional"
    python -m adapters.gdpval.adapter  # all 220 tasks
"""

from pathlib import Path

from adapters.core.models import BenchmarkTask
from adapters.core.builder import HarborTaskBuilder, FileDownloader
from adapters.core.verifier import VerifierConfig, VerifierType
from adapters.core.adapter import BenchmarkAdapter

from adapters.gdpval.loader import GDPValLoader


class GDPValAdapter(BenchmarkAdapter):
    """
    GDPVal-specific adapter.

    Overrides `extra_test_files` to inject the rubric into each task,
    which the Gemini judge reads at verification time.
    """

    def extra_test_files(self, task: BenchmarkTask) -> dict[str, str]:
        """Inject the rubric JSON for the LLM judge."""
        rubric = (
            task.metadata.get("rubric_json")
            or task.metadata.get("rubric_pretty")
            or "{}"
        )
        return {"rubric.json": rubric}


def build_adapter(output_dir: str = "datasets/gdpval") -> GDPValAdapter:
    """Factory function: assembles all GDPVal dependencies."""
    template_dir = Path(__file__).parent / "template"
    out = Path(output_dir)

    loader = GDPValLoader()
    downloader = FileDownloader()
    verifier = VerifierConfig(
        verifier_type=VerifierType.LLM_JUDGE,
        judge_model="gemini-3.1-pro-preview",
        judge_api_env_var="GEMINI_API_KEY",
        timeout_sec=300.0,
    )
    builder = HarborTaskBuilder(
        template_dir=template_dir,
        downloader=downloader,
        verifier_config=verifier,
        dockerfile_packages=["openpyxl", "pandas", "python-docx", "pdfplumber"],
    )

    return GDPValAdapter(
        name="gdpval",
        loader=loader,
        builder=builder,
        output_dir=out,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert GDPVal (220 tasks) to Harbor format"
    )
    parser.add_argument(
        "--output-dir", "-o", default="datasets/gdpval",
        help="Output directory (default: datasets/gdpval)",
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=None,
        help="Max tasks to convert (default: all 220)",
    )
    parser.add_argument(
        "--sector", "-s", default=None,
        help="Filter by sector name (partial match)",
    )
    args = parser.parse_args()

    adapter = build_adapter(args.output_dir)

    filter_fn = None
    if args.sector:
        sector_lower = args.sector.lower()
        filter_fn = lambda t: sector_lower in t.metadata.get("sector", "").lower()

    generated = adapter.run(limit=args.limit, filter_fn=filter_fn)

    print(f"\nDone! Generated {len(generated)} tasks in {args.output_dir}/")
    print(f"Run: harbor run -p {args.output_dir}/<task> -a claude-code -m <model>")


if __name__ == "__main__":
    main()
