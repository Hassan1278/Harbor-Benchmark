# Harbor Benchmark

Benchmarking AI coding agents using the [Harbor](https://github.com/harbor-framework/harbor) framework with [Terminal-Bench 2.0](https://www.tbench.ai/) (89 real-world terminal tasks).

## Prerequisites

- **Docker Desktop** (running)
- **Harbor**: `pip install harbor`
- **Claude Code CLI**: `npm install -g @anthropic-ai/claude-code`
- **Ollama** (optional, for local/cloud open-source models): [ollama.com](https://ollama.com)
- **Terminal-Bench dataset**: `harbor download "terminal-bench@2.0"`

## Quick Start

```bash
# Run with Claude Pro subscription (OAuth)
bash run.sh --claude -d terminal-bench@2.0 -n 1 -i fix-git

# Run with Ollama (local or cloud models)
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama -d terminal-bench@2.0 -n 1 -i fix-git

# Run with Terminus-2 agent + Ollama
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama-terminus -d terminal-bench@2.0 -n 1 -i fix-git

# Run with Groq (free API)
bash run.sh --groq -d terminal-bench@2.0 -n 1 -i fix-git

# Pick N random tasks
bash run.sh --claude --random 5 -d terminal-bench@2.0 -n 2
```

## Providers

| Flag | Agent | Model | Auth |
|---|---|---|---|
| `--claude` | claude-code | Claude Sonnet 4 | OAuth (Claude Pro $20/mo) |
| `--ollama` | claude-code | Any Ollama model | Ollama account |
| `--ollama-terminus` | terminus-2 | Any Ollama model | Ollama account |
| `--groq` | terminus-2 | Llama 3.3 70B | API key in `.env` |
| `--gemini` | terminus-2 | Gemini 2.0 Flash | API key in `.env` |

## Ollama Cloud Setup

To use large cloud models (e.g., Qwen3-Coder 480B) through Ollama:

```bash
# 1. Install Ollama and sign in for cloud access
# 2. Create an alias for the cloud model
echo 'FROM qwen3-coder:480b-cloud' > Modelfile
ollama create qwen3-coder-cloud -f Modelfile

# 3. Run
OLLAMA_MODEL="qwen3-coder-cloud" bash run.sh --ollama -d terminal-bench@2.0 -n 1 -i fix-git
```

## Configuration

Create a `.env` file for API keys:

```
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

Set `OLLAMA_MODEL` to override the default Ollama model:

```bash
OLLAMA_MODEL="qwen3:0.6b" bash run.sh --ollama ...
```

## Files

| File | Purpose |
|---|---|
| `run.sh` | Main runner script (Bash) |
| `get_token.py` | Extracts Claude OAuth token from credentials |
| `pick_tasks.py` | Picks N random tasks from the 89-task pool |
| `tasks_2.0.txt` | List of all 89 Terminal-Bench 2.0 task names |
| `.env` | API keys (git-ignored) |
| `jobs/` | Benchmark results (git-ignored) |

## Results

Results are saved to `jobs/<timestamp>/`. Each task folder contains:
- `result.json` — pass/fail, timing, errors
- `agent/trajectory.json` — full agent trace (what the AI did step by step)

## Research Goal

Building an objective harness quality metric using e-values (testing by betting) to compare AI agent harnesses with statistical rigor.
