# Backup & Restore Runbook

This runbook documents the database backup and restore procedures for ShopHub.
Backups are stored in Cloudflare R2 (S3-compatible, 10 GB free tier).

---

## Trigger a manual backup

Ensure the following environment variables are set, then run:

```bash
DATABASE_URL="postgresql://user:pass@host:5432/shophub" \
R2_BUCKET="shophub-backups" \
R2_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com" \
AWS_ACCESS_KEY_ID="<r2-key-id>" \
AWS_SECRET_ACCESS_KEY="<r2-secret-key>" \
./scripts/backup_db.sh
```

On success the script prints:
```
Starting backup: backup_20260324T020000.dump
Running pg_dump...
pg_dump complete: 12M
Uploading to s3://shophub-backups/backups/backup_20260324T020000.dump ...
Upload complete.
Pruning backups older than 7 days...
Backup complete: backup_20260324T020000.dump
```

On failure it exits with code 1 and prints an error to stderr.

---

## Verify backup was created

List recent backups in R2:

```bash
aws s3 ls s3://$R2_BUCKET/backups/ \
    --endpoint-url "$R2_ENDPOINT_URL" \
    | sort | tail -10
```

---

## Restore procedure

```bash
./scripts/restore_db.sh backup_20260324T020000.dump
```

The script will:
1. Download the backup from R2 to `/tmp/`
2. Prompt: `WARNING: This will overwrite $DATABASE_URL. Type YES to continue:`
3. Run `pg_restore --clean --no-owner` against the target database
4. Print row counts for key tables as a verification step

**Full walkthrough:**

```
$ ./scripts/restore_db.sh backup_20260324T020000.dump
Downloading s3://shophub-backups/backups/backup_20260324T020000.dump ...
Download complete: /tmp/backup_20260324T020000.dump

WARNING: This will overwrite postgresql://....  Type YES to continue: YES

Restoring from /tmp/backup_20260324T020000.dump ...
Restore complete.

Row counts after restore:
  products_product : 42
  accounts_user    : 18
  orders_order     : 103
```

---

## Verify restore

Expected post-restore row counts (update after each major data migration):

| Table | Expected rows (approx.) |
|-------|------------------------|
| `products_product` | ≥ 1 |
| `accounts_user` | ≥ 1 |
| `orders_order` | ≥ 0 |

Check manually if needed:
```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM products_product;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM accounts_user;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM orders_order;"
```

---

## Automated daily backup

The `.github/workflows/backup.yml` workflow runs daily at **02:00 UTC** via:

```yaml
schedule:
  - cron: "0 2 * * *"
```

It SSHs into the production VM and runs `./scripts/backup_db.sh` with R2 credentials
injected as environment variables from GitHub Secrets/Variables.

Required GitHub configuration:

| Type | Name | Value |
|------|------|-------|
| Secret | `FLY_API_TOKEN` | Fly.io deploy token |
| Secret | `R2_ACCESS_KEY_ID` | Cloudflare R2 key ID |
| Secret | `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret |
| Variable | `FLY_PRODUCTION_APP` | `shophub` |
| Variable | `R2_BUCKET` | `shophub-backups` |
| Variable | `R2_ENDPOINT_URL` | `https://<id>.r2.cloudflarestorage.com` |

If the backup job fails, GitHub Actions marks the workflow run as failed and sends
an email notification to the repository owner (satisfies FR-039 alert-on-failure).

To re-run a failed backup manually:
- Navigate to **GitHub → Actions → Automated Database Backup → Re-run jobs**

---

## What to do if backup storage is full or unavailable

1. **Check Cloudflare R2 dashboard** for storage usage. Free tier limit: 10 GB.
2. **Prune old backups manually** (the script already prunes > 7 days automatically):
   ```bash
   aws s3 ls s3://$R2_BUCKET/backups/ --endpoint-url "$R2_ENDPOINT_URL" | \
     awk '{print $4}' | head -20 | xargs -I{} \
     aws s3 rm "s3://$R2_BUCKET/backups/{}" --endpoint-url "$R2_ENDPOINT_URL"
   ```
3. **If R2 is unavailable**, take a local backup:
   ```bash
   pg_dump --format=custom "$DATABASE_URL" -f "/tmp/emergency_backup_$(date +%Y%m%dT%H%M%S).dump"
   ```
   Then transfer to a safe location manually.
4. **Escalation**: If backups remain unavailable for > 24 hours, notify the team and
   consider pausing writes until storage is restored.
