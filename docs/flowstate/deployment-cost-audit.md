# AEGISSTOR FLOWSTATE — Deployment & Cost Audit (Prompt 16.0)
**Date**: October 2026  
**Target Environment**: Render.com Free Tier / Zero-Cost Hosting  
**Audit Status**: Complete Baseline Recorded  

---

## 1. Hosting Environment Constraints & Reality

Modern cloud free tiers (such as Render.com Free Web Service and Free Static Site) impose specific technical limitations:

| Platform Feature | Render Free Tier Specification | Architectural Impact on AEGISSTOR |
| :--- | :--- | :--- |
| **Frontend Type** | Static Site (Free) | Global CDN distribution; zero compute cost. Requires client-side routing fallback (`/* -> /index.html`). |
| **Backend Type** | Web Service (Free) | 512 MB RAM, 0.1 vCPU. Spins down after 15 minutes of inactivity; cold start delay 30-50s. |
| **Filesystem Durability** | **Ephemeral** | The local filesystem is wiped on every deploy or spin-down. **Local SQLite files are not persistent**. |
| **Listening Port** | Dynamic `$PORT` | Application must bind to `0.0.0.0:$PORT` (not hardcoded `127.0.0.1:8000`). |
| **Database Option** | Ephemeral or Free PostgreSQL | Render Free PostgreSQL expires after 30 days unless upgraded. |
| **External AI / APIs** | \$0.00 / Zero external calls | Must not require OpenAI, Anthropic, or external paid LLM tokens for basic operation. |

---

## 2. Low-Resource Architectural Design for Zero-Dollar Operation

To ensure the platform runs effortlessly on free compute (512 MB RAM):

1. **Decoupled Static Frontend**:
   - The React + Vite frontend compiles to pure static HTML/JS/CSS assets.
   - Deployed as a Render Static Site: 100% free, unlimited bandwidth, instant edge delivery, zero server RAM consumption.

2. **Lightweight FastAPI Backend Service**:
   - Runs via Uvicorn with single worker process (`--workers 1`), consuming ~65 MB RAM.
   - Binds to `0.0.0.0` using `os.getenv("PORT", 8000)`.

3. **Stateless Deterministic Demo Mode**:
   - When deployed without a paid persistent PostgreSQL database, the platform operates in **Idempotent Demo Mode** (`DEMO_MODE=true`).
   - The synthetic storage generator deterministically re-seeds realistic storage telemetry, workloads, and alert states on spin-up.
   - The UI clearly labels: `OPERATING IN DETERMINISTIC DEMO MODE — EPHEMERAL STORAGE`.
   - Never tricks the operator into believing ephemeral data is permanent hardware telemetry.

4. **Optional External PostgreSQL Support**:
   - If `DATABASE_URL` is provided (e.g. Supabase, Neon, or Render PostgreSQL), the backend connects seamlessly and runs Alembic/SQLAlchemy table creation.

---

## 3. Cost Projection Summary

| Resource | Service Type | Monthly Cost | Notes |
| :--- | :--- | :--- | :--- |
| Frontend Hosting | Render Static Site | **\$0.00** | Unlimited bandwidth, global CDN |
| Backend API | Render Free Web Service | **\$0.00** | 512 MB RAM, spins down on idle |
| Database | Ephemeral SQLite / Neon Free Postgres | **\$0.00** | Zero cost demonstration |
| External ML / LLM APIs | Pure local ML algorithms | **\$0.00** | Zero API keys required |
| **Total Platform Cost** | **Zero-Cost Deployment** | **\$0.00 / mo** | 100% free-tier compatible |
