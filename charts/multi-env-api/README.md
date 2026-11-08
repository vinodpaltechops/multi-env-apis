# multi-env-api Helm chart

One chart for all environments. Differences live only in `values-dev.yaml`,
`values-staging.yaml` and `values-prod.yaml`. Identity/endpoint values (client id,
tenant, DB server, ALB id, hostname, AGC subnet CIDR) are **not** in the repo; the
deploy workflow passes them with `--set` from GitHub Environment variables.

Required at install time:

| Value | Source |
|---|---|
| `image.repository`, `image.digest` | pipeline (image is always referenced by digest) |
| `workloadIdentity.clientId`, `.tenantId` | env var `WORKLOAD_IDENTITY_CLIENT_ID`, `AZURE_TENANT_ID` |
| `app.db.server`, `app.db.name` | env vars `DB_SERVER`, `DB_NAME` |
| `gateway.albId`, `.frontendName`, `.hostname` | env vars `ALB_ID`, `AGC_FRONTEND`, `APP_HOSTNAME` |
| `networkPolicy.ingressCidrs` | env var `AGC_SUBNET_CIDR` |
| `keyVault.name`, `.tenantId` | only if `keyVault.objects` is non-empty |

## Zero-downtime design
- RollingUpdate `maxUnavailable: 0`, `maxSurge: 25%`; startup/readiness/liveness probes.
- `/readyz` checks the database; `/healthz` never does (a DB blip must not restart pods).
- preStop `sleep` 15s (lets AGC drop the endpoint) + uvicorn graceful drain 25s = 40s < `terminationGracePeriodSeconds` 45s.
- PodDisruptionBudget, zone + node topology spread, HPA (staging min 2, prod min 3).

## Secrets
Never in values files. Key Vault objects listed in `keyVault.objects` are mounted as
files under `/mnt/secrets` through a `SecretProviderClass` using the pod's Workload
Identity. The default DB auth is Entra token auth, so no DB password exists at all.

## Database migrations — must be backward compatible
`alembic upgrade head` runs in a **pre-install/pre-upgrade Helm hook Job** before the new
pods roll out. During the rollout (and after any `helm rollback`) the *previous* app
version runs against the *new* schema. Therefore every migration must follow
**expand/contract**:

1. **Expand** (release N): add nullable columns/new tables/indexes; never drop or rename in-use objects; keep old code working.
2. **Migrate/backfill** and switch the code to the new schema (release N+1).
3. **Contract** (release N+2, only after N+1 is fully rolled out and rollback to N is no longer needed): drop old columns/tables.

Never combine destructive changes with the code that stops using them in one release.
Because the Job is a hook, a failed migration fails the upgrade before any pod is replaced.
The ServiceAccount and SecretProviderClass are also hooks (weight -10) so the Job can run
on first install; they are re-created on each upgrade and not removed by `helm uninstall`.

## Local checks
```
helm lint charts/multi-env-api -f charts/multi-env-api/values-dev.yaml $(cat ci/lint-set.txt)
```
See `.github/workflows/pr.yml` for the exact `--set` flags used in CI.
