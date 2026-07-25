#!/bin/bash

set -uo pipefail

# PPI housekeeping: remove only disposable, timestamped artifacts.
# Default retention is 35 days. Override with RETENTION_DAYS=<n>.
# Use --dry-run to list files without deleting them.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RETENTION_DAYS="${RETENTION_DAYS:-35}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

if ! [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || (( RETENTION_DAYS < 1 )); then
    echo "RETENTION_DAYS must be a positive integer." >&2
    exit 2
fi

RETENTION_MINUTES=$((RETENTION_DAYS * 1440))
deleted=0

delete_old_files() {
    local directory="$1"
    local pattern="$2"

    [[ -d "$directory" ]] || return 0

    while IFS= read -r -d '' file; do
        if (( DRY_RUN )); then
            printf 'Would delete: %s\n' "$file"
        else
            printf 'Deleting: %s\n' "$file"
            rm -- "$file"
        fi
        deleted=$((deleted + 1))
    done < <(
        find "$directory" \
            -type f \
            -name "$pattern" \
            -mmin "+${RETENTION_MINUTES}" \
            -print0
    )
}

# Per-run debug logs are timestamped and otherwise unbounded.
delete_old_files "$ROOT/logs/runs" "*.log"

# TIDAL matched/unmatched reports are timestamped and otherwise accumulate.
# Keep the legacy '=' pattern so reports created before CP025 still age out.
delete_old_files "$ROOT/reports" "tidal-matched=*.csv"
delete_old_files "$ROOT/reports" "tidal-matched-*.csv"
delete_old_files "$ROOT/reports" "tidal-unmatched-*.csv"

if (( DRY_RUN )); then
    echo "Dry run complete: $deleted file(s) eligible for deletion."
else
    echo "Housekeeping complete: $deleted file(s) deleted."
fi

exit 0
