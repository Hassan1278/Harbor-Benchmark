"""
Harbor task directory builder.

Generates the standard Harbor task layout from a BenchmarkTask:

    <task-slug>/
    ├── instruction.md
    ├── task.toml
    ├── environment/
    │   ├── Dockerfile
    │   └── references/     (if any)
    ├── tests/
    │   └── test.sh
    └── solution/

This module is benchmark-agnostic. Benchmark-specific files (rubrics,
patches, etc.) are injected via the `extra_test_files` parameter.
"""

import shutil
import textwrap
from pathlib import Path

import requests

from adapters.core.models import BenchmarkTask, ReferenceFile
from adapters.core.verifier import VerifierConfig


class FileDownloader:
    """Downloads files from URLs."""

    TIMEOUT_SEC = 60

    def download(self, url: str, dest: Path) -> bool:
        try:
            resp = requests.get(url, timeout=self.TIMEOUT_SEC)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.content)
            return True
        except Exception as e:
            print(f"  WARNING: Failed to download {url}: {e}")
            return False


DEFAULT_APT_PACKAGES = ("curl", "jq", "file")


class HarborTaskBuilder:
    """
    Builds a Harbor task directory from a BenchmarkTask.

    Parameters:
        template_dir:    Path to benchmark-specific template/ folder
        downloader:      For fetching reference files
        verifier_config: How to verify results
        pip_packages:    Python packages installed into the task image
        apt_packages:    Debian packages installed into the task image
                         (defaults: curl, jq, file)
    """

    def __init__(
        self,
        template_dir: Path,
        downloader: FileDownloader,
        verifier_config: VerifierConfig,
        pip_packages: list[str] | None = None,
        apt_packages: list[str] | None = None,
    ):
        self._template_dir = template_dir
        self._downloader = downloader
        self._verifier = verifier_config
        self._pip_packages = pip_packages or []
        self._apt_packages = list(apt_packages) if apt_packages else list(DEFAULT_APT_PACKAGES)

    def build(
        self,
        task: BenchmarkTask,
        output_dir: Path,
        extra_test_files: dict[str, str] | None = None,
    ) -> Path:
        """
        Create the full task directory.

        Args:
            task:             The benchmark task to convert
            output_dir:       Parent directory for all tasks
            extra_test_files: Additional files to write into tests/
                              (e.g., {"rubric.json": <content>})

        Returns:
            Path to the created task directory.
        """
        task_dir = output_dir / task.slug
        task_dir.mkdir(parents=True, exist_ok=True)

        self._write_instruction(task, task_dir)
        self._write_task_toml(task, task_dir)
        self._write_environment(task, task_dir)
        self._write_tests(task, task_dir, extra_test_files or {})
        self._write_solution(task, task_dir)

        return task_dir

    def _write_solution(self, task: BenchmarkTask, task_dir: Path):
        sol_dir = task_dir / "solution"
        sol_dir.mkdir(parents=True, exist_ok=True)
        for sf in task.solution_files:
            if sf.url:
                self._downloader.download(sf.url, sol_dir / sf.name)

    def _write_instruction(self, task: BenchmarkTask, task_dir: Path):
        sections = [task.prompt]

        if task.reference_files:
            lines = [
                "", "## Reference Files", "",
                "The following files are available in `/app/references/`:",
            ]
            lines += [f"- `{rf.name}`" for rf in task.reference_files]
            sections.append("\n".join(lines))

        if task.deliverable_files:
            lines = [
                "", "## Deliverables", "",
                "Produce the following files in `/app/output/`:",
            ]
            lines += [f"- `{f}`" for f in task.deliverable_files]
            sections.append("\n".join(lines))

        (task_dir / "instruction.md").write_text(
            "\n".join(sections), encoding="utf-8"
        )

    def _write_task_toml(self, task: BenchmarkTask, task_dir: Path):
        tags_str = ", ".join(f'"{t}"' for t in task.tags)
        content = textwrap.dedent(f"""\
            version = "1.0"

            [metadata]
            author_name = "Harbor Adapter"
            author_email = ""
            category = "{task.category}"
            tags = [{tags_str}]

            [verifier]
            timeout_sec = {self._verifier.timeout_sec}

            [agent]
            timeout_sec = 1800.0

            [environment]
            cpus = 2
            memory_mb = 4096
        """)

        extras = {
            k: v for k, v in (task.metadata or {}).items()
            if isinstance(v, str) and "\n" not in v and len(v) <= 200
        }
        if extras:
            content += "\n[metadata.extra]\n"
            for k, v in extras.items():
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                content += f'{k} = "{escaped}"\n'

        (task_dir / "task.toml").write_text(content, encoding="utf-8")

    def _write_environment(self, task: BenchmarkTask, task_dir: Path):
        env_dir = task_dir / "environment"
        env_dir.mkdir(parents=True, exist_ok=True)

        ref_dir = env_dir / "references"
        for rf in task.reference_files:
            if rf.url:
                self._downloader.download(rf.url, ref_dir / rf.name)

        has_refs = bool(task.reference_files)
        (env_dir / "Dockerfile").write_text(
            self._render_dockerfile(has_refs), encoding="utf-8"
        )

    def _write_tests(
        self,
        task: BenchmarkTask,
        task_dir: Path,
        extra_files: dict[str, str],
    ):
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        template_tests = self._template_dir / "tests"
        if template_tests.is_dir():
            for src in template_tests.iterdir():
                if src.is_file():
                    shutil.copy(src, tests_dir / src.name)

        # Write deliverables list (used by most verifiers)
        (tests_dir / "deliverables.txt").write_text(
            "\n".join(task.deliverable_files), encoding="utf-8"
        )

        # Write any extra files the benchmark needs (rubrics, patches, etc.)
        for filename, content in extra_files.items():
            (tests_dir / filename).write_text(content, encoding="utf-8")

    def _render_dockerfile(self, has_references: bool) -> str:
        apt = " ".join(self._apt_packages)
        lines = [
            "FROM python:3.11-slim",
            "WORKDIR /app",
            f"RUN apt-get update && apt-get install -y --no-install-recommends {apt} \\",
            "    && rm -rf /var/lib/apt/lists/*",
        ]
        if self._pip_packages:
            pip = " ".join(self._pip_packages)
            lines.append(f"RUN pip install --no-cache-dir {pip}")
        lines.append("RUN mkdir -p /app/references /app/output")
        if has_references:
            lines.append("COPY references/ /app/references/")
        return "\n".join(lines) + "\n"
