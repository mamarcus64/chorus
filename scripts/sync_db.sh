#!/usr/bin/env bash
# Reconcile this machine's project database with the copy on another host.
# Nothing here opens a database connection across the network. Each side is
# snapshotted with SQLite's backup API, the snapshots are merged on this
# machine, and the merged file is written back into the existing database
# files. The app is not stopped or started. Set CHORUS_REMOTE_DIR if the
# folder is not /data/mjma/chorus.
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
REMOTE="$REMOTE_DIR/db/${PROJECT}.sqlite"
REMOTE_BASE="$REMOTE_DIR/db/.base/${PROJECT}.sqlite"
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

# Copy src into dest through SQLite, including pages still in the WAL. A plain
# file copy of a database an app has open can miss those pages or replace the
# file the app is still writing.
snapshot() {
  python3 - "$1" "$2" << 'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
source.execute("PRAGMA busy_timeout=5000")
target.execute("PRAGMA busy_timeout=5000")
try:
    source.backup(target)
    target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
finally:
    target.close()
    source.close()
PY
}

echo "Snapshotting local database"
snapshot "$LOCAL" "$WORKDIR/local.sqlite"

echo "Snapshotting remote database"
REMOTE_SNAP="$(ssh "$HOST" mktemp)"
ssh "$HOST" python3 - "$REMOTE" "$REMOTE_SNAP" << 'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
source.execute("PRAGMA busy_timeout=5000")
target.execute("PRAGMA busy_timeout=5000")
try:
    source.backup(target)
    target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
finally:
    target.close()
    source.close()
PY
scp "$HOST:$REMOTE_SNAP" "$WORKDIR/remote.sqlite"
ssh "$HOST" rm -f "$REMOTE_SNAP"

echo "Merging"
python3 "$MERGE" "$BASE" "$WORKDIR/local.sqlite" "$WORKDIR/remote.sqlite" -o "$WORKDIR/merged.sqlite"

echo "Installing merged database locally and as the new base"
mkdir -p "$ROOT/db/.base" "$ROOT/db/backups"
cp "$WORKDIR/local.sqlite" "$ROOT/db/backups/${PROJECT}-before-merge-$(date -u +%Y%m%dT%H%M%SZ).sqlite"
snapshot "$WORKDIR/merged.sqlite" "$LOCAL"
cp "$WORKDIR/merged.sqlite" "$BASE"

echo "Writing merged database on the remote"
REMOTE_MERGED="$(ssh "$HOST" mktemp)"
scp "$WORKDIR/merged.sqlite" "$HOST:$REMOTE_MERGED"
ssh "$HOST" python3 - "$REMOTE_MERGED" "$REMOTE" << 'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
source.execute("PRAGMA busy_timeout=5000")
target.execute("PRAGMA busy_timeout=5000")
try:
    source.backup(target)
    target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
finally:
    target.close()
    source.close()
PY
ssh "$HOST" "mkdir -p '$REMOTE_DIR/db/.base' && cp '$REMOTE_MERGED' '$REMOTE_BASE' && rm -f '$REMOTE_MERGED'"
echo "Merged $PROJECT"
