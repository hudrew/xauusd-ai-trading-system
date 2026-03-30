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

resolve_absolute_project_path() {
  local path_value="$1"
  if [[ "${path_value}" = /* ]]; then
    echo "${path_value}"
    return
  fi
  echo "${ROOT_DIR}/${path_value}"
}

run_cli() {
  local config_path="$1"
  shift
  PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli --config "${config_path}" "$@"
}

default_mt5_config_path_for_mode() {
  local mode="${1:-${XAUUSD_AI_ENV:-paper}}"
  if [[ "${mode}" == "prod" ]]; then
    echo "${ROOT_DIR}/configs/mt5_prod.yaml"
    return
  fi
  echo "${ROOT_DIR}/configs/mt5_paper.yaml"
}

resolve_mt5_config() {
  local config_path="${1:-${XAUUSD_AI_CONFIG_PATH:-}}"
  local mode="${2:-${XAUUSD_AI_ENV:-paper}}"
  if [[ -z "${config_path}" ]]; then
    config_path="$(default_mt5_config_path_for_mode "${mode}")"
  else
    config_path="$(resolve_absolute_project_path "${config_path}")"
  fi

  if [[ ! -f "${config_path}" ]]; then
    echo "MT5 config not found: ${config_path}" >&2
    exit 1
  fi

  echo "${config_path}"
}
