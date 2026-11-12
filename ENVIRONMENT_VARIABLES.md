# AEGISSTOR — Environment Variables Reference

Templates are provided in `.env.local.example`, `.env.staging.example`, and `.env.production.example`. Never commit real secrets.

| Variable | Required in Prod | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Yes | `local`, `staging`, or `production` |
| `AEGISSTOR_MODE` | Yes | `demo`, `replay`, or `live` |
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql://...`) |
| `DB_SSL_MODE` | Recommended | `require` for managed PostgreSQL TLS |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | Optional | SQLAlchemy pool size (defaults `10` / `20`) |
| `REDIS_URL` | Recommended | Managed Redis URL (`rediss://...`) for multi-instance WS Pub/Sub |
| `SECRET_KEY` | **Yes** | >=32-char cryptographic secret (`validate_production_safety` enforces) |
| `CORS_ALLOWED_ORIGINS` | **Yes** | Comma-separated Vercel/custom origins (cannot be `*` in prod) |
| `AEGISSTOR_COOKIE_SECURE` | Yes | `true` in staging/production HTTPS |
| `AEGISSTOR_COOKIE_SAMESITE` | Yes | `none` for cross-origin Vercel + Render, `lax` for same-origin |
| `AEGISSTOR_ALLOW_DEV_SEED` | Yes | Must be `false` in staging/production |
| `OBJECT_STORAGE_BUCKET` | Recommended | S3/R2 bucket for durable ML artifacts & PDF reports |
| `OBJECT_STORAGE_ENDPOINT_URL` | Optional | S3-compatible endpoint (e.g. Cloudflare R2) |
| `OBJECT_STORAGE_ACCESS_KEY_ID` | With Bucket | S3 access key ID |
| `OBJECT_STORAGE_SECRET_ACCESS_KEY` | With Bucket | S3 secret access key |
| `PROMETHEUS_URL` | Optional | Prometheus Node Exporter HTTP/HTTPS endpoint |
| `PROMETHEUS_BEARER_TOKEN` | Optional | Bearer token if Prometheus endpoint is authenticated |
| `PROMETHEUS_TLS_VERIFY` | Optional | `true` (default) or `false` |
| `VITE_API_BASE_URL` | Yes (Frontend) | Full backend API base URL (`https://<backend>/api/v1`) |
