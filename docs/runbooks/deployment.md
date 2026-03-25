# Deployment Runbook

This runbook covers staging and production deploy procedures for ShopHub on Fly.io.

---

## Trigger a staging deploy

Staging is deployed automatically whenever a push to `main` passes all CI checks.

**Flow:**
1. Push or merge to `main`
2. The `CI` workflow runs: quality → security → test matrix → E2E
3. On CI success, the `Deploy` workflow's `deploy-staging` job triggers automatically via `workflow_run`
4. Fly.io rolling deploy begins; migration release command runs first (`python manage.py migrate --noinput`)
5. Health-check gating: Fly.io shifts traffic only after `/health/` returns 200

To watch live:
```bash
flyctl logs --app shophub-staging -f
```

---

## Trigger a production deploy

Production requires manual approval via the GitHub environment protection rule.

1. Navigate to **GitHub → Actions → Deploy** workflow
2. The `deploy-production` job pauses waiting for a reviewer listed under the `production` environment
3. An authorised reviewer clicks **Review deployments → Approve**
4. `flyctl deploy --remote-only --app shophub` runs; migration release command runs first
5. Rolling deploy with health-check gating

Or trigger the whole deploy manually (staging + production):
- Click **Run workflow** on the `Deploy` workflow and select `main`

---

## Monitor deploy progress

```bash
# Staging
flyctl logs --app shophub-staging -f

# Production
flyctl logs --app shophub -f

# Health check status
curl https://shophub-staging.fly.dev/health/
curl https://shophub.fly.dev/health/
```

---

## Rollback procedure

### List releases
```bash
flyctl releases list --app shophub
```

### Roll back to a specific version
```bash
flyctl releases rollback <version-number> --app shophub
```

### Roll back to a specific image
```bash
flyctl deploy --image registry.fly.io/shophub:<previous-tag> --app shophub
```

After rollback, confirm the health check passes:
```bash
curl https://shophub.fly.dev/health/
```

---

## Run migrations manually (emergency)

Use only when the release command has failed and migrations must be applied while the app is running:

```bash
flyctl ssh console --app shophub -C "python manage.py migrate --noinput"
```

For staging:
```bash
flyctl ssh console --app shophub-staging -C "python manage.py migrate --noinput"
```

---

## Known irreversible migrations

| Migration | Date | Reason |
|-----------|------|--------|
| *(none yet)* | — | — |

Before authoring a squash migration, update this table with any destructive changes
(column drops, table deletions, data transforms without a backward path).

---

## Zero-downtime guarantee

ShopHub uses Fly.io's **rolling deploy** strategy:

1. A new VM is started with the new image
2. The `release_command` (`python manage.py migrate --noinput`) runs once before any traffic shifts
3. Fly.io's http health check polls `/health/` every 30 s with a 10 s grace period
4. Traffic is only routed to a new VM after it passes the health check
5. Old VMs are terminated after successful handover

This means that as long as migrations are backward-compatible (new columns are nullable or have defaults), zero downtime is guaranteed.

---

## Monitoring

UptimeRobot monitors the production health endpoint every **5 minutes**.

- Monitor URL: `https://uptimerobot.com/dashboard` (login required)
- Alert contact: operator email configured at account setup
- Target: `GET https://shophub.fly.dev/health/` → 200

If UptimeRobot cannot reach the endpoint for two consecutive checks (10 minutes), an alert email is sent.
