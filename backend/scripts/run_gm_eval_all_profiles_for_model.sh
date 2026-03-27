#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <openrouter-model>"
  echo "Example: $0 google/gemini-2.5-flash"
  exit 1
fi

MODEL="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/run_gm_eval_profile_for_model.sh" basic "$MODEL"
"$SCRIPT_DIR/run_gm_eval_profile_for_model.sh" intermediate "$MODEL"
"$SCRIPT_DIR/run_gm_eval_profile_for_model.sh" complex "$MODEL"
