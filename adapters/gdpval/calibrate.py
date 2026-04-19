"""
Judge calibration — score GDPVal's gold solutions with our judge chain.

A well-calibrated rubric + judge should score the human expert's solution
near 1.0. If the mean calibration score is <0.9, either the judge is too
harsh or the rubric has ambiguous items — agent scores are uncalibrated
until that's resolved.

Usage:
    python -m adapters.gdpval.calibrate                     # all tasks
    python -m adapters.gdpval.calibrate --limit 5
    python -m adapters.gdpval.calibrate -o calibration.json # save results

Host deps (for text-only judges and non-PDF solutions):
    pip install openpyxl pdfplumber python-docx
LibreOffice on PATH is required for xlsx/docx -> PDF (Gemini/Anthropic).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_TEMPLATE_JUDGE = Path(__file__).parent / "template" / "tests" / "judge.py"


def _load_judge_module():
    spec = importlib.util.spec_from_file_location("gdpval_judge", _TEMPLATE_JUDGE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gdpval_judge"] = module
    spec.loader.exec_module(module)
    return module


def calibrate_task(task_dir: Path, judge_mod) -> dict:
    rubric_path = task_dir / "tests" / "rubric.json"
    deliverables_path = task_dir / "tests" / "deliverables.txt"
    solution_dir = task_dir / "tests" / "solution"

    if not rubric_path.exists() or not deliverables_path.exists():
        return {"task": task_dir.name, "score": None, "error": "missing rubric/deliverables"}

    deliverables = [
        d.strip() for d in deliverables_path.read_text().splitlines() if d.strip()
    ]

    attachments = []
    missing = []
    for name in deliverables:
        candidate = solution_dir / name
        if not candidate.is_file():
            candidate = solution_dir / Path(name).name  # fallback: flat layout
        if candidate.is_file():
            attachments.append(judge_mod.Attachment(name, candidate))
        else:
            missing.append(name)

    if missing:
        return {"task": task_dir.name, "score": None, "error": f"missing gold: {missing}"}

    rubric = rubric_path.read_text()
    judge = judge_mod.Judge()
    try:
        result = judge.score_rubric(rubric, attachments)
    except Exception as e:
        return {"task": task_dir.name, "score": None, "error": f"{judge.provider} errored: {e}"}
    return {
        "task": task_dir.name,
        "score": float(result.get("score", 0)),
        "judge": f"{judge.provider}/{judge.model}",
        "reason": str(result.get("reason", ""))[:300],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", "-d", default="datasets/gdpval")
    parser.add_argument("--limit", "-l", type=int, default=None)
    parser.add_argument("--out", "-o", default=None, help="Write JSON results to file")
    args = parser.parse_args()

    judge_mod = _load_judge_module()
    root = Path(args.dataset_dir)
    task_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if args.limit:
        task_dirs = task_dirs[: args.limit]

    results = []
    for task_dir in task_dirs:
        print(f"calibrating {task_dir.name} ...", flush=True)
        r = calibrate_task(task_dir, judge_mod)
        results.append(r)
        if r.get("score") is not None:
            print(f"  score={r['score']:.3f} judge={r['judge']}")
        else:
            print(f"  skipped: {r.get('error')}")

    scored = [r["score"] for r in results if isinstance(r.get("score"), float)]
    if scored:
        mean = sum(scored) / len(scored)
        print(f"\nMean calibration score: {mean:.3f} (n={len(scored)})")
        print("Gold solutions should score >=0.9. Lower -> judge too harsh or rubric ambiguous.")
    else:
        print("\nNo tasks scored. Check solution/ folders and judge credentials.")

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
