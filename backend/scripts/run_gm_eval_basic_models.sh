#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/run_gm_eval_profile_for_model.sh" basic openai/gpt-4.1-mini
"$SCRIPT_DIR/run_gm_eval_profile_for_model.sh" basic anthropic/claude-sonnet-4.6
