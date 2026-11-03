#!/usr/bin/env bash
set -e

# ==============================================================================
# Aerus RPG - Local Game Launcher
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================================"
echo "  🗡️  Aerus RPG - Single Player Narrative Experience   "
echo "========================================================"

# Default to local ExLlamaV3 with UnslopNemo if TabbyAPI or local weights exist
TABBY_DIR="$HOME/.local/share/exllamav3/tabbyAPI"
TABBY_VENV="$HOME/.local/share/exllamav3/venv/bin/python"
DEFAULT_LOCAL_MODEL="UnslopNemo-12B-v4.1-exl3-4.25bpw"

if [ -d "$HOME/.local/share/exllamav3/models/$DEFAULT_LOCAL_MODEL" ]; then
    export AERUS_LLM_PROVIDER="${AERUS_LLM_PROVIDER:-exllamav3}"
    export AERUS_EXLLAMAV3_MODEL="${AERUS_EXLLAMAV3_MODEL:-$DEFAULT_LOCAL_MODEL}"
    export AERUS_EXLLAMAV3_URL="${AERUS_EXLLAMAV3_URL:-http://127.0.0.1:5000/v1}"
else
    export AERUS_OPENROUTER_MODEL="${AERUS_OPENROUTER_MODEL:-openai/gpt-6-luna}"
    export AERUS_LLM_PROVIDER="${AERUS_LLM_PROVIDER:-openrouter}"
fi

echo ">> Provedor de IA: $AERUS_LLM_PROVIDER"
if [ "$AERUS_LLM_PROVIDER" = "exllamav3" ]; then
    echo ">> Modelo do Game Master Local (GPU): $AERUS_EXLLAMAV3_MODEL"
else
    echo ">> Modelo do Game Master: $AERUS_OPENROUTER_MODEL"
fi

# Determine python interpreter
if [ -f "$PROJECT_DIR/backend/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_DIR/backend/.venv/bin/python"
    UVICORN_BIN="$PROJECT_DIR/backend/.venv/bin/uvicorn"
elif [ -f "/tmp/agents-recovery-20261006-132731/python311/bin/python" ]; then
    PYTHON_BIN="/tmp/agents-recovery-20261006-132731/python311/bin/python"
    UVICORN_BIN="/tmp/agents-recovery-20261006-132731/python311/bin/uvicorn"
else
    PYTHON_BIN="python3"
    UVICORN_BIN="uvicorn"
fi

VAULT_SCRIPT="$HOME/.agents/scripts/axon-secrets.sh"

run_services() {
    TABBY_PID=""
    if [ "$AERUS_LLM_PROVIDER" = "exllamav3" ]; then
        if curl -s -f "http://127.0.0.1:5000/v1/model" >/dev/null 2>&1; then
            echo ">> TabbyAPI já está ativo em http://127.0.0.1:5000/v1"
        elif [ -f "$TABBY_DIR/main.py" ] && [ -f "$TABBY_VENV" ]; then
            echo ">> Iniciando TabbyAPI com $AERUS_EXLLAMAV3_MODEL..."
            (
                cd "$TABBY_DIR"
                "$TABBY_VENV" main.py
            ) &
            TABBY_PID=$!
            sleep 4
        fi
    fi

    echo ">> Iniciando Backend FastAPI (Porta 8000)..."
    (
        cd "$PROJECT_DIR/backend"
        $UVICORN_BIN src.main:app --host 0.0.0.0 --port 8000 --reload
    ) &
    BACKEND_PID=$!

    echo ">> Iniciando Frontend Vite (Porta 5173)..."
    (
        cd "$PROJECT_DIR/frontend"
        npm run dev -- --host 0.0.0.0 --port 5173
    ) &
    FRONTEND_PID=$!

    cleanup() {
        echo ""
        echo ">> Encerrando servidores..."
        kill $BACKEND_PID $FRONTEND_PID $TABBY_PID 2>/dev/null || true
        exit 0
    }

    trap cleanup INT TERM EXIT

    echo ""
    echo "========================================================"
    echo "  🎮 Aerus RPG rodando com sucesso!"
    echo "  ⚡ IA Local: $AERUS_EXLLAMAV3_MODEL"
    echo "  👉 Acesse no navegador: http://localhost:5173"
    echo "========================================================"
    echo ""
    echo "Pressione Ctrl+C para encerrar os servidores."

    wait
}

# Run wrapped in vault if present, otherwise direct
if [ -x "$VAULT_SCRIPT" ]; then
    echo ">> Carregando chaves de assinatura do cofre axon-secrets..."
    "$VAULT_SCRIPT" run -- bash -c "$(declare -f run_services); PROJECT_DIR='$PROJECT_DIR' PYTHON_BIN='$PYTHON_BIN' UVICORN_BIN='$UVICORN_BIN' AERUS_OPENROUTER_MODEL='$AERUS_OPENROUTER_MODEL' AERUS_LLM_PROVIDER='$AERUS_LLM_PROVIDER' AERUS_EXLLAMAV3_MODEL='$AERUS_EXLLAMAV3_MODEL' AERUS_EXLLAMAV3_URL='$AERUS_EXLLAMAV3_URL' TABBY_DIR='$TABBY_DIR' TABBY_VENV='$TABBY_VENV' run_services"
else
    run_services
fi

