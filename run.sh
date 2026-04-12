#!/bin/bash
# Harbor run script — auto-loads credentials, supports random tasks and provider switching
#
# Usage:
#   bash run.sh [options] [harbor run flags]
#
# Options:
#   --random N       Pick N random tasks from Terminal-Bench 2.0
#   --claude         Use Claude Code + OAuth (default)
#   --ollama         Use Claude Code + Ollama Cloud (qwen3-coder:480b)
#   --groq           Use Terminus + Groq
#   --gemini         Use Terminus + Gemini
#
# Examples:
#   bash run.sh --random 8 -d terminal-bench@2.0 -n 2
#   bash run.sh --ollama --random 8 -d terminal-bench@2.0 -n 2
#   bash run.sh --claude --random 5 -d terminal-bench@2.0 -n 1

SCRIPT_DIR="$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUTF8=1  # Fix Windows encoding issues with non-ASCII model output

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Defaults
PROVIDER="claude"
RANDOM_N=""

# Parse our custom flags
while true; do
    case "$1" in
        --groq)
            PROVIDER="groq"
            shift
            ;;
        --gemini)
            PROVIDER="gemini"
            shift
            ;;
        --claude)
            PROVIDER="claude"
            shift
            ;;
        --ollama)
            PROVIDER="ollama"
            shift
            ;;
        --ollama-terminus)
            PROVIDER="ollama-terminus"
            shift
            ;;
        --random)
            RANDOM_N="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Set up provider-specific args
PROVIDER_ARGS=()
case "$PROVIDER" in
    claude)
        export CLAUDE_CODE_OAUTH_TOKEN=$(python3 "$SCRIPT_DIR/get_token.py" 2>/dev/null)
        echo "Provider: Claude Code (OAuth: ${CLAUDE_CODE_OAUTH_TOKEN:0:20}...)"
        PROVIDER_ARGS+=("-a" "claude-code" "-m" "anthropic/claude-sonnet-4-20250514")
        ;;
    ollama)
        # Claude Code agent pointed at Ollama's Anthropic-compatible API
        # See: https://docs.ollama.com/integrations/claude-code
        # Ollama runs on host, Docker containers reach it via host.docker.internal
        export ANTHROPIC_BASE_URL="http://host.docker.internal:11434"
        export ANTHROPIC_AUTH_TOKEN="ollama"
        export ANTHROPIC_API_KEY=""
        # Claude Code uses 3 internal model tiers — all must point to our Ollama model
        OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:0.6b}"
        export ANTHROPIC_DEFAULT_HAIKU_MODEL="$OLLAMA_MODEL"
        export ANTHROPIC_DEFAULT_SONNET_MODEL="$OLLAMA_MODEL"
        export ANTHROPIC_DEFAULT_OPUS_MODEL="$OLLAMA_MODEL"
        echo "Provider: Claude Code + Ollama (Model: $OLLAMA_MODEL)"
        PROVIDER_ARGS+=("-a" "claude-code" "-m" "$OLLAMA_MODEL")
        ;;
    ollama-terminus)
        # Official Harbor approach: Terminus-2 agent + LiteLLM Ollama support
        # See: https://github.com/harbor-framework/harbor/commit/e4b6e0b
        OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:0.6b}"
        echo "Provider: Terminus-2 + Ollama (Model: $OLLAMA_MODEL)"
        PROVIDER_ARGS+=("-a" "terminus-2" "-m" "ollama/$OLLAMA_MODEL")
        ;;
    groq)
        if [ -z "$GROQ_API_KEY" ]; then
            echo "ERROR: GROQ_API_KEY not set. Add it to .env"
            exit 1
        fi
        echo "Provider: Groq + Terminus (Key: ${GROQ_API_KEY:0:10}...)"
        PROVIDER_ARGS+=("-a" "terminus-2" "-m" "groq/llama-3.3-70b-versatile")
        ;;
    gemini)
        if [ -z "$GEMINI_API_KEY" ]; then
            echo "ERROR: GEMINI_API_KEY not set. Add it to .env"
            exit 1
        fi
        echo "Provider: Gemini + Terminus (Key: ${GEMINI_API_KEY:0:10}...)"
        PROVIDER_ARGS+=("-a" "terminus-2" "-m" "gemini/gemini-2.0-flash")
        ;;
esac

# Build random task flags if requested
INCLUDE_ARGS=()
if [ -n "$RANDOM_N" ]; then
    echo "Picking $RANDOM_N random tasks..."
    RAW=$(python3 "$SCRIPT_DIR/pick_tasks.py" "$RANDOM_N" | tr -d '\r\n')
    read -ra TASKS <<< "$RAW"

    for task in "${TASKS[@]}"; do
        echo "  - $task"
        INCLUDE_ARGS+=("-i" "$task")
    done
fi

echo "---"
echo "Running: harbor run ${PROVIDER_ARGS[*]} ${INCLUDE_ARGS[*]} $@"
echo "---"
harbor run "${PROVIDER_ARGS[@]}" "${INCLUDE_ARGS[@]}" "$@"
