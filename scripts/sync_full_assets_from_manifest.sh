#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MANIFEST="${MANIFEST:-$PACKAGE_ROOT/artifacts/path_index/full_asset_sync_manifest.csv}"
SSH_HOST="${SSH_HOST:-taotao@10.181.10.20}"
DRY_RUN="${DRY_RUN:-1}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing full asset manifest: $MANIFEST" >&2
  exit 1
fi

tail -n +2 "$MANIFEST" | while IFS=, read -r asset_type source_hint destination_hint status notes; do
  asset_type="${asset_type%$'\r'}"
  source_hint="${source_hint%$'\r'}"
  destination_hint="${destination_hint%$'\r'}"
  status="${status%$'\r'}"
  [[ -n "$asset_type" ]] || continue
  if [[ "$status" == "included" ]]; then
    continue
  fi
  if [[ "$source_hint" == TODO_NEEDS_REFRESH* ]]; then
    echo "TODO_NEEDS_REFRESH $asset_type: $notes"
    continue
  fi
  dest="$PACKAGE_ROOT/$destination_hint"
  mkdir -p "$(dirname "$dest")"
  if [[ "$source_hint" == /backup/* ]]; then
    if [[ "$DRY_RUN" != "0" ]]; then
      echo "DRY_RUN scp -r $SSH_HOST:$source_hint $dest"
    else
      scp -r "$SSH_HOST:$source_hint" "$dest"
    fi
  else
    if [[ "$DRY_RUN" != "0" ]]; then
      echo "DRY_RUN cp -r $source_hint $dest"
    else
      cp -r "$source_hint" "$dest"
    fi
  fi
done
