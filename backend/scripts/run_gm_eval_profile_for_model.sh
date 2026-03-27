#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <profile> <openrouter-model> [extra env assignments via current shell]"
  echo "Example: $0 basic openai/gpt-4.1-mini"
  exit 1
fi

PROFILE="$1"
MODEL="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$BACKEND_DIR/.venv/Scripts/python.exe"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found at $PYTHON_BIN"
  exit 1
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set in this shell."
  exit 1
fi

TEMP_ROOT="${TMPDIR:-/tmp}"
TEMP_CONFIG_DIR="$(mktemp -d "$TEMP_ROOT/aerus-gm-eval-config-XXXXXX")"
cleanup() {
  rm -rf "$TEMP_CONFIG_DIR"
}
trap cleanup EXIT

cp -R "$BACKEND_DIR/config/." "$TEMP_CONFIG_DIR/"

"$PYTHON_BIN" - <<'PY' "$TEMP_CONFIG_DIR" "$MODEL"
from pathlib import Path
import sys
import yaml

config_dir = Path(sys.argv[1])
model = sys.argv[2]
campaign_path = config_dir / "campaign.yaml"
data = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
selection = data.setdefault("model_selection", {})
selection["default"] = model
selection["fallback"] = model
selection["tension_thresholds"] = {
    "low": {"max": 3, "model": model},
    "medium": {"max": 6, "model": model},
    "high": {"max": 8, "model": model},
    "critical": {"max": 10, "model": model},
}
campaign_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"Prepared temporary config for model: {model}")
PY

echo "========================================================================"
echo "GM_EVAL hosted run"
echo "Profile: $PROFILE"
echo "Hosted model override: $MODEL"
echo "Temp CONFIG_DIR: $TEMP_CONFIG_DIR"
echo "========================================================================"

(
  cd "$BACKEND_DIR"
  CONFIG_DIR="$TEMP_CONFIG_DIR" \
  AERUS_LOCAL_ONLY=false \
  AERUS_OLLAMA_URL="${AERUS_OLLAMA_URL:-http://127.0.0.1:1}" \
  AERUS_EVAL_PROFILE="$PROFILE" \
  AERUS_EVAL_INCLUDE_STABLE="${AERUS_EVAL_INCLUDE_STABLE:-1}" \
  AERUS_EVAL_CONCURRENCY="${AERUS_EVAL_CONCURRENCY:-1}" \
  "$PYTHON_BIN" eval/gm_eval.py
)

echo "========================================================================"
echo "GM_EVAL run completed"
echo "Profile: $PROFILE"
echo "Hosted model override: $MODEL"
echo "History file: $BACKEND_DIR/eval/history/gm_eval_runs.jsonl"
echo "========================================================================"
