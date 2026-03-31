#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

CSV_PATH="${1:-${ROOT_DIR}/tmp/xauusd_m1_history_150000_chunked_vps_full.csv}"
OUTPUT_PATH="${2:-${ROOT_DIR}/tmp/research_pullback_sell_v3_density_probe_latest.json}"
CONFIG_PATH="${ROOT_DIR}/configs/mvp_pullback_sell_research_v3_branch_gate.yaml"

if [[ $# -gt 0 ]]; then
  shift
fi
if [[ $# -gt 0 ]]; then
  shift
fi

ensure_venv
if [[ $# -gt 0 ]]; then
  run_cli "${CONFIG_PATH}" pullback-density-probe "${CSV_PATH}" --config-path "${CONFIG_PATH}" --output "${OUTPUT_PATH}" "$@"
else
  run_cli "${CONFIG_PATH}" pullback-density-probe "${CSV_PATH}" --config-path "${CONFIG_PATH}" --output "${OUTPUT_PATH}"
fi
