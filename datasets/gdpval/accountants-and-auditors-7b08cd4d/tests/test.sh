#!/bin/bash
# GDPVal verifier — delegates to judge.py.
#
# judge.py:
#   1. Checks deliverable files exist (/app/output/... or /app/...)
#   2. Extracts text from .xlsx/.pdf/.docx (paper-faithful content grading)
#   3. Calls a judge LLM (Gemini → Anthropic → Ollama Cloud)
#   4. Writes /logs/verifier/reward.json
#
# See: https://artificialanalysis.ai/evaluations/gdpval-aa

set -e
mkdir -p /logs/verifier

python3 /tests/judge.py

echo "--- Verification complete ---"
cat /logs/verifier/reward.json
