#!/usr/bin/env bash
# Copy the stills the project's partitions need. The list comes from the local
# database. The database itself is not copied.
#
#   data/sync.sh user@host [project]
#
# Set CHORUS_REMOTE_DIR if the remote folder is not /data/mjma/chorus.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: sync.sh user@host [project]" >&2
  exit 1
fi

HOST="$1"
PROJECT="${2:-voices}"
REMOTE_DIR="${CHORUS_REMOTE_DIR:-/data/mjma/chorus}"

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$REPO/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO/.env"
  set +a
fi
ROOT="${CHORUS_ROOT:-$ROOT}"
SOURCE="$ROOT/data/$PROJECT"
DEST="$HOST:$REMOTE_DIR/data/$PROJECT"

if [[ ! -d "$SOURCE" ]]; then
  echo "No data directory at $SOURCE" >&2
  exit 1
fi

if [[ -x "$REPO/.venv/bin/python" ]]; then
  PYTHON="$REPO/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
  export PYTHONPATH="$REPO/backend${PYTHONPATH:+:$PYTHONPATH}"
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
"$PYTHON" -m chorus files --project "$PROJECT" --partition all > "$WORKDIR/files.txt"

mkdir -p "$SOURCE"
rsync -a --copy-links --files-from="$WORKDIR/files.txt" "$SOURCE/" "$DEST"
if [[ -f "$SOURCE/manifest.json" ]]; then
  rsync -a "$SOURCE/manifest.json" "$DEST"
fi
echo "Synced $(wc -l < "$WORKDIR/files.txt") files plus manifest.json to $DEST"
