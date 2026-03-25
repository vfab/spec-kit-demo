#!/usr/bin/env bash
# restore_db.sh — Download a PostgreSQL backup from Cloudflare R2 and restore it.
#
# Required environment variables:
#   DATABASE_URL        PostgreSQL connection string
#   R2_BUCKET           Cloudflare R2 bucket name
#   R2_ENDPOINT_URL     Cloudflare R2 endpoint URL
#   AWS_ACCESS_KEY_ID   R2 API key ID
#   AWS_SECRET_ACCESS_KEY  R2 API secret key
#
# Usage:
#   ./scripts/restore_db.sh backup_20260324T020000.dump
#
# ⚠️  WARNING: This will OVERWRITE the target database — it cannot be undone!

set -euo pipefail

# ---------------------------------------------------------------------------
# Validate argument
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <backup-key>" >&2
    echo "Example: $0 backup_20260324T020000.dump" >&2
    echo "" >&2
    echo "To list available backups:" >&2
    echo "  aws s3 ls s3/\$R2_BUCKET/backups/ --endpoint-url \$R2_ENDPOINT_URL" >&2
    exit 1
fi

BACKUP_KEY="$1"

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
# Confirm destructive operation
# ---------------------------------------------------------------------------
echo ""
echo "WARNING: This will overwrite ${DATABASE_URL}."
echo "All existing data will be replaced with the backup: ${BACKUP_KEY}"
echo ""
printf "Type YES to continue: "
read -r CONFIRM

if [[ "$CONFIRM" != "YES" ]]; then
    echo "Restore aborted." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Download backup from R2
# ---------------------------------------------------------------------------
TMPFILE="/tmp/${BACKUP_KEY}"
echo "Downloading s3://${R2_BUCKET}/backups/${BACKUP_KEY} ..."
aws s3 cp \
    "s3://${R2_BUCKET}/backups/${BACKUP_KEY}" \
    "$TMPFILE" \
    --endpoint-url "$R2_ENDPOINT_URL" || {
    echo "ERROR: Download failed. Check that the backup key exists." >&2
    exit 1
}
echo "Download complete: $(du -sh "$TMPFILE" | cut -f1)"

# ---------------------------------------------------------------------------
# Restore database
# ---------------------------------------------------------------------------
echo "Restoring database..."
pg_restore \
    --clean \
    --no-owner \
    --if-exists \
    -d "$DATABASE_URL" \
    "$TMPFILE" || {
    echo "ERROR: pg_restore failed." >&2
    rm -f "$TMPFILE"
    exit 1
}
echo "Restore complete."

# ---------------------------------------------------------------------------
# Post-restore verification: print row counts for key tables
# ---------------------------------------------------------------------------
echo ""
echo "Post-restore row counts:"
psql "$DATABASE_URL" -c "
SELECT
    'products_product'   AS table_name, COUNT(*) AS rows FROM products_product
UNION ALL
SELECT 'accounts_user',                 COUNT(*)         FROM auth_user
UNION ALL
SELECT 'orders_order',                  COUNT(*)         FROM orders_order;
" 2>/dev/null || echo "(psql not available — skipping row count verification)"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
rm -f "$TMPFILE"
echo ""
echo "Database restore from ${BACKUP_KEY} completed successfully."
