# AEGISSTOR — Production Deployment Guide (Phases 2 & 14)

## 1. Service Architecture Map

| Service | Platform | Entrypoint / Build | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend (`aegisstor-frontend`)** | Vercel | `cd frontend && npm run build` -> `dist/` | React/Vite SPA, connects via `VITE_API_BASE_URL` |
| **Backend API (`aegisstor-backend`)** | Render Web Service | `cd backend && pip install -r requirements.txt && python -m alembic upgrade head` -> `python run.py` | FastAPI + Uvicorn + WebSockets (`/health/ready`) |
| **Background Worker (`aegisstor-worker`)** | Render Background Worker | `cd backend && pip install -r requirements.txt` -> `python worker.py` | Async ML training, stale job recovery, heartbeats |
| **Database (`aegisstor-db`)** | Render Managed PostgreSQL | PostgreSQL 16+ (`sslmode=require`) | Authoritative state, outbox events, tasks, audit logs |
| **Event Bus (`aegisstor-redis`)** | Render Key Value (Redis) | Managed Redis | Cross-instance WebSocket Pub/Sub fan-out |
| **Object Storage** | S3-Compatible (R2 / S3) | `OBJECT_STORAGE_BUCKET` | Durable `.joblib` ML models, PDF reports, uploads |

---

## 2. Step-by-Step Deployment

### A. Database & Migrations
1. Provision separate Staging and Production Managed PostgreSQL databases.
2. Run migrations before starting new instances:
   ```bash
   cd backend
   python -m alembic upgrade head
   ```

### B. Render Backend + Worker + Redis (`render.yaml`)
1. Connect the GitHub repository (`DileepKumarPallapu/Predictive-Storage-Management`) in Render Blueprints using `render.yaml`.
2. Set `sync: false` secrets in Render Dashboard (`OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ENDPOINT_URL`, `OBJECT_STORAGE_ACCESS_KEY_ID`, `OBJECT_STORAGE_SECRET_ACCESS_KEY`).
3. Verify `ENVIRONMENT=production`, `AEGISSTOR_ALLOW_DEV_SEED=false`, `AEGISSTOR_COOKIE_SECURE=true`, `AEGISSTOR_COOKIE_SAMESITE=none`.
4. Confirm `/health/ready` returns `200 OK` with `database.connected=true` and `worker.status=healthy`.

### C. Vercel Frontend (`vercel.json`)
1. Import `frontend/` (or repo root with Root Directory = `frontend`) in Vercel.
2. Set `VITE_API_BASE_URL=https://<your-render-backend>.onrender.com/api/v1`.
3. Add the Vercel production domain to `CORS_ALLOWED_ORIGINS` on Render.
4. Complete initial Administrator onboarding at `/setup` (or via `AEGISSTOR_BOOTSTRAP_ADMIN_*` env vars on first boot).

## 3. Current Deployment Status in This Session
- **Local Verification:** Verified on `http://127.0.0.1:5173` + `http://127.0.0.1:8000` + `worker.py`.
- **Cloud Deployment (Vercel / Render / Managed PG / S3):** **BLOCKED_BY_CREDENTIALS** (`vercel`, `render`, `gh`, `psql` CLIs are not installed/authenticated in this environment).
