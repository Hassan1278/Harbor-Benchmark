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

# Claude Pro (OAuth) — default Sonnet
bash run.sh --claude -d terminal-bench@2.0 -n 1 -i fix-git

# Claude Pro with Haiku (cheap/fast)
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 -d terminal-bench@2.0 -n 1

# Ollama Cloud (qwen3-coder 480B)
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama -d terminal-bench@2.0 -n 1 -i fix-git

# Random N tasks
bash run.sh --claude --random 5 -d terminal-bench@2.0 -n 2
```

## Quick Start — GDPVal

```bash
# Generate Harbor tasks from the HuggingFace dataset (includes gold solutions)
python -m adapters.gdpval.adapter --limit 5   # first 5 tasks
python -m adapters.gdpval.adapter              # all 220 tasks

# Run one task with Claude Code + Haiku
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 \
    -p datasets/gdpval -n 1 -i accountants-and-auditors-7b08cd4d

# Run 30 tasks in parallel (1 concurrent trial)
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 \
    -p datasets/gdpval -n 1 -l 30
```

`python -m adapters.gdpval.adapter --help` for filtering by sector and output dir.

Each generated task pre-downloads the human expert's **gold solution** into `solution/` — used by the calibration helper below, ignored by Harbor at runtime.

## Tutorial: Running GDPVal with Claude Pro

### 1. Log in with your Claude Pro account

```bash
claude auth logout     # clear any existing credentials
claude auth login      # browser opens → log in with your Pro account
python get_token.py    # verify: should print sk-ant-oat01-...
```

### 2. Configure the judge

Edit `.env` (copy from `.env.example` if it doesn't exist):

```env
# Force judge to use Anthropic (Haiku) via your Claude Pro OAuth token
JUDGE_PROVIDER=anthropic
JUDGE_MODEL=claude-haiku-4-5-20251001
```

The judge automatically gets your OAuth token — `run.sh` extracts it and forwards it to the verifier container.

### 3. Generate tasks (one-time)

```bash
python -m adapters.gdpval.adapter     # downloads all 220 from HuggingFace
```

### 4. Run

```bash
# Single task (smoke test)
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 \
    -p datasets/gdpval -n 1 -l 1

# Recommended: 30 tasks
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 \
    -p datasets/gdpval -n 1 -l 30

# Full benchmark (all 220)
bash run.sh --claude --model anthropic/claude-haiku-4-5-20251001 \
    -p datasets/gdpval -n 1
```

### 5. Check results

```bash
cat jobs/<latest-timestamp>/result.json                       # aggregate
cat jobs/<latest-timestamp>/<task-slug>/verifier/judge.json    # per-task
```

### 6. Calibrate the judge

Verify that your chosen judge model scores gold solutions near 1.0:

```bash
pip install openpyxl pdfplumber python-docx
python -m adapters.gdpval.calibrate --limit 5 -o calibration.json
```

If the mean is <0.9, your judge model is too harsh — consider upgrading to Sonnet for the judge while keeping Haiku for the agent:

```env
JUDGE_MODEL=claude-sonnet-4-5-20241022
```

## Any model, any harness

`run.sh` is a convenience wrapper. Under the hood it calls `harbor run` — which supports **any** combination of agent and model:

### Supported agents (harnesses)

`claude-code`, `terminus-2`, `aider`, `codex`, `cursor-cli`, `gemini-cli`, `goose`, `hermes`, `swe-agent`, `openhands`, `opencode`, `kimi-cli`, `qwen-coder`, and more. Custom agents via `--agent-import-path`.

### Supported models

Any model ID that the agent + [LiteLLM](https://docs.litellm.ai/docs/providers) supports:

| Provider | Model format | Auth |
|---|---|---|
| Anthropic | `anthropic/claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` or OAuth |
| Anthropic (Haiku) | `anthropic/claude-haiku-4-5-20251001` | same |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| Google | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Ollama | `ollama/<model>` or just `<model>` | Ollama running |

### Direct harbor commands (skip run.sh)

```bash
# Aider + GPT-4o on GDPVal
harbor run -a aider -m openai/gpt-4o -p datasets/gdpval -n 1 \
    --env-file .env -y

# SWE-Agent + Claude Sonnet on a single task
harbor run -a swe-agent -m anthropic/claude-sonnet-4-20250514 \
    -p datasets/gdpval -n 1 -i accountants-and-auditors-7b08cd4d \
    --env-file .env -y

# OpenHands + Gemini on Terminal-Bench
harbor run -a openhands -m gemini/gemini-2.0-flash \
    -d terminal-bench@2.0 -n 1 -i fix-git --env-file .env -y
```

### run.sh convenience flags

| Flag | Default model | Agent |
|---|---|---|
| `--claude` | `anthropic/claude-sonnet-4-20250514` | claude-code |
| `--claude --model <id>` | any Anthropic model | claude-code |
| `--ollama` | `qwen3:0.6b` (or `OLLAMA_MODEL`) | claude-code |
| `--ollama-terminus` | same | terminus-2 |
| `--groq` | `groq/llama-3.3-70b-versatile` | terminus-2 |
| `--gemini` | `gemini/gemini-2.0-flash` | terminus-2 |

All flags accept `--model <id>` to override the default.

## GDPVal judging

Two judging modes, controlled by `JUDGE_MODE` in `.env`:

### Rubric mode (default)

Scores the model's deliverable against a JSON rubric, outputting a float in `[0, 1]`. Faster, deterministic, uses the rubric from the HuggingFace dataset.

```env
JUDGE_MODE=rubric                         # default
JUDGE_MODEL=claude-haiku-4-5-20251001
```

### Pairwise mode (paper-faithful)

Reproduces the GDPVal paper's methodology — compares model output against the human expert's gold solution and emits `{0.0, 0.5, 1.0}` (lose / tie / win). Mean reward = win-or-tie rate. A/B positions are randomized per-task to blind the judge against position bias.

```env
JUDGE_MODE=pairwise
JUDGE_MODEL=gemini-3.1-pro-preview        # recommended: strong judge
```

ELO vs. human expert (anchored at 1500):
```
ELO_diff = -400 * log10(1 / win_or_tie_rate - 1)
```

### Provider selection

`JUDGE_PROVIDER` is auto-inferred from model name (`claude-*` → anthropic, `gemini-*` → gemini, else → ollama). If both are unset, the first provider with valid credentials wins.

| Provider | Multimodal? | Auth | Default model |
|---|---|---|---|
| `gemini` | Yes (PDF) | `GEMINI_API_KEY` | `gemini-3.1-pro-preview` (paper default) |
| `anthropic` | Yes (PDF) | `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` | `claude-sonnet-4-5` |
| `ollama` | No (text only) | Ollama on `host.docker.internal:11434` | `gpt-oss:120b-cloud` |

Multimodal providers receive xlsx/docx converted to PDF (via LibreOffice). Text-only providers receive extracted text.

### Judge choice matters

Haiku tends to call close comparisons "tie" (~70% tie rate observed), which inflates win-or-tie rates. For paper-accurate ELO numbers, use `gemini-3.1-pro-preview` or `claude-sonnet-4-5`.

## Configuration

Copy `.env.example` → `.env` and fill in what you have.

## Repo layout

| Path | Purpose |
|---|---|
| `run.sh` | Main runner — provider switching, `--model` override, env forwarding |
| `adapters/core/` | Generic benchmark-to-Harbor framework (loader, builder, verifier, adapter) |
| `adapters/gdpval/` | GDPVal plugin: HuggingFace loader, LLM judge template, calibration |
| `adapters/gdpval/calibrate.py` | Scores gold solutions with the judge to verify calibration |
| `datasets/gdpval/` | Generated Harbor tasks — **git-ignored**, regenerate with `python -m adapters.gdpval.adapter` |
| `get_token.py` | Extracts Claude OAuth token from `~/.claude/.credentials.json` |
| `pick_tasks.py` | Random task picker for `--random N` mode |
| `tasks_2.0.txt` | Terminal-Bench 2.0 task names |
| `jobs/` | Benchmark results (git-ignored) |

## Results

Each run writes `jobs/<timestamp>/` with:
- `result.json` — aggregate metrics (mean reward, error count)
- `<task>/agent/trajectory.json` — step-by-step agent trace
- `<task>/verifier/reward.json` — `{"reward": <float>}` (Harbor-compatible)
- `<task>/verifier/judge.json` — full details including `reward`, `reason`, `judge`, `mode`, and for pairwise runs: `raw_winner` ("A"/"B"/"tie") + `model_was` ("A"/"B") for blinding audit

## Adding a new benchmark

Subclass `BenchmarkAdapter` and `DatasetLoader` — see `adapters/gdpval/` for the reference implementation. The core framework is dataset-agnostic:

1. `adapters/mybench/loader.py` — implement `DatasetLoader.load() -> list[BenchmarkTask]`
2. `adapters/mybench/adapter.py` — optionally override `extra_test_files()` to inject benchmark-specific files
3. `adapters/mybench/template/tests/test.sh` — verification script
4. Run: `python -m adapters.mybench.adapter && bash run.sh --claude -p datasets/mybench -n 1`
