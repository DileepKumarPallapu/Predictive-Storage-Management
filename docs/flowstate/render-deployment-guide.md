# AEGISSTOR FLOWSTATE — Render.com Zero-Cost Deployment Guide
**Module**: FLOWSTATE Free-Tier Cloud Deployment  
**Version**: 16.0  
**Status**: Verified with `render.yaml` Blueprint  

---

## 1. Prerequisites

- A free account on [Render.com](https://render.com).
- Forked or pushed Git repository containing `render.yaml`.
- No credit card or paid services required.

---

## 2. Deploying via Render Blueprint (Recommended)

1. Log in to your Render Dashboard.
2. Click **New +** $\to$ **Blueprint**.
3. Connect your repository containing `render.yaml`.
4. Render automatically parses `render.yaml` and provisions two zero-cost services:
   - **`aegisstor-frontend`** (Static Site): Global edge CDN, unlimited bandwidth, pre-configured SPA client rewrites (`/* -> /index.html`).
   - **`aegisstor-backend`** (Web Service): Python FastAPI service, auto-linked to frontend via `VITE_API_BASE_URL`.
5. Click **Apply**.
6. Deployment will complete in ~3-4 minutes.

---

## 3. Manual Step-by-Step Configuration (Alternative)

If you prefer deploying services individually:

### Backend (Web Service)
- **Environment**: Python 3
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python run.py`
- **Health Check Path**: `/api/v1/health`
- **Environment Variables**:
  - `AEGISSTOR_MODE`: `demo`
  - `DATABASE_URL`: `sqlite:///./aegisstor.db` (or external PostgreSQL connection string)
  - `SHADOW_MODE_ENABLED`: `true`
  - `SECRET_KEY`: `<generate-a-secure-random-string>`

### Frontend (Static Site)
- **Environment**: Static
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
- **Rewrite Rule**: `Source: /*` $\to$ `Destination: /index.html`
- **Environment Variables**:
  - `VITE_API_BASE_URL`: `https://your-backend-name.onrender.com/api/v1`

---

## 4. Verification & Health Check

After deployment, test your public URL:
```bash
# Verify backend health and synthetic storage generator status
curl https://your-backend-name.onrender.com/api/v1/health

# Output:
# {"status":"ok","version":"1.0.0","mode":"demo","database":"connected","models_loaded":5}
```
Open your frontend URL in any desktop or mobile browser. The Ember Noir interface loads instantly with full deterministic storage fleet telemetry.
