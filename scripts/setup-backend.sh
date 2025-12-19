#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENV_DIR=${VENV_DIR:-"$REPO_ROOT/.venv"}
PYTHON_BIN=${PYTHON_BIN:-python3}

if [ ! -d "$VENV_DIR" ]; then
  echo "[setup] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install --upgrade wheel setuptools

REQ_FILE="$REPO_ROOT/backend/requirements.lock.txt"
if [ -f "$REQ_FILE" ]; then
  echo "[setup] Installing pinned backend dependencies from $REQ_FILE"
  python -m pip install -r "$REQ_FILE"
else
  echo "[setup] requirements.lock.txt missing, falling back to requirements.txt"
  python -m pip install -r "$REPO_ROOT/backend/requirements.txt"
fi

echo "[setup] Backend environment ready at $VENV_DIR"
