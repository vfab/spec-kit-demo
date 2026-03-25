#!/usr/bin/env bash
# backup_db.sh — Create a PostgreSQL backup and upload it to Cloudflare R2.
#
# Required environment variables:
#   DATABASE_URL        PostgreSQL connection string
#   R2_BUCKET           Cloudflare R2 bucket name
#   R2_ENDPOINT_URL     Cloudflare R2 endpoint URL
#   AWS_ACCESS_KEY_ID   R2 API key ID
#   AWS_SECRET_ACCESS_KEY  R2 API secret key
#
# Usage:
#   DATABASE_URL=... R2_BUCKET=... R2_ENDPOINT_URL=... \
#   AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \
#   ./scripts/backup_db.sh
#
# On failure: exits 1 and prints an error message (satisfies FR-039)

set -euo pipefail

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------
check_var() {
    local var_name="$1"
    if [[ -z "${!var_name:-}" ]]; then
        echo "ERROR: Required environment variable '${var_name}' is not set." >&2
        exit 1
    fi
}

check_var DATABASE_URL
check_var R2_BUCKET
check_var R2_ENDPOINT_URL
check_var AWS_ACCESS_KEY_ID
check_var AWS_SECRET_ACCESS_KEY

# ---------------------------------------------------------------------------
# Generate backup filename with timestamp
# ---------------------------------------------------------------------------
FILENAME="backup_$(date +%Y%m%dT%H%M%S).dump"
TMPFILE="/tmp/${FILENAME}"

echo "Starting backup: ${FILENAME}"

# ---------------------------------------------------------------------------
# Run pg_dump
# ---------------------------------------------------------------------------
echo "Running pg_dump..."
pg_dump --format=custom "$DATABASE_URL" -f "$TMPFILE" || {
    echo "ERROR: pg_dump failed." >&2
    exit 1
}
echo "pg_dump complete: $(du -sh "$TMPFILE" | cut -f1)"

# ---------------------------------------------------------------------------
# Upload to Cloudflare R2
# ---------------------------------------------------------------------------
echo "Uploading to s3://${R2_BUCKET}/backups/${FILENAME} ..."
aws s3 cp "$TMPFILE" "s3://${R2_BUCKET}/backups/${FILENAME}" \
    --endpoint-url "$R2_ENDPOINT_URL" || {
    echo "ERROR: Upload to R2 failed." >&2
    rm -f "$TMPFILE"
    exit 1
}
echo "Upload complete."

# ---------------------------------------------------------------------------
# Delete backups older than 7 days (7-day retention policy)
# ---------------------------------------------------------------------------
echo "Pruning backups older than 7 days..."
CUTOFF=$(date -d "-7 days" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || echo "")

if [[ -n "$CUTOFF" ]]; then
    # List all objects in backups/ prefix and filter by LastModified
    aws s3api list-objects \
        --bucket "$R2_BUCKET" \
        --prefix "backups/" \
        --endpoint-url "$R2_ENDPOINT_URL" \
        --query "Contents[?LastModified<='${CUTOFF}'].Key" \
        --output text 2>/dev/null | tr '\t' '\n' | \
    while read -r key; do
        [[ -z "$key" || "$key" == "None" ]] && continue
        echo "  Deleting old backup: ${key}"
        aws s3api delete-object \
            --bucket "$R2_BUCKET" \
            --key "$key" \
            --endpoint-url "$R2_ENDPOINT_URL" || true
    done
fi

# ---------------------------------------------------------------------------
# Cleanup and report success
# ---------------------------------------------------------------------------
rm -f "$TMPFILE"
echo "Backup complete: ${FILENAME}"
