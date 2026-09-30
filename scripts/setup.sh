#!/usr/bin/env bash
# Create the conda env, install Chorus, build the frontend, migrate projects.
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

CONDA="${CONDA_EXE:-}"
if [[ -z "$CONDA" && -x /data2/mjma/miniconda3/bin/conda ]]; then
  CONDA=/data2/mjma/miniconda3/bin/conda
fi
if [[ -z "$CONDA" ]]; then
  echo "conda was not found. Install miniconda or set CONDA_EXE." >&2
  exit 1
fi

if "$CONDA" env list | awk '{print $1}' | grep -qx chorus; then
  echo "Updating conda env chorus"
  "$CONDA" env update -f "$REPO/environment.yml" --prune
else
  echo "Creating conda env chorus"
  "$CONDA" env create -f "$REPO/environment.yml"
fi

# shellcheck disable=SC1091
source "$("$CONDA" info --base)/etc/profile.d/conda.sh"
conda activate chorus

python -m pip install -e "$REPO"
(
  cd "$REPO/frontend"
  npm install
  npm run build
)
rm -rf "$REPO/backend/chorus/static"
mkdir -p "$REPO/backend/chorus/static"
cp -a "$REPO/frontend/dist/." "$REPO/backend/chorus/static/"

mkdir -p "$ROOT/db" "$ROOT/db/.base" "$ROOT/db/backups" "$ROOT/data"
ln -sfn "$REPO/scripts/merge.py" "$ROOT/db/merge.py"
ln -sfn "$REPO/scripts/sync_db.sh" "$ROOT/db/sync_db.sh"
ln -sfn "$REPO/scripts/backup.sh" "$ROOT/db/backup.sh"
ln -sfn "$REPO/scripts/sync_data.sh" "$ROOT/data/sync.sh"
chmod +x "$REPO/scripts/"*.sh "$REPO/scripts/merge.py"

IFS=',' read -r -a PROJECTS <<< "${CHORUS_PROJECTS:-voices}"
for project in "${PROJECTS[@]}"; do
  project="$(echo "$project" | tr -d ' ')"
  [[ -z "$project" ]] && continue
  python -m chorus migrate --project "$project"
done

echo "Setup complete. Start with: bash scripts/start.sh"
