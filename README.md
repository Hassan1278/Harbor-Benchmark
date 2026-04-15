# Harbor Benchmark

Benchmarking AI coding agents using the [Harbor](https://github.com/harbor-framework/harbor) framework, with support for:

- **[Terminal-Bench 2.0](https://www.tbench.ai/)** — 89 real-world terminal tasks (pass/fail shell verifier)
- **[GDPVal](https://huggingface.co/datasets/openai/gdpval)** — 220 expert-authored real-world knowledge-work tasks graded by an LLM judge ([paper](https://arxiv.org/abs/2510.04374))

## Prerequisites

- **Docker Desktop** (running)
- **Harbor**: `pip install harbor`
- **Claude Code CLI**: `npm install -g @anthropic-ai/claude-code`
- **Ollama** (optional, for local/cloud open-source models): [ollama.com](https://ollama.com)

## Quick Start — Terminal-Bench

```bash
harbor download "terminal-bench@2.0"

# Claude Pro (OAuth)
bash run.sh --claude -d terminal-bench@2.0 -n 1 -i fix-git

# Ollama Cloud (qwen3-coder 480B)
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama -d terminal-bench@2.0 -n 1 -i fix-git

# Random N tasks
bash run.sh --claude --random 5 -d terminal-bench@2.0 -n 2
```

## Quick Start — GDPVal

```bash
# Generate Harbor tasks from the HuggingFace dataset
python -m adapters.gdpval.adapter --limit 5

# Run one task with Claude Code + Ollama Cloud qwen
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama -p datasets/gdpval/ -n 1
```

`python -m adapters.gdpval.adapter --help` for filtering by sector and output dir.

Each generated task also pre-downloads the human expert's **gold solution** into `solution/` — used by the calibration helper below, ignored by Harbor at runtime.

### Judge calibration

Sanity-check that the judge scores the gold solutions near 1.0:

```bash
pip install openpyxl pdfplumber python-docx
python -m adapters.gdpval.calibrate --limit 10 -o calibration.json
```

If the mean calibration score is <0.9, the judge is too harsh or the rubric is ambiguous — agent comparisons are uncalibrated until that's resolved.

## Providers

| Flag | Agent | Model | Auth |
|---|---|---|---|
| `--claude` | claude-code | Claude Sonnet 4 | OAuth (Claude Pro) |
| `--ollama` | claude-code | Any Ollama model | Ollama account (cloud models free) |
| `--ollama-terminus` | terminus-2 | Any Ollama model | Ollama account |
| `--groq` | terminus-2 | Llama 3.3 70B | `GROQ_API_KEY` |
| `--gemini` | terminus-2 | Gemini 2.0 Flash | `GEMINI_API_KEY` |

## GDPVal judging

The paper grades deliverables with **Gemini 3.1 Pro Preview** as an LLM judge. Our [judge.py](adapters/gdpval/template/tests/judge.py) walks a provider chain and stops at the first one with credentials:

1. **Gemini** (`GEMINI_API_KEY`) — paper default. PDFs sent as native multimodal parts; xlsx/docx extracted to text.
2. **Anthropic** (`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`) — Claude Sonnet 4.5 default. PDFs as document blocks.
3. **Ollama Cloud** (`http://host.docker.internal:11434`) — free fallback. All files extracted to text. Default judge model: `gpt-oss:120b-cloud`.
4. **No judge reachable** → flat reward `0.5`.

Override with `JUDGE_PROVIDER=gemini|anthropic|ollama` and `JUDGE_MODEL=<id>`.

> **Env forwarding note:** Harbor must propagate `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` into the verifier container. If it doesn't by default, declare them in your task's `[environment]` section or set globally.

## Configuration

Copy `.env.example` → `.env` and fill in the keys you have. All values are optional — the judge chain falls through cleanly.

## Repo layout

| Path | Purpose |
|---|---|
| `run.sh` | Main runner — provider switching, env load, Harbor invocation |
| `adapters/core/` | Generic benchmark-to-Harbor conversion framework (loader, builder, verifier, adapter) |
| `adapters/gdpval/` | GDPVal plugin: HuggingFace loader + Gemini judge template |
| `datasets/gdpval/` | Generated Harbor task directories (1 example committed; regenerate with `python -m adapters.gdpval.adapter`) |
| `get_token.py` | Extracts Claude OAuth token from credentials |
| `pick_tasks.py` | Random task picker for `--random N` mode |
| `tasks_2.0.txt` | Terminal-Bench 2.0 task names |
| `jobs/` | Benchmark results (git-ignored) |

## Results

Each run writes `jobs/<timestamp>/` with:
- `result.json` — aggregate metrics
- `<task>/agent/trajectory.json` — step-by-step agent trace
- `<task>/verifier/reward.json` — `{"reward": <float>}` (Harbor-compatible)
- `<task>/verifier/judge.json` — `{"reward", "reason", "judge"}` (human-readable judge output)

## Adding a new benchmark

Subclass `BenchmarkAdapter` and `DatasetLoader` — see `adapters/gdpval/` for the reference implementation. The core framework is dataset-agnostic.
