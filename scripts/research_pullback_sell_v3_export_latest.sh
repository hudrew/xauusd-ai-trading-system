#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

OUTPUT_PATH="${1:-${ROOT_DIR}/tmp/research_pullback_sell_v3_acceptance_latest.json}"
REPORT_DIR="${ROOT_DIR}/reports/research_pullback_sell_v3"

ensure_venv
PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli report-export "${OUTPUT_PATH}" --report-dir "${REPORT_DIR}" "${@:2}"
