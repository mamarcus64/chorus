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
PORT="${CHORUS_PORT:-1945}"

CONDA="${CONDA_EXE:-}"
if [[ -z "$CONDA" && -x /data2/mjma/miniconda3/bin/conda ]]; then
  CONDA=/data2/mjma/miniconda3/bin/conda
fi
if [[ -n "$CONDA" ]]; then
  # shellcheck disable=SC1091
  source "$("$CONDA" info --base)/etc/profile.d/conda.sh"
  conda activate chorus
fi

# The served pages live in backend/chorus/static, which git does not track.
# Rebuild when frontend source is newer than that bundle, including after a pull.
static_index="$REPO/backend/chorus/static/index.html"
frontend_inputs=()
for path in \
  "$REPO/frontend/index.html" \
  "$REPO/frontend/package.json" \
  "$REPO/frontend/package-lock.json" \
  "$REPO/frontend/vite.config.ts" \
  "$REPO/frontend/tsconfig.json" \
  "$REPO/frontend/tsconfig.app.json" \
  "$REPO/frontend/tsconfig.node.json"
do
  [[ -e "$path" ]] && frontend_inputs+=("$path")
done
[[ -d "$REPO/frontend/src" ]] && frontend_inputs+=("$REPO/frontend/src")
[[ -d "$REPO/frontend/public" ]] && frontend_inputs+=("$REPO/frontend/public")

frontend_newer=""
if [[ -f "$static_index" && ${#frontend_inputs[@]} -gt 0 ]]; then
  frontend_newer="$(find "${frontend_inputs[@]}" -type f -newer "$static_index" -print -quit)"
fi
if [[ ! -f "$static_index" || -n "$frontend_newer" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "Frontend is stale and npm was not found. Run: bash scripts/setup.sh" >&2
    exit 1
  fi
  echo "Frontend is stale. Rebuilding."
  lock_stamp="$REPO/frontend/node_modules/.package-lock.json"
  if [[ ! -d "$REPO/frontend/node_modules" || "$REPO/frontend/package-lock.json" -nt "$lock_stamp" ]]; then
    (cd "$REPO/frontend" && npm install)
  fi
  (cd "$REPO/frontend" && npm run build)
  rm -rf "$REPO/backend/chorus/static"
  mkdir -p "$REPO/backend/chorus/static"
  cp -a "$REPO/frontend/dist/." "$REPO/backend/chorus/static/"
fi

if command -v lsof >/dev/null 2>&1; then
  lsof -ti:"$PORT" | xargs -r kill -9 || true
fi

cd "$REPO/backend"
exec uvicorn chorus.main:app --host 127.0.0.1 --port "$PORT"
