# AEGISSTOR CERBERUS — Operational Runbook & Local Execution Guide

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** CERBERUS-RUNBOOK-001  
**Target Environment:** Local Workstation (Windows / Linux / macOS)  

---

## 1. Prerequisites

| Component | Minimum Required | Tested Version | Status |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10.0 | 3.13.14 (64-bit) | Compatible |
| **Node.js** | v18.0.0 | v24.14.1 | Compatible |
| **npm** | 9.0.0 | 11.11.0 | Compatible |
| **Git** | 2.30.0 | 2.40+ | Clean working tree |
| **Operating System** | Windows 10/11 or Ubuntu 20.04+ | Windows 11 Enterprise | Supported |

---

## 2. Clean Environment Setup Instructions

### Step 1: Virtual Environment Creation
```bash
# From repository root
python -m venv env

# Activate virtual environment
# Windows:
.\env\Scripts\activate
# Linux/macOS:
source env/bin/activate

# Install locked dependencies
pip install -r backend/requirements.txt
```

### Step 2: Database Initialization & Seeding
```bash
# Run standalone seeder to create tables and generate deterministic telemetry
python scripts/seed_demo_data.py
```
*Note: SQLite database will be initialized at `backend/aegisstor.db` ($10.45\,\text{MB}$).*

---

## 3. Server Startup Commands

### Start the Backend Server (Port 8000)
```bash
cd backend
python run.py
```
*Verification URL:* `http://127.0.0.1:8000/api/v1/health`  
*API Swagger Documentation:* `http://127.0.0.1:8000/docs`

### Start the Frontend Dev Server (Port 5173)
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
*Dashboard URL:* `http://127.0.0.1:5173`

---

## 4. Verification & Health Checks

### Test 1: Quick Backend & Frontend Health Probe
```bash
python -c "import urllib.request; print('Backend Health:', urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').read().decode()); print('Frontend Status:', urllib.request.urlopen('http://127.0.0.1:5173').status)"
```

### Test 2: Run the 10-Step Mission 11 Demonstration Flow
```bash
python scripts/test_cerberus_demo.py
```

### Test 3: Run the 120-Test Backend Suite
```bash
python -m pytest backend/tests -v
```

---

## 5. Troubleshooting Guide

| Symptom / Error | Root Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'app'` | Running pytest from root without pythonpath | Ensure `pytest.ini` is present at root, or invoke via `python -m pytest backend/tests`. |
| `sqlite3.OperationalError: no such table: devices` | Relative SQLite path invoked from wrong directory | Hardened in `database.py` to always target `backend/aegisstor.db`. Run `python scripts/seed_demo_data.py` if database is unseeded. |
| `Port 8000 already in use` | Existing backend daemon running | Check task list (`manage_task list`) or terminate the background process using port 8000. |
| `HTTP 422 on /api/v1/scenarios` | Missing required `name` field in JSON payload | Pass `'name': '...'` in scenario creation dictionary. |

---

## 6. Clean Shutdown Instructions

- **Backend:** Press `Ctrl + C` in the backend terminal window or kill the background task.
- **Frontend:** Press `Ctrl + C` in the frontend dev server terminal window.
- **Environment:** Run `deactivate` to exit the Python virtual environment.
