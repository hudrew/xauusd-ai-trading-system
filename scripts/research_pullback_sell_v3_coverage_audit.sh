#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

OUTPUT_PATH="${1:-${ROOT_DIR}/tmp/research_pullback_sell_v3_coverage_audit_latest.json}"

shift || true

DEFAULT_JSON_PATHS=(
  "${ROOT_DIR}/tmp/research_pullback_sell_v3_probe_acceptance_150000_local.json"
  "${ROOT_DIR}/tmp/research_pullback_sell_v3_probe_acceptance_300000_local.json"
  "${ROOT_DIR}/tmp/research_pullback_sell_v3_probe_acceptance_500000_local.json"
)

JSON_PATHS=("$@")
if [[ ${#JSON_PATHS[@]} -eq 0 ]]; then
  JSON_PATHS=("${DEFAULT_JSON_PATHS[@]}")
fi

ensure_venv
PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli report-audit "${JSON_PATHS[@]}" --output "${OUTPUT_PATH}"
