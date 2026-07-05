#!/usr/bin/env bash
#
# Sync the vendored copy of the pyfosi library into the integration.
#
# This integration vendors (ships an in-tree copy of) the standalone `pyfosi`
# client library so it has no external PyPI dependency. The canonical source
# lives in the sibling `pyfosi/` project. Run this after changing the library
# to keep the vendored copy from drifting.
#
# Usage:
#   scripts/sync_pyfosi.sh          # copy source -> vendored
#   scripts/sync_pyfosi.sh --check  # verify in sync, non-zero exit if not (CI)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDORED="$REPO_ROOT/custom_components/fosi_s3/pyfosi"
SOURCE="${PYFOSI_SRC:-$REPO_ROOT/../pyfosi/pyfosi}"

FILES=(client.py models.py __init__.py)

if [[ ! -d "$SOURCE" ]]; then
  echo "error: pyfosi source not found at: $SOURCE" >&2
  echo "       set PYFOSI_SRC to the pyfosi/pyfosi package directory." >&2
  exit 2
fi

if [[ "${1:-}" == "--check" ]]; then
  status=0
  for f in "${FILES[@]}"; do
    if ! diff -q "$SOURCE/$f" "$VENDORED/$f" >/dev/null 2>&1; then
      echo "OUT OF SYNC: $f" >&2
      status=1
    fi
  done
  [[ $status -eq 0 ]] && echo "vendored pyfosi is in sync."
  exit $status
fi

for f in "${FILES[@]}"; do
  cp "$SOURCE/$f" "$VENDORED/$f"
  echo "synced $f"
done
