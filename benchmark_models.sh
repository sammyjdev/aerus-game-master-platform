#!/usr/bin/env bash
set -e

# ==============================================================================
# Aerus RPG - Multi-Model Benchmark Runner (OpenAI, Anthropic, Gemini, etc.)
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

MODELS=("$@")
if [ ${#MODELS[@]} -eq 0 ]; then
    MODELS=(
        "openai/gpt-6-luna"
        "deepseek/deepseek-v4.1-flash"
        "sao10k/l3.3-euryale-70b"
        "thedrummer/cydonia-24b-v4.1"
        "thedrummer/unslopnemo-12b"
        "nousresearch/hermes-3-llama-3.1-70b"
        "meta-llama/llama-3.3-70b-instruct"
        "google/gemini-3.8-flash"
    )
fi

echo "========================================================"
echo "  ⚔️  Aerus RPG - Game Master Model Benchmark Harness   "
echo "========================================================"
echo "Modelos a serem avaliados:"
for m in "${MODELS[@]}"; do
    echo "  - $m"
done
echo "========================================================"
echo ""

# Determine python interpreter
if [ -f "/tmp/agents-recovery-20261006-132731/python311/bin/python" ]; then
    PYTHON_BIN="/tmp/agents-recovery-20261006-132731/python311/bin/python"
elif [ -f "$PROJECT_DIR/backend/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_DIR/backend/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

VAULT_SCRIPT="$HOME/.agents/scripts/axon-secrets.sh"

run_benchmark_for_model() {
    local target_model="$1"
    echo ""
    echo "--------------------------------------------------------"
    echo ">> Testando Modelo: $target_model"
    echo "--------------------------------------------------------"

    export AERUS_LLM_PROVIDER="openrouter"
    export AERUS_OPENROUTER_MODEL="$target_model"
    export AERUS_EVAL_PROFILE="default"
    export AERUS_EVAL_TIER="core"

    (
        cd "$PROJECT_DIR/backend"
        $PYTHON_BIN eval/gm_eval.py
    )
}

for model in "${MODELS[@]}"; do
    if [ -x "$VAULT_SCRIPT" ]; then
        "$VAULT_SCRIPT" run -- bash -c "$(declare -f run_benchmark_for_model); PROJECT_DIR='$PROJECT_DIR' PYTHON_BIN='$PYTHON_BIN' run_benchmark_for_model '$model'"
    else
        run_benchmark_for_model "$model"
    fi
done

echo ""
echo "========================================================"
echo "  🏁 Benchmark de todos os modelos concluído!"
echo "========================================================"
