# AEGISSTOR — Deployment & Local Production Guide (`DEPLOYMENT.md`)

## 1. Local Docker Compose Deployment (PostgreSQL + Redis + Backend + Frontend)
1. Copy `.env.example` to `.env` and set strong values for `SECRET_KEY`, `POSTGRES_PASSWORD`, and optional `AEGISSTOR_BOOTSTRAP_ADMIN_*`:
   ```bash
   cp .env.example .env
   ```
2. Launch all containers:
   ```bash
   docker compose up --build -d
   ```
   - `postgres:16-alpine` runs on port `5432` with persistent volume `aegisstor_pgdata`.
   - `redis:7-alpine` runs on port `6379`.
   - Backend runs on port `8000` (`AEGISSTOR_MODE=live`, `AEGISSTOR_SEED_SYNTHETIC_DEMO=false`) with `/api/v1/health` healthcheck.
   - Frontend serves built production assets via Nginx on port `3000`.
3. Open `http://localhost:3000/setup` to bootstrap the initial Administrator account (if `AEGISSTOR_BOOTSTRAP_ADMIN_*` env vars were not set).

## 2. Standalone Local Development Run (SQLite)
### Backend
```powershell
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
# Optional local-dev synthetic accounts ONLY (never use in production):
python -m scripts.seed_dev_users
python run.py
```
### Frontend
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## 3. Cloud Deployment (Render + Vercel)
- **Backend (`render.yaml`)**: Deploy FastAPI + PostgreSQL with `DATABASE_URL`, `SECRET_KEY` (32+ chars), `AEGISSTOR_COOKIE_SECURE=true`, `AEGISSTOR_MODE=live`, `AEGISSTOR_SEED_SYNTHETIC_DEMO=false`, and health check `/api/v1/health`.
- **Frontend (`vercel.json`)**: Build Vite SPA (`npm run build` -> `dist/`) with `/api/:path*` rewrite or `VITE_API_BASE_URL` pointing to your Render backend HTTPS origin.
