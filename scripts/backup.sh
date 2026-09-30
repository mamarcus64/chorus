#!/usr/bin/env bash
# Consistent snapshot of one project database.
#   db/backup.sh [project]
set -euo pipefail

PROJECT="${1:-voices}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

SOURCE="$ROOT/db/${PROJECT}.sqlite"
DEST_DIR="$ROOT/db/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEST_DIR"
if [[ ! -f "$SOURCE" ]]; then
  echo "No database at $SOURCE" >&2
  exit 1
fi
sqlite3 "$SOURCE" ".backup '$DEST_DIR/${PROJECT}-${STAMP}.sqlite'"
echo "Wrote $DEST_DIR/${PROJECT}-${STAMP}.sqlite"
