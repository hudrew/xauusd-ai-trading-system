#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
DEFAULT_ENV_FILE="${ROOT_DIR}/.env.mt5.local"

ensure_venv() {
  if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "Missing virtual environment python: ${VENV_PYTHON}" >&2
    echo "Create it first with: python3 -m venv .venv && source .venv/bin/activate" >&2
    exit 1
  fi
}

load_env_file() {
  local env_file="${1:-${DEFAULT_ENV_FILE}}"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  fi
}

run_cli() {
  local config_path="$1"
  shift
  PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli --config "${config_path}" "$@"
}

resolve_mt5_config() {
  local env_name="${XAUUSD_AI_ENV:-paper}"
  if [[ "${env_name}" == "prod" ]]; then
    echo "${ROOT_DIR}/configs/mt5_prod.yaml"
    return
  fi
  echo "${ROOT_DIR}/configs/mt5_paper.yaml"
}
