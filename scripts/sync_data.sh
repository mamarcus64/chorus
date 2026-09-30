#!/usr/bin/env bash
# Copy the raw files a partition needs. File-level sync: a file changed on only
# one side is copied. The database is not part of this sync.
#
#   data/sync.sh user@host:/data/mjma/chorus/data/voices /tmp/files.txt
#   data/sync.sh /some/local/dir /tmp/files.txt
#
# The file list is relative paths under data/<project>/, one per line,
# as printed by: python -m chorus files --project voices --partition <id|all>
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: sync.sh DEST FILE_LIST [project]" >&2
  exit 1
fi

DEST="$1"
FILE_LIST="$2"
PROJECT="${3:-voices}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# This script lives in the repo (scripts/) and is linked from data/sync.sh.
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
SOURCE="$ROOT/data/$PROJECT"

if [[ ! -d "$SOURCE" ]]; then
  echo "No data directory at $SOURCE" >&2
  exit 1
fi

mkdir -p "$SOURCE"
rsync -a --copy-links --files-from="$FILE_LIST" "$SOURCE/" "$DEST"
if [[ -f "$SOURCE/manifest.json" ]]; then
  rsync -a "$SOURCE/manifest.json" "$DEST"
fi
echo "Synced $(wc -l < "$FILE_LIST") files plus manifest.json to $DEST"
