#!/usr/bin/env bash
# Reconcile this machine's project database with the copy on another host.
# Nothing here opens a database connection across the network. The files are
# copied, then merged on this machine, then the merged file is copied back.
#
# Stop writers on both sides first. The remote app is stopped with pkill and
# started again with scripts/start.sh. Set CHORUS_REMOTE_DIR if the folder is
# not /data/mjma/chorus.
#
#   db/sync_db.sh user@host [project]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: sync_db.sh user@host [project]" >&2
  exit 1
fi

HOST="$1"
PROJECT="${2:-voices}"
REMOTE_DIR="${CHORUS_REMOTE_DIR:-/data/mjma/chorus}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
  REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  REPO="$ROOT/chorus"
fi

LOCAL="$ROOT/db/${PROJECT}.sqlite"
BASE="$ROOT/db/.base/${PROJECT}.sqlite"
MERGE="$REPO/scripts/merge.py"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

if [[ ! -f "$LOCAL" ]]; then
  echo "No local database at $LOCAL" >&2
  exit 1
fi
if [[ ! -f "$BASE" ]]; then
  echo "No merge base at $BASE." >&2
  echo "On the first deploy, copy the database you sent to the host into that path." >&2
  exit 1
fi

echo "Stopping remote app"
ssh "$HOST" "pkill -f 'uvicorn chorus.main:app' || true"

echo "Pulling remote database"
scp "$HOST:$REMOTE_DIR/db/${PROJECT}.sqlite" "$WORKDIR/remote.sqlite"

echo "Merging"
python3 "$MERGE" "$BASE" "$LOCAL" "$WORKDIR/remote.sqlite" -o "$WORKDIR/merged.sqlite"

echo "Installing merged database locally and as the new base"
mkdir -p "$ROOT/db/.base" "$ROOT/db/backups"
cp "$LOCAL" "$ROOT/db/backups/${PROJECT}-before-merge-$(date -u +%Y%m%dT%H%M%SZ).sqlite"
cp "$WORKDIR/merged.sqlite" "$LOCAL"
cp "$WORKDIR/merged.sqlite" "$BASE"

echo "Pushing merged database"
scp "$WORKDIR/merged.sqlite" "$HOST:$REMOTE_DIR/db/${PROJECT}.sqlite"
ssh "$HOST" "mkdir -p '$REMOTE_DIR/db/.base' && cp '$REMOTE_DIR/db/${PROJECT}.sqlite' '$REMOTE_DIR/db/.base/${PROJECT}.sqlite'"

echo "Starting remote app"
ssh "$HOST" "cd '$REMOTE_DIR/chorus' && bash scripts/start.sh"
echo "Merged $PROJECT"
