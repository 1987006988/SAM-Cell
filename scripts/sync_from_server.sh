#!/usr/bin/env bash
        set -u

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
        SSH_HOST="${SSH_HOST:-taotao@10.181.10.20}"
        DRY_RUN="${DRY_RUN:-1}"
        DEST_ROOT="${DEST_ROOT:-$PACKAGE_ROOT/artifacts/remote_synced}"
        MANIFEST="$PACKAGE_ROOT/artifacts/path_index/remote_small_artifacts.csv"
        MISSING="$DEST_ROOT/TODO_NEEDS_REFRESH_missing_remote_files.txt"

        mkdir -p "$DEST_ROOT"
        : > "$MISSING"

        tail -n +2 "$MANIFEST" | while IFS=, read -r category remote_path; do
          category="${category%$'\r'}"
          remote_path="${remote_path%$'\r'}"
          [ -n "$remote_path" ] || continue
          rel="${remote_path#/backup/taotao_work/sam_cell/}"
          rel="${rel#/backup/taotao_work/}"
          dest="$DEST_ROOT/$category/$rel"
          mkdir -p "$(dirname "$dest")"
          if [[ "$DRY_RUN" != "0" ]]; then
            echo "DRY_RUN scp $SSH_HOST:$remote_path $dest"
            continue
          fi
          if scp "$SSH_HOST:$remote_path" "$dest"; then
            echo "copied $remote_path"
          else
            echo "TODO_NEEDS_REFRESH $remote_path" | tee -a "$MISSING" >&2
          fi
        done

        if [[ "$DRY_RUN" != "0" ]]; then
          echo "sync_from_server: dry-run complete"
        else
          echo "sync_from_server: complete; missing list at $MISSING"
        fi
