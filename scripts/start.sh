#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$REPO/.." && pwd)"
cd "$REPO"

if [[ -f "$REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO/.env"
  set +a
fi
export CHORUS_ROOT="${CHORUS_ROOT:-$ROOT}"
export PYTHONPATH="$REPO/backend${PYTHONPATH:+:$PYTHONPATH}"
PORT="${CHORUS_PORT:-8733}"

CONDA="${CONDA_EXE:-}"
if [[ -z "$CONDA" && -x /data2/mjma/miniconda3/bin/conda ]]; then
  CONDA=/data2/mjma/miniconda3/bin/conda
fi
if [[ -n "$CONDA" ]]; then
  # shellcheck disable=SC1091
  source "$("$CONDA" info --base)/etc/profile.d/conda.sh"
  conda activate chorus
fi

if command -v lsof >/dev/null 2>&1; then
  lsof -ti:"$PORT" | xargs -r kill -9 || true
fi

cd "$REPO/backend"
exec uvicorn chorus.main:app --host 0.0.0.0 --port "$PORT"
